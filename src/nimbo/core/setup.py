import sys
import json
import boto3
from botocore.exceptions import ClientError

from nimbo import CONFIG
from nimbo.core.print import print, print_header
from nimbo.core.statics import EC2_POLICY_JSON, ASSUME_ROLE_POLICY

NIMBO_USER_GROUP = "NimboUserGroup"
EC2_POLICY_NAME = "NimboEC2Policy"
CRED_POLICY_NAME = "NimboCredentialsPolicy"
PASS_ROLE_POLICY_NAME = "NimboPassRolePolicy"
S3_ACCESS_ROLE_NAME = "NimboFullS3AccessRole"


def create_group(client, group_name):
    try:
        client.create_group(GroupName=group_name)
    except ClientError as e:
        if e.response["Error"]["Code"] == "EntityAlreadyExists":
            print(f"User group {group_name} already exists. Skipping.", style="warning")
        else:
            raise


def create_policy(client, policy_name, policy_json):
    try:
        ec2_policy = client.create_policy(
            PolicyName=policy_name, PolicyDocument=json.dumps(policy_json)
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "EntityAlreadyExists":
            print(f"Policy {policy_name} already exists. Skipping.", style="warning")
        else:
            raise


def create_role_and_instance_profile(client, role_name):
    try:
        client.create_role(
            RoleName=role_name, AssumeRolePolicyDocument=json.dumps(ASSUME_ROLE_POLICY)
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "EntityAlreadyExists":
            print(f"Role {role_name} already exists. Skipping.", style="warning")
        else:
            raise

    try:
        client.create_instance_profile(InstanceProfileName=role_name, Path="/")
    except ClientError as e:
        if e.response["Error"]["Code"] == "EntityAlreadyExists":
            print(
                f"Instance profile for role {role_name} already exists. Skipping.",
                style="warning",
            )
        else:
            raise

    try:
        client.add_role_to_instance_profile(
            InstanceProfileName=role_name, RoleName=role_name
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "LimitExceeded":
            print(
                f"Instance profile {role_name} already has a role. Skipping.",
                style="warning",
            )
        else:
            raise


def setup(profile, full_s3_access=False):
    session = boto3.Session(profile_name=profile)
    account = session.client("sts").get_caller_identity()["Account"]

    iam = session.client("iam")

    print_header(f"Creating user group {NIMBO_USER_GROUP}...")
    create_group(iam, NIMBO_USER_GROUP)

    print_header(f"Creating policy {EC2_POLICY_NAME}...")
    create_policy(iam, EC2_POLICY_NAME, EC2_POLICY_JSON)

    print_header(
        f"Attaching policy {EC2_POLICY_NAME} to user group {NIMBO_USER_GROUP}..."
    )
    iam.attach_group_policy(
        GroupName=NIMBO_USER_GROUP,
        PolicyArn=f"arn:aws:iam::{account}:policy/{EC2_POLICY_NAME}",
    )

    if full_s3_access:
        print_header(f"Creating role {S3_ACCESS_ROLE_NAME}...")
        create_role_and_instance_profile(iam, S3_ACCESS_ROLE_NAME)

        print_header(
            f"Attaching AmazonS3FullAccess policy to role {S3_ACCESS_ROLE_NAME}..."
        )
        iam.attach_role_policy(
            PolicyArn="arn:aws:iam::aws:policy/AmazonS3FullAccess",
            RoleName=S3_ACCESS_ROLE_NAME,
        )

        print_header(f"Creating policy {PASS_ROLE_POLICY_NAME}...")
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
        create_policy(iam, PASS_ROLE_POLICY_NAME, pass_role_policy_json)

        print_header(
            f"Attaching policy {PASS_ROLE_POLICY_NAME} to user group {NIMBO_USER_GROUP}..."
        )
        iam.attach_group_policy(
            GroupName=NIMBO_USER_GROUP,
            PolicyArn=f"arn:aws:iam::{account}:policy/{PASS_ROLE_POLICY_NAME}",
        )

        print_header(
            f"Attaching policy AmazonS3FullAccess to user group {NIMBO_USER_GROUP}..."
        )
        iam.attach_group_policy(
            GroupName=NIMBO_USER_GROUP,
            PolicyArn="arn:aws:iam::aws:policy/AmazonS3FullAccess",
        )

    else:
        print(
            "\nSince you chose not to give full S3 access to the Nimbo user group and instance role,\n"
            "we recommend that you create a role with the necessary S3 permissions in the AWS console.\n"
            "Once you do this, give the role name to the people using Nimbo so that they can set\n"
            "the 'role' field in the nimbo-config.yml to this value.",
            style="warning",
        )

    print()
    print_header("Done.")
    print_header(
        "To add users to the NimboUserGroup, simply run 'nimbo add-user USERNAME YOUR_AWS_PROFILE'.\n"
        "For more info use 'nimbo add-user --help'"
    )


def add_user(username, profile):
    session = boto3.Session(profile_name=profile)
    iam = session.client("iam")

    response = iam.add_user_to_group(GroupName=NIMBO_USER_GROUP, UserName=username)
    print(f"User {username} added to {NIMBO_USER_GROUP}.")
