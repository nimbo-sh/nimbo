import logging
import subprocess
from os.path import join

import boto3
from botocore.exceptions import ClientError

from .utils import handle_boto_client_errors


@handle_boto_client_errors
def upload_file(session, file_name, bucket, object_name=None):
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
    s3 = session.client("s3")
    try:
        response = s3.upload_file(file_name, bucket, object_name)
    except ClientError as e:
        logging.error(e)
        return False
    return True


@handle_boto_client_errors
def create_bucket(session, bucket_name, dry_run):
    """Create an S3 bucket in a specified region

    :param bucket_name: Bucket to create
    :return: True if bucket created, else False
    """

    # Create bucket
    try:
        s3 = session.client("s3")
        location = {"LocationConstraint": session.region_name}
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
def list_buckets(session, bucket_name):

    # Retrieve the list of existing buckets
    s3 = boto3.client("s3")
    response = s3.list_buckets()

    # Output the bucket names
    print("Existing buckets:")
    for bucket in response["Buckets"]:
        print(f'  {bucket["Name"]}')


@handle_boto_client_errors
def list_snapshots(session):
    # Retrieve the list of existing buckets
    ec2 = session.client("ec2")

    response = ec2.describe_snapshots(
        Filters=[
            {
                "Name": "tag:created_by",
                "Values": [
                    "nimbo",
                ],
            },
        ],
        MaxResults=100,
    )
    return list(sorted(response["Snapshots"], key=lambda x: x["StartTime"]))


@handle_boto_client_errors
def check_snapshot_state(session, snapshot_id):
    ec2 = session.client("ec2")
    response = ec2.describe_snapshots(SnapshotIds=[snapshot_id])
    return response["Snapshots"][0]["State"]


@handle_boto_client_errors
def sync_folder(session, source, target, profile, region, delete=False):
    command = f"aws s3 sync {source} {target} --profile {profile} --region {region}"
    if delete:
        command = command + " --delete"
    print(f"\nRunning command: {command}\n")
    subprocess.Popen(command, shell=True).communicate()


@handle_boto_client_errors
def pull(session, config, folder, delete=False):
    assert folder in ["datasets", "results", "logs"]

    if folder == "logs":
        source = join(config["s3_results_path"], "nimbo-logs")
        target = join(config["local_results_path"], "nimbo-logs")
    else:
        source = config["s3_" + folder + "_path"]
        target = config["local_" + folder + "_path"]
    sync_folder(
        session, source, target, config["aws_profile"], config["region_name"], delete
    )


@handle_boto_client_errors
def push(session, config, folder, delete=False):
    assert folder in ["datasets", "results", "logs"]

    if folder == "logs":
        source = join(config["local_results_path"], "nimbo-logs")
        target = join(config["s3_results_path"], "nimbo-logs")
    else:
        source = config["local_" + folder + "_path"]
        target = config["s3_" + folder + "_path"]
    sync_folder(
        session, source, target, config["aws_profile"], config["region_name"], delete
    )


@handle_boto_client_errors
def ls(session, config, path):
    profile = config["aws_profile"]
    region = config["region_name"]
    path = path.strip("/")
    path = path + "/"
    command = f"aws s3 ls {path} --profile {profile} --region {region}"
    print(f"Running command: {command}")
    subprocess.Popen(command, shell=True).communicate()
