import os
import yaml
from aws_cdk import Stack
from aws_cdk import aws_route53 as route53
from aws_cdk import aws_route53_targets as targets
from aws_cdk.aws_elasticloadbalancingv2 import IApplicationLoadBalancer
from constructs import Construct
from helpers.config_loader import load_yaml_config

class Route53Stack(Stack):
    def __init__(
        self, 
        scope: Construct,
        id: str,
        **kwargs
    ):
        super().__init__(scope, id, **kwargs)
        config = load_yaml_config('config/route53/route53.yml')
        alb = IApplicationLoadBalancer.from_lookup(self, "ALB", load_balancer_arn=config['alb_arn'])
        domain_name = config['domain_name']
        subdomain = config['subdomain']

        hosted_zone = route53.HostedZone.from_lookup(
            self, "HostedZone",
            domain_name=domain_name
        )

        route53.ARecord(
            self, "AliasRecord",
            zone=hosted_zone,
            record_name=subdomain,  # Result: subdomain.domain_name
            target=route53.RecordTarget.from_alias(targets.LoadBalancerTarget(alb))
        )
