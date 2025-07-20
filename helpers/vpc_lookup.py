import boto3

def get_vpc_id(name: str, region="eu-west-2") -> str:
    ssm = boto3.client("ssm", region_name=region)
    return ssm.get_parameter(Name=f"/transendence/vpc-id/{name}")["Parameter"]["Value"]
