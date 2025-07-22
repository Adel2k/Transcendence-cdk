from aws_cdk import (
    aws_iam as iam,
)
from constructs import Construct
from helpers.tools import tools


class IAMStack(tools):
    def __init__(
            self,
            scope: Construct,
            id: str,
            **kwargs
        ):

        super().__init__(scope, id, **kwargs)

        config = self.load_yaml_config('config/roles/iam.yml')
        self.roles = {}

        for role_def in config.get("roles", []):
            role_name = role_def["name"]
            app_name = role_def["app_name"]
            service = role_def["service"]
            description = role_def.get("description", role_name)

            role = iam.Role(
                self, f"{role_name}-{service}-role",
                role_name=f"tmp-{role_name}",
                assumed_by=iam.ServicePrincipal(service),
                description=description
            )

            for policy_name in role_def.get("managed_policies", []):
                role.add_managed_policy(
                    iam.ManagedPolicy.from_aws_managed_policy_name(policy_name)
                )

            self.store_ssm_parameter(
                f"{role_name}-arn",
                self.generate_ssm_parameter_path(app_name, role_name, "role"),
                role.role_arn
            )

            self.roles[role_name] = role
