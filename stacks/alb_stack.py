from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_elasticloadbalancingv2 as elbv2,
    aws_certificatemanager as acm,
    aws_ssm as ssm,
    aws_ecs as ecs,
)
from constructs import Construct

from helpers.tools import tools

class ALBStack(tools):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        config = self.load_yaml_config('config/alb/alb.yml')

        vpc_id = self.get_vpc_id(config["vpc"]["name"])
        vpc = ec2.Vpc.from_lookup(self, f"{vpc_id}VpcImported-ALBStack", vpc_id=vpc_id)

        cert_param = ssm.StringParameter.from_string_parameter_attributes(
            self, "ImportedCertParam",
            parameter_name=config["certificate"]["ssm_param"],
            simple_name=False
        )
        self.create_route53_record(self)
        cert_arn = cert_param.string_value
        certificate = acm.Certificate.from_certificate_arn(self, "ImportedCert", cert_arn)

        cluster = ecs.Cluster.from_cluster_attributes(
            self, "ClusterImported",
            cluster_name=config["cluster"]["name"],
            vpc=vpc
        )

        services = {}
        for svc in config["alb"]["services"]:
            name = svc["name"]
            service_name = ssm.StringParameter.value_for_string_parameter(
                self, svc["ecs_service_ssm_param"]
            )
            services[name] = ecs.Ec2Service.from_ec2_service_attributes(
                self, f"{name.capitalize()}ServiceImported",
                cluster=cluster,
                service_name=service_name
            )

        self.alb = elbv2.ApplicationLoadBalancer(
            self, config['alb']['name'],
            vpc=vpc,
            internet_facing=True
        )

        self.target_groups = {
            tg_name: self.create_target_group(self, f"{tg_name.capitalize()}TG", vpc, cfg)
            for tg_name, cfg in config['alb']['target_groups'].items()
        }

        if config.get('redirect_http', True):
            self.add_http_redirect_listener(self, self.alb)

        self.https_listener = self.add_https_listener(
            self, self.alb, certificate, config['alb']['routing'], self.target_groups
        )

        ssm.StringParameter(
            self, "ALBEndpoint",
            parameter_name=config["alb"]["endpoint_ssm"],
            string_value=self.alb.load_balancer_dns_name
        )
