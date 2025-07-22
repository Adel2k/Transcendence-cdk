from aws_cdk import (
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as cpactions,
    aws_codebuild as codebuild,
    aws_ecr as ecr,
    aws_ec2 as ec2,
    aws_secretsmanager as secretsmanager,
    aws_ecs as ecs,
)
from constructs import Construct
from helpers.tools import tools


class GenericPipelineStack(tools):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        config = self.load_yaml_config('config/pipelines/pipelines.yml')

        aws_service = "pipelineStack"

        for pipeline_def in config["pipelines"]:
            stages = pipeline_def.get("stages", [])
            cluster_name = pipeline_def["cluster"]
            vpc_name = pipeline_def["vpc"]

            vpc_id = self.get_vpc_id(vpc_name)
            vpc = ec2.Vpc.from_lookup(self, f"{cluster_name}-{pipeline_def["name"]}-VpcImported-{aws_service}", vpc_id=vpc_id)

            cluster = ecs.Cluster.from_cluster_attributes(
                self, f"{cluster_name}-{pipeline_def["name"]}-ImportedCluster-{aws_service}",
                cluster_name=cluster_name,
                vpc=vpc
            )

            service = ecs.Ec2Service.from_ec2_service_attributes(
                self, f"{cluster_name}-{pipeline_def['name']}-ServiceImported-{aws_service}",
                cluster=cluster,
                service_name=pipeline_def["name"]
            )

            self._create_pipeline(
                name=pipeline_def["name"],
                stages=stages,
                github=pipeline_def["github"],
                ecr_repo_name=pipeline_def["ecr_repo"],
                image_def_file=pipeline_def["image_definition_file"],
                service=service
            )

                
    def _create_pipeline(self, name, stages, github, ecr_repo_name, image_def_file, service):
        pipeline = codepipeline.Pipeline(self, f"{name.capitalize()}Pipeline")

        secret = secretsmanager.Secret.from_secret_name_v2(
            self, f"{name.capitalize()}GitHubToken", github["secret_name"]
        )

        source_output = codepipeline.Artifact(f"{name}SourceOutput")
        build_output = codepipeline.Artifact(f"{name}BuildOutput")

        if "source" in stages:
            pipeline.add_stage(
                stage_name="Source",
                actions=[
                    cpactions.GitHubSourceAction(
                        action_name=f"{name.capitalize()}Source",
                        owner=github["owner"],
                        repo=github["repo"],
                        branch=github["branch"],
                        oauth_token=secret.secret_value,
                        output=source_output,
                        trigger=cpactions.GitHubTrigger.NONE
                    )
                ]
            )

        if "build" in stages:
            repo = ecr.Repository.from_repository_name(
                self, f"{name.capitalize()}Repo", ecr_repo_name
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

        if "deploy" in stages:
            pipeline.add_stage(
                stage_name="Deploy",
                actions=[
                    cpactions.EcsDeployAction(
                        action_name=f"Deploy{name.capitalize()}",
                        service=service,
                        image_file=codepipeline.ArtifactPath(
                            build_output if "build" in stages else source_output,
                            image_def_file
                        )
                    )
                ]
            )
