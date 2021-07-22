import json
import os
import sys

import boto3
import botocore.exceptions
import requests

from nimbo import CONFIG
from nimbo.core.cloud_provider.provider.services.permissions import Permissions
from nimbo.core.constants import ASSUME_ROLE_POLICY, EC2_POLICY_JSON
from nimbo.core.print import nprint, nprint_header

NIMBO_USER_GROUP = "NimboUserGroup"
EC2_POLICY_NAME = "NimboEC2Policy"
CRED_POLICY_NAME = "NimboCredentialsPolicy"
PASS_ROLE_POLICY_NAME = "NimboPassRolePolicy"
S3_ACCESS_ROLE_NAME = "NimboFullS3AccessRole"


class AwsPermissions(Permissions):
    @staticmethod
    def mk_instance_key(dry_run=False) -> None:
        ec2 = CONFIG.get_session().client("ec2")

        if "/" in CONFIG.user_arn:
            username = CONFIG.user_arn.split("/")[1]
        else:
            username = CONFIG.user_arn.split(":")[-1]
        key_name = f"{username}-{CONFIG.region_name}"

        try:
            response = ec2.create_key_pair(KeyName=key_name, DryRun=dry_run)
            key_body = response["KeyMaterial"]

            with open(f"{key_name}.pem", "w") as f:
                f.write(key_body)

            os.chmod(f"{key_name}.pem", int("400", base=8))
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "UnauthorizedOperation":
                return
            else:
                raise

    @staticmethod
    def allow_ingress_current_ip(target: str, dry_run=False) -> None:
        ec2 = CONFIG.get_session().client("ec2")

        try:
            response = ec2.describe_security_groups(GroupNames=[target], DryRun=dry_run)
            security_group_id = response["SecurityGroups"][0]["GroupId"]
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "InvalidGroup.NotFound":
                nprint(
                    f"Security group {target} not found. Please use an existing"
                    " security group or create a new one in the AWS console.",
                    style="error",
                )
                sys.exit(1)
            elif e.response["Error"]["Code"] == "UnauthorizedOperation":
                return
            else:
                raise

        my_public_ip = requests.get("https://checkip.amazonaws.com").text.strip()

        try:
            ec2.authorize_security_group_ingress(
                GroupId=security_group_id,
                IpPermissions=[
                    {
                        "IpProtocol": "tcp",
                        "FromPort": 22,
                        "ToPort": 22,
                        "IpRanges": [
                            {"CidrIp": f"{my_public_ip}/{CONFIG.ip_cidr_range}"}
                        ],
                    }
                ],
            )
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "InvalidPermission.Duplicate":
                return
            elif e.response["Error"]["Code"] == "UnauthorizedOperation":
                return
            else:
                raise

    @staticmethod
    def setup(profile: str, no_s3_access=False) -> None:
        session = boto3.Session(profile_name=profile)
        account = session.client("sts").get_caller_identity()["Account"]

        iam = session.client("iam")

        nprint_header(f"Creating user group {NIMBO_USER_GROUP}...")
        AwsPermissions._create_group(iam, NIMBO_USER_GROUP)

        nprint_header(f"Creating policy {EC2_POLICY_NAME}...")
        AwsPermissions._create_policy(iam, EC2_POLICY_NAME, EC2_POLICY_JSON)

        nprint_header(
            f"Attaching policy {EC2_POLICY_NAME} to user group {NIMBO_USER_GROUP}..."
        )
        iam.attach_group_policy(
            GroupName=NIMBO_USER_GROUP,
            PolicyArn=f"arn:aws:iam::{account}:policy/{EC2_POLICY_NAME}",
        )

        if no_s3_access:
            nprint(
                "\nSince you chose not to give full S3 access to the Nimbo user group"
                " and instance role,\nwe recommend that you create a role with the"
                " necessary S3 permissions in the AWS console.\nOnce you do this, give"
                " the role name to the people using Nimbo so that they can set\n"
                "the 'role' field in the configuration file to this value.",
                style="warning",
            )
        else:
            nprint_header(f"Creating role {S3_ACCESS_ROLE_NAME}...")
            AwsPermissions._create_role_and_instance_profile(iam, S3_ACCESS_ROLE_NAME)

            nprint_header(
                f"Attaching AmazonS3FullAccess policy to role {S3_ACCESS_ROLE_NAME}..."
            )
            iam.attach_role_policy(
                PolicyArn="arn:aws:iam::aws:policy/AmazonS3FullAccess",
                RoleName=S3_ACCESS_ROLE_NAME,
            )

            nprint_header(f"Creating policy {PASS_ROLE_POLICY_NAME}...")
            pass_role_policy_json = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "NimboPassRolePolicy",
                        "Effect": "Allow",
                        "Action": "iam:PassRole",
                        "Resource": f"arn:aws:iam::*:role/{S3_ACCESS_ROLE_NAME}",
                    }
                ],
            }
            AwsPermissions._create_policy(
                iam, PASS_ROLE_POLICY_NAME, pass_role_policy_json
            )

            nprint_header(
                f"Attaching policy {PASS_ROLE_POLICY_NAME}"
                f" to user group {NIMBO_USER_GROUP}..."
            )
            iam.attach_group_policy(
                GroupName=NIMBO_USER_GROUP,
                PolicyArn=f"arn:aws:iam::{account}:policy/{PASS_ROLE_POLICY_NAME}",
            )

            nprint_header(
                f"Attaching policy AmazonS3FullAccess"
                f" to user group {NIMBO_USER_GROUP}..."
            )
            iam.attach_group_policy(
                GroupName=NIMBO_USER_GROUP,
                PolicyArn="arn:aws:iam::aws:policy/AmazonS3FullAccess",
            )

        print()
        nprint_header("Done.")
        nprint_header(
            "To add users to the NimboUserGroup, simply"
            " run 'nimbo add-user USERNAME YOUR_AWS_PROFILE'.\n"
            "For more info use 'nimbo add-user --help'"
        )

    @staticmethod
    def add_user(profile: str, username: str) -> None:
        session = boto3.Session(profile_name=profile)
        iam = session.client("iam")

        iam.add_user_to_group(GroupName=NIMBO_USER_GROUP, UserName=username)
        print(f"User {username} added to {NIMBO_USER_GROUP}.")

    @staticmethod
    def _create_group(client, group_name):
        try:
            client.create_group(GroupName=group_name)
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "EntityAlreadyExists":
                nprint(
                    f"User group {group_name} already exists. Skipping.",
                    style="warning",
                )
            else:
                raise

    @staticmethod
    def _create_policy(client, policy_name, policy_json):
        try:
            client.create_policy(
                PolicyName=policy_name, PolicyDocument=json.dumps(policy_json)
            )
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "EntityAlreadyExists":
                nprint(
                    f"Policy {policy_name} already exists. Skipping.", style="warning"
                )
            else:
                raise

    @staticmethod
    def _create_role_and_instance_profile(client, role_name):
        try:
            client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(ASSUME_ROLE_POLICY),
            )
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "EntityAlreadyExists":
                nprint(f"Role {role_name} already exists. Skipping.", style="warning")
            else:
                raise

        try:
            client.create_instance_profile(InstanceProfileName=role_name, Path="/")
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "EntityAlreadyExists":
                nprint(
                    f"Instance profile for role {role_name} already exists. Skipping.",
                    style="warning",
                )
            else:
                raise

        try:
            client.add_role_to_instance_profile(
                InstanceProfileName=role_name, RoleName=role_name
            )
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "LimitExceeded":
                nprint(
                    f"Instance profile {role_name} already has a role. Skipping.",
                    style="warning",
                )
            else:
                raise
