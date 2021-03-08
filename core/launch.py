import os
import time
import subprocess
from pprint import pprint
from datetime import datetime
from botocore.exceptions import ClientError

from . import storage
from . import utils


def launch_instance_from_scratch(session, config, noscript=False):

    # Create main bucket
    # Operation is idempotent, so will not do anything if bucket already exists
    success = storage.create_bucket(session, 'nimbo-main-bucket')

    # Launch instance
    print("Launching instance... ", end="", flush=True)
    ec2 = session.client('ec2')

    # print(userdata)
    instance = ec2.run_instances(
        ImageId='ami-0e5657f6d3c3ea350',
        InstanceType=config["instance_type"],
        KeyName='instance-key-laptop',
        MinCount=1,
        MaxCount=1,
        Placement={
            "Tenancy": "default"
        },
        IamInstanceProfile={
            "Name": "NimboInstanceProfile"
        }
    )
    instance = instance["Instances"][0]
    status = ""

    # Wait for the instance to be running
    while status != "running":
        time.sleep(1)
        status = utils.check_instance_status(session, instance["InstanceId"])
    print("Instance running.")

    host = utils.check_instance_host(session, instance["InstanceId"])

    # Wait for the instance to be ready for ssh
    print("Waiting for instance to be ready for ssh... ", end="", flush=True)
    host_ready = False
    while 1:
        output, error = subprocess.Popen(f"ssh -i ./instance-key.pem ubuntu@{host} echo 'Hello World'", shell=True,
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
        if error == b'':
            break
        else:
            time.sleep(2)
    print("Ready.")

    # Get conda env yml of current env
    bash_command = "conda env export"
    with open("./nimbo-environment.yml", "w") as f:
        process = subprocess.Popen(bash_command.split(), stdout=f)
    output, error = process.communicate()

    # Send conda env yaml and setup scripts to instance
    print("\nSyncing conda, config, and setup files...")
    subprocess.Popen(f"scp -i ./instance-key.pem ./nimbo-environment.yml ./config.yml ./scripts/remote_setup.sh ubuntu@{host}:/home/ubuntu", shell=True).communicate()
    subprocess.Popen(f"rm ./nimbo-environment.yml", shell=True).communicate()

    # Sync code with instance
    print("\nSyncing code...")
    subprocess.Popen(f"rsync -avm -e 'ssh -i ./instance-key.pem' "
                     f"--include '*/' --include '*.py' --exclude '*' "
                     f". ubuntu@{host}:/home/ubuntu", shell=True).communicate()

    print("\nSetting up conda environment...")
    command = "bash ./remote_setup.sh"
    subprocess.Popen(f"ssh -i ./instance-key.pem ubuntu@{host} {command}", shell=True).communicate()

    # Save image
    print("\nBacking up instance...")
    now_string = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")[:-3]
    ec2.create_image(Name=f"nimbo-image_{now_string}",
                     InstanceId=instance["InstanceId"],
                     Description="Image created by Nimbo",
                     NoReboot=True,
                     TagSpecifications=[{'ResourceType': 'image',
                                         'Tags': [{'Key': 'created_by', 'Value': 'nimbo'}]}])

    # aws ssm send-command --document-name "AWS-RunShellScript" --comment "listing services" --instance-ids "Instance-ID"
    # --parameters commands="service --status-all" --region us-west-2 --output text

    if noscript:
        pass
    else:
        # Run user script
        pass

    # Terminate instance
    utils.delete_instance(session, instance["InstanceId"])


def launch_instance_from_ami(session, config, ami):
    # Launch instance
    print("Launching instance... ", end="", flush=True)
    ec2 = session.client('ec2')

    t0 = time.time()
    # print(userdata)
    instance = ec2.run_instances(
        ImageId=ami,
        InstanceType=config["instance_type"],
        KeyName='instance-key-laptop',
        MinCount=1,
        MaxCount=1,
        Placement={
            "Tenancy": "default"
        },
        IamInstanceProfile={
            "Name": "NimboInstanceProfile"
        }
    )
    instance = instance["Instances"][0]
    status = ""

    # Wait for the instance to be running
    while status != "running":
        time.sleep(1)
        status = utils.check_instance_status(session, instance["InstanceId"])
    t1 = time.time()
    print("Instance running (%0.3fs)" % (t1 - t0))

    host = utils.check_instance_host(session, instance["InstanceId"])

    # Wait for the instance to be ready for ssh
    host_ready = False
    while 1:
        output, error = subprocess.Popen(f"ssh -i ./instance-key.pem ubuntu@{host} echo 'Hello World'", shell=True,
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
        if error == b'':
            break
        else:
            time.sleep(2)

    """ The steps below should be ran in the background because they can take a while """

    print("Stopping instance...")
    ec2.stop_instances(InstanceIds=[instance["InstanceId"]])

    # Create new image
    print("Creating new image...")
    now_string = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")[:-3]
    response = ec2.create_image(Name=f"nimbo-image_{now_string}",
                                InstanceId=instance["InstanceId"],
                                Description="Image created by Nimbo",
                                NoReboot=True,
                                TagSpecifications=[{'ResourceType': 'image',
                                                    'Tags': [{'Key': 'created_by', 'Value': 'nimbo'}]}])
    image_id = response["ImageId"]

    print("Waiting for image to be available...")
    # Wait for the image to be available before terminating the instance
    image_ready = False
    while 1:
        response = ec2.describe_images(ImageIds=[image_id])["Images"][0]
        if response["State"] != "available":
            time.sleep(1)
        else:
            break

    # aws s3 cp --recursive s3://nimbo-main-bucket/data/datasets /home/ubuntu/data/datasets

    # Terminate instance
    print("Terminating instance...")
    utils.delete_instance(session, instance["InstanceId"])

    print("Done.")