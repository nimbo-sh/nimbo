import json
import pprint

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
