import os
import subprocess
import sys
import time
from pprint import pprint
from typing import Dict, List, Union

import botocore.exceptions
import requests

from nimbo import CONFIG
from nimbo.core import telemetry
from nimbo.core.cloud_provider.provider.services.instance import Instance


class AwsInstance(Instance):
    @staticmethod
    def run(job_cmd: str, dry_run=False) -> Dict[str, str]:
        if dry_run:
            return {"message": job_cmd + "_dry_run"}

        # Launch instance with new volume for anaconda
        print("Launching instance... ", end="", flush=True)
        telemetry.record_event("run")

        start_t = time.monotonic()

        instance_id = AwsInstance._start_instance()

        try:
            # Wait for the instance to be running
            AwsInstance._block_until_instance_running(instance_id)
            end_t = time.monotonic()
            print(f"Instance running. ({round((end_t - start_t), 2)}s)")
            print(f"InstanceId: {instance_id}")
            print()

            time.sleep(5)
            host = AwsInstance._get_host_from_instance_id(instance_id)

            AwsInstance._block_until_ssh_ready(host)

            if job_cmd == "_nimbo_launch":
                print(f"Run 'nimbo ssh {instance_id}' to log onto the instance")
                return {"message": job_cmd + "_success", "instance_id": instance_id}

            ssh = (
                f"ssh -i {CONFIG.instance_key} -o 'StrictHostKeyChecking no'"
                " -o ServerAliveInterval=20 "
            )
            scp = f"scp -i {CONFIG.instance_key} -o 'StrictHostKeyChecking no'"

            local_env = "local_env.yml"
            user_conda_yml = CONFIG.conda_env
            subprocess.check_output(f"cp {user_conda_yml} local_env.yml", shell=True)

            # Send conda env yaml and setup scripts to instance
            print("\nSyncing conda, config, and setup files...")

            # Create project folder and send env and config files there
            subprocess.check_output(
                f"{ssh} ubuntu@{host} " f"mkdir project", shell=True
            )
            subprocess.check_output(
                f"{scp} {local_env} {CONFIG.nimbo_config_file} "
                f"ubuntu@{host}:/home/ubuntu/project/",
                shell=True,
            )
            subprocess.check_output(f"rm {local_env}", shell=True)

            # Sync code with instance
            print("\nSyncing code...")
            AwsInstance._sync_code(host)

            # Run remote_setup script on instance
            AwsInstance._run_remote_script(
                ssh, scp, host, instance_id, job_cmd, "remote_setup.sh"
            )

            return {"message": job_cmd + "_success", "instance_id": instance_id}

        except BaseException as e:
            if (
                type(e) != KeyboardInterrupt
                and type(e) != subprocess.CalledProcessError
            ):
                print(e)

            if not CONFIG.persist:
                print(f"Deleting instance {instance_id} (from local)...")
                AwsInstance.delete_instance(instance_id)

            return {"message": job_cmd + "_error", "instance_id": instance_id}

    @staticmethod
    def run_access_test(dry_run=False) -> None:
        if dry_run:
            return

        CONFIG.instance_type = "t2.medium"
        CONFIG.run_in_background = False
        CONFIG.persist = False

        try:
            # Send test file to s3 results path and delete it
            profile = CONFIG.aws_profile
            region = CONFIG.region_name
            results_path = CONFIG.s3_results_path
            subprocess.check_output(
                "echo 'Hello World' > nimbo-access-test.txt", shell=True
            )
            command = (
                f"aws s3 cp nimbo-access-test.txt {results_path} "
                f" --profile {profile} --region {region}"
            )
            subprocess.check_output(command, shell=True)
            command = f"aws s3 ls {results_path} --profile {profile} --region {region}"
            subprocess.check_output(command, shell=True)
            command = (
                f"aws s3 rm {results_path}/nimbo-access-test.txt "
                f"--profile {profile} --region {region}"
            )
            subprocess.check_output(command, shell=True)

            print(
                "You have the necessary S3 read/write "
                "permissions from your computer \u2713"
            )

        except subprocess.CalledProcessError:
            print("\nError.")
            sys.exit(1)

        # Launch instance with new volume for anaconda
        print("Launching test instance... ", end="", flush=True)

        instance_id = AwsInstance._start_instance()

        try:
            # Wait for the instance to be running
            AwsInstance._block_until_instance_running(instance_id)
            print(f"Instance running. Instance creation allowed \u2713")
            print(f"InstanceId: {instance_id}")
            print()

            print("Trying to delete this instance...")
            AwsInstance.delete_instance(instance_id)

            print("Instance deletion allowed \u2713")
            print("\nLaunching another instance...")
            instance_id = AwsInstance._start_instance()
            print(f"Instance running. InstanceId: {instance_id}")

            time.sleep(5)
            host = AwsInstance._get_host_from_instance_id(instance_id)
            ssh = (
                f"ssh -i {CONFIG.instance_key} -o 'StrictHostKeyChecking no'"
                "-o ServerAliveInterval=20"
            )
            scp = f"scp -i {CONFIG.instance_key} -o 'StrictHostKeyChecking no'"

            AwsInstance._block_until_ssh_ready(host)

            print("Instance key allows ssh access to remote instance \u2713")
            print("Security group allows ssh access to remote instance \u2713")
            subprocess.check_output(
                f"{scp} {CONFIG.nimbo_config_file} " f"ubuntu@{host}:/home/ubuntu/",
                shell=True,
            )
            AwsInstance._run_remote_script(
                ssh, scp, host, instance_id, "", "remote_s3_test.sh"
            )
            print("The instance profile has the required S3 and EC2 permissions \u2713")

            print("\nEverything working \u2713")
            print("Instance has been deleted.")

        except BaseException as e:
            if (
                type(e) != KeyboardInterrupt
                and type(e) != subprocess.CalledProcessError
            ):
                print(e)

            if not CONFIG.persist:
                print(f"Deleting instance {instance_id} (from local)...")
                AwsInstance.delete_instance(instance_id)

            sys.exit(1)

    @staticmethod
    def _block_until_instance_running(instance_id: str) -> None:
        status = ""
        while status != "running":
            time.sleep(1)
            status = AwsInstance.get_instance_status(instance_id)

    @staticmethod
    def _get_host_from_instance_id(instance_id: str, dry_run=False) -> str:
        ec2 = CONFIG.get_session().client("ec2")
        try:
            response = ec2.describe_instances(
                InstanceIds=[instance_id],
                Filters=AwsInstance._make_instance_filters(),
                DryRun=dry_run,
            )
            host = response["Reservations"][0]["Instances"][0]["PublicIpAddress"]
        except botocore.exceptions.ClientError as e:
            if "DryRunOperation" not in str(e):
                raise
            host = ""
        return host

    @staticmethod
    def _get_image_id() -> str:
        if CONFIG.image[:4] == "ami-":
            image_id = CONFIG.image
        else:
            response = requests.get(
                "https://nimboami-default-rtdb.firebaseio.com/images.json"
            )
            catalog = response.json()
            region = CONFIG.region_name
            if region in catalog:
                region_catalog = catalog[region]
                image_name = CONFIG.image
                if image_name in region_catalog:
                    image_id = region_catalog[image_name]
                else:
                    raise ValueError(
                        f"The image {image_name} was not found in the"
                        " image catalog managed by Nimbo.\n"
                        "Check https://docs.nimbo.sh/managed-images"
                        " for the list of managed images."
                    )
            else:
                raise ValueError(
                    f"Currently, Nimbo does not support managed images in {region}."
                    " Please use another region."
                )

        return image_id

    @staticmethod
    def _make_instance_tags() -> List[Dict[str, str]]:
        return [
            {"Key": "CreatedBy", "Value": "nimbo"},
            {"Key": "Owner", "Value": CONFIG.user_id},
        ]

    @staticmethod
    def _make_instance_filters() -> List[Dict[str, Union[str, List[str]]]]:
        tags = AwsInstance._make_instance_tags()
        filters = []
        for tag in tags:
            tag_filter = {"Name": "tag:" + tag["Key"], "Values": [tag["Value"]]}
            filters.append(tag_filter)
        return filters

    @staticmethod
    def _start_instance() -> str:
        ec2 = CONFIG.get_session().client("ec2")
        instance_tags = AwsInstance._make_instance_tags()
        instance_filters = AwsInstance._make_instance_filters()

        image = AwsInstance._get_image_id()
        print(f"Using image {image}")

        ebs_config = {
            "VolumeSize": CONFIG.disk_size,
            "VolumeType": CONFIG.disk_type,
        }
        if CONFIG.disk_iops:
            ebs_config["Iops"] = CONFIG.disk_iops

        instance_config = {
            "BlockDeviceMappings": [{"DeviceName": "/dev/sda1", "Ebs": ebs_config}],
            "ImageId": image,
            "InstanceType": CONFIG.instance_type,
            "KeyName": os.path.basename(CONFIG.instance_key).rstrip(".pem"),
            "Placement": {"Tenancy": "default"},
            "SecurityGroups": [CONFIG.security_group],
            "IamInstanceProfile": {"Name": "NimboInstanceProfile"},
        }

        if CONFIG.spot:
            extra_kwargs = {}
            if CONFIG.spot_duration:
                extra_kwargs = {"BlockDurationMinutes": CONFIG.spot_duration}

            instance = ec2.request_spot_instances(
                LaunchSpecification=instance_config,
                TagSpecifications=[
                    {"ResourceType": "spot-instances-request", "Tags": instance_tags}
                ],
                **extra_kwargs,
            )
            instance_request = instance["SpotInstanceRequests"][0]
            request_id = instance_request["SpotInstanceRequestId"]

            try:
                print("Spot instance request submitted.")
                print(
                    "Waiting for the spot instance request to be fulfilled... ",
                    end="",
                    flush=False,
                )

                status = ""
                while status != "fulfilled":
                    time.sleep(2)
                    response = ec2.describe_spot_instance_requests(
                        SpotInstanceRequestIds=[request_id], Filters=instance_filters,
                    )
                    instance_request = response["SpotInstanceRequests"][0]
                    status = instance_request["Status"]["Code"]
                    if status not in [
                        "fulfilled",
                        "pending-evaluation",
                        "pending-fulfillment",
                    ]:
                        raise Exception(response["SpotInstanceRequests"][0]["Status"])
            except KeyboardInterrupt:
                ec2.cancel_spot_instance_requests(SpotInstanceRequestIds=[request_id])
                print("Cancelled spot instance request.")
                sys.exit(1)

            print("Done.")
            ec2.create_tags(
                Resources=[instance_request["InstanceId"]], Tags=instance_tags,
            )
            instance = instance_request
        else:
            instance_config["MinCount"] = 1
            instance_config["MaxCount"] = 1
            instance_config["TagSpecifications"] = [
                {"ResourceType": "instance", "Tags": instance_tags}
            ]
            instance = ec2.run_instances(**instance_config)
            instance = instance["Instances"][0]

        return instance["InstanceId"]

    @staticmethod
    def stop_instance(instance_id: str, dry_run=False) -> None:
        ec2 = CONFIG.get_session().client("ec2")
        try:
            response = ec2.stop_instances(InstanceIds=[instance_id], DryRun=dry_run)
            pprint(response)
        except botocore.exceptions.ClientError as e:
            if "DryRunOperation" not in str(e):
                raise

    @staticmethod
    def delete_instance(instance_id: str, dry_run=False) -> None:
        ec2 = CONFIG.get_session().client("ec2")
        try:
            response = ec2.terminate_instances(
                InstanceIds=[instance_id], DryRun=dry_run
            )
            status = response["TerminatingInstances"][0]["CurrentState"]["Name"]
            print(f"Instance {instance_id}: {status}")
        except botocore.exceptions.ClientError as e:
            if "DryRunOperation" not in str(e):
                raise

    @staticmethod
    def delete_all_instances(dry_run=False) -> None:
        ec2 = CONFIG.get_session().client("ec2")
        try:
            response = ec2.describe_instances(
                Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
                + AwsInstance._make_instance_filters(),
                DryRun=dry_run,
            )
            for reservation in response["Reservations"]:
                for inst in reservation["Instances"]:
                    instance_id = inst["InstanceId"]
                    delete_response = ec2.terminate_instances(
                        InstanceIds=[instance_id],
                    )
                    status = delete_response["TerminatingInstances"][0]["CurrentState"][
                        "Name"
                    ]
                    print(f"Instance {instance_id}: {status}")
        except botocore.exceptions.ClientError as e:
            if "DryRunOperation" not in str(e):
                raise

    @staticmethod
    def get_instance_status(instance_id: str, dry_run=False) -> str:
        ec2 = CONFIG.get_session().client("ec2")
        try:
            response = ec2.describe_instances(
                InstanceIds=[instance_id],
                Filters=AwsInstance._make_instance_filters(),
                DryRun=dry_run,
            )
            status = response["Reservations"][0]["Instances"][0]["State"]["Name"]
            return status
        except botocore.exceptions.ClientError as e:
            if "DryRunOperation" not in str(e):
                raise

    @staticmethod
    def ls_active_instances(dry_run=False) -> None:
        ec2 = CONFIG.get_session().client("ec2")
        try:
            response = ec2.describe_instances(
                Filters=[
                    {"Name": "instance-state-name", "Values": ["running", "pending"]}
                ]
                + AwsInstance._make_instance_filters(),
                DryRun=dry_run,
            )
            for reservation in response["Reservations"]:
                for inst in reservation["Instances"]:
                    print(
                        f"Id: {inst['InstanceId']}\n"
                        f"Status: {inst['State']['Name']}\n"
                        f"Launch Time: {inst['LaunchTime']}\n"
                        f"InstanceType: {inst['InstanceType']}\n"
                        f"IP Address: {inst['PublicIpAddress']}\n"
                    )

        except botocore.exceptions.ClientError as e:
            if "DryRunOperation" not in str(e):
                raise

    @staticmethod
    def ls_stopped_instances(dry_run=False) -> None:
        ec2 = CONFIG.get_session().client("ec2")
        try:
            response = ec2.describe_instances(
                Filters=[
                    {"Name": "instance-state-name", "Values": ["stopped", "stopping"]}
                ]
                + AwsInstance._make_instance_filters(),
                DryRun=dry_run,
            )
            for reservation in response["Reservations"]:
                for inst in reservation["Instances"]:
                    print(
                        f"ID: {inst['InstanceId']}\n"
                        f"Launch Time: {inst['LaunchTime']}\n"
                        f"InstanceType: {inst['InstanceType']}\n"
                    )
        except botocore.exceptions.ClientError as e:
            if "DryRunOperation" not in str(e):
                raise
