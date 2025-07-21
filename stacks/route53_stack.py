import os
import yaml
from aws_cdk import Stack
from aws_cdk import aws_route53 as route53
from aws_cdk import aws_route53_targets as targets
from constructs import Construct
from aws_cdk.aws_elasticloadbalancingv2 import ApplicationLoadBalancer
from helpers.config_loader import load_yaml_config
import boto3

class Route53Stack(Stack):
    def __init__(
        self, 
        scope: Construct,
        id: str,
        **kwargs
    ):
        super().__init__(scope, id, **kwargs)
        config = load_yaml_config('config/route53/route53.yml')["route53"]
        alb_name = config['alb_arn']
        ssm = boto3.client("ssm")
        alb_arn = ssm.get_parameter(Name=f"/{alb_name}/alb/arn")["Parameter"]["Value"]

        alb = ApplicationLoadBalancer.from_lookup(self, "ALB", load_balancer_arn=alb_arn)

        domain_name = config['domain_name']
        subdomain = config['subdomain']

        hosted_zone = route53.HostedZone.from_lookup(
            self, "HostedZone",
            domain_name=domain_name
        )

        route53.ARecord(
            self, "AliasRecord",
            zone=hosted_zone,
            record_name=subdomain,  
            target=route53.RecordTarget.from_alias(targets.LoadBalancerTarget(alb))
        )
