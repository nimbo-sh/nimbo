from pprint import pprint

import boto3
import firebase_admin
from firebase_admin import credentials, db

from nimbo import CONFIG
from nimbo.core.statics import NIMBO_ROOT

cred = credentials.Certificate(
    NIMBO_ROOT + "/ami/credentials/nimboami-firebase-adminsdk-yxyfy-6d01f1d35f.json"
)
firebase_admin.initialize_app(
    cred, options={"databaseURL": "https://nimboami-default-rtdb.firebaseio.com"}
)
image_db = db.reference("images")

image_catalog = {}
for dest_region in CONFIG.full_region_names.keys():
    print(dest_region)
    session = boto3.Session(profile_name="nimbo", region_name=dest_region)
    ec2 = session.client("ec2")
    response = ec2.describe_images(
        Filters=[
            {"Name": "tag:CreatedBy", "Values": ["nimbo"]},
            {"Name": "tag:Type", "Values": ["production"]},
        ]
    )
    images = response["Images"]
    image_catalog_per_region = {img["Name"]: img["ImageId"] for img in images}
    image_catalog[dest_region] = image_catalog_per_region.copy()
    pprint(image_catalog_per_region)

image_db.set(image_catalog)
