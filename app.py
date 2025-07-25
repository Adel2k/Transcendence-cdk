#!/usr/bin/env python3
import aws_cdk as cdk
from aws_cdk import Environment
from aws_cdk import aws_secretsmanager as secretsmanager
from aws_cdk import aws_route53 as route53
from aws_cdk import aws_ec2 as ec2
from stacks.vpcs.vpc_stack import VpcStack
from stacks.security_group.security_stack import SecurityStack
from stacks.s3.s3_stack import S3Stack
from stacks.ecs.ecs_services_stack import ECSServicesStack
from stacks.ecs.ecs_cluster_stack import ECSClusterStack
from stacks.alb.alb_stack import ALBStack
from stacks.acm.acm_stack import ACMStack
from stacks.waf.waf_stack import WAFStack
from stacks.roles.iam_stack import IAMStack
from stacks.pipelines.generic_pipeline import GenericPipelineStack

app = cdk.App()

env = Environment(account="577638398727", region="eu-west-2")
vpc_stack = VpcStack(
    app, 
    "vpc-stack", 
    env=env
    )

iam_stack = IAMStack(
    app, 
    "iam-stack", 
    env=env
    )

security_stack = SecurityStack(
    app, 
    "security-stack",
    env=env
    )

s3_stack = S3Stack(
    app, 
    "s3-stack", 
    env=env
    )

ecs_cluster_stack = ECSClusterStack(
    app, 
    "ecs-cluster-stack",
    env=env
    )

ecs_services_stack = ECSServicesStack(
    app,
    "ecs-services-stack",
    env=env
    )

# GenericPipelineStack(
#     app, 
#     "pipeline-stack",
#     env=env
# )

acm_stack = ACMStack(
    app,
    "acm-stack",
    env=env
)

alb_stack = ALBStack(
    app,
    "alb-stack",
    env=env
)


# # # waf_stack = WAFStack(
# # #     app,
# # #     "waf-stack",
# # #     env=env
# # # )

app.synth()
