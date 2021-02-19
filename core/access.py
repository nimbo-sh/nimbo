import boto3
import requests
from botocore.exceptions import ClientError

""" These functions are to be ran at setup """

def create_security_group(session, group_name):

    ec2 = session.client("ec2")
    response = ec2.describe_vpcs()
    vpc_id = response.get('Vpcs', [{}])[0].get('VpcId', '')

    response = ec2.create_security_group(GroupName=group_name,
                                         Description="Base VPC security group for Nimbo jobs.",
                                         VpcId=vpc_id)

    security_group_id = response['GroupId']
    print(f'Security Group {group_name} (id={security_group_id}) Created in vpc {vpc_id}.')


def allow_inbound_current_device(session, group_name):

    ec2 = session.client("ec2")

    # Get the security group id
    response = ec2.describe_security_groups(GroupNames=[group_name])
    security_group_id = response['SecurityGroups'][0]['GroupId']

    my_public_ip = requests.get('https://checkip.amazonaws.com').text.strip()

    data = ec2.authorize_security_group_ingress(
        GroupId=security_group_id,
        IpPermissions=[
            {
                'IpProtocol': 'tcp',
                'FromPort': 22,
                'ToPort': 22,
                'IpRanges': [{'CidrIp': f'{my_public_ip}/32'}]
            }
        ]
    )
    print('Ingress Successfully Set %s' % data)


def create_s3_full_access_ec2_role(session):
    iam = session.client("iam")

    policy = {
        "Version": "2012-10-17",
        "Statement":
        {
            "Effect": "Allow",
            "Action": "sts:AssumeRole",
            "Principal": {"Service": "ec2.amazonaws.com"}
        }
    }
    role = iam.create_role(RoleName="AllowFullS3Access", AssumeRolePolicyDocument=json.dumps(policy))
    response = iam.attach_role_policy(PolicyArn='arn:aws:iam::aws:policy/AmazonS3FullAccess', RoleName='AllowFullS3Access')


if __name__ == "__main__":

    session = boto3.Session()

    group_name = "nimbo-security-group"
    #create_security_group(session, group_name)
    allow_inbound_current_device(session, group_name)
