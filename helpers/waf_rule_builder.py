from aws_cdk import aws_wafv2 as wafv2

def build_managed_rules(rules_config: list) -> list:
    return [
        wafv2.CfnWebACL.RuleProperty(
            name=rule["name"],
            priority=rule["priority"],
            override_action=wafv2.CfnWebACL.OverrideActionProperty(none={}),
            statement=wafv2.CfnWebACL.StatementProperty(
                managed_rule_group_statement=wafv2.CfnWebACL.ManagedRuleGroupStatementProperty(
                    name=rule["managed_group"]["name"],
                    vendor_name=rule["managed_group"]["vendor"]
                )
            ),
            visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                sampled_requests_enabled=True,
                cloud_watch_metrics_enabled=True,
                metric_name=rule["metric_name"]
            )
        )
        for rule in rules_config
    ]
