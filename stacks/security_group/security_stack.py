import os
import yaml
from aws_cdk import (
    Stack, aws_ec2 as ec2, CfnOutput
)
from constructs import Construct
from helpers.tools import tools

class SecurityStack(tools):
    def __init__(
            self,
            scope: Construct,
            id: str,
            **kwargs
        ):
        
        super().__init__(scope, id, **kwargs)

        self.sg_lookup = {}

        config = self.load_yaml_config('config/security_group/security_groups.yml')

        for sg_def in config["security_groups"]:
            name = sg_def["name"]
            vpc_name = sg_def["vpc"]
            app_name = sg_def["app_name"]
            vpc_id = self.get_vpc_id(vpc_name)
            self.vpc = ec2.Vpc.from_vpc_attributes(
                self, f"{name}-{vpc_id}-VpcImported-SecurityStack",
                vpc_id=vpc_id,
                availability_zones=self.availability_zones
            )
            sg = ec2.SecurityGroup(self, name,
                security_group_name=f"tmp-{name}",
                vpc=self.vpc,
                description=sg_def.get("description", name),
                allow_all_outbound=sg_def.get("allow_all_outbound", True)
            )
            self.sg_lookup[name] = sg

        for sg_def in config["security_groups"]:
            sg = self.sg_lookup[sg_def["name"]]
            for rule in sg_def.get("ingress", []):
                port = ec2.Port.tcp(rule["port"]) if rule["protocol"] == "tcp" else None
                desc = rule.get("description", "")
                if "source" in rule:
                    sg.add_ingress_rule(
                        peer=ec2.Peer.ipv4(rule["source"]),
                        connection=port,
                        description=desc
                    )
                elif "source_sg" in rule:
                    source_sg = self.sg_lookup[rule["source_sg"]]
                    sg.add_ingress_rule(
                        peer=source_sg,
                        connection=port,
                        description=desc
                    )

        if "ecs-sg" in self.sg_lookup:
            CfnOutput(self, "SecurityGroupId", value=self.sg_lookup["ecs-sg"].security_group_id)
        if "db-sg" in self.sg_lookup:
            CfnOutput(self, "DBSecurityGroupId", value=self.sg_lookup["db-sg"].security_group_id)
