import time
import subprocess
from pprint import pprint
from botocore.exceptions import ClientError

from . import execute
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

    # Launch instance
    print("Launching instance... ", end="", flush=True)
    ec2 = session.client('ec2')

    # print(userdata)
    instance = ec2.run_instances(
        ImageId='ami-0e5657f6d3c3ea350',
        InstanceType='t2.micro',
        KeyName='instance-key',
        MinCount=1,
        MaxCount=1,
        Placement={
            "Tenancy": "default"
        },
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
    host_ready = False
    while 1:
        output, error = subprocess.Popen(f"ssh -i ./instance-key.pem ubuntu@{host} echo 'Hello World'", shell=True, 
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
        if error == b'':
            break
        else:
            time.sleep(2)

    # Send bash, env, and python scripts to instance
    print("\nSyncing setup scripts...")
    subprocess.Popen(f"scp -i ./instance-key.pem ./scripts/remote_setup.sh ubuntu@{host}:/home/ubuntu", shell=True).communicate()

    print("\nSyncing conda env yml...")
    subprocess.Popen(f"scp -i ./instance-key.pem ./nimbo-environment.yml ubuntu@{host}:/home/ubuntu", shell=True).communicate()

    print("\nSyncing code...")
    subprocess.Popen(f"rsync -avm -e 'ssh -i ./instance-key.pem' "
                     f"--include '*/' --include '*.py' --exclude '*' "
                     f". ubuntu@{host}:/home/ubuntu", shell=True).communicate()


    print("\nSetting up conda environment...")
    command = "bash ./remote_setup.sh"
    subprocess.Popen(f"ssh -i ./instance-key.pem ubuntu@{host} {command}", shell=True).communicate()

    # aws ssm send-command --document-name "AWS-RunShellScript" --comment "listing services" --instance-ids "Instance-ID"
    # --parameters commands="service --status-all" --region us-west-2 --output text

    # Terminate instance
    utils.delete_instance(session, instance["InstanceId"])
