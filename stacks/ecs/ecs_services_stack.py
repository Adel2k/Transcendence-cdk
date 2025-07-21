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
    aws_ssm as ssm,
    aws_elasticloadbalancingv2 as elbv2,
    CfnOutput
)
from constructs import Construct
from aws_cdk.aws_ecs import LogDrivers
from helpers.tools import tools

class ECSServicesStack(tools):
    def __init__(
        self,
        scope: Construct,
        id: str,
        **kwargs
    ):
        super().__init__(scope, id, **kwargs)

        service_configs = self.load_yaml_config('config/ecs/services.yml')["services"]

        if not isinstance(service_configs, list):
            raise TypeError("ECS services configuration must be a list of service definitions under 'services' key.")

        self.services = {}

        main_alb_listener = None
        try:
            listener_arn_param_name = f"/{cluster_name}/alb/main-listener-arn"
            main_alb_listener_arn = ssm.StringParameter.value_for_string_parameter(self, listener_arn_param_name)
            main_alb_listener = elbv2.ApplicationListener.from_listener_arn(
                self, f"{cluster_name}-MainAlbListenerImport", main_alb_listener_arn
            )
        except Exception as e:
            print(f"CRITICAL ERROR: Could not find main ALB Listener. Please ensure it's deployed and its ARN is in SSM parameter '{listener_arn_param_name}'. Error: {e}")

        for svc_cfg in service_configs:
            service_name = svc_cfg["name"]
            repo_name = svc_cfg["repo"]
            cluster_name = svc_cfg["cluster"]
            container_port = svc_cfg["port"]
            target_group_name = svc_cfg["target_group"]

            vpc_name = svc_cfg["vpc"]
            task_role_arn = svc_cfg["ecs_task_role_arn"]

            try:
                vpc_id = self.get_vpc_id(vpc_name)
                vpc = ec2.Vpc.from_lookup(self, self.logical_id_generator(cluster_name, f"{service_name}-VpcImported"), vpc_id=vpc_id)
            except Exception as e:
                print(f"Error looking up VPC '{vpc_name}' for service '{service_name}': {e}")
                continue

            cluster = ecs.Cluster.from_cluster_attributes(
                self, self.logical_id_generator(cluster_name, f"{service_name}-EcsClusterImport"),
                cluster_name=cluster_name,
                vpc=vpc
            )

            task_role = iam.Role.from_role_arn(
                self, self.logical_id_generator(cluster_name, f"{service_name}-EcsTaskRole"),
                role_arn=task_role_arn
            )

            secret_manager_name = svc_cfg.get("secrets_manager_name")
            secret_fields = svc_cfg.get("secrets", [])

            self._create_service(
                name=service_name,
                repo_name=repo_name,
                port=container_port,
                secret_fields=secret_fields,
                cluster=cluster,
                secret_manager_name=secret_manager_name if secret_manager_name else None,
                task_role=task_role,
                vpc=vpc,
                alb_listener=main_alb_listener
            )

    def _create_service(self, name, repo_name, port, secret_fields, cluster, task_role, secret_manager_name, vpc, alb_listener):

        container_secrets = {}
        if secret_manager_name:
            try:
                secret = secretsmanager.Secret.from_secret_name_v2(
                    self, self.logical_id_generator(name, "ServiceSecretLookup"), secret_manager_name
                )

                task_role.add_to_policy(iam.PolicyStatement(
                    actions=["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"],
                    resources=[secret.secret_full_arn]
                ))

                for key in secret_fields:
                    container_secrets[key] = ecs.Secret.from_secrets_manager(secret, field=key)
            except Exception as e:
                print(f"Warning: Could not load secret '{secret_manager_name}' for service '{name}'. Error: {e}")
        else:
            print(f"Info: No secrets_manager_name specified for service '{name}'. Skipping secret injection.")


        repo = ecr.Repository.from_repository_name(
            self, self.logical_id_generator(name, "Repo"), repo_name
        )

        log_group = logs.LogGroup(self, self.logical_id_generator(name, "LogGroup"))

        task_def = ecs.FargateTaskDefinition(
            self, self.logical_id_generator(name, "TaskDef"),
            cpu=256,
            memory_mib=512,
            task_role=task_role,
            execution_role=task_role
        )

        container = task_def.add_container(
            self.logical_id_generator(name, "Container"),
            image=ecs.ContainerImage.from_ecr_repository(repo, tag="latest"),
            secrets=container_secrets,
            essential=True,
            logging=LogDrivers.aws_logs(
                stream_prefix=name,
                log_group=log_group
            )
        )

        container.add_port_mappings(
            ecs.PortMapping(container_port=port)
        )

        ecs_service = ecs.FargateService(
            self, self.logical_id_generator(name, "Service"),
            cluster=cluster,
            task_definition=task_def,
            desired_count=1,
            service_name=name,
            assign_public_ip=True
        )
        self.services[name] = ecs_service

        if alb_listener:
            target_group = elbv2.ApplicationTargetGroup(
                self, self.logical_id_generator(name, "TargetGroup"),
                port=port,
                vpc=vpc,
                protocol=elbv2.ApplicationProtocol.HTTP,
                targets=[ecs_service]
            )

            alb_listener.add_action(
                self.logical_id_generator(name, "ListenerRuleAction"),
                action=elbv2.ListenerAction.forward([target_group]),
                conditions=[elbv2.ListenerCondition.path_patterns([f"/{name}*", f"/{name.capitalize()}*"])]
            )

            CfnOutput(self, self.logical_id_generator(name, "ServiceURL"),
                value=f"http://{alb_listener.load_balancer.load_balancer_dns_name}/{name}/",
                description=f"URL for {name} service"
            )
        else:
            print(f"Warning: No ALB listener provided. Service '{name}' will not be publicly exposed via ALB.")

        self.store_ssm_parameter(
            f"/{self.app_name}/ecs/service/{name}/task-definition-arn",
            task_def.task_definition_arn
        )
        self.store_ssm_parameter(
            f"/{self.app_name}/ecs/service/{name}/service-arn",
            ecs_service.service_arn
        )