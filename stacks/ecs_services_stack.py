from aws_cdk import (
    Stack,
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_ecr as ecr,
    aws_secretsmanager as secretsmanager,
    aws_logs as logs
)
from constructs import Construct
from aws_cdk.aws_ecs import LogDrivers


class ECSServicesStack(Stack):
    def __init__(
            self, 
            scope: Construct, 
            id: str, 
            vpc, 
            cluster, 
            **kwargs
            ):
        
        super().__init__(scope, id, **kwargs)

        self.backend_service = self._create_service("backend", cluster, container_port=3000)
        self.frontend_service = self._create_service("frontend", cluster, container_port=80)


    def _create_service(
            self, 
            name: str, 
            cluster: ecs.Cluster, 
            container_port: int
            ) -> ecs.Ec2Service:
        
        JWT_SECRET = secretsmanager.Secret.from_secret_name_v2(
            self, "JWTSecret", "JWT_SECRET"
        )

        JWT_EXPIRES_IN = secretsmanager.Secret.from_secret_name_v2(
            self, "JWTExpiresIn", "JWT_EXPIRES_IN"
        )

        DEFAULT_AVATAR = secretsmanager.Secret.from_secret_name_v2(
            self, "DefaultAvatar", "DEFAULT_AVATAR"
        )

        repo = ecr.Repository.from_repository_name(self, f"{name.capitalize()}Repo", name)

        log_group = logs.LogGroup(self, f"{name.capitalize()}LogGroup")

        task_def = ecs.Ec2TaskDefinition(self, f"{name.capitalize()}TaskDef")

        container = task_def.add_container(
            f"{name.capitalize()}Container",
            image=ecs.ContainerImage.from_ecr_repository(repo, tag="latest"),
            secrets={
                "JWT_SECRET": ecs.Secret.from_secrets_manager(JWT_SECRET),
                "JWT_EXPIRES_IN": ecs.Secret.from_secrets_manager(JWT_EXPIRES_IN),
                "DEFAULT_AVATAR": ecs.Secret.from_secrets_manager(DEFAULT_AVATAR)
            },
            memory_reservation_mib=256,
            cpu=256,
            essential=True,
            logging=LogDrivers.aws_logs(
                stream_prefix=name,
                log_group=log_group
            )
        )

        container.add_port_mappings(
            ecs.PortMapping(container_port=container_port)
        )

        return ecs.Ec2Service(
            self, f"{name.capitalize()}Service",
            cluster=cluster,
            task_definition=task_def,
            desired_count=1
        )
