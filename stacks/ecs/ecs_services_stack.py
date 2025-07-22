from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecr as ecr,
    aws_secretsmanager as secretsmanager,
    aws_logs as logs,
    aws_iam as iam,
)
from constructs import Construct
from aws_cdk.aws_ecs import LogDrivers
from helpers.tools import tools


class ECSServicesStack(tools):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        config = self.load_yaml_config('config/ecs/services.yml')

        services = config.get("services", [])
        if not services:
            raise ValueError("No ECS services defined in config.")

        for svc in services:
            name = svc["name"]
            cluster_name = svc["cluster"]
            vpc_name = svc["vpc"]
            task_role_arn = svc["ecs_task_role_arn"]
            secrets_manager_name = svc.get("secrets_manager_name")
            secret_keys = svc.get("secrets", [])

            vpc_id = self.get_vpc_id(vpc_name)
            vpc = ec2.Vpc.from_lookup(
                self, 
                self.logical_id_generator(cluster_name, vpc_name, name), 
                vpc_id=vpc_id)

            cluster = ecs.Cluster.from_cluster_attributes(
                self,
                self.logical_id_generator(cluster_name, name, "cluster"),
                cluster_name=cluster_name,
                vpc=vpc
            )

            task_role = iam.Role.from_role_arn(
                self, 
                self.logical_id_generator(cluster_name, name, "task-role"),
                role_arn=task_role_arn
            )

            self._create_service(
                name=name,
                repo_name=svc["repo"],
                port=svc["port"],
                cluster=cluster,
                task_role=task_role,
                secret_manager_name=secrets_manager_name,
                secret_keys=secret_keys
            )

    def _create_service(self, name, repo_name, port, cluster, task_role, secret_manager_name, secret_keys):
        container_secrets = {}
        if secret_manager_name and secret_keys:
            secret = secretsmanager.Secret.from_secret_name_v2(
                self, self.logical_id_generator(cluster.cluster_name ,name,"secret"), secret_manager_name
            )
            container_secrets = {
                key: ecs.Secret.from_secrets_manager(secret, field=key)
                for key in secret_keys
            }

        repo = ecr.Repository.from_repository_name(
            self, 
            self.logical_id_generator(cluster.cluster_name, name, "repo"),
            repo_name
        )

        log_group = logs.LogGroup(self, f"{name}LogGroup")

        task_def = ecs.Ec2TaskDefinition(
            self, 
            self.logical_id_generator(cluster.cluster_name, name, "taskdef"),
            task_role=task_role
        )

        container = task_def.add_container(
            self.logical_id_generator(cluster.cluster_name, name, "container"),
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

        service = ecs.Ec2Service(
            self, 
            self.logical_id_generator(cluster.cluster_name, name, "service"),
            cluster=cluster,
            task_definition=task_def,
            desired_count=1,
            service_name=name,
        )

        
        self.store_ssm_parameter(
            self.logical_id_generator(cluster.cluster_name, name, "TaskDefARN"),
            self.generate_ssm_parameter_path(cluster.cluster_name, name, "task-definition"),
            task_def.task_definition_arn
        )

        self.store_ssm_parameter(
            self.logical_id_generator(cluster.cluster_name, name, "ServiceARN"),
            self.generate_ssm_parameter_path(cluster.cluster_name, name, "service"),
            service.service_arn
        )
