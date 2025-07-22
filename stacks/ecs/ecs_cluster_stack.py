from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    CfnOutput
)
from constructs import Construct
from helpers.tools import tools

class ECSClusterStack(tools):
    def __init__(
            self,
            scope: Construct,
            id: str,
            **kwargs
        ):

        super().__init__(scope, id, **kwargs)
        cluster_configs = self.load_yaml_config('config/ecs/cluster.yml').get("clusters", [])

        self.clusters = {}
        aws_service = "cluster"
        for cluster_cfg in cluster_configs:
            cluster_name = cluster_cfg["name"]
            instance_type = cluster_cfg["instance_type"]
            min_capacity = cluster_cfg["min_capacity"]
            max_capacity = cluster_cfg["max_capacity"]
            subnet_type_str = cluster_cfg.get("subnet_type", "PUBLIC").upper()
            vpc_name = cluster_cfg["vpc"]

            try:
                vpc_id = self.get_vpc_id(vpc_name)
                vpc = ec2.Vpc.from_lookup(
                    self, 
                    self.logical_id_generator(cluster_name, vpc_name, aws_service),
                    vpc_id=vpc_id
                )
            except Exception as e:
                print(f"Error looking up VPC '{vpc_name}': {e}")
                continue 

            subnet_type_map = {
                "PUBLIC": ec2.SubnetType.PUBLIC,
                "PRIVATE": ec2.SubnetType.PRIVATE_ISOLATED,
                "PRIVATE_WITH_EGRESS": ec2.SubnetType.PRIVATE_WITH_EGRESS,
            }
            subnet_type = subnet_type_map.get(subnet_type_str, ec2.SubnetType.PUBLIC)

            cluster = ecs.Cluster(
                self, 
                self.logical_id_generator(cluster_name, "Create", aws_service),
                vpc=vpc,
                cluster_name=cluster_name
            )
            self.clusters[cluster_name] = cluster
            cluster.add_capacity(
                self.logical_id_generator(cluster_name, "AddCapacity", aws_service),
                instance_type=ec2.InstanceType(instance_type),
                min_capacity=min_capacity,
                max_capacity=max_capacity,
                vpc_subnets=ec2.SubnetSelection(subnet_type=subnet_type),
            )
            ssm_path = self.generate_ssm_parameter_path(cluster_name, service_name=None, aws_service="cluster")
            self.store_ssm_parameter(
                self.logical_id_generator(cluster_name, "StoreCluster", aws_service),
                ssm_path, 
                cluster.cluster_name
            )

            CfnOutput(
                self, 
                self.logical_id_generator(cluster_name, "output", aws_service), 
                value=cluster.cluster_name
            )