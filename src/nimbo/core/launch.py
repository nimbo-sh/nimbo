import os
from os.path import join, basename, isfile
import sys
import time
import logging
import subprocess
from subprocess import PIPE
import traceback
from pprint import pprint
from datetime import datetime
from botocore.exceptions import ClientError

from . import storage, utils, access
from .paths import NIMBO, CONFIG
from .ami.catalog import AMI_MAP


def run_job(session, config, job_cmd):
    print("Config:")
    pprint(config)

    print("Job command:", job_cmd)

    access.verify_nimbo_instance_profile(session)

    # Launch instance with new volume for anaconda
    print("Launching instance... ", end="", flush=True)
    ec2 = session.client('ec2')

    # print(userdata)
    start_t = time.time()
    instance_config = {
        "BlockDeviceMappings": [{
            'DeviceName': '/dev/sda1',
            'Ebs': {'VolumeSize': config["disk_size"]}
        }],
        "ImageId": AMI_MAP[config['image']],
        "InstanceType": config["instance_type"],
        "KeyName": config["instance_key"],
        "Placement": {"Tenancy": "default"},
        "SecurityGroups": [config["security_group"]],
        "IamInstanceProfile": {
            "Name": "NimboInstanceProfile"
        }
    }

    if config["spot"]:
        instance = ec2.request_spot_instances(
            BlockDurationMinutes=config["spot_duration"],
            LaunchSpecification=instance_config,
            TagSpecifications=[{
                'ResourceType': 'spot-instances-request',
                'Tags': [{'Key': 'CreatedBy', 'Value': 'nimbo'},
                         {'Key': 'Owner', 'Value': config["user_id"]}]
            }]
        )
        instance = instance["SpotInstanceRequests"][0]

    else:
        instance_config["MinCount"] = 1
        instance_config["MaxCount"] = 1
        instance_config["TagSpecifications"] = [{
            'ResourceType': 'instance',
            'Tags': [{'Key': 'CreatedBy', 'Value': 'nimbo'},
                     {'Key': 'Owner', 'Value': config["user_id"]}]
        }]
        instance = ec2.run_instances(**instance_config)
        instance = instance["Instances"][0]

    instance_id = instance["InstanceId"]
    status = ""
    try:
        # Wait for the instance to be running
        while status != "running":
            time.sleep(1)
            status = utils.check_instance_status(session, config, instance_id)

        end_t = time.time()
        print(f"Instance running. ({round((end_t-start_t), 2)}s)")
        print(f"InstanceId: {instance_id}")
        print()

        if job_cmd == "_nimbo_launch":
            print(f"Run 'nimbo ssh {instance_id}' to log onto the instance")
            print("Please allow a few seconds for the instance to be ready for ssh.")
            print(f"If the connection is refused when you run 'nimbo ssh {instance_id}' "
                  "wait a few seconds and try again.")
            print(f"If the connection keeps being refused, delete the instance and try again, "
                  "or refer to https://docs.nimbo.sh/connection-refused.")
            sys.exit()

        INSTANCE_KEY = config["instance_key"] + ".pem"
        host = utils.check_instance_host(session, config, instance_id)
        ssh = f"ssh -i {INSTANCE_KEY} -o 'StrictHostKeyChecking no'"
        scp = f"scp -i {INSTANCE_KEY}"

        # Wait for the instance to be ready for ssh
        print("Waiting for instance to be ready for ssh... ", end="", flush=True)
        host_ready = False
        wait_time = 0
        while 1:
            time.sleep(10)
            wait_time += 5
            output, error = subprocess.Popen(f"{ssh} ubuntu@{host} echo HelloWorld",
                                             stdout=PIPE, stderr=PIPE, shell=True).communicate()
            if error == b'':
                break

            if wait_time == 60:
                raise Exception("Something failed when connecting to the instance.\n"
                                "Please verify your security groups, instance key and instance profile.\n"
                                "More info at docs.nimbo.sh/connection-issues.")
        print("Ready.")

        REMOTE_SETUP = join(NIMBO, "scripts/remote_setup.sh")

        LOCAL_ENV = "local_env.yml"
        user_conda_yml = config["conda_env"]
        output = subprocess.check_output(f"cp {user_conda_yml} local_env.yml", shell=True)

        # Send conda env yaml and setup scripts to instance
        print("\nSyncing conda, config, and setup files...")

        # Create project folder and send env and config files there
        subprocess.check_output(f"{ssh} ubuntu@{host} "
                                f"mkdir project", shell=True)
        subprocess.check_output(f"{scp} {LOCAL_ENV} {CONFIG} "
                                f"ubuntu@{host}:/home/ubuntu/project/", shell=True)
        subprocess.check_output(f"rm {LOCAL_ENV}", shell=True)

        # Sync code with instance
        print("\nSyncing code...")
        if ".git" not in os.listdir():
            print("No git repo found. Syncing all the python files as a fallback.")
            print("Please consider using git to track the files to sync.")
            subprocess.Popen(f"rsync -avm -e 'ssh -i {INSTANCE_KEY}' "
                             f"--include '*/' --include '*.py' --exclude '*' "
                             f". ubuntu@{host}:/home/ubuntu/project", shell=True).communicate()
        else:
            output, error = subprocess.Popen("git ls-tree -r HEAD --name-only",
                                             stdout=PIPE, shell=True).communicate()
            git_tracked_files = output.decode("utf-8").strip().splitlines()
            include_files = [f"--include '{file_name}'" for file_name in git_tracked_files]
            include_string = " ".join(include_files)
            subprocess.Popen(f"rsync -amr -e 'ssh -i {INSTANCE_KEY}' "
                             f"--include '*/' {include_string} --exclude '*' "
                             f". ubuntu@{host}:/home/ubuntu", shell=True).communicate()

        # Run remote_setup script on instance
        subprocess.check_output(f"{scp} {REMOTE_SETUP} "
                                f"ubuntu@{host}:/home/ubuntu/", shell=True)
        bash = f"bash remote_setup.sh"
        if config["run_in_background"]:
            results_path = config["results_path"]
            full_command = f"'nohup {bash} {instance_id} {job_cmd} </dev/null >/home/ubuntu/{results_path}/nimbo-log.txt 2>&1 &'"
        else:
            full_command = f"{bash} {instance_id} {job_cmd}"

        process = subprocess.Popen(f"{ssh} ubuntu@{host} {full_command}", shell=True)
        stdout, stderr = process.communicate()
        retcode = process.poll()
        if retcode:
            raise subprocess.CalledProcessError(retcode, process.args,
                                                output=stdout, stderr=stderr)

        if config["delete_when_done"] and \
           not config["run_in_background"] and \
           job_cmd != "_nimbo_launch_and_setup":

            if utils.check_instance_status(session, config, instance_id) in ["running", "pending"]:
                # Terminate instance if it isn't already being terminated
                utils.delete_instance(session, instance_id)

        if config["run_in_background"]:
            print(f"Job running in instance {instance_id}")

    except Exception as e:
        if config["delete_on_error"]:
            print("\nDeleting instance...")
            utils.delete_instance(session, instance_id)
        traceback.print_exc()
    except KeyboardInterrupt:
        print("\nDeleting instance...")
        utils.delete_instance(session, instance_id)
        sys.exit()


