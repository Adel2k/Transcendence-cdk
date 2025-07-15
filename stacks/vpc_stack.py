from aws_cdk import (
    Stack,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_ecr_assets as ecr_assets,
    aws_rds as rds,
    aws_secretsmanager as secretsmanager,
    aws_ec2 as ec2,
    aws_ssm as ssm
)
from constructs import Construct
import os

class VpcStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        prj_name = self.node.try_get_context("transendence")
        env_name = self.node.try_get_context("env")
        
        self.vpc = ec2.Vpc(self, 'transendenceVPC', 
                           ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
                           max_azs=2,
                           enable_dns_hostnames=True,
                           enable_dns_support=True,
                           subnet_configuration=[
                               ec2.SubnetConfiguration(
                                   name="Public",
                                   subnet_type=ec2.SubnetType.PUBLIC,
                                   cidr_mask=24
                               ),
                               ec2.SubnetConfiguration(
                                   name="Private",
                                   subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                                   cidr_mask=24
                               )
                           ],
                           nat_gateways=1
                           )
        
        priv_subnets = [subnet.subnet_id for subnet in self.vpc.private_subnets]

        count = 1
        for ps in priv_subnets:
            ssm.StringParameter(self, 'private-subnet-'+str(count),
                string_value=ps,
                parameter_name='/'+env_name+'/private-subnet-'+str(count)
            )
            count += 1