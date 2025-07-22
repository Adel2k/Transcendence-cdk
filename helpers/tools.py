from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_elasticloadbalancingv2 as elbv2,
    aws_certificatemanager as acm,
    aws_ssm as ssm,
    aws_ecs as ecs,
)
from constructs import Construct
import boto3
from aws_cdk import aws_wafv2 as wafv2
from aws_cdk import aws_route53 as route53
from aws_cdk import aws_route53_targets as targets
from aws_cdk.aws_elasticloadbalancingv2 import ApplicationLoadBalancer
from constructs import Construct
from botocore.exceptions import ClientError


class tools(Stack):
    def __init__(
            self, 
            scope: Construct, 
            id: str, 
            **kwargs
        ) -> None:

        super().__init__(scope, id, **kwargs)

        self.ssm = boto3.client('ssm', region_name='eu-west-2')

    #######################################################################

    def get_or_create_parameter(self, name: str, default_value: str) -> str:
        try:
            response = self.ssm.get_parameter(Name=name)
            return response['Parameter']['Value']
        except ClientError as e:
            if e.response['Error']['Code'] == 'ParameterNotFound':
                self.ssm.put_parameter(Name=name, Value=default_value, Type='String', Overwrite=True)
                return default_value
            else:
                raise e
            
    #######################################################################

    def load_yaml_config(self, path: str) -> dict:
        import yaml
        with open(path, 'r') as file:
            return yaml.safe_load(file)
        
    #######################################################################

    def create_target_group(self, id, vpc, cfg):
        return elbv2.ApplicationTargetGroup(
            self, id,
            vpc=vpc,
            port=cfg['port'],
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.IP,
            health_check=elbv2.HealthCheck(
                path=cfg.get('health_path', '/'),
                healthy_http_codes="200"
            )
        )
    
    #######################################################################

    def get_vpc_id(self, app_name: str, region="eu-west-2") -> str:
        ssm = boto3.client("ssm", region_name=region)
        return ssm.get_parameter(Name=f"/{app_name}/vpc-id")["Parameter"]["Value"]
    
    #######################################################################

    def build_certificate(self, domain_name: str, region: str = "eu-west-2") -> acm.Certificate:
        cert_param = ssm.StringParameter.from_string_parameter_attributes(
            self, "ImportedCertParam",
            parameter_name=f"/transendence/certificate/{domain_name}",
            simple_name=False
        )
        cert_arn = cert_param.string_value
        return acm.Certificate.from_certificate_arn(self, "ImportedCert", cert_arn)
    
    #######################################################################

    def build_ecs_cluster(self, cluster_name: str, vpc: ec2.IVpc) -> ecs.Cluster:
        return ecs.Cluster.from_cluster_attributes(
            self, "ClusterImported",
            cluster_name=cluster_name,
            vpc=vpc
        )
    
    #######################################################################

    def build_ecs_service(self, cluster: ecs.ICluster, service_name: str) -> ecs.Ec2Service:
        return ecs.Ec2Service.from_ec2_service_attributes(
            self, f"{service_name.capitalize()}ServiceImported",
            cluster=cluster,
            service_name=service_name
        )
    
    #######################################################################

    def add_http_redirect_listener(self, alb):
        alb.add_listener(
            "HttpRedirectListener",
            port=80,
            open=True,
            default_action=elbv2.ListenerAction.redirect(
                protocol="HTTPS",
                port="443"
            )
        )

    #######################################################################

    def add_https_listener(self, alb, certificate, routes, target_groups):
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

    ########################################################################

    def build_managed_rules(self, rules_config: list) -> list:
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

    ########################################################################

    def store_ssm_parameter(self: Construct, id: str, parameter_name: str, string_value: str):

        ssm.StringParameter(
            self,
            id,
            parameter_name=parameter_name,
            string_value=string_value
        )
    ########################################################################

    def logical_id_generator(self, cluster_name: str, type: str, aws_service: str) -> str:
        return f"{cluster_name.capitalize()}-{type.capitalize()}-{aws_service.capitalize()}"
    
    #########################################################################

    def create_route53_record(self, domain_name: str, subdomain: str, alb: ApplicationLoadBalancer):
        hosted_zone = route53.HostedZone.from_lookup(self, f"{subdomain}HostedZone", domain_name=domain_name)

        route53.ARecord(
            self, f"{subdomain}AliasRecord",
            zone=hosted_zone,
            record_name=subdomain,
            target=route53.RecordTarget.from_alias(targets.LoadBalancerTarget(alb))
        )

    #########################################################################

    def generate_ssm_parameter_path(self, cluster_name: str, service_name: str, aws_service: str) -> str:
        if service_name is None:
            return f"/{cluster_name}/ecs/{aws_service}"
        return f"/{cluster_name}/{service_name}/ecs/{aws_service}-arn"
    
    #########################################################################