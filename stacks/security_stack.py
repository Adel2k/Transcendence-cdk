from aws_cdk import (
    Stack,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_ecr_assets as ecr_assets,
    aws_rds as rds,
    aws_secretsmanager as secretsmanager,
    aws_ec2 as ec2,
    aws_ssm as ssm,
    CfnOutput
)
from constructs import Construct
import os

class SecurityStack(Stack):

    def __init__(self, scope: Construct, id: str,vpc: ec2.Vpc, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        self.vpc = vpc

        prj_name = self.node.try_get_context("transendence")
        env_name = self.node.try_get_context("env")

        self.lambda_sg = ec2.SecurityGroup(self, 'lambdasg',
            security_group_name='lambda-sg',
            vpc=vpc,
            description="SG for Lambda Functions",
            allow_all_outbound=True
        )
        
        self.bastion_sg = ec2.SecurityGroup(self, 'bastionsg',
            security_group_name='bastion-sg',
            vpc=vpc,
            description="SG for Bastion Host",
            allow_all_outbound=True
        )

        self.bastion_sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(22), "SSH Access")
        
        redis_sg = ec2.SecurityGroup(self, 'redissg',
            security_group_name='redis-sg',
            vpc=vpc,
            description="SG for Redis Cluster",
            allow_all_outbound=True
        )
        redis_sg.add_ingress_rule(self.lambda_sg, ec2.Port.tcp(6379), 'Access from Lambda functions')

        self.ecs_sg = ec2.SecurityGroup(
        self, "TranscendenceSG",
        vpc=self.vpc,
        description="Allow HTTP and HTTPS",
        allow_all_outbound=True
        )

        self.ecs_sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(80), "Allow HTTP")
        self.ecs_sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(443), "Allow HTTPS")

        CfnOutput(self, "VpcId", value=self.vpc.vpc_id)
        CfnOutput(self, "SecurityGroupId", value=self.ecs_sg.security_group_id)