from aws_cdk import aws_elasticloadbalancingv2 as elbv2

def add_http_redirect_listener(scope, alb):
    alb.add_listener(
        "HttpRedirectListener",
        port=80,
        open=True,
        default_action=elbv2.ListenerAction.redirect(
            protocol="HTTPS",
            port="443"
        )
    )

def add_https_listener(scope, alb, certificate, routes, target_groups):
    listener = alb.add_listener(
        "HttpsListener",
        port=443,
        open=True,
        certificates=[certificate],
        default_action=elbv2.ListenerAction.forward([target_groups["frontend"]])
    )
    for route in routes:
        target_group = target_groups[route['target']]
        listener.add_action(
            route['name'],
            priority=route['priority'],
            conditions=[elbv2.ListenerCondition.path_patterns([route['path']])],
            action=elbv2.ListenerAction.forward([target_group])
        )
    return listener
