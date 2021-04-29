import json
import pprint
import textwrap

import requests

from nimbo import CONFIG
from nimbo.core.cloud_provider.provider.services.permissions import Permissions


class AwsPermissions(Permissions):
    @staticmethod
    def allow_ingress_current_ip(target: str, dry_run=False) -> None:
        ec2 = CONFIG.get_session().client("ec2")

        # Get the security group id
        response = ec2.describe_security_groups(GroupNames=[target], DryRun=dry_run)
        security_group_id = response["SecurityGroups"][0]["GroupId"]

        my_public_ip = requests.get("https://checkip.amazonaws.com").text.strip()

        # TODO: config option for CIDR range
        response = ec2.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=[
                {
                    "IpProtocol": "tcp",
                    "FromPort": 22,
                    "ToPort": 22,
                    "IpRanges": [{"CidrIp": f"{my_public_ip}/16"}],
                }
            ],
        )
        print("Ingress Successfully Set")
        pprint.pprint(response)

    @staticmethod
    def setup_as_user(role_name: str = "", dry_run=False) -> None:
        """
        PLACEHOLDER
        At the moment, this creates instance profile for role_name.

        TODO: remove/generalise role_name parameter

        In future this method is going to do more than it does now - and is
        very much work in progress.
        """

        iam = CONFIG.get_session().client("iam")
        instance_profile_name = "NimboInstanceProfile"

        if dry_run:
            return

        iam.create_instance_profile(InstanceProfileName=instance_profile_name, Path="/")
        iam.add_role_to_instance_profile(
            InstanceProfileName=instance_profile_name, RoleName=role_name
        )

    @staticmethod
    def setup_as_admin(dry_run=False) -> None:
        """
        PLACEHOLDER
        At the moment, this creates instance profile and role.

        In future this method is going to do more than it does now - and is
        very much work in progress.
        """

        iam = CONFIG.get_session().client("iam")
        role_name = "NimboS3AndEC2FullAccess"
        instance_profile_name = "NimboInstanceProfile"

        policy = {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "sts:AssumeRole",
                "Principal": {"Service": "ec2.amazonaws.com"},
            },
        }
        if dry_run:
            return
        iam.create_role(RoleName=role_name, AssumeRolePolicyDocument=json.dumps(policy))
        iam.attach_role_policy(
            PolicyArn="arn:aws:iam::aws:policy/AmazonS3FullAccess", RoleName=role_name
        )
        iam.attach_role_policy(
            PolicyArn="arn:aws:iam::aws:policy/AmazonEC2FullAccess", RoleName=role_name
        )

        iam.create_instance_profile(InstanceProfileName=instance_profile_name, Path="/")
        iam.add_role_to_instance_profile(
            InstanceProfileName=instance_profile_name, RoleName=role_name
        )

    @staticmethod
    def create_security_group(group_name: str, dry_run=False):
        # TODO: not used

        ec2 = CONFIG.get_session().client("ec2")
        response = ec2.describe_vpcs()
        vpc_id = response.get("Vpcs", [{}])[0].get("VpcId", "")

        response = ec2.create_security_group(
            GroupName=group_name,
            Description="Base VPC security group for Nimbo jobs.",
            VpcId=vpc_id,
            DryRun=dry_run,
        )

        security_group_id = response["GroupId"]
        print(
            f"Security Group {group_name} (id={security_group_id}) Created in vpc {vpc_id}."
        )

    @staticmethod
    def verify_nimbo_instance_profile(dry_run=False):
        # TODO: not used

        iam = CONFIG.get_session().client("iam")

        if dry_run:
            return

        response = iam.list_instance_profiles()
        instance_profiles = response["InstanceProfiles"]
        instance_profile_names = [p["InstanceProfileName"] for p in instance_profiles]
        if "NimboInstanceProfiles" not in instance_profile_names:
            raise Exception(
                textwrap.dedent(
                    """Instance profile 'NimboInstanceProfile' not found.

                    An instance profile is necessary to give your instance access
                    to EC2 and S3 resources. You can create an instance profile using
                    'nimbo create_instance_profile <role_name>'. If you are a root user,
                    you can simply run 'nimbo create_instance_profile_and_role', and
                    nimbo will create the necessary role policies and instance profile
                    for you. Otherwise, please ask your admin for a role that provides
                    the necessary EC2 and S3 read/write access.

                    For more details please go to docs.nimbo.sh/instance-profiles."
                    """
                )
            )
