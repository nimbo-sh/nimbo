import os
from os.path import join, basename, isfile
import sys
import time
import logging
import subprocess
from subprocess import PIPE
import traceback
import requests
from pprint import pprint
from datetime import datetime
from botocore.exceptions import ClientError

from nimbo.core import storage, utils, access
from nimbo.core.utils import instance_tags, instance_filters
from nimbo.core.paths import NIMBO, CONFIG
#from nimbo.core.ami.catalog import AMI_MAP


def launch_instance(client, config):
    response = requests.get("https://nimboami-default-rtdb.firebaseio.com/ami-map.json")
    ami_map = response.json()
    if config["image"][:4] == "ami-":
        image = config["image"]
    else:
        if config['image'] in ami_map:
            image = ami_map[config['image']]
        else:
            raise ValueError(f"The image {config['image']} was not found in Nimbo's managed image catalog.\n"
                             "Check https://docs.nimbo.sh/managed-images for a list of managed images.")
    print(f"Using image {image}")

    instance_config = {
        "BlockDeviceMappings": [{
            'DeviceName': '/dev/sda1',
            'Ebs': {'VolumeSize': config["disk_size"]}
        }],
        "ImageId": image,
        "InstanceType": config["instance_type"],
        "KeyName": config["instance_key"],
        "Placement": {"Tenancy": "default"},
        "SecurityGroups": [config["security_group"]],
        "IamInstanceProfile": {
            "Name": "NimboInstanceProfile"
        }
    }

    if config["spot"]:
        if "spot_duration" in config:
            extra_kwargs = {"BlockDurationMinutes": config["spot_duration"]}
        else:
            extra_kwargs = {}

        instance = client.request_spot_instances(
            LaunchSpecification=instance_config,
            TagSpecifications=[{
                'ResourceType': 'spot-instances-request',
                'Tags': instance_tags(config)
            }],
            **extra_kwargs
        )
        instance_request = instance["SpotInstanceRequests"][0]
        request_id = instance_request["SpotInstanceRequestId"]
        print("Spot instance request submitted.")
        print("Waiting for the spot instance request to be fulfilled... ", end="", flush=False)

        status = ""
        while status != "fulfilled":
            time.sleep(1)
            response = client.describe_spot_instance_requests(
                SpotInstanceRequestIds=[request_id],
                Filters=instance_filters(config)
            )
            instance_request = response["SpotInstanceRequests"][0]
            status = instance_request["Status"]["Code"]
            if status not in ["fulfilled", "pending-evaluation", "pending-fulfillment"]:
                raise Exception(response["SpotInstanceRequests"][0]["Status"])

        print("Done.")
        client.create_tags(
            Resources=[instance_request["InstanceId"]],
            Tags=instance_tags(config)
        )
        instance = instance_request
    else:
        instance_config["MinCount"] = 1
        instance_config["MaxCount"] = 1
        instance_config["TagSpecifications"] = [{
            'ResourceType': 'instance',
            'Tags': instance_tags(config)
        }]
        instance = client.run_instances(**instance_config)
        instance = instance["Instances"][0]

    return instance


def wait_for_instance_running(session, config, instance_id):
    status = ""
    while status != "running":
        time.sleep(1)
        status = utils.check_instance_status(session, config, instance_id)


def wait_for_ssh_ready(host):
    print(f"Waiting for instance to be ready for ssh at {host}. "
          "This can take up to 2 minutes... ", end="", flush=True)
    start = time.time()
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
                            "Please verify your security groups, instance key and instance profile, and try again.\n"
                            "More info at docs.nimbo.sh/common-issues#cant-ssh.")
    finish = time.time()
    print("Ready. (%0.3fs)" % (finish - start))


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
                         f". ubuntu@{host}:/home/ubuntu/project", shell=True).communicate()


def run_remote_script(ssh_cmd, scp_cmd, host, instance_id, job_cmd, script, config):
    REMOTE_SCRIPT = join(NIMBO, "scripts", script)
    subprocess.check_output(f"{scp_cmd} {REMOTE_SCRIPT} "
                            f"ubuntu@{host}:/home/ubuntu/", shell=True)

    NIMBO_LOG = "/home/ubuntu/nimbo-log.txt"
    bash_cmd = f"bash {script}"
    if config["run_in_background"]:
        results_path = config["local_results_path"]
        full_command = f"nohup {bash_cmd} {instance_id} {job_cmd} </dev/null >{NIMBO_LOG} 2>&1 &"
    else:
        full_command = f"{bash_cmd} {instance_id} {job_cmd} | tee {NIMBO_LOG}"

    stdout, stderr = subprocess.Popen(f'{ssh_cmd} ubuntu@{host} "{full_command}"', shell=True).communicate()
    """
    retcode = process.poll()
    if retcode:
        raise subprocess.CalledProcessError(retcode, process.args,
                                            output=stdout, stderr=stderr)
    """


