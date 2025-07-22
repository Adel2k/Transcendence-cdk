from aws_cdk import aws_wafv2 as wafv2
from aws_cdk.aws_elasticloadbalancingv2 import IApplicationLoadBalancer
from constructs import Construct
from helpers.tools import tools
from aws_cdk import aws_ssm as ssm

class WAFStack(tools):
    def __init__(
            self, 
            scope: Construct, 
            id: str,
            **kwargs
            ):
        super().__init__(scope, id, **kwargs)

        config = self.load_yaml_config("config/waf/waf.yml")
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
            rules=self.build_managed_rules(acl_cfg["rules"])
        )
        alb_name = acl_cfg["alb_arn"]

        ssm_path = self.generate_ssm_parameter_path(alb_name, None, aws_service="alb")
        alb_arn = ssm.StringParameter.value_for_string_parameter(self, ssm_path)

        wafv2.CfnWebACLAssociation(
            self, "WAFALBAssociation",
            resource_arn=alb_arn,
            web_acl_arn=web_acl.attr_arn
        )