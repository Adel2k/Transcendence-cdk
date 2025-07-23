from aws_cdk import ( aws_ec2 as ec2, CfnOutput
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
                self, self.logical_id_generator(app_name, vpc_name, name),
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
            for rule in config.get("ingress", []):
                if "source_sg" in rule:
                    source = rule["source_sg"]
                    if self.sg_lookup.get(source):
                        sg.connections.allow_from(
                            self.sg_lookup[source],
                            ec2.Port(protocol=rule["protocol"], string_representation=rule.get("description", ""), from_port=rule["port"], to_port=rule["port"])
                        )
                    else:
                        sg.connections.allow_from(
                            ec2.Peer.ipv4(source),
                            ec2.Port(protocol=rule["protocol"], string_representation=rule.get("description", ""), from_port=rule["port"], to_port=rule["port"])
                        )
            ssm_path = self.generate_ssm_parameter_path(app_name, name, "security-group")
            logical_id = self.logical_id_generator(app_name, name, "security-group")

            self.store_ssm_parameter(
                logical_id,
                parameter_name=ssm_path,
                string_value=self.sg_lookup[sg_def["name"]].security_group_id
            )


        if "ecs-sg" in self.sg_lookup:
            CfnOutput(self, "SecurityGroupId", value=self.sg_lookup["ecs-sg"].security_group_id)
        if "db-sg" in self.sg_lookup:
            CfnOutput(self, "DBSecurityGroupId", value=self.sg_lookup["db-sg"].security_group_id)
