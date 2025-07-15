from aws_cdk import (
    Stack,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as cpactions,
    aws_codebuild as codebuild,
    aws_ecr as ecr,
    aws_iam as iam,
    aws_s3 as s3,
    aws_codecommit as codecommit,
    aws_secretsmanager as secretsmanager,
    aws_ecs as ecs,
)
from constructs import Construct

class PipelineStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # Retrieve GitHub token from Secrets Manager
        github_token_secret = secretsmanager.Secret.from_secret_name_v2(
            self, "GithubTokenSecret", "github-token"
        )

        # ECR repositories
        backend_ecr = ecr.Repository.from_repository_name(self, "BackendECR", "backend")
        frontend_ecr = ecr.Repository.from_repository_name(self, "FrontendECR", "frontend")

        # Artifact buckets
        artifact_bucket = s3.Bucket(self, "PipelineArtifacts")

        # CodeBuild projects
        backend_build = codebuild.PipelineProject(
            self, "BackendBuild",
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
                privileged=True  # Needed for Docker
            ),
            environment_variables={
                "REPOSITORY_URI": codebuild.BuildEnvironmentVariable(value=backend_ecr.repository_uri)
            }
        )
        backend_ecr.grant_pull_push(backend_build.role)

        frontend_build = codebuild.PipelineProject(
            self, "FrontendBuild",
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
                privileged=True
            ),
            environment_variables={
                "REPOSITORY_URI": codebuild.BuildEnvironmentVariable(value=frontend_ecr.repository_uri)
            }
        )
        frontend_ecr.grant_pull_push(frontend_build.role)

        # Pipeline
        pipeline = codepipeline.Pipeline(
            self, "TranscendencePipeline",
            artifact_bucket=artifact_bucket
        )

        # Artifacts
        backend_source_output = codepipeline.Artifact()
        frontend_source_output = codepipeline.Artifact()
        backend_build_output = codepipeline.Artifact()
        frontend_build_output = codepipeline.Artifact()

        # Source stage using GitHub
        pipeline.add_stage(
            stage_name="Source",
            actions=[
                cpactions.GitHubSourceAction(
                    action_name="BackendSource",
                    owner="adelll42",
                    repo="backend-repo",
                    branch="main",
                    oauth_token=github_token_secret.secret_value,
                    output=backend_source_output
                ),
                cpactions.GitHubSourceAction(
                    action_name="FrontendSource",
                    owner="adelll42",
                    repo="frontend-repo",
                    branch="main",
                    oauth_token=github_token_secret.secret_value,
                    output=frontend_source_output
                )
            ]
        )

        # Build stage
        pipeline.add_stage(
            stage_name="Build",
            actions=[
                cpactions.CodeBuildAction(
                    action_name="BackendBuild",
                    project=backend_build,
                    input=backend_source_output,
                    outputs=[backend_build_output]
                ),
                cpactions.CodeBuildAction(
                    action_name="FrontendBuild",
                    project=frontend_build,
                    input=frontend_source_output,
                    outputs=[frontend_build_output]
                )
            ]
        )

        # Deploy stage (after Build stage)
        pipeline.add_stage(
            stage_name="Deploy",
            actions=[
                cpactions.EcsDeployAction(
                    action_name="DeployBackend",
                    service=backend_service,  # Reference to your ECS backend service
                    input=backend_build_output
                ),
                cpactions.EcsDeployAction(
                    action_name="DeployFrontend",
                    service=frontend_service,  # Reference to your ECS frontend service
                    input=frontend_build_output
                )
            ]
        )

        # You can add more stages or actions as needed
