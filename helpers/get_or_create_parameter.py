import boto3
from botocore.exceptions import ClientError

ssm = boto3.client('ssm', region_name='us-east-1')

def get_or_create_parameter(name: str, default_value: str) -> str:
    try:
        response = ssm.get_parameter(Name=name)
        return response['Parameter']['Value']
    except ClientError as e:
        if e.response['Error']['Code'] == 'ParameterNotFound':
            ssm.put_parameter(
                Name=name,
                Value=default_value,
                Type='String'
            )
            return default_value
        else:
            raise e
