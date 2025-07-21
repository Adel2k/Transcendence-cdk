import os
import yaml
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ssm as ssm,
    CfnOutput
)
from constructs import Construct
from helpers.vpc_lookup import get_vpc_id
from helpers.config_loader import load_yaml_config


class ECSClusterStack(Stack):
    def __init__(
            self, 
            scope: Construct,
            id: str,
            **kwargs
        ):

        super().__init__(scope, id, **kwargs)
        full_config = load_yaml_config('config/ecs/cluster.yml')
        cluster_config = full_config["cluster"]


        vpc_name = full_config["vpc"]["name"]
        vpc_id = get_vpc_id(vpc_name)
        vpc = ec2.Vpc.from_lookup(self, "VpcImported", vpc_id=vpc_id)

        cluster_name = cluster_config["name"]
        instance_type = cluster_config["instance_type"]
        min_capacity = cluster_config["min_capacity"]
        max_capacity = cluster_config["max_capacity"]
        subnet_type_str = cluster_config.get("subnet_type", "PUBLIC").upper()

        subnet_type_map = {
            "PUBLIC": ec2.SubnetType.PUBLIC,
            "PRIVATE": ec2.SubnetType.PRIVATE_ISOLATED,
            "PRIVATE_WITH_EGRESS": ec2.SubnetType.PRIVATE_WITH_EGRESS,
        }
        subnet_type = subnet_type_map.get(subnet_type_str, ec2.SubnetType.PUBLIC)

        self.cluster = ecs.Cluster(self, "transendenceCluster",
            vpc=vpc,
            cluster_name=cluster_name
        )

        self.cluster.add_capacity(
            "DefaultAutoScalingGroup",
            instance_type=ec2.InstanceType(instance_type),
            min_capacity=min_capacity,
            max_capacity=max_capacity,
            vpc_subnets=ec2.SubnetSelection(subnet_type=subnet_type),
        )
        ssm.StringParameter(
            self, "ClusterNameParameter",
            parameter_name=f"/transendence/{cluster_name}",
            string_value=self.cluster.cluster_name
        )

        CfnOutput(self, "ClusterName", value=self.cluster.cluster_name)
