import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as cpactions,
    aws_codebuild as codebuild,
    aws_iam as iam,
    aws_s3 as s3,
)
from constructs import Construct

class CodePipelineBackendStack(Stack):
    def __init__(self, scope: Construct, id: str, repo_name: str, branch: str = "main", **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        artifact_bucket = s3.Bucket(self, "PipelineArtifacts")

        source_output = codepipeline.Artifact()
        build_output = codepipeline.Artifact()

        build_project = codebuild.PipelineProject(
            self, "BackendBuild",
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_7_0
            ),
        )

        pipeline = codepipeline.Pipeline(
            self, "BackendPipeline",
            artifact_bucket=artifact_bucket,
        )

        pipeline.add_stage(
            stage_name="Source",
            actions=[
                cpactions.GitHubSourceAction(
                    action_name="GitHub_Source",
                    owner="Adel2k",
                    repo=repo_name,
                    branch=branch,
                    oauth_token=cdk.SecretValue.secrets_manager("github-token"),
                    output=source_output,
                )
            ]
        )

        pipeline.add_stage(
            stage_name="Build",
            actions=[
                cpactions.CodeBuildAction(
                    action_name="Build",
                    project=build_project,
                    input=source_output,
                    outputs=[build_output],
                )
            ]
        )
