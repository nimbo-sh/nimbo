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
