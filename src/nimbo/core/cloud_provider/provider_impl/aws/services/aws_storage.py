import collections
import functools
import os
import typing as t
from datetime import datetime, timezone

import boto3.exceptions
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
        # AWSCLI has a regex for parsing s3_paths :))), should probably replace
        # globally AWS_CONFIG to expect the regex, and parse it in some object.
        # https://github.com/aws/aws-cli/blob/45b0063b2d0b245b17a57fd9eebd9fcc87c4426a/awscli/customizations/s3/utils.py
        return s3_path.split("/")[2]

    @staticmethod
    def _get_s3_basedir(s3_path: str) -> str:
        # TODO: this should be somewhere else, not reliable
        return "/".join(s3_path.split("/")[3:])

    @staticmethod
    @_handle_common_exceptions
    def push(directory: str, delete=False) -> None:
        """
        TODO:
        1. Test uploading 1GB-10GB files. Automatically use multipart upload for large files?
        2. Should multithreading uploads.
        3. I don't like the fact that I'm building in-memory data structures that hold
           the differences. 100M file paths in memory take around 1-2GB of RAM.
           Uploading 1M files to S3 costs $5USD just in pricing per 1000 requests.
           ext4 supports having 4 billion files.

           If we to stream differences, there are two issues:
           - Cannot detect if a directory has been renamed, so everything in a renamed
             directory will be re-uploaded.
           - When pushing, will have to build a set of paths of what to delete to
             collect delete requests and make it cheaper, which is problematic in some
             edge cases. Alternatively, delete per object, which will increase the overall
             delete cost by a factor of 1000x. But for this we could just display
             a warning explaining why the 1000x price increase, and suggest to
             delete the bucket, and push from scratch.
        """

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

        not_in_local, not_in_remote = AwsStorage._symmetric_diff(local_dir, remote_dir)

        if len(not_in_local) == 0 and len(not_in_remote) == 0:
            NimboPrint.success("Nothing to push.")
            return

        s3 = CONFIG.get_session().client("s3")
        bucket_name = AwsStorage._get_bucket_name(remote_dir)
        s3_base_dir = AwsStorage._get_s3_basedir(remote_dir)

        extra_step = 0

        # TODO: limited to 1000
        if delete and not_in_local:
            extra_step = 1
            NimboPrint.step(
                1,
                2 if not_in_remote else 1,
                f"Deleting {len(not_in_local)} object(s) from {remote_dir}",
            )
            s3.delete_objects(
                Bucket=bucket_name,
                Delete={
                    "Objects": [
                        {"Key": os.path.join(s3_base_dir, file_path)}
                        for file_path in not_in_local
                    ]
                },
            )

        if not not_in_remote:
            NimboPrint.success("Files deleted.")
            return

        NimboPrint.step(
            1 + extra_step,
            1 + extra_step,
            f"Uploading files from ./{local_dir} to {remote_dir}",
        )

        extra_args = (
            {"ServerSideEncryption": CONFIG.encryption.value}
            if CONFIG.encryption
            else {}
        )

        for file_path in not_in_remote:
            local_file_path = os.path.join(local_dir, file_path)
            remote_file_path = os.path.join(s3_base_dir, file_path)

            NimboPrint.indented(6, f"- ./{local_file_path}")
            try:
                s3.upload_file(
                    Filename=local_file_path,
                    Bucket=bucket_name,
                    Key=remote_file_path,
                    ExtraArgs=extra_args,
                )
            except boto3.exceptions.S3UploadFailedError as e:
                NimboPrint.error(str(e))
                return
        NimboPrint.success("All files have been pushed.")

    @staticmethod
    def _symmetric_diff(
        local_dir: str, remote_dir: str
    ) -> t.Tuple[t.Set[str], t.Set[str]]:
        """
        Find and return:
        the set of paths that are in S3 and not locally,
        the set of paths that are locally, but not in S3.
        The returned paths do not include parent directories, just like in UNIX 'ls'
        """

        l_gen = AwsStorage._ls_local_dir(local_dir)
        r_gen = AwsStorage._ls_bucket(
            AwsStorage._get_bucket_name(remote_dir),
            AwsStorage._get_s3_basedir(remote_dir),
        )

        not_in_local, not_in_remote = set(), set()

        l_path, l_last_modified = next(l_gen, (None, None))
        r_path, r_last_modified = next(r_gen, (None, None))

        while l_path and r_path:
            if r_path < l_path:
                not_in_local.add(r_path)
                r_path, r_last_modified = next(r_gen, (None, None))
            elif r_path > l_path:
                not_in_remote.add(l_path)
                l_path, l_last_modified = next(l_gen, (None, None))
            else:
                if r_last_modified <= l_last_modified:
                    not_in_remote.add(l_path)
                l_path, l_last_modified = next(l_gen, (None, None))
                r_path, r_last_modified = next(r_gen, (None, None))
        while l_path:
            not_in_remote.add(l_path)
            l_path, l_last_modified = next(l_gen, (None, None))
        while r_path:
            not_in_local.add(r_path)
            r_path, r_last_modified = next(r_gen, (None, None))

        return not_in_local, not_in_remote

    @staticmethod
    def _ls_local_dir(path: str) -> t.Generator[t.Tuple[str, datetime], None, None]:
        """
        Recursively find all paths to files in a directory, sorted alphabetically.
        Each path is relative to the given path argument.
        """

        base_prefix = len(path) + 1  # +1 to account for /
        to_traverse = collections.deque([path])

        while len(to_traverse) > 0:
            curr_path = to_traverse.popleft()

            if os.path.isdir(curr_path):
                # If '/' is not added after directories, once the directories get
                # expanded, the resulting file list might not be sorted properly.
                # e.g. shared-name/file.txt, shared-name.txt
                to_traverse.extendleft(
                    sorted(
                        map(
                            lambda p: p + "/" if os.path.isdir(p) else p,
                            (os.path.join(curr_path, p) for p in os.listdir(curr_path)),
                        ),
                        reverse=True,
                    )
                )
            elif os.path.isfile(curr_path):
                last_modified = datetime.fromtimestamp(
                    round(os.path.getmtime(os.path.join(curr_path))), tz=timezone.utc
                )
                yield curr_path[base_prefix:], last_modified

    @staticmethod
    def _ls_bucket(
        bucket_name: str, prefix: str
    ) -> t.Generator[t.Tuple[str, datetime], None, None]:
        """
        Recursively find all paths to files in an s3 bucket, sorted alphabetically.
        Each path is relative to the bucket_name.
        """

        s3 = CONFIG.get_session().client("s3")
        paginator = s3.get_paginator("list_objects_v2")
        page_iter = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

        prefix_len = 0 if len(prefix) == 0 else len(prefix) + 1

        for page in page_iter:
            if "Contents" in page:
                for obj in page["Contents"]:
                    yield obj["Key"][prefix_len:], obj["LastModified"]

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
    def rm_bucket(bucket_name: str) -> None:
        session = CONFIG.get_session()
        s3_resource = session.resource("s3")
        s3_client = session.client("s3")

        bucket = s3_resource.Bucket(bucket_name)
        bucket_versioning = s3_resource.BucketVersioning(bucket_name)

        try:
            NimboPrint.step(1, 2, f"Emptying bucket {bucket_name}.")
            if bucket_versioning.status == "Enabled":
                bucket.object_versions.delete()
            else:
                bucket.objects.all().delete()

            NimboPrint.step(2, 2, f"Deleting bucket {bucket_name}.")
            s3_client.delete_bucket(Bucket=bucket_name)
        except botocore.exceptions.ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "NoSuchBucket":
                NimboPrint.error(f"Bucket {bucket_name} does not exist.")
                return
            else:
                raise
        NimboPrint.success(f"Bucket {bucket_name} has been deleted.")

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
                return
            elif error_code == "InvalidBucketName":
                NimboPrint.error(
                    f"""
                    Bucket name {bucket_name} is invalid, please refer to
                    https://ext.nimbo.sh/j9l for bucket naming rules.
                    """
                )
                return
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

        NimboPrint.success(f"Bucket {bucket_name} has been created.")

    @staticmethod
    @_handle_common_exceptions
    def ls_bucket(bucket_name: str, prefix: str) -> None:
        for file, _ in AwsStorage._ls_bucket(bucket_name, prefix):
            print(file)

    @staticmethod
    @_handle_common_exceptions
    def ls_buckets() -> None:
        s3 = CONFIG.get_session().client("s3")

        for bucket in s3.list_buckets()["Buckets"]:
            print(bucket["Name"])
