import subprocess
import sys
import time
from pathlib import Path
from pprint import pprint
from typing import Dict, List, Union

import botocore.exceptions
import requests

from nimbo import CONFIG
from nimbo.core import telemetry
from nimbo.core.cloud_provider.provider.services.instance import Instance
from nimbo.core.cloud_provider.provider_impl.aws.services.aws_permissions import (
    AwsPermissions,
)
from nimbo.core.cloud_provider.provider_impl.aws.services.aws_storage import AwsStorage
from nimbo.core.constants import NIMBO_VARS
from nimbo.core.print import nprint, nprint_header


class AwsInstance(Instance):
    @staticmethod
    def run(job_cmd: str, dry_run=False) -> Dict[str, str]:
        if dry_run:
            return {"message": job_cmd + "_dry_run"}

        # Launch instance with new volume for anaconda
        telemetry.record_event("run")

        start_t = time.monotonic()

        instance_id = AwsInstance._start_instance()

        try:
            # Wait for the instance to be running
            AwsInstance._block_until_instance_running(instance_id)
            end_t = time.monotonic()
            nprint_header(f"Instance running. ({round((end_t - start_t), 2)} s)")
            nprint_header(f"InstanceId: [green]{instance_id}[/green]")
            print()

            time.sleep(5)
            host = AwsInstance._get_host_from_instance_id(instance_id)

            AwsInstance._block_until_ssh_ready(host)

            if job_cmd == "_nimbo_launch":
                nprint_header(
                    f"Run [cyan]nimbo ssh {instance_id}[/cyan] to log onto the instance"
                )
                return {"message": job_cmd + "_success", "instance_id": instance_id}

            ssh = (
                f"ssh -i {CONFIG.instance_key} -o 'StrictHostKeyChecking no'"
                " -o ServerAliveInterval=5 "
            )
            scp = f"scp -i {CONFIG.instance_key} -o 'StrictHostKeyChecking no'"

            local_env = "/tmp/local_env.yml"
            user_conda_yml = CONFIG.conda_env
            # TODO: Replace this with shutil
            subprocess.check_output(f"cp {user_conda_yml} {local_env}", shell=True)

            # Send conda env yaml and setup scripts to instance
            print()
            nprint_header(f"Syncing conda, config, and setup files...")
            AwsInstance._write_nimbo_vars()

            # Create project folder and send env and config files there
            subprocess.check_output(f"{ssh} ubuntu@{host} mkdir project", shell=True)
            subprocess.check_output(
                f"{scp} {local_env} {CONFIG.config_path} {NIMBO_VARS}"
                f" ubuntu@{host}:/home/ubuntu/project/",
                shell=True,
            )

            # Sync code with instance
            print()
            nprint_header(f"Syncing code...")
            AwsInstance._sync_code(host)

            nprint_header(f"Running setup code on the instance from here on.")
            # Run remote_setup script on instance
            AwsInstance._run_remote_script(
                ssh, scp, host, instance_id, job_cmd, "remote_setup.sh"
            )

            if job_cmd == "_nimbo_notebook":
                subprocess.Popen(
                    f"{ssh} -o 'ExitOnForwardFailure yes' "
                    f"ubuntu@{host} -NfL 57467:localhost:57467 >/dev/null 2>&1",
                    shell=True,
                ).communicate()
                nprint_header(
                    "Make sure to run 'nimbo sync-notebooks <instance_id>' frequently "
                    "to sync the notebook to your local folder, as the remote notebooks"
                    " will be lost once the instance is terminated."
                )

            return {"message": job_cmd + "_success", "instance_id": instance_id}

        except BaseException as e:
            if (
                type(e) != KeyboardInterrupt
                and type(e) != subprocess.CalledProcessError
            ):
                nprint(e, style="error")

            if not CONFIG.persist:
                nprint_header(f"Deleting instance {instance_id} (from local)... ")
                AwsInstance.delete_instance(instance_id)

            return {"message": job_cmd + "_error", "instance_id": instance_id}

    @staticmethod
    def run_access_test(dry_run=False) -> None:
        if dry_run:
            return

        CONFIG.instance_type = "t3.medium"
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
            command = AwsStorage.mk_s3_command(
                "cp", "nimbo-access-test.txt", results_path
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

        except subprocess.CalledProcessError as e:
            nprint(e, style="error")
            sys.exit(1)

        # Launch instance with new volume for anaconda
        print("Launching test instance... ")

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
                f"ssh -i {CONFIG.instance_key} -o 'StrictHostKeyChecking no' "
                "-o ServerAliveInterval=20"
            )
            scp = f"scp -i {CONFIG.instance_key} -o 'StrictHostKeyChecking no'"

            AwsInstance._block_until_ssh_ready(host)

            print("Instance key allows ssh access to remote instance \u2713")
            print("Security group allows ssh access to remote instance \u2713")

            AwsInstance._write_nimbo_vars()

            subprocess.check_output(
                f"{scp} {CONFIG.config_path} {NIMBO_VARS} "
                + f"ubuntu@{host}:/home/ubuntu/",
                shell=True,
            )
            AwsInstance._run_remote_script(
                ssh, scp, host, instance_id, "", "remote_s3_test.sh"
            )

        except BaseException as e:
            if (
                type(e) != KeyboardInterrupt
                and type(e) != subprocess.CalledProcessError
            ):
                nprint(e, style="error")

            if not CONFIG.persist:
                nprint_header(f"Deleting instance {instance_id} (from local)...")
                AwsInstance.delete_instance(instance_id)

            sys.exit(1)

    @staticmethod
    def _block_until_instance_running(instance_id: str) -> None:
        status = ""
        while status != "running":
            time.sleep(1)
            status = AwsInstance.get_status(instance_id)

    @staticmethod
    def _write_nimbo_vars() -> None:
        var_list = [
            f"S3_DATASETS_PATH={CONFIG.s3_datasets_path}",
            f"S3_RESULTS_PATH={CONFIG.s3_results_path}",
            f"LOCAL_DATASETS_PATH={CONFIG.local_datasets_path}",
            f"LOCAL_RESULTS_PATH={CONFIG.local_results_path}",
        ]
        if CONFIG.encryption:
            var_list.append(f"ENCRYPTION={CONFIG.encryption}")
        with open(NIMBO_VARS, "w") as f:
            f.write("\n".join(var_list))

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
        AwsPermissions.allow_ingress_current_ip(CONFIG.security_group)

        ec2 = CONFIG.get_session().client("ec2")
        instance_tags = AwsInstance._make_instance_tags()
        instance_filters = AwsInstance._make_instance_filters()

        image = AwsInstance._get_image_id()
        nprint_header(f"Launching instance with image {image}... ")

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
            "KeyName": Path(CONFIG.instance_key).stem,
            "Placement": {"Tenancy": "default"},
            "SecurityGroups": [CONFIG.security_group],
            "IamInstanceProfile": {"Name": CONFIG.role},
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
                nprint_header("Spot instance request submitted.")
                nprint_header(
                    "Waiting for the spot instance request to be fulfilled... "
                )

                status = ""
                while status != "fulfilled":
                    time.sleep(2)
                    response = ec2.describe_spot_instance_requests(
                        SpotInstanceRequestIds=[request_id],
                        Filters=instance_filters,
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
                nprint_header("Cancelled spot instance request.")
                sys.exit(1)

            nprint_header("Done.")
            ec2.create_tags(
                Resources=[instance_request["InstanceId"]],
                Tags=instance_tags,
            )
            instance = instance_request
        else:
            instance_config["MinCount"] = 1
            instance_config["MaxCount"] = 1
            instance_config["InstanceInitiatedShutdownBehavior"] = "terminate"
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
    def resume_instance(instance_id: str, dry_run=False) -> None:
        ec2 = CONFIG.get_session().client("ec2")
        try:
            response = ec2.start_instances(InstanceIds=[instance_id], DryRun=dry_run)
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
            nprint_header(f"Instance [green]{instance_id}[/green]: {status}")
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
                    nprint_header(f"Instance [green]{instance_id}[/green]: {status}")
        except botocore.exceptions.ClientError as e:
            if "DryRunOperation" not in str(e):
                raise

    @staticmethod
    def get_status(instance_id: str, dry_run=False) -> str:
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
                    nprint(
                        f"Id: [bright_green]{inst['InstanceId']}[/bright_green]\n"
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
