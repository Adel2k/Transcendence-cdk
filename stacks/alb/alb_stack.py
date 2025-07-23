from aws_cdk import (
    aws_elasticloadbalancingv2 as elbv2,
    aws_certificatemanager as acm,
    aws_ssm as ssm,
    aws_ecs as ecs,
)
import aws_cdk.aws_ec2 as ec2
from constructs import Construct
from helpers.tools import tools
from aws_cdk.aws_elasticloadbalancingv2_targets import InstanceIdTarget


class ALBStack(tools):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        full_config = self.load_yaml_config('config/alb/alb.yml')

        for config in full_config.get("alb", []):
            alb_name = config["name"]
            vpc_id = self.get_vpc_id(config["vpc"])
            vpc = ec2.Vpc.from_lookup(self, f"{alb_name}-VpcImported", vpc_id=vpc_id)

            cluster = ecs.Cluster.from_cluster_attributes(
                self, f"{alb_name}ClusterImported",
                cluster_name=f"{config["cluster"]}-cluster",
                vpc=vpc
            )

            services = {}
            for svc in config["services"]:

                name = svc["name"]
                ssm_path = self.generate_ssm_parameter_path(cluster.cluster_name, name, aws_service="service")
                service_name = ssm.StringParameter.value_for_string_parameter(
                    self,
                    ssm_path
                )
                services[name] = ecs.Ec2Service.from_ec2_service_attributes(
                    self, self.logical_id_generator(cluster.cluster_name, alb_name, name),
                    cluster=cluster,
                    service_name=service_name
                )

            alb = elbv2.ApplicationLoadBalancer(
                self, alb_name,
                vpc=vpc,
                internet_facing=True
            )

            target_groups = {
                tg_name: self.create_target_group(f"{alb_name}-{tg_name}-TG", vpc, cfg)
                for tg_name, cfg in config['target_groups'].items()
            }
                    
            for instance_cfg in config.get("instances", []):
                instance_id = instance_cfg["id"]
                for target in instance_cfg.get("targets", []):
                    tg_name = target["group"]
                    port = target["port"]
                    tg = target_groups.get(tg_name)
                    if tg:
                        tg.add_target(InstanceIdTarget(instance_id, port=port))
                    if config.get('redirect_http', True):
                        self.add_http_redirect_listener(alb, alb_name)


            certificate = None
            if "certificate" in config and config["certificate"]:
                ssm_path = self.generate_ssm_parameter_path(
                    config["certificate"], None, aws_service="certificate"
                )
                cert_param = ssm.StringParameter.from_string_parameter_attributes(
                    self,
                    self.logical_id_generator(cluster.cluster_name, alb_name, "CertParam"),
                    parameter_name=ssm_path,
                    simple_name=False
                )
                cert_arn = cert_param.string_value
                certificate = acm.Certificate.from_certificate_arn(self, self.logical_id_generator(cluster.cluster_name, alb_name, ""), cert_arn)

            if certificate:
                self.add_https_listener(
                    alb, certificate, config['routing'], target_groups
                )
            ssm_path = self.generate_ssm_parameter_path(
                alb_name, None, aws_service="alb"
            )
            self.store_ssm_parameter(
                f"{alb_name}Endpoint",
                parameter_name=ssm_path,
                string_value=alb.load_balancer_dns_name
            )

            if "route53" in config:
                self.create_route53_record(
                    domain_name=config["route53"]["domain_name"],
                    subdomain=config["route53"]["subdomain"],
                    alb=alb
                )
