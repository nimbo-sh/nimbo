from os.path import join
import sys
import time
import subprocess
from pprint import pprint
from datetime import datetime
from botocore.exceptions import ClientError

from . import storage
from . import utils
from .paths import NIMBO
from .ami.catalog import AMI_MAP


def launch_instance(session, config, job_cmd, noscript=False):
    assert config["image"] in AMI_MAP, \
        "The image requested doesn't exist. " \
        "Please check this link for a list of supported images."

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
        BlockDeviceMappings=[{
            'DeviceName': '/dev/sda1',
            'Ebs': {'VolumeSize': config["disk_size"]}}],
        ImageId=AMI_MAP[config['image']],
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

    if config["launch_only"]:
        sys.exit()

    INSTANCE_KEY = config["instance_key"]+".pem"
    host = utils.check_instance_host(session, instance["InstanceId"])
    ssh = f"ssh -i {INSTANCE_KEY} -o 'StrictHostKeyChecking no'"
    scp = f"scp -i {INSTANCE_KEY}"

    # Wait for the instance to be ready for ssh
    print("Waiting for instance to be ready for ssh... ", end="", flush=True)
    host_ready = False
    while 1:
        output, error = subprocess.Popen(f"{ssh} ubuntu@{host} echo 'Hello World'", shell=True,
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
        if error == b'':
            break
        else:
            time.sleep(2)
    print("Ready.")

    LOCAL_ENV = "local_env.yml"
    CONFIG = "config.yml"
    REMOTE_SETUP = join(NIMBO, "scripts/remote_setup.sh")

    # Get conda env yml of current env
    command = f"conda env export > {LOCAL_ENV}"
    output, error = subprocess.Popen(command, shell=True).communicate()

    # Send conda env yaml and setup scripts to instance
    print("\nSyncing conda, config, and setup files...")
    subprocess.Popen(f"{scp} "
                     f"{LOCAL_ENV} {CONFIG} {REMOTE_SETUP} "
                     f"ubuntu@{host}:/home/ubuntu", shell=True).communicate()
    subprocess.Popen(f"rm {LOCAL_ENV}", shell=True).communicate()

    # Sync code with instance
    print("\nSyncing code...")
    subprocess.Popen(f"rsync -avm -e 'ssh -i {INSTANCE_KEY}' "
                     f"--include '*/' --include '*.py' --exclude '*' "
                     f". ubuntu@{host}:/home/ubuntu", shell=True).communicate()

    print("\nSetting up environment...")
    command = f"bash remote_setup.sh"
    subprocess.Popen(f"{ssh} ubuntu@{host} {command} {job_cmd}", shell=True).communicate()

    if config["delete_after_job_finish"] == True:
        # Terminate instance
        utils.delete_instance(session, instance["InstanceId"])
