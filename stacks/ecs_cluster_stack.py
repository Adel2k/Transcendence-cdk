from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
)
from constructs import Construct

class ECSClusterStack(Stack):
    def __init__(self, scope: Construct, id: str, vpc: ec2.Vpc, **kwargs):
        super().__init__(scope, id, **kwargs)

        # Create ECS cluster
        cluster = ecs.Cluster(self, "TranscendenceCluster", vpc=vpc)

        # Add EC2 capacity
        cluster.add_capacity(
            "DefaultAutoScalingGroupCapacity",
            instance_type=ec2.InstanceType("t3.medium"),
            min_capacity=1
        )

        # Optionally export the cluster for use in other stacks
        self.cluster = cluster