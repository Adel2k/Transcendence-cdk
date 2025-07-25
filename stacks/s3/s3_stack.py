from aws_cdk import (
    Duration,
    RemovalPolicy,
    aws_s3 as s3
)
from constructs import Construct
from helpers.tools import tools

class S3Stack(tools):
    def __init__(
            self,
            scope: Construct,
            id: str,
            **kwargs
        ):

        super().__init__(scope, id, **kwargs)
        config = self.load_yaml_config('config/s3/s3.yml')

        bucket_configs = config.get("buckets", [])

        self.buckets = {} 
        self.bucket_prefixes = {}

        for bucket_cfg in bucket_configs:
            bucket_name = bucket_cfg["name"]
            versioned = bucket_cfg.get("versioned", True)
            encrypted = bucket_cfg.get("encrypted", True)
            destroy_on_remove = bucket_cfg.get("destroy_on_remove", False)
            lifecycle_days = bucket_cfg.get("lifecycle_days", 30)
            cors_cfg = bucket_cfg.get("cors", [])
            prefixes = bucket_cfg.get("prefixes", [])

            cors_rules = []
            for rule in cors_cfg:
                cors_rules.append(s3.CorsRule(
                    allowed_methods=[s3.HttpMethods[method] for method in rule["methods"]],
                    allowed_origins=rule["origins"],
                    allowed_headers=rule["headers"]
                ))

            bucket = s3.Bucket(self,
                f"{bucket_name}-Bucket",
                bucket_name=bucket_name,
                versioned=versioned,
                encryption=s3.BucketEncryption.S3_MANAGED if encrypted else s3.BucketEncryption.UNENCRYPTED,
                block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
                removal_policy=RemovalPolicy.DESTROY if destroy_on_remove else RemovalPolicy.RETAIN,
                lifecycle_rules=[
                    s3.LifecycleRule(
                        id=f"AutoDeleteAfter{lifecycle_days}Days",
                        enabled=True,
                        expiration=Duration.days(lifecycle_days)
                    )
                ],
                cors=cors_rules
            )
            self.buckets[bucket_name] = bucket
            self.bucket_prefixes[bucket_name] = {name.strip("/"): name for name in prefixes}
