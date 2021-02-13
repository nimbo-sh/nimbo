import subprocess
from pprint import pprint
from botocore.exceptions import ClientError

from . import storage
from . import utils


def run_job(session):

    # Create main bucket
    # Operation is idempotent, so will not do anything if bucket already exists
    success = storage.create_bucket(session, 'nimbo-main-bucket')

    # Get conda env yml of current env
    bash_command = "conda env export"
    with open("./nimbo-environment.yml", "w") as f:
        process = subprocess.Popen(bash_command.split(), stdout=f)
    output, error = process.communicate()

    # Upload code files to bucket
    print("Syncing code...")
    bash_command = 'aws s3 sync . s3://nimbo-main-bucket/code --profile nimbo --exclude * --include *.py --include nimbo-environment.yml'
    process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    output = output.decode("utf-8") if output is not None else ''
    error = error.decode("utf-8") if error is not None else ''
    print(output, error)

    # Launch instance
    ec2 = session.client('ec2')
    instance = ec2.run_instances(
        ImageId='ami-0e5657f6d3c3ea350',
        InstanceType='t2.micro',
        MinCount=1,
        MaxCount=1,
        Placement={
            "Tenancy": "default"
        }
    )
    instance = instance["Instances"][0]

    # Terminate instance
    utils.delete_instance(session, instance["InstanceId"])
