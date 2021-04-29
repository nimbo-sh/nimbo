import os.path
import subprocess

import botocore.exceptions

from nimbo import CONFIG
from nimbo.core.cloud_provider.provider.services.storage import Storage


class AwsStorage(Storage):
    # noinspection DuplicatedCode
    @staticmethod
    def push(directory: str, delete=False) -> None:
        assert directory in ["datasets", "results", "logs"]

        if directory == "logs":
            source = os.path.join(CONFIG.local_results_path, "nimbo-logs")
            target = os.path.join(CONFIG.s3_results_path, "nimbo-logs")
        else:
            if directory == "results":
                source = CONFIG.local_results_path
                target = CONFIG.s3_results_path
            else:
                source = CONFIG.local_datasets_path
                target = CONFIG.s3_datasets_path

        AwsStorage._sync_folder(
            source, target, CONFIG.aws_profile, CONFIG.region_name, delete
        )

    # noinspection DuplicatedCode
    @staticmethod
    def pull(directory: str, delete=False) -> None:
        assert directory in ["datasets", "results", "logs"]

        if directory == "logs":
            source = os.path.join(CONFIG.s3_results_path, "nimbo-logs")
            target = os.path.join(CONFIG.local_results_path, "nimbo-logs")
        else:
            if directory == "results":
                source = CONFIG.s3_results_path
                target = CONFIG.local_results_path
            else:
                source = CONFIG.s3_datasets_path
                target = CONFIG.local_datasets_path

        AwsStorage._sync_folder(
            source, target, CONFIG.aws_profile, CONFIG.region_name, delete
        )

    @staticmethod
    def ls(path: str) -> None:
        profile = CONFIG.aws_profile
        region = CONFIG.region_name
        path = path.rstrip("/") + "/"
        command = f"aws s3 ls {path} --profile {profile} --region {region}"
        print(f"Running command: {command}")
        subprocess.Popen(command, shell=True).communicate()

    @staticmethod
    def mk_bucket(bucket_name: str, dry_run=False) -> bool:
        # TODO: return value

        """Create an S3 bucket in a specified region

        :param bucket_name: Bucket to create
        :param dry_run
        :return: True if bucket created, else False
        """

        try:
            session = CONFIG.get_session()
            s3 = session.client("s3")
            location = {"LocationConstraint": session.region_name}
            s3.create_bucket(
                Bucket=bucket_name, CreateBucketConfiguration=location, DryRun=dry_run
            )
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "BucketAlreadyOwnedByYou":
                print("Bucket nimbo-main-bucket already exists.")
            else:
                print(e)
            return False

        print("Bucket %s created." % bucket_name)
        return True

    @staticmethod
    def ls_buckets() -> None:
        s3 = CONFIG.get_session().client("s3")
        response = s3.list_buckets()

        print("Existing buckets:")
        for bucket in response["Buckets"]:
            print(f' {bucket["Name"]}')

    @staticmethod
    def _sync_folder(source, target, profile, region, delete=False) -> None:
        command = f"aws s3 sync {source} {target} --profile {profile} --region {region}"
        if delete:
            command = command + " --delete"
        print(f"\nRunning command: {command}\n")
        subprocess.Popen(command, shell=True).communicate()
