import sys
from botocore.exceptions import ClientError

from nimbo import CONFIG
from nimbo.core.print import print, print_header

NIMBO_USER_GROUP = "NimboUserGroup"
EC2_POLICY_NAME = "NimboEC2Policy"
CRED_POLICY_NAME = "NimboCredentialsPolicy"
PASS_ROLE_POLICY_NAME = "NimboPassRolePolicy"
INSTANCE_ROLE_NAME = "NimboInstanceRole"
INSTANCE_PROFILE_NAME = "NimboInstanceProfile"


def setup():
    iam = CONFIG.get_session().client("iam")

    try:
        print_header(f"Creating user group {NIMBO_USER_GROUP}...")
        iam.create_group(GroupName=NIMBO_USER_GROUP)
    except ClientError as e:
        if e.response['Error']['Code'] == 'EntityAlreadyExists':
            print(f"User group {NIMBO_USER_GROUP} already exists. Skipping.", style="warning")
        else:
            print(e, style="error")
            sys.exit(1)


    policy_json = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "VisualEditor0",
                "Effect": "Allow",
                "Action": [
                    "ec2:AssociateDhcpOptions",
                    "ec2:AssociateIamInstanceProfile",
                    "ec2:AssociateRouteTable",
                    "ec2:AttachInternetGateway",
                    "ec2:AttachVolume",
                    "ec2:AuthorizeSecurityGroupEgress",
                    "ec2:AuthorizeSecurityGroupIngress",
                    "ec2:CancelSpotInstanceRequests",
                    "ec2:CreateDhcpOptions",
                    "ec2:CreateInternetGateway",
                    "ec2:CreateKeyPair",
                    "ec2:CreatePlacementGroup",
                    "ec2:CreateRoute",
                    "ec2:CreateSecurityGroup",
                    "ec2:CreateSubnet",
                    "ec2:CreateTags",
                    "ec2:CreateVolume",
                    "ec2:CreateVpc",
                    "ec2:CreateVpcPeeringConnection",
                    "ec2:DeleteInternetGateway",
                    "ec2:DeleteKeyPair",
                    "ec2:DeletePlacementGroup",
                    "ec2:DeleteRoute",
                    "ec2:DeleteRouteTable",
                    "ec2:DeleteSecurityGroup",
                    "ec2:DeleteSubnet",
                    "ec2:DeleteTags",
                    "ec2:DeleteVolume",
                    "ec2:DeleteVpc",
                    "ec2:DescribeAvailabilityZones",
                    "ec2:DescribeIamInstanceProfileAssociations",
                    "ec2:DescribeInstanceStatus",
                    "ec2:DescribeInstances",
                    "ec2:DescribeKeyPairs",
                    "ec2:DescribePlacementGroups",
                    "ec2:DescribePrefixLists",
                    "ec2:DescribeReservedInstancesOfferings",
                    "ec2:DescribeRouteTables",
                    "ec2:DescribeSecurityGroups",
                    "ec2:DescribeSpotInstanceRequests",
                    "ec2:DescribeSpotPriceHistory",
                    "ec2:DescribeSubnets",
                    "ec2:DescribeVolumes",
                    "ec2:DescribeVpcs",
                    "ec2:DetachInternetGateway",
                    "ec2:DisassociateIamInstanceProfile",
                    "ec2:ModifyVpcAttribute",
                    "ec2:ReplaceIamInstanceProfileAssociation",
                    "ec2:RequestSpotInstances",
                    "ec2:RevokeSecurityGroupEgress",
                    "ec2:RevokeSecurityGroupIngress",
                    "ec2:RunInstances",
                    "ec2:TerminateInstances"
                    "pricing:*"
                ],
                "Resource": "*"
            },
            {
                "Sid": "VisualEditor1",
                "Effect": "Allow",
                "Action": "ec2:RunInstances",
                "Resource": [
                    "arn:aws:ec2:*:*:subnet/*",
                    "arn:aws:ec2:*::snapshot/*",
                    "arn:aws:ec2:*:*:launch-template/*",
                    "arn:aws:ec2:*:*:security-group/*",
                    "arn:aws:ec2:*:*:placement-group/*",
                    "arn:aws:ec2:*:*:network-interface/*",
                    "arn:aws:ec2:*:*:capacity-reservation/*",
                    "arn:aws:ec2:*:*:key-pair/*",
                    "arn:aws:ec2:*:*:instance/*",
                    "arn:aws:elastic-inference:*:*:elastic-inference-accelerator/*",
                    "arn:aws:ec2:*:*:elastic-gpu/*",
                    "arn:aws:ec2:*:*:volume/*",
                    "arn:aws:ec2:*::image/*"
                ]
            },
            {
                "Sid": "VisualEditor2",
                "Effect": "Allow",
                "Action": "ec2:RequestSpotInstances",
                "Resource": [
                    "arn:aws:ec2:*:*:subnet/*",
                    "arn:aws:ec2:*:*:security-group/*",
                    "arn:aws:ec2:*:*:spot-instances-request/*",
                    "arn:aws:ec2:*:*:key-pair/*",
                    "arn:aws:ec2:*::image/*"
                ]
            }
        ]
    }

    try:
        print_header(f"Creating EC2 policy {EC2_POLICY_NAME}...")
        ec2_policy = iam_client.create_policy(
            PolicyName=EC2_POLICY_NAME,
            PolicyDocument=json.dumps(policy_json)
        )
        ec2_policy_arn = policy['Policy']['Arn']
    except ClientError as error:
        if e.response['Error']['Code'] == 'EntityAlreadyExists':
            print(f"Policy {EC2_POLICY_NAME} already exists. Skipping.", style="warning")
        else:
            print(e, style="error")
            sys.exit(1)

    print_header(f"Attaching EC2 policy {EC2_POLICY_NAME} to user group {NIMBO_USER_GROUP}...")        
    iam.attach_group_policy(GroupName=NIMBO_USER_GROUP, PolicyArn=ec2_policy_arn)


    policy = {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Action": "sts:AssumeRole",
            "Principal": {"Service": "ec2.amazonaws.com"},
        },
    }
    iam.create_role(RoleName=INSTANCE_ROLE_NAME, AssumeRolePolicyDocument=json.dumps(policy))
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






