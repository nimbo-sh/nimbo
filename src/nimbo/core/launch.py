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


def launch_instance(client, config):
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
        instance = client.request_spot_instances(
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
        instance = client.run_instances(**instance_config)
        instance = instance["Instances"][0]

    return instance


def wait_for_instance_running(session, config, instance_id):
    status = ""
    while status != "running":
        time.sleep(1)
        status = utils.check_instance_status(session, config, instance_id)


def wait_for_ssh_ready(ssh_cmd, host):
    print(f"Waiting for instance to be ready for ssh at {host}... ", end="", flush=True)
    host_ready = False
    wait_time = 0
    while 1:
        time.sleep(5)
        wait_time += 2
        output, error = subprocess.Popen(f"nc -w 2 {host} 22", 
                                         stdout=PIPE, stderr=PIPE, shell=True).communicate()

        if "ssh" in output.decode("utf-8").lower():
            break

        if error != b"":
            raise Exception(error)

        if wait_time == 60:
            raise Exception("Something failed when connecting to the instance.\n"
                            "Please verify your security groups, instance key and instance profile.\n"
                            "More info at docs.nimbo.sh/connection-issues.")
    print("Ready.")


def sync_code(host, instance_key):
    if ".git" not in os.listdir():
        print("No git repo found. Syncing all the python files as a fallback.")
        print("Please consider using git to track the files to sync.")
        subprocess.Popen(f"rsync -avm -e 'ssh -i {instance_key}' "
                         f"--include '*/' --include '*.py' --exclude '*' "
                         f". ubuntu@{host}:/home/ubuntu/project", shell=True).communicate()
    else:
        output, error = subprocess.Popen("git ls-tree -r HEAD --name-only",
                                         stdout=PIPE, shell=True).communicate()
        git_tracked_files = output.decode("utf-8").strip().splitlines()
        include_files = [f"--include '{file_name}'" for file_name in git_tracked_files]
        include_string = " ".join(include_files)
        subprocess.Popen(f"rsync -amr -e 'ssh -i {instance_key}' "
                         f"--include '*/' {include_string} --exclude '*' "
                         f". ubuntu@{host}:/home/ubuntu", shell=True).communicate()


def run_remote_script(ssh_cmd, scp_cmd, host, instance_id, job_cmd, script, config):
    REMOTE_SCRIPT = join(NIMBO, "scripts", script)
    subprocess.check_output(f"{scp_cmd} {REMOTE_SCRIPT} "
                            f"ubuntu@{host}:/home/ubuntu/", shell=True)

    bash_cmd = f"bash {script}"
    if config["run_in_background"]:
        results_path = config["local_results_path"]
        full_command = f"'nohup {bash_cmd} {instance_id} {job_cmd} </dev/null >/home/ubuntu/nimbo-log.txt 2>&1 &'"
    else:
        full_command = f"{bash_cmd} {instance_id} {job_cmd}"

    process = subprocess.Popen(f"{ssh_cmd} ubuntu@{host} {full_command}", shell=True)
    stdout, stderr = process.communicate()
    retcode = process.poll()
    if retcode:
        raise subprocess.CalledProcessError(retcode, process.args,
                                            output=stdout, stderr=stderr)


def run_job(session, config, job_cmd):
    print("Config:")
    pprint(config)

    print("Job command:", job_cmd)

    access.verify_nimbo_instance_profile(session)

    # Launch instance with new volume for anaconda
    print("Launching instance... ", end="", flush=True)
    ec2 = session.client('ec2')

    start_t = time.time()

    instance = launch_instance(ec2, config)
    instance_id = instance["InstanceId"]

    try:
        # Wait for the instance to be running
        wait_for_instance_running(session, config, instance_id)
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
        time.sleep(5)
        host = utils.check_instance_host(session, config, instance_id)
        ssh = f"ssh -i {INSTANCE_KEY} -o 'StrictHostKeyChecking no'"
        scp = f"scp -i {INSTANCE_KEY} -o 'StrictHostKeyChecking no'"

        # Wait for the instance to be ready for ssh
        wait_for_ssh_ready(ssh, host)

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
        sync_code(host, INSTANCE_KEY)

        # Run remote_setup script on instance
        run_remote_script(ssh, scp, host, instance_id, job_cmd, "remote_setup.sh", config)

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
        traceback.print_exc()
        sys.exit()


def run_access_test(session, config):
    config["instance_type"] = "t3.medium"
    config["run_in_background"] = False
    config["delete_when_done"] = True

    access.verify_nimbo_instance_profile(session)
    print("Instance profile 'NimboInstanceProfile' found \u2713")

    # Launch instance with new volume for anaconda
    print("Launching test instance... ", end="", flush=True)
    ec2 = session.client('ec2')

    # print(userdata)
    start_t = time.time()
    instance = launch_instance(ec2, config)
    instance_id = instance["InstanceId"]

    try:
        # Wait for the instance to be running
        wait_for_instance_running(session, config, instance_id)
        end_t = time.time()
        print(f"Instance running. Instance creation allowed \u2713")
        print(f"InstanceId: {instance_id}")
        print()

        print("Trying to delete this instance...")
        utils.delete_instance(session, instance_id)

        print("Instance deletion allowed \u2713")
        print("\nLaunching another instance...")
        instance = launch_instance(ec2, config)
        instance_id = instance["InstanceId"]
        print(f"Instance running. InstanceId: {instance_id}")

        INSTANCE_KEY = config["instance_key"] + ".pem"
        time.sleep(5)
        host = utils.check_instance_host(session, config, instance_id)
        ssh = f"ssh -i {INSTANCE_KEY} -o 'StrictHostKeyChecking no'"
        scp = f"scp -i {INSTANCE_KEY} -o 'StrictHostKeyChecking no'"

        # Wait for the instance to be ready for ssh
        wait_for_ssh_ready(ssh, host)

        print("Instance key allows ssh access to remote instance \u2713")
        print("Security group allows ssh access to remote instance \u2713")
        subprocess.check_output(f"{scp} {CONFIG} "
                                f"ubuntu@{host}:/home/ubuntu/", shell=True)
        run_remote_script(ssh, scp, host, instance_id, "", "remote_s3_test.sh", config)
        """
        REMOTE_TEST = join(NIMBO, "scripts/remote_s3_test.sh")
        subprocess.Popen(f"{scp} {CONFIG} {REMOTE_TEST} "
                         f"ubuntu@{host}:/home/ubuntu", shell=True).communicate()
        command = "bash remote_s3_test.sh"
        output, error = subprocess.Popen(f"{ssh} ubuntu@{host} {command} {instance_id}", shell=True,
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
        """
        print("The instance profile has the required S3 and EC2 permissions \u2713")

        # Send test file to s3 results path and delete it
        profile = config["aws_profile"]
        results_path = config["s3_results_path"]
        subprocess.check_output("echo 'Hellow World' > nimbo-access-test.txt", shell=True)
        command = f"aws s3 cp nimbo-access-test.txt {results_path} --profile {profile}"
        subprocess.check_output(command, shell=True)
        command = f"aws s3 rm {results_path}/nimbo-access-test.txt --profile {profile}"
        subprocess.check_output(command, shell=True)

        # List folders in s3 datasets path
        datasets_path = config["s3_datasets_path"]
        command = f"aws s3 ls {datasets_path} --profile {profile}"
        subprocess.check_output(command, shell=True)
        print("You have the necessary S3 read/write permissions for the remote paths \u2713")

        print("\nEverything working \u2713")
        print("Instance has been deleted.")

    except Exception as e:
        if config["delete_on_error"]:
            print("\nDeleting instance...")
            utils.delete_instance(session, instance_id)
        traceback.print_exc()
    except KeyboardInterrupt:
        print("\nDeleting instance...")
        utils.delete_instance(session, instance_id)
        traceback.print_exc()
        sys.exit()
