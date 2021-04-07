from os.path import join
import json
import boto3
import requests
import subprocess
from pprint import pprint
from botocore.exceptions import ClientError


def create_security_group(session, group_name):

    ec2 = session.client("ec2")
    response = ec2.describe_vpcs()
    vpc_id = response.get('Vpcs', [{}])[0].get('VpcId', '')

    response = ec2.create_security_group(GroupName=group_name,
                                         Description="Base VPC security group for Nimbo jobs.",
                                         VpcId=vpc_id)

    security_group_id = response['GroupId']
    print(f'Security Group {group_name} (id={security_group_id}) Created in vpc {vpc_id}.')


def verify_current_machine_security_group(session, group_name):
    # NOTE: This function is not working correctly.
    # Verify that the security group chosen by the user has the inbound rule allowing the current computer

    ec2 = session.client("ec2")
    my_public_ip = requests.get('https://checkip.amazonaws.com').text.strip()

    response = ec2.describe_security_groups(
        GroupNames=[group_name],
        Filters=[{"Name": "ip-permission.cidr", "Values": [f"{my_public_ip}/32"]}]
    )
    if len(response["SecurityGroups"]) == 0:
        raise Exception(f"The securty group '{group_name}' doesn't give access "
                        f"to your machine's public IP ({my_public_ip}/32). "
                        "Please run 'nimbo allow-current-device <group_name>' "
                        "or ask your admin to add your IP to this security group.")


def allow_inbound_current_ip(session, group_name):

    ec2 = session.client("ec2")

    # Get the security group id
    response = ec2.describe_security_groups(GroupNames=[group_name])
    security_group_id = response['SecurityGroups'][0]['GroupId']

    my_public_ip = requests.get('https://checkip.amazonaws.com').text.strip()

    response = ec2.authorize_security_group_ingress(
        GroupId=security_group_id,
        IpPermissions=[
            {
                'IpProtocol': 'tcp',
                'FromPort': 22,
                'ToPort': 22,
                'IpRanges': [{'CidrIp': f'{my_public_ip}/16'}]
            }
        ]
    )
    print("Ingress Successfully Set")
    pprint(response)


def create_instance_profile_and_role(session):
    iam = session.client("iam")
    role_name = "NimboAllowS3AndEC2FullAccess"
    instance_profile_name = "NimboInstanceProfile"

    policy = {
        "Version": "2012-10-17",
        "Statement":
        {
            "Effect": "Allow",
            "Action": "sts:AssumeRole",
            "Principal": {"Service": "ec2.amazonaws.com"}
        }
    }
    role = iam.create_role(RoleName=role_name, AssumeRolePolicyDocument=json.dumps(policy))
    response = iam.attach_role_policy(PolicyArn='arn:aws:iam::aws:policy/AmazonS3FullAccess', RoleName=role_name)
    response = iam.attach_role_policy(PolicyArn='arn:aws:iam::aws:policy/AmazonEC2FullAccess', RoleName=role_name)

    instance_profile = iam.create_instance_profile(InstanceProfileName=instance_profile_name, Path='/')
    iam.add_role_to_instance_profile(InstanceProfileName=instance_profile_name, RoleName=role_name)


def create_instance_profile(session, role_name):
    iam = session.client("iam")
    instance_profile_name = "NimboInstanceProfile"
    instance_profile = iam.create_instance_profile(InstanceProfileName=instance_profile_name, Path='/')
    iam.add_role_to_instance_profile(InstanceProfileName=instance_profile_name, RoleName=role_name)


def list_instance_profiles(session):
    iam = session.client("iam")
    response = iam.list_instance_profiles()
    pprint(response["InstanceProfiles"])


def verify_nimbo_instance_profile(session):
    iam = session.client("iam")
    response = iam.list_instance_profiles()
    instance_profiles = response["InstanceProfiles"]
    instance_profile_names = [p["InstanceProfileName"] for p in instance_profiles]
    if "NimboInstanceProfile" not in instance_profile_names:
        raise Exception("Instance profile 'NimboInstanceProfile' not found.\n"
                        "An instance profile is necessary to give your instance access to EC2 and S3 resources.\n"
                        "You can create an instance profile using 'nimbo create_instance_profile <role_name>'.\n"
                        "If you are a root user, you can simply run 'nimbo create_instance_profile_and_role', "
                        "and nimbo will create the necessary role policies and instance profile for you.\n"
                        "Otherwise, please ask your admin for a role that provides the necessary EC2 and S3 read/write access.\n"
                        "For more details please go to docs.nimbo.sh/instance-profiles.")


if __name__ == "__main__":

    session = boto3.Session(profile_name="nimbo")

    group_name = "default"
    #create_security_group(session, group_name)
    #allow_inbound_current_device(session, group_name)
    create_s3_full_access_ec2_role(session)
