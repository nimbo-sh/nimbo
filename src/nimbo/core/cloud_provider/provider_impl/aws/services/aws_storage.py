import botocore.exceptions

from nimbo import CONFIG
from nimbo.core.cloud_provider.provider.services.storage import Storage
from nimbo.core.print import NimboPrint


class AwsStorage(Storage):
    @staticmethod
    def push(directory: str, delete=False) -> None:
        pass

    @staticmethod
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
            elif error_code == "AccessDenied":
                NimboPrint.error(
                    """
                    Access denied - make sure that the role defined in Nimbo config
                    has the 's3:CreateBucket' action for creating S3 buckets.
                    """
                )
            else:
                raise

        try:
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
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "AccessDenied":
                NimboPrint.error(
                    f"""
                    Access denied - make sure that the role defined in Nimbo config has
                    the 's3:PutBucketPublicAccessBlock' action.
                    """
                )
            else:
                raise

        NimboPrint.success(f"Bucket {bucket_name} created.")

    @staticmethod
    def ls_bucket(bucket_name: str, prefix: str) -> None:
        s3 = CONFIG.get_session().client("s3")

        try:
            for obj in s3.list_objects(Bucket=bucket_name, Prefix=prefix)["Contents"]:
                print(obj["Key"])
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "AccessDenied":
                NimboPrint.error(
                    f"""
                    Access denied - make sure that you own the bucket {bucket_name},
                    and that the role defined in Nimbo config has the 's3:ListBucket'
                    action.
                    """
                )
            else:
                raise

    @staticmethod
    def ls_buckets() -> None:
        s3 = CONFIG.get_session().client("s3")

        try:
            for bucket in s3.list_buckets()["Buckets"]:
                print(bucket["Name"])
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "AccessDenied":
                NimboPrint.error(
                    f"""
                    Access denied - make sure that the role defined in Nimbo config has
                    the 's3:ListAllMyBuckets' action.
                    """
                )
            else:
                raise
