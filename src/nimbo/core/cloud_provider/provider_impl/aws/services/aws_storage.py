import os.path
import subprocess

import botocore.exceptions

from nimbo import CONFIG
from nimbo.core.cloud_provider.provider.services.storage import Storage
from nimbo.core.print import nprint


class AwsStorage(Storage):
    # noinspection DuplicatedCode
    @staticmethod
    def push(folder: str, delete=False) -> None:
        assert folder in ["datasets", "results", "logs"]

        if folder == "logs":
            source = os.path.join(CONFIG.local_results_path, "nimbo-logs")
            target = os.path.join(CONFIG.s3_results_path, "nimbo-logs")
        else:
            if folder == "results":
                source = CONFIG.local_results_path
                target = CONFIG.s3_results_path
            else:
                source = CONFIG.local_datasets_path
                target = CONFIG.s3_datasets_path

        AwsStorage._sync_folder(source, target, delete)

    # noinspection DuplicatedCode
    @staticmethod
    def pull(folder: str, delete=False) -> None:
        assert folder in ["datasets", "results", "logs"]

        if folder == "logs":
            source = os.path.join(CONFIG.s3_results_path, "nimbo-logs")
            target = os.path.join(CONFIG.local_results_path, "nimbo-logs")
        else:
            if folder == "results":
                source = CONFIG.s3_results_path
                target = CONFIG.local_results_path
            else:
                source = CONFIG.s3_datasets_path
                target = CONFIG.local_datasets_path

        AwsStorage._sync_folder(source, target, delete)

    @staticmethod
    def ls_bucket(path: str) -> None:
        profile = CONFIG.aws_profile
        region = CONFIG.region_name
        path = path.rstrip("/") + "/"
        command = f"aws s3 ls {path} --profile {profile} --region {region}"
        print(f"Running command: {command}")
        subprocess.Popen(command, shell=True).communicate()

    @staticmethod
    def mk_bucket(bucket_name: str, dry_run=False) -> None:
        """Create an S3 bucket in a specified region

        :param bucket_name: Bucket to create
        :param dry_run
        :return: True if bucket created, else False
        """

        try:
            session = CONFIG.get_session()
            s3 = session.client("s3")
            location = {"LocationConstraint": session.region_name}
            s3.create_bucket(Bucket=bucket_name, CreateBucketConfiguration=location)
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "BucketAlreadyOwnedByYou":
                nprint("Bucket nimbo-main-bucket already exists.", style="warning")
            else:
                nprint(e, style="error")
            return

        print("Bucket %s created." % bucket_name)

    @staticmethod
    def _sync_folder(source, target, delete=False) -> None:
        command = AwsStorage.mk_s3_command("sync", source, target, delete)
        print(f"\nRunning command: {command}")
        subprocess.Popen(command, shell=True).communicate()

    @staticmethod
    def mk_s3_command(cmd, source, target, delete=False) -> str:
        command = (
            f"aws s3 {cmd} {source} {target} "
            f" --profile {CONFIG.aws_profile} --region {CONFIG.region_name}"
        )

        if delete:
            command += " --delete"

        if CONFIG.encryption:
            command += f" --sse {CONFIG.encryption}"
        return command
