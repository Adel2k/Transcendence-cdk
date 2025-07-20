from aws_cdk import aws_elasticloadbalancingv2 as elbv2

def create_target_group(scope, id, vpc, cfg):
    return elbv2.ApplicationTargetGroup(
        scope, id,
        vpc=vpc,
        port=cfg['port'],
        protocol=elbv2.ApplicationProtocol.HTTP,
        target_type=elbv2.TargetType.IP,
        health_check=elbv2.HealthCheck(
            path=cfg.get('health_path', '/'),
            healthy_http_codes="200"
        )
    )
