from aws_cdk import Stack, aws_wafv2 as wafv2
from aws_cdk.aws_elasticloadbalancingv2 import IApplicationLoadBalancer
from constructs import Construct
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from helpers.config_loader import load_yaml_config
from helpers.waf_rule_builder import build_managed_rules
from helpers.vpc_lookup import get_vpc_id

class WAFStack(Stack):
    def __init__(
            self, 
            scope: Construct, 
            id: str,
            **kwargs
            ):
        super().__init__(scope, id, **kwargs)

        config = load_yaml_config("config/waf/waf.yml")
        acl_cfg = config["web_acl"]

        web_acl = wafv2.CfnWebACL(
            self, "WAF",
            scope="REGIONAL",
            default_action=wafv2.CfnWebACL.DefaultActionProperty(allow={}),
            visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                sampled_requests_enabled=True,
                cloud_watch_metrics_enabled=True,
                metric_name=acl_cfg["metric_name"]
            ),
            name=acl_cfg["name"],
            rules=build_managed_rules(acl_cfg["rules"])
        )

        alb = IApplicationLoadBalancer.from_lookup(self, "ALB", load_balancer_arn=config['alb_arn'])

        wafv2.CfnWebACLAssociation(
            self, "WAFALBAssociation",
            resource_arn=alb.load_balancer_arn,
            web_acl_arn=web_acl.attr_arn
        )
