from aws_cdk import (
    Stack,
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_ecr as ecr,
)
from constructs import Construct

class ECSServicesStack(Stack):
    def __init__(self, scope: Construct, id: str, vpc: ec2.Vpc, cluster: ecs.Cluster, **kwargs):
        super().__init__(scope, id, **kwargs)

        # Reference ECR repositories
        backend_repo = ecr.Repository.from_repository_name(self, "BackendRepo", "backend")
        frontend_repo = ecr.Repository.from_repository_name(self, "FrontendRepo", "frontend")

        # Backend Task Definition
        backend_task_def = ecs.Ec2TaskDefinition(self, "BackendTaskDef")
        backend_task_def.add_container(
            "BackendContainer",
            image=ecs.ContainerImage.from_ecr_repository(backend_repo, tag="latest"),
            memoryLimitMiB=512,
            cpu=256,
            essential=True
        )

        # Frontend Task Definition
        frontend_task_def = ecs.Ec2TaskDefinition(self, "FrontendTaskDef")
        frontend_task_def.add_container(
            "FrontendContainer",
            image=ecs.ContainerImage.from_ecr_repository(frontend_repo, tag="latest"),
            memoryLimitMiB=512,
            cpu=256,
            essential=True
        )

        # Backend Service
        backend_service = ecs.Ec2Service(
            self, "BackendService",
            cluster=cluster,
            task_definition=backend_task_def,
            desired_count=1
        )

        # Frontend Service
        frontend_service = ecs.Ec2Service(
            self, "FrontendService",
            cluster=cluster,
            task_definition=frontend_task_def,
            desired_count=1
        )