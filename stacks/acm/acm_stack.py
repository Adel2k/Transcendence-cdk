from aws_cdk import (
    aws_certificatemanager as acm,
    aws_route53 as route53,
)
from constructs import Construct
from helpers.tools import tools

class ACMStack(tools):
    def __init__(
            self, 
            scope: Construct, 
            id: str, 
            **kwargs
        ):
        super().__init__(scope, id, **kwargs)

        config = self.load_yaml_config('config/acm/acm.yml')

        certs = config.get("certificates", [])

        for cert_def in certs:
            cert_id = cert_def["id"]
            domain_name = cert_def["domain_name"]
            hosted_zone_name = cert_def["hosted_zone"]

            hosted_zone = route53.HostedZone.from_lookup(
                self, f"{cert_id}-{domain_name}-Zone",
                domain_name=hosted_zone_name
            )

            certificate = acm.Certificate(
                self, f"{cert_id}-{domain_name}-Certificate",
                domain_name=domain_name,
                validation=acm.CertificateValidation.from_dns(hosted_zone)
            )

            ssm_path = self.generate_ssm_parameter_path(
                cert_id, None ,aws_service="certificate"
            )

            self.store_ssm_parameter(
                f"{cert_id}-{domain_name}-CertArn",
                ssm_path,
                certificate.certificate_arn
            )
