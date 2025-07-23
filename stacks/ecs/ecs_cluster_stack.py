from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ssm as ssm,

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
            name = cluster_cfg["name"]
            cluster_name = f"{cluster_cfg["name"]}-cluster"
            instance_type = cluster_cfg["instance_type"]
            min_capacity = cluster_cfg["min_capacity"]
            max_capacity = cluster_cfg["max_capacity"]
            security_group = cluster_cfg.get("security_group")
            subnet_type_str = cluster_cfg.get("subnet_type", "PUBLIC").upper()
            vpc_name = cluster_cfg["vpc"]

            try:
                vpc_id = self.get_vpc_id(vpc_name)
                vpc = ec2.Vpc.from_lookup(
                    self, 
                    self.logical_id_generator(name, vpc_name, aws_service),
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
            ssm_path_sg = self.generate_ssm_parameter_path(name, security_group, "security-group")
            sg_id = ssm.StringParameter.value_for_string_parameter(
                self,
                ssm_path_sg
            )

            imported_sg = ec2.SecurityGroup.from_security_group_id(
                self,
                self.logical_id_generator(name, sg_id, ssm_path_sg),
                security_group_id=sg_id
            )
            self.clusters[cluster_name] = cluster
            asg = cluster.add_capacity(
                self.logical_id_generator(name, "AddCapacity", aws_service),
                instance_type=ec2.InstanceType(instance_type),
                min_capacity=min_capacity,
                max_capacity=max_capacity,
                vpc_subnets=ec2.SubnetSelection(subnet_type=subnet_type)
            )

            asg.add_security_group(imported_sg)

            ssm_path = self.generate_ssm_parameter_path(name, service_name=None, aws_service="cluster")
            self.store_ssm_parameter(
                self.logical_id_generator(name, "StoreCluster", aws_service),
                ssm_path, 
                cluster.cluster_name
            )

            CfnOutput(
                self, 
                self.logical_id_generator(cluster_name, "output", aws_service), 
                value=cluster.cluster_name
            )