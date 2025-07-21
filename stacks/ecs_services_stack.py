import os
import yaml
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecr as ecr,
    aws_secretsmanager as secretsmanager,
    aws_logs as logs,
    aws_iam as iam,
    aws_ssm as ssm
)
from constructs import Construct
from aws_cdk.aws_ecs import LogDrivers
from helpers.vpc_lookup import get_vpc_id
from helpers.config_loader import load_yaml_config


class ECSServicesStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        **kwargs
    ):
        super().__init__(scope, id, **kwargs)

        config = load_yaml_config('config/ecs/services.yml')

        vpc_name = config["vpc"]["name"]
        vpc_id = get_vpc_id(vpc_name)
        vpc = ec2.Vpc.from_lookup(self, "VpcImported", vpc_id=vpc_id)

        cluster_name = config["cluster"]["name"]
        task_role_arn = config["roles"]["ecs_task_role_arn"]

        cluster = ecs.Cluster.from_cluster_attributes(
            self, "ClusterImported",
            cluster_name=cluster_name,
            vpc=vpc
        )

        task_role = iam.Role.from_role_arn(
            self, "ImportedTaskRole",
            role_arn=task_role_arn
        )

        for svc in config["services"]:
            self._create_service(
                name=svc["name"],
                repo_name=svc["repo"],
                port=svc["port"],
                secret_fields=svc.get("secrets") or {},
                cluster=cluster,
                task_role=task_role
            )

    def _create_service(self, name, repo_name, port, secret_fields, cluster, task_role):
        secret = secretsmanager.Secret.from_secret_name_v2(
            self, f"{name}Secret", "JWT_EXPIRES_IN/JWT_SECRET/DEFAULT_AVATAR"
        )
        container_secrets = {}
        container_secrets = {
            key: ecs.Secret.from_secrets_manager(secret, field=key)
            for key in ["JWT_EXPIRES_IN", "JWT_SECRET", "DEFAULT_AVATAR", "DATABASE_URL"]
        }



        repo = ecr.Repository.from_repository_name(
            self, f"{name.capitalize()}Repo", repo_name
        )

        log_group = logs.LogGroup(self, f"{name.capitalize()}LogGroup")

        task_def = ecs.Ec2TaskDefinition(
            self, f"{name.capitalize()}TaskDef",
            task_role=task_role
        )

        container = task_def.add_container(
            f"{name.capitalize()}Container",
            image=ecs.ContainerImage.from_ecr_repository(repo, tag="latest"),
            secrets=container_secrets,
            memory_reservation_mib=256,
            cpu=256,
            essential=True,
            logging=LogDrivers.aws_logs(
                stream_prefix=name,
                log_group=log_group
            )
        )


        container.add_port_mappings(
            ecs.PortMapping(container_port=port)
        )

        ecs.Ec2Service(
            self, f"{name.capitalize()}Service",
            cluster=cluster,
            task_definition=task_def,
            desired_count=1,
            service_name=name,
        )

        ssm.StringParameter(
            self, f"{name.capitalize()}ServiceSSMParam",
            parameter_name=f"/transendence/ecs/services/{name}/service_name",
            string_value=name
        )
