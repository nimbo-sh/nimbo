from os.path import join, basename
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


def run_job(session, config, job_cmd):
    print("Job command:", job_cmd)

    # Create main bucket
    # Operation is idempotent, so will not do anything if bucket already exists
    success = storage.create_bucket(session, 'nimbo-main-bucket')

    # Launch instance with new volume for anaconda
    print("Launching instance... ", end="", flush=True)
    ec2 = session.client('ec2')

    # print(userdata)
    start_t = time.time()
    instance_config = {
        "BlockDeviceMappings": [{
            'DeviceName': '/dev/sda1',
            'Ebs': {'VolumeSize': config["disk_size"]}}],
        "ImageId": AMI_MAP[config['image']],
        "InstanceType": config["instance_type"],
        "KeyName": config["instance_key"],
        "Placement": {
            "Tenancy": "default"
        },
        "IamInstanceProfile": {
            "Name": "NimboInstanceProfile"
        }
    }
    if config["spot"]:
        instance = ec2.request_spot_instances(
            BlockDurationMinutes=config["spot_duration"],
            LaunchSpecification=instance_config
        )
        instance = instance["SpotInstanceRequests"][0]
        
    else:
        instance_config["MinCount"] = 1
        instance_config["MaxCount"] = 1
        instance = ec2.run_instances(**instance_config)
        instance = instance["Instances"][0]

    instance_id = instance["InstanceId"]
    status = ""

    # Wait for the instance to be running
    while status != "running":
        time.sleep(1)
        status = utils.check_instance_status(session, instance_id)

    end_t = time.time()
    print(f"Instance running. ({round((end_t-start_t), 2)}s)")

    if job_cmd == "_nimbo_launch":
        sys.exit()

    INSTANCE_KEY = config["instance_key"]+".pem"
    host = utils.check_instance_host(session, instance_id)
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

    CONFIG = "config.yml"
    REMOTE_SETUP = join(NIMBO, "scripts/remote_setup.sh")

    LOCAL_ENV = "local_env.yml"
    if "conda_yml" in config:
        user_conda_yml = config["conda_yml"]
        output, error = subprocess.Popen(f"cp {user_conda_yml} local_env.yml", shell=True).communicate()
    else:
        # Get conda env yml of current env
        command = f"conda env export > {LOCAL_ENV}"
        output, error = subprocess.Popen(command, shell=True).communicate()

    # Send conda env yaml and setup scripts to instance
    print("\nSyncing conda, config, and setup files...")

    # Create project folder and send env and config files there
    subprocess.Popen(f"{ssh} ubuntu@{host} "
                     f"mkdir project", shell=True).communicate()
    subprocess.Popen(f"{scp} {LOCAL_ENV} {CONFIG} "
                     f"ubuntu@{host}:/home/ubuntu/project/", shell=True).communicate()
    subprocess.Popen(f"rm {LOCAL_ENV}", shell=True).communicate()

     # Sync code with instance
    print("\nSyncing code...")
    output, error = subprocess.Popen("git ls-tree -r HEAD --name-only", stdout=subprocess.PIPE, shell=True).communicate()
    git_tracked_files = output.decode("utf-8").strip().splitlines()
    include_files = [f"--include '{file_name}'" for file_name in git_tracked_files]
    include_string = " ".join(include_files)
    #subprocess.Popen(f"rsync -amr -e 'ssh -i {INSTANCE_KEY}' "
    #                 f"--include '*/' {include_string} --exclude '*' "
    #                 f". ubuntu@{host}:/home/ubuntu", shell=True).communicate()
    subprocess.Popen(f"rsync -avm -e 'ssh -i {INSTANCE_KEY}' "
                     f"--include '*/' --include '*.py' --exclude '*' "
                     f". ubuntu@{host}:/home/ubuntu/project", shell=True).communicate()

    # Run remote_setup script on instance
    subprocess.Popen(f"{scp} {REMOTE_SETUP} "
                     f"ubuntu@{host}:/home/ubuntu/", shell=True).communicate()
    command = f"bash remote_setup.sh"
    subprocess.Popen(f"{ssh} ubuntu@{host} {command} {instance_id} {job_cmd}", shell=True).communicate()

    if config["delete_after_job_finish"] == True and \
       job_cmd != "_nimbo_launch_and_setup":
        # Terminate instance
        utils.delete_instance(session, instance["InstanceId"])
