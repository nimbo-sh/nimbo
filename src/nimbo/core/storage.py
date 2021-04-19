import logging
import subprocess
from os.path import join

import boto3
from botocore.exceptions import ClientError

from nimbo.core.globals import CONFIG, SESSION
from .utils import handle_boto_client_errors


@handle_boto_client_errors
def upload_file(file_name, bucket, object_name=None):
    """Upload a file to an S3 bucket

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :return: True if file was uploaded, else False
    """

    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = file_name

    # Upload the file
    s3 = SESSION.client("s3")
    try:
        s3.upload_file(file_name, bucket, object_name)
    except ClientError as e:
        logging.error(e)
        return False
    return True


@handle_boto_client_errors
def create_bucket(bucket_name, dry_run):
    """Create an S3 bucket in a specified region

    :param bucket_name: Bucket to create
    :param dry_run
    :return: True if bucket created, else False
    """

    # Create bucket
    try:
        s3 = SESSION.client("s3")
        location = {"LocationConstraint": SESSION.region_name}
        s3.create_bucket(Bucket=bucket_name, CreateBucketConfiguration=location)
    except ClientError as e:
        if e.response["Error"]["Code"] == "BucketAlreadyOwnedByYou":
            print("Bucket nimbo-main-bucket already exists.")
        else:
            logging.error(e)
        return False

    print("Bucket %s created." % bucket_name)
    return True


@handle_boto_client_errors
def list_buckets(bucket_name):

    # Retrieve the list of existing buckets
    s3 = boto3.client("s3")
    response = s3.list_buckets()

    # Output the bucket names
    print("Existing buckets:")
    for bucket in response["Buckets"]:
        print(f' {bucket["Name"]}')


@handle_boto_client_errors
def list_snapshots():
    # Retrieve the list of existing buckets
    ec2 = SESSION.client("ec2")

    response = ec2.describe_snapshots(
        Filters=[{"Name": "tag:created_by", "Values": ["nimbo"]}], MaxResults=100,
    )
    return list(sorted(response["Snapshots"], key=lambda x: x["StartTime"]))


@handle_boto_client_errors
def check_snapshot_state(snapshot_id):
    ec2 = SESSION.client("ec2")
    response = ec2.describe_snapshots(SnapshotIds=[snapshot_id])
    return response["Snapshots"][0]["State"]


def sync_folder(source, target, profile, region, delete=False):
    command = f"aws s3 sync {source} {target} --profile {profile} --region {region}"
    if delete:
        command = command + " --delete"
    print(f"\nRunning command: {command}\n")
    subprocess.Popen(command, shell=True).communicate()


def pull(folder, delete=False):
    assert folder in ["datasets", "results", "logs"]

    if folder == "logs":
        source = join(CONFIG.s3_results_path, "nimbo-logs")
        target = join(CONFIG.local_results_path, "nimbo-logs")
    else:
        if folder == "results":
            source = CONFIG.s3_results_path
            target = CONFIG.local_results_path
        else:
            source = CONFIG.s3_datasets_path
            target = CONFIG.local_datasets_path

    sync_folder(source, target, CONFIG.aws_profile, CONFIG.region_name, delete)


def push(folder, delete=False):
    assert folder in ["datasets", "results", "logs"]

    if folder == "logs":
        source = join(CONFIG.local_results_path, "nimbo-logs")
        target = join(CONFIG.s3_results_path, "nimbo-logs")
    else:
        if folder == "results":
            source = CONFIG.local_results_path
            target = CONFIG.s3_results_path
        else:
            source = CONFIG.local_datasets_path
            target = CONFIG.s3_datasets_path

    sync_folder(source, target, CONFIG.aws_profile, CONFIG.region_name, delete)


def ls(path):
    profile = CONFIG.aws_profile
    region = CONFIG.region_name
    path = path.rstrip("/") + "/"
    command = f"aws s3 ls {path} --profile {profile} --region {region}"
    print(f"Running command: {command}")
    subprocess.Popen(command, shell=True).communicate()
