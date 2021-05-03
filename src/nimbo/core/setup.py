import sys
import json
from botocore.exceptions import ClientError

from nimbo import CONFIG
from nimbo.core.print import print, print_header

NIMBO_USER_GROUP = "NimboUserGroup"
EC2_POLICY_NAME = "NimboEC2Policy"
CRED_POLICY_NAME = "NimboCredentialsPolicy"
PASS_ROLE_POLICY_NAME = "NimboPassRolePolicy"
S3_ACCESS_ROLE_NAME = "NimboFullS3AccessRole"


def setup(full_s3_access=False):
    iam = CONFIG.get_session().client("iam")

    # Create user group
    try:
        print_header(f"Creating user group {NIMBO_USER_GROUP}...")
        iam.create_group(GroupName=NIMBO_USER_GROUP)
    except ClientError as e:
        if e.response['Error']['Code'] == 'EntityAlreadyExists':
            print(f"User group {NIMBO_USER_GROUP} already exists. Skipping.", style="warning")
        else:
            print(e, style="error")
            sys.exit(1)

    # Create EC2 policy for user group
    ec2_policy_json = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "NimboEC2Policy1",
                "Effect": "Allow",
                "Action": [
                    "ec2:AuthorizeSecurityGroupEgress",
                    "ec2:AuthorizeSecurityGroupIngress",
                    "ec2:CopySnapshot",
                    "ec2:CreateKeyPair",
                    "ec2:CreatePlacementGroup",
                    "ec2:CreateSecurityGroup",
                    "ec2:CreateSnapshot",
                    "ec2:CreateSnapshots",
                    "ec2:CreateSubnet",
                    "ec2:CreateVolume",
                    "ec2:CreateVpc",
                    "ec2:CreateVpcPeeringConnection",
                    "ec2:DeleteKeyPair",
                    "ec2:DeletePlacementGroup",
                    "ec2:DeleteSecurityGroup",
                    "ec2:DeleteSubnet",
                    "ec2:DeleteTags",
                    "ec2:DeleteVolume",
                    "ec2:DeleteVpc",
                    "ec2:Describe*",
                    "ec2:GetConsole*",
                    "ec2:ImportSnapshot",
                    "ec2:ModifySnapshotAttribute",
                    "ec2:ModifyVpcAttribute",
                    "ec2:RequestSpotInstances",
                    "ec2:RevokeSecurityGroupEgress",
                    "ec2:RevokeSecurityGroupIngress",
                    "ec2:RunInstances",
                ],
                "Resource": "*"
            },
            {
                "Sid": "NimboEC2Policy2",
                "Effect": "Allow",
                "Action": [
                    "ec2:CreateTags",
                    "ec2:StartInstances",
                    "ec2:StopInstances",
                    "ec2:TerminateInstances",
                    "ec2:DeleteSnapshot",
                    "ec2:CancelSpotInstanceRequests",
                ],
                "Resource": "*",
                "Condition": {
                    "StringEquals": {
                        "ec2:ResourceTag/Owner": "${aws:userid}"
                    }
                }
            },
            {
                "Sid": "NimboEC2Policy3",
                "Effect": "Allow",
                "Action": [
                    "ec2:AttachVolume",
                    "ec2:DetachVolume"
                ],
                "Resource": "arn:aws:ec2:*:*:instance/*",
                "Condition": {
                    "StringEquals": {"ec2:ResourceTag/Owner": "${aws:userid}"}
                }
            },
            {
                "Sid": "NimboPricingPolicy",
                "Effect": "Allow",
                "Action": ["pricing:*"],
                "Resource": "*"
            },
        ]
    }

    #"Resource": "arn:aws:iam::*:role/Role1"
    #"Condition": {
    #"StringEquals": {
    #    "aws:username": [
    #        "Miguel",
    #        "Employee",
    #    ]
    #}

    try:
        print_header(f"Creating EC2 policy {EC2_POLICY_NAME}...")
        ec2_policy = iam.create_policy(
            PolicyName=EC2_POLICY_NAME,
            PolicyDocument=json.dumps(ec2_policy_json)
        )
        ec2_policy_arn = ec2_policy['Policy']['Arn']
        print_header(f"Attaching EC2 policy {EC2_POLICY_NAME} to user group {NIMBO_USER_GROUP}...")
        iam.attach_group_policy(GroupName=NIMBO_USER_GROUP, PolicyArn=ec2_policy_arn)
    except ClientError as e:
        if e.response['Error']['Code'] == 'EntityAlreadyExists':
            print(f"Policy {EC2_POLICY_NAME} already exists. Skipping.", style="warning")
        else:
            print(e, style="error")
            sys.exit(1)

    if full_s3_access:
        print_header(f"Creating role {S3_ACCESS_ROLE_NAME}...")
        assume_role_policy = {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Action": "sts:AssumeRole",
                "Principal": {"Service": "ec2.amazonaws.com"},
            },
        }
        iam.create_role(RoleName=S3_ACCESS_ROLE_NAME, AssumeRolePolicyDocument=json.dumps(assume_role_policy))
        iam.attach_role_policy(
            PolicyArn="arn:aws:iam::aws:policy/AmazonS3FullAccess", RoleName=S3_ACCESS_ROLE_NAME
        )
        iam.create_instance_profile(InstanceProfileName=S3_ACCESS_ROLE_NAME, Path="/")
        iam.add_role_to_instance_profile(
            InstanceProfileName=S3_ACCESS_ROLE_NAME, RoleName=S3_ACCESS_ROLE_NAME
        )

        pass_role_policy_json = {
            "Version": "2012-10-17",
            "Statement": [{
                "Sid": "NimboPassRolePolicy",
                "Effect": "Allow",
                "Action": "iam:PassRole",
                "Resource": f"arn:aws:iam::*:role/{S3_ACCESS_ROLE_NAME}"
            }]
        }
        pass_role_policy = iam.create_policy(
            PolicyName=PASS_ROLE_POLICY_NAME,
            PolicyDocument=json.dumps(pass_role_policy_json)
        )
        pass_role_policy_arn = ec2_policy['Policy']['Arn']
        print_header(f"Attaching policy {PASS_ROLE_POLICY_NAME} to user group {NIMBO_USER_GROUP}...")
        iam.attach_group_policy(GroupName=NIMBO_USER_GROUP, PolicyArn=pass_role_policy_arn)
        print_header(f"Attaching policy AmazonS3FullAccess to user group {NIMBO_USER_GROUP}...")
        iam.attach_group_policy(GroupName=NIMBO_USER_GROUP, PolicyArn="arn:aws:iam::aws:policy/AmazonS3FullAccess")

    print_header("Done.")