import os
import yaml
from aws_cdk import (
    Stack,
    aws_iam as iam,
)
from constructs import Construct
from aws_cdk import aws_ssm as ssm
from helpers.config_loader import load_yaml_config


class IAMStack(Stack):
    def __init__(
            self,
            scope: Construct,
            id: str,
            **kwargs
        ):

        super().__init__(scope, id, **kwargs)

        config = load_yaml_config('config/roles/iam.yml')
        self.roles = {}

        for role_def in config.get("roles", []):
            role_name = role_def["name"]
            service = role_def["service"]
            description = role_def.get("description", role_name)

            role = iam.Role(
                self, f"{role_name}-role",
                role_name=f"tmp-{role_name}",
                assumed_by=iam.ServicePrincipal(service),
                description=description
            )

            for policy_name in role_def.get("managed_policies", []):
                role.add_managed_policy(
                    iam.ManagedPolicy.from_aws_managed_policy_name(policy_name)
                )

            ssm.StringParameter(
                self, f"{role_name}-param",
                parameter_name=f"/transendence/roles/{role_name}/arn",
                string_value=role.role_arn
            )

            self.roles[role_name] = role
