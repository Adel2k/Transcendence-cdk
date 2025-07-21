from aws_cdk import (
    aws_ec2 as ec2
)
from constructs import Construct
from helpers.tools import tools

class VpcStack(tools):
    def __init__(
            self, 
            scope: Construct, 
            construct_id: str, 
            **kwargs
            ):

        super().__init__(scope, construct_id, **kwargs)

        config = self.load_yaml_config('config/vpcs/vpcs.yml')
        vpcs = config.get("vpcs", [])

        for vpc_def in vpcs:
            name = vpc_def["name"]
            subnet_defs = vpc_def.get("subnets", [])

            subnet_configs = [
                ec2.SubnetConfiguration(
                    name=subnet["name"],
                    subnet_type=ec2.SubnetType[subnet["type"]],
                    cidr_mask=subnet["cidr_mask"]
                )
                for subnet in subnet_defs
            ]

            logical_id = self.logical_id_generator(name, "vpc")

            vpc = ec2.Vpc(self, logical_id,
                vpc_name=logical_id,
                cidr=vpc_def["cidr"],
                max_azs=vpc_def.get("max_azs", 2),
                subnet_configuration=subnet_configs,
                nat_gateways=vpc_def.get("nat_gateways", 0),
                enable_dns_support=vpc_def.get("enable_dns_support", True),
                enable_dns_hostnames=vpc_def.get("enable_dns_hostnames", True),
                restrict_default_security_group=vpc_def.get("restrict_default_security_group", True)
            )

            self.store_ssm_parameter(
                f"{name}-vpc-id",
                f"/transendence/vpc-id/{name}",
                vpc.vpc_id
            )

            for i, subnet in enumerate(vpc.private_subnets, 1):
                self.store_ssm_parameter(
                    f"{name}-private-subnet-{i}",
                    f"/transendence/{name}/private-subnet-{i}",
                    subnet.subnet_id
                )

            for i, subnet in enumerate(vpc.public_subnets, 1):
                self.store_ssm_parameter(
                    f"{name}-public-subnet-{i}",
                    f"/transendence/{name}/public-subnet-{i}",
                    subnet.subnet_id
                )
