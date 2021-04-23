import sys

import boto3

from nimbo import CONFIG

image_id = sys.argv[1]

base_region = "eu-west-1"
session = boto3.Session(profile_name="nimbo", region_name=base_region)
ec2 = session.client("ec2")
response = ec2.describe_images(
    Filters=[
        {"Name": "tag:CreatedBy", "Values": ["nimbo"]},
        {"Name": "tag:Type", "Values": ["production"]},
    ],
    ImageIds=[image_id],
)
image = response["Images"][0]

for dest_region in CONFIG.full_region_names.keys():
    if dest_region == base_region:
        continue
    print(dest_region)
    session = boto3.Session(profile_name="nimbo", region_name=dest_region)
    ec2 = session.client("ec2")

    response = ec2.copy_image(
        ClientToken=image_id,
        Name=image["Name"],
        SourceImageId=image_id,
        SourceRegion=base_region,
        Description=image["Description"],
    )
    new_image_id = response["ImageId"]
    ec2.create_tags(
        Resources=[new_image_id],
        Tags=[
            {"Key": "CreatedBy", "Value": "nimbo"},
            {"Key": "Type", "Value": "production"},
        ],
    )