def run_job(session, config, job_cmd, dry_run=False):
    if dry_run:
        return {"message": job_cmd + "_dry_run"}
    print("Config:")
    pprint(config)

    print("Job command:", job_cmd)

    #access.verify_nimbo_instance_profile(session)

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

        INSTANCE_KEY = config["instance_key"] + ".pem"
        time.sleep(5)
        host = utils.check_instance_host(session, config, instance_id)

        # Wait for the instance to be ready for ssh
        wait_for_ssh_ready(host)

        if job_cmd == "_nimbo_launch":
            print(f"Run 'nimbo ssh {instance_id}' to log onto the instance")
            """
            print("Please allow a few seconds for the instance to be ready for ssh.")
            print(f"If the connection is refused when you run 'nimbo ssh {instance_id}' "
                  "wait a few seconds and try again.")
            print(f"If the connection keeps being refused, delete the instance and try again, "
                  "or refer to https://docs.nimbo.sh/connection-refused.")
            """
            return {"message": job_cmd + "_success", "instance_id": instance_id}

        ssh = f"ssh -i {INSTANCE_KEY} -o 'StrictHostKeyChecking no' -o ServerAliveInterval=20 "
        scp = f"scp -i {INSTANCE_KEY} -o 'StrictHostKeyChecking no'"

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

        return job_cmd + "_success"

    except Exception as e:
        print("\nError.")
        if not config["persist"]:
            print(f"Deleting instance {instance_id} (from local)...")
            utils.delete_instance(session, instance_id)
        traceback.print_exc()
        sys.exit()

    except KeyboardInterrupt:
        if not config["persist"]:
            print(f"Deleting instance {instance_id} (from local)...")
            utils.delete_instance(session, instance_id)
        traceback.print_exc()
        sys.exit()


def run_access_test(session, config, dry_run=False):
    if dry_run:
        return
    config["instance_type"] = "t3.medium"
    config["run_in_background"] = False
    config["persist"] = False

    try:
        # Send test file to s3 results path and delete it
        profile = config["aws_profile"]
        region = config["region_name"]
        results_path = config["s3_results_path"]
        subprocess.check_output("echo 'Hellow World' > nimbo-access-test.txt", shell=True)
        command = f"aws s3 cp nimbo-access-test.txt {results_path} --profile {profile} --region {region}"
        subprocess.check_output(command, shell=True)
        command = f"aws s3 rm {results_path}/nimbo-access-test.txt --profile {profile} --region {region}"
        subprocess.check_output(command, shell=True)

        # List folders in s3 datasets path
        datasets_path = config["s3_datasets_path"]
        command = f"aws s3 ls {datasets_path} --profile {profile} --region {region}"
        subprocess.check_output(command, shell=True)
        print("You have the necessary S3 read/write permissions from your computer \u2713")

    except subprocess.CalledProcessError as e:
        print("\nError.")
        sys.exit()

    #access.verify_nimbo_instance_profile(session)
    #print("Instance profile 'NimboInstanceProfile' found \u2713")

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
        ssh = f"ssh -i {INSTANCE_KEY} -o 'StrictHostKeyChecking no' -o ServerAliveInterval=20"
        scp = f"scp -i {INSTANCE_KEY} -o 'StrictHostKeyChecking no'"

        # Wait for the instance to be ready for ssh
        wait_for_ssh_ready(host)

        print("Instance key allows ssh access to remote instance \u2713")
        print("Security group allows ssh access to remote instance \u2713")
        subprocess.check_output(f"{scp} {CONFIG} "
                                f"ubuntu@{host}:/home/ubuntu/", shell=True)
        run_remote_script(ssh, scp, host, instance_id, "", "remote_s3_test.sh", config)
        print("The instance profile has the required S3 and EC2 permissions \u2713")

        print("\nEverything working \u2713")
        print("Instance has been deleted.")

    except subprocess.CalledProcessError as e:
        print("\nError.")
        if not config["persist"]:
            print(f"Deleting instance {instance_id} (from local)...")
            utils.delete_instance(session, instance_id)
        sys.exit()

    except Exception as e:
        print("\nError.")
        if not config["persist"]:
            print(f"Deleting instance {instance_id} (from local)...")
            utils.delete_instance(session, instance_id)
        traceback.print_exc()
        sys.exit()

    except KeyboardInterrupt:
        if not config["persist"]:
            print(f"Deleting instance {instance_id} (from local)...")
            utils.delete_instance(session, instance_id)
        traceback.print_exc()
        sys.exit()


def run_commands_on_instance(session, commands, instance_id):
    """Runs commands on remote linux instances
    :param client: a boto/boto3 ssm client
    :param commands: a list of strings, each one a command to execute on the instances
    :param instance_ids: a list of instance_id strings, of the instances on which to execute the command
    :return: the response from the send_command function (check the boto3 docs for ssm client.send_command() )
    """

    client = session.client('ssm')
    resp = client.send_command(
        DocumentName="AWS-RunShellScript",  # One of AWS' preconfigured documents
        Parameters={'commands': commands},
        InstanceIds=[instance_id],
    )
    return resp
