import os
import yaml
from aws_cdk import (
    Stack,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as cpactions,
    aws_codebuild as codebuild,
    aws_ecr as ecr,
    aws_iam as iam,
    aws_s3 as s3,
    aws_ec2 as ec2,
    aws_secretsmanager as secretsmanager,
    aws_ecs as ecs
)
from constructs import Construct
from aws_cdk import aws_ssm as ssm
from helpers.vpc_lookup import get_vpc_id
from helpers.config_loader import load_yaml_config

####for stages is there a way to use one automation for all the stages?
class GenericPipelineStack(Stack):
    def __init__(
            self, 
            scope: Construct, 
            id: str, 
            **kwargs
        ):
        super().__init__(scope, id, **kwargs)
        config = load_yaml_config('config/pipelines/pipelines.yml')
        vpc_name = config["vpc"]["name"]
        vpc_id = get_vpc_id(vpc_name)
        vpc = ec2.Vpc.from_lookup(self, "VpcImported", vpc_id=vpc_id)

        cluster_name = config["cluster"]["name"]

        cluster = ecs.Cluster.from_cluster_attributes(
            self, "ClusterImported",
            cluster_name=cluster_name,
            vpc=vpc
        )

        for pipeline_def in config["pipelines"]:
            service_name = ssm.StringParameter.value_for_string_parameter(
                self, pipeline_def["ecs_service_ssm_param"]
            )
            service = ecs.Ec2Service.from_ec2_service_attributes(
                self, f"{pipeline_def['name'].capitalize()}ServiceImported",
                cluster=cluster,
                service_name=service_name
            )

            self._create_pipeline(
                name=pipeline_def["name"],
                github=pipeline_def["github"],
                ecr_repo_name=pipeline_def["ecr_repo"],
                image_def_file=pipeline_def["image_definition_file"],
                service=service
            )

    def _create_pipeline(self, name, github, ecr_repo_name, image_def_file, service):
        secret = secretsmanager.Secret.from_secret_name_v2(
            self, f"{name.capitalize()}GitHubToken", github["secret_name"]
        )

        repo = ecr.Repository.from_repository_name(
            self, f"{name.capitalize()}Repo", ecr_repo_name
        )

        bucket = s3.Bucket(self, f"{name.capitalize()}PipelineArtifacts")

        pipeline = codepipeline.Pipeline(self, f"{name.capitalize()}Pipeline", artifact_bucket=bucket)

        source_output = codepipeline.Artifact(f"{name}SourceOutput")
        build_output = codepipeline.Artifact(f"{name}BuildOutput")

        pipeline.add_stage(
            stage_name="Source",
            actions=[
                cpactions.GitHubSourceAction(
                    action_name=f"{name.capitalize()}Source",
                    owner=github["owner"],
                    repo=github["repo"],
                    branch=github["branch"],
                    oauth_token=secret.secret_value_from_json(github["secret_name"]),
                    output=source_output
                )
            ]
        )

        build_project = codebuild.PipelineProject(
            self, f"{name.capitalize()}BuildProject",
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
                privileged=True
            ),
            environment_variables={
                "REPOSITORY_URI": codebuild.BuildEnvironmentVariable(value=repo.repository_uri)
            }
        )
        repo.grant_pull_push(build_project.role)

        pipeline.add_stage(
            stage_name="Build",
            actions=[
                cpactions.CodeBuildAction(
                    action_name=f"{name.capitalize()}Build",
                    project=build_project,
                    input=source_output,
                    outputs=[build_output]
                )
            ]
        )

        pipeline.add_stage(
            stage_name="Deploy",
            actions=[
                cpactions.EcsDeployAction(
                    action_name=f"Deploy{name.capitalize()}",
                    service=service,
                    image_file=codepipeline.ArtifactPath(build_output, image_def_file)
                )
            ]
        )
