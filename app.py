#!/usr/bin/env python3
import aws_cdk as cdk

from stacks.vpc_stack import VpcStack
from stacks.security_stack import SecurityStack
from stacks.s3_stack import S3Stack
from stacks.codepipeline_backend import CodePipelineBackendStack
from stacks.ecs_cluster_stack import ECSClusterStack
from stacks.ecs_services_stack import ECSServicesStack
from stacks.pipeline_stack import PipelineStack
# Initialize the CDK application


app = cdk.App()

vpc_stack = VpcStack(app, "vpc")

security_stack = SecurityStack(app, "security-stack", vpc=vpc_stack.vpc)

codepipeline_backend_stack = CodePipelineBackendStack(
    app,
    "codepipeline-backend",
    repo_name="your-repo-name",
    branch="main"
) 

s3_stack = S3Stack(app, "s3-stack")

ecs_cluster_stack = ECSClusterStack(
    app,
    "ecs-cluster-stack",
    vpc=vpc_stack.vpc
)

ecs_services_stack = ECSServicesStack(
    app,
    "ecs-services-stack",
    vpc=vpc_stack.vpc,
    cluster=ecs_cluster_stack.cluster
)

pipeline_stack = PipelineStack(
    app,
    "pipeline-stack",
    vpc=vpc_stack.vpc,
    cluster=ecs_cluster_stack.cluster,
    backend_service=ecs_services_stack.backend_service,
    frontend_service=ecs_services_stack.frontend_service,
    github_token_secret=codepipeline_backend_stack.github_token_secret
)

# Synthesize the CDK application
app.synth()