def run_access_test(session, config):

    access.verify_nimbo_instance_profile(session)
    print("Instance profile 'NimboInstanceProfile' found \u2713")

    # Launch instance with new volume for anaconda
    print("Launching test instance... ", end="", flush=True)
    ec2 = session.client('ec2')

    # print(userdata)
    start_t = time.time()
    instance_config = {
        "BlockDeviceMappings": [{
            'DeviceName': '/dev/sda1',
            'Ebs': {'VolumeSize': config["disk_size"]}
        }],
        "ImageId": AMI_MAP[config['image']],
        "InstanceType": config["instance_type"],
        "KeyName": config["instance_key"],
        "Placement": {"Tenancy": "default"},
        "SecurityGroups": [config["security_group"]],
        "IamInstanceProfile": {
            "Name": "NimboInstanceProfile"
        }
    }
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
    print(f"Instance running. Instance creation allowed \u2713")
    print()

    INSTANCE_KEY = config["instance_key"] + ".pem"
    host = utils.check_instance_host(session, instance_id)
    ssh = f"ssh -i {INSTANCE_KEY} -o 'StrictHostKeyChecking no'"
    scp = f"scp -i {INSTANCE_KEY}"

    # Wait for the instance to be ready for ssh
    print("Waiting for instance to be ready for ssh... ", end="", flush=True)
    host_ready = False
    wait_time = 0
    time.sleep(30)
    while 1:
        output, error = subprocess.Popen(f"{ssh} ubuntu@{host} echo HelloWorld", shell=True,
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
        wait_time += 5
        if error == b'':
            break

        if wait_time == 60:
            print("\nDeleting test instance...")
            utils.delete_instance(session, instance_id)
            raise Exception("Something failed connecting to the instance. "
                            "Please verify your security groups, instance key and instance profile. "
                            "More info at docs.nimbo.sh/connection-issues.")

    print("Ready.")
    print("Instance key allows ssh access to remote instance \u2713")
    print("Security group allows ssh access to remote instance \u2713")

    CONFIG = "config.yml"
    REMOTE_TEST = join(NIMBO, "scripts/remote_s3_test.sh")
    subprocess.Popen(f"{scp} {CONFIG} {REMOTE_TEST} "
                     f"ubuntu@{host}:/home/ubuntu", shell=True).communicate()
    command = "bash remote_s3_test.sh"
    output, error = subprocess.Popen(f"{ssh} ubuntu@{host} {command} {instance_id}", shell=True,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()

    if error == b'':
        print("The instance has access the required S3 and EC2 permissions \u2713")
        print("\nEverything working \u2713")
        print("Instance has been deleted.")
    else:
        print("Error found:")
        print(error.decode("utf-8"))
        print("\nDeleting test instance...")
        utils.delete_instance(session, instance_id)
