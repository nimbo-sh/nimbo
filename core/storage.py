import logging
import boto3
from botocore.exceptions import ClientError


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
    s3 = session.client('s3')
    try:
        response = s3.upload_file(file_name, bucket, object_name)
    except ClientError as e:
        logging.error(e)
        return False
    return True


def create_bucket(session, bucket_name):
    """Create an S3 bucket in a specified region

    :param bucket_name: Bucket to create
    :return: True if bucket created, else False
    """

    # Create bucket
    try:
        s3 = session.client('s3')
        location = {'LocationConstraint': session.region_name}
        s3.create_bucket(Bucket=bucket_name,
                         CreateBucketConfiguration=location)
    except ClientError as e:
        if e.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
            print("Bucket nimbo-main-bucket already exists, ignoring.")
        else:
            logging.error(e)
        return False

    print("Bucket %s created." % bucket_name)
    return True


def list_buckets(session, bucket_name):

    # Retrieve the list of existing buckets
    s3 = boto3.client('s3')
    response = s3.list_buckets()

    # Output the bucket names
    print('Existing buckets:')
    for bucket in response['Buckets']:
        print(f'  {bucket["Name"]}')
