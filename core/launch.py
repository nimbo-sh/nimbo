import os
import sys
import time
import subprocess
from pprint import pprint
from datetime import datetime
from botocore.exceptions import ClientError

from . import storage
from . import utils


def launch_instance(session, config, job_cmd, noscript=False):
    print("Job command:", job_cmd)

    # Create main bucket
    # Operation is idempotent, so will not do anything if bucket already exists
    success = storage.create_bucket(session, 'nimbo-main-bucket')

    # Launch instance with new volume for anaconda
    print("Launching instance... ", end="", flush=True)
    ec2 = session.client('ec2')

    # print(userdata)
    start_t = time.time()
    instance = ec2.run_instances(
        ImageId=config['ami'],
        InstanceType=config["instance_type"],
        KeyName=config["instance_key"],
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

    end_t = time.time()
    print(f"Instance running. ({round((end_t-start_t), 2)}s)")

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
    command = "conda env export > local_env.yml"
    output, error = subprocess.Popen(command, shell=True).communicate()

    # Send conda env yaml and setup scripts to instance
    print("\nSyncing conda, config, and setup files...")
    subprocess.Popen("scp -i ./instance-key.pem "
                     "./local_env.yml ./config.yml "
                     "./scripts/remote_setup.sh "
                     f"ubuntu@{host}:/home/ubuntu", shell=True).communicate()
    subprocess.Popen(f"rm ./local_env.yml", shell=True).communicate()

    # Sync code with instance
    print("\nSyncing code...")
    subprocess.Popen(f"rsync -avm -e 'ssh -i ./instance-key.pem' "
                     f"--include '*/' --include '*.py' --exclude '*' "
                     f". ubuntu@{host}:/home/ubuntu", shell=True).communicate()

    print("\nSetting up environment...")
    command = "bash remote_setup.sh"
    subprocess.Popen(f"ssh -i ./instance-key.pem ubuntu@{host} {command} {job_cmd}", shell=True).communicate()


    # aws ssm send-command --document-name "AWS-RunShellScript" --comment "listing services" --instance-ids "Instance-ID"
    # --parameters commands="service --status-all" --region us-west-2 --output text

    if noscript:
        pass
    else:
        # Run user script
        pass

    if config["delete_after_job_finish"] == True:
        # Terminate instance
        utils.delete_instance(session, instance["InstanceId"])
