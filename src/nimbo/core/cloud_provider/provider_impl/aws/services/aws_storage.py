import functools
import os

import botocore.exceptions

from nimbo import CONFIG
from nimbo.core.cloud_provider.provider.services.storage import Storage
from nimbo.core.print import NimboPrint


def _handle_common_exceptions(func):
    @functools.wraps(func)
    def decorated(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "AccessDenied":
                NimboPrint.error("Access denied.")
            else:
                raise

    return decorated


class AwsStorage(Storage):
    @staticmethod
    def _get_bucket_name(s3_path: str) -> str:
        # TODO: this should be somewhere else, not reliable
        return s3_path.replace("s3://", "").split("/")[0]

    @staticmethod
    @_handle_common_exceptions
    def push(directory: str, delete=False) -> None:
        # TODO: this function is wayy too long

        local_dir = (
            CONFIG.local_results_path
            if directory == "results"
            else CONFIG.local_datasets_path
        )
        remote_dir = (
            CONFIG.s3_results_path
            if directory == "results"
            else CONFIG.s3_datasets_path
        )

        # Paths generated by os.walk include basename of local_dir
        root_prefix = len(os.path.basename(local_dir)) + 1

        all_files_in_local_dir = [
            os.path.join(common_dir, file)[root_prefix:]
            for common_dir, _, files in os.walk(local_dir)
            for file in files
        ]
        step_count = len(all_files_in_local_dir) + 1

        s3 = CONFIG.get_session().client("s3")

        NimboPrint.step(
            1, step_count, f"Pushing files from {local_dir} to {remote_dir}."
        )
        extra_args = (
            {"ServerSideEncryption": CONFIG.encryption} if CONFIG.encryption else {}
        )
        for index, file in enumerate(all_files_in_local_dir, start=2):
            local_file_path = os.path.join(local_dir, file)
            NimboPrint.step(index, step_count, f"Uploading {local_file_path}.")
            s3.upload_file(
                Filename=local_file_path,
                Bucket=AwsStorage._get_bucket_name(remote_dir),
                Key=file,
                ExtraArgs=extra_args,
            )
        NimboPrint.success("All files have been pushed.")

    @staticmethod
    @_handle_common_exceptions
    def pull(directory: str, delete=False) -> None:
        pass

    # @staticmethod
    # def _sync_folder(source, target, delete=False) -> None:
    #     command = AwsStorage.mk_s3_command("sync", source, target, delete)
    #     print(f"\nRunning command: {command}")
    #     subprocess.Popen(command, shell=True).communicate()

    # @staticmethod
    # TODO: this is used in multiple places
    # def mk_s3_command(cmd, source, target, delete=False) -> str:
    #     command = (
    #         f"aws s3 {cmd} {source} {target}"
    #         f" --profile {CONFIG.aws_profile} --region {CONFIG.region_name}"
    #     )

    #     if delete:
    #         command += " --delete"

    #     if CONFIG.encryption:
    #         command += f" --sse {CONFIG.encryption}"
    #     return command

    # noinspection DuplicatedCode
    # @staticmethod
    # def push(folder: str, delete=False) -> None:
    #     assert folder in ["datasets", "results", "logs"]

    #     if folder == "logs":
    #         source = os.path.join(CONFIG.local_results_path, "nimbo-logs")
    #         target = os.path.join(CONFIG.s3_results_path, "nimbo-logs")
    #     else:
    #         if folder == "results":
    #             source = CONFIG.local_results_path
    #             target = CONFIG.s3_results_path
    #         else:
    #             source = CONFIG.local_datasets_path
    #             target = CONFIG.s3_datasets_path

    #     AwsStorage._sync_folder(source, target, delete)

    # noinspection DuplicatedCode
    # @staticmethod
    # def pull(folder: str, delete=False) -> None:
    #     assert folder in ["datasets", "results", "logs"]

    #     if folder == "logs":
    #         source = os.path.join(CONFIG.s3_results_path, "nimbo-logs")
    #         target = os.path.join(CONFIG.local_results_path, "nimbo-logs")
    #     else:
    #         if folder == "results":
    #             source = CONFIG.s3_results_path
    #             target = CONFIG.local_results_path
    #         else:
    #             source = CONFIG.s3_datasets_path
    #             target = CONFIG.local_datasets_path

    #     AwsStorage._sync_folder(source, target, delete)

    @staticmethod
    @_handle_common_exceptions
    def mk_bucket(bucket_name: str) -> None:
        s3 = CONFIG.get_session().client("s3")

        try:
            NimboPrint.step(1, 2, f"Creating bucket {bucket_name}.")
            s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": CONFIG.region_name},
            )
        except botocore.exceptions.ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code in {"BucketAlreadyOwnedByYou", "BucketAlreadyExists"}:
                NimboPrint.error(f"Bucket {bucket_name} already exists.")
            elif error_code == "InvalidBucketName":
                NimboPrint.error(
                    f"""
                    Bucket name {bucket_name} is invalid, please refer to
                    https://ext.nimbo.sh/j9l for bucket naming rules.
                    """
                )
            else:
                raise

        NimboPrint.step(2, 2, f"Making bucket {bucket_name} private.")
        s3.put_public_access_block(
            Bucket=bucket_name,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            },
        )

        NimboPrint.success(f"Bucket {bucket_name} created.")

    @staticmethod
    @_handle_common_exceptions
    def ls_bucket(bucket_name: str, prefix: str) -> None:
        s3 = CONFIG.get_session().client("s3")

        for obj in s3.list_objects(Bucket=bucket_name, Prefix=prefix)["Contents"]:
            print(obj["Key"])

    @staticmethod
    @_handle_common_exceptions
    def ls_buckets() -> None:
        s3 = CONFIG.get_session().client("s3")

        for bucket in s3.list_buckets()["Buckets"]:
            print(bucket["Name"])
