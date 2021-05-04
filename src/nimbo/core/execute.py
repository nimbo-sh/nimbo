import os
import socket
import subprocess
import sys
import time
from os.path import join
from subprocess import PIPE
from pathlib import Path

from nimbo import CONFIG
from nimbo.core import telemetry, utils, access
from nimbo.core.storage import s3_cp_command, s3_sync_command
from nimbo.core.statics import NIMBO_ROOT, NIMBO_VARS
from nimbo.core.print import print, print_header


def launch_instance(client):

    access.allow_inbound_current_ip(CONFIG.security_group)
    image = utils.get_image_id()
    print_header(f"Launching instance with image {image}... ")

    ebs_config = {
        "VolumeSize": CONFIG.disk_size,
        "VolumeType": CONFIG.disk_type,
    }
    if CONFIG.disk_iops:
        ebs_config["Iops"] = CONFIG.disk_iops

    instance_config = {
        "BlockDeviceMappings": [{"DeviceName": "/dev/sda1", "Ebs": ebs_config}],
        "ImageId": image,
        "InstanceType": CONFIG.instance_type,
        "KeyName": Path(CONFIG.instance_key).stem,
        "Placement": {"Tenancy": "default"},
        "SecurityGroups": [CONFIG.security_group],
        "IamInstanceProfile": {"Name": CONFIG.role},
    }

    if CONFIG.spot:
        extra_kwargs = {}
        if CONFIG.spot_duration:
            extra_kwargs = {"BlockDurationMinutes": CONFIG.spot_duration}

        instance = client.request_spot_instances(
            LaunchSpecification=instance_config,
            TagSpecifications=[
                {
                    "ResourceType": "spot-instances-request",
                    "Tags": utils.make_instance_tags(),
                }
            ],
            **extra_kwargs,
        )
        instance_request = instance["SpotInstanceRequests"][0]
        request_id = instance_request["SpotInstanceRequestId"]

        try:
            print_header("Spot instance request submitted.")
            print_header("Waiting for the spot instance request to be fulfilled... ")

            status = ""
            while status != "fulfilled":
                time.sleep(2)
                response = client.describe_spot_instance_requests(
                    SpotInstanceRequestIds=[request_id],
                    Filters=utils.make_instance_filters(),
                )
                instance_request = response["SpotInstanceRequests"][0]
                status = instance_request["Status"]["Code"]
                if status not in [
                    "fulfilled",
                    "pending-evaluation",
                    "pending-fulfillment",
                ]:
                    raise Exception(response["SpotInstanceRequests"][0]["Status"])
        except KeyboardInterrupt:
            client.cancel_spot_instance_requests(SpotInstanceRequestIds=[request_id])
            print_header("Cancelled spot instance request.")
            sys.exit(1)

        print_header("Done.")
        client.create_tags(
            Resources=[instance_request["InstanceId"]], Tags=utils.make_instance_tags()
        )
        instance = instance_request
    else:
        instance_config["MinCount"] = 1
        instance_config["MaxCount"] = 1
        instance_config["InstanceInitiatedShutdownBehavior"] = "terminate"
        instance_config["TagSpecifications"] = [
            {"ResourceType": "instance", "Tags": utils.make_instance_tags()}
        ]
        instance = client.run_instances(**instance_config)
        instance = instance["Instances"][0]

    return instance


def write_nimbo_vars():
    var_list = [
        f"S3_DATASETS_PATH={CONFIG.s3_datasets_path}",
        f"S3_RESULTS_PATH={CONFIG.s3_results_path}",
        f"LOCAL_DATASETS_PATH={CONFIG.local_datasets_path}",
        f"LOCAL_RESULTS_PATH={CONFIG.local_results_path}",
    ]
    if CONFIG.encryption:
        var_list.append(f"ENCRYPTION={CONFIG.encryption}")
    with open(NIMBO_VARS, "w") as f:
        f.write("\n".join(var_list))


def wait_for_instance_running(instance_id):
    status = ""
    while status != "running":
        time.sleep(1)
        status = utils.check_instance_status(instance_id)


def block_until_ssh_ready(host: str) -> None:
    print_header(
        f"Waiting for instance to be ready for ssh at {host}. "
        "This can take up to 2 minutes... "
    )

    start = time.monotonic()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)

    reconnect_count = 0
    while reconnect_count < CONFIG.ssh_timeout:
        error_num = sock.connect_ex((host, 22))

        if error_num == 0:
            break

        time.sleep(1)
        reconnect_count += 1
    else:
        raise RuntimeError(
            "Something went wrong while connecting to the instance.\n"
            "Please verify your security groups, instance key and "
            "instance profile, and try again.\n"
            "More info at docs.nimbo.sh/common-issues#cant-ssh.\n"
        )

    print_header(f"Ready. (%0.3f s)" % (time.monotonic() - start))


def sync_code(host):
    if ".git" not in os.listdir():
        print(
            "No git repo found. Syncing all the python and bash files as a fallback.",
            style="warning",
        )
        print("Please consider using git to track the files to sync.", style="warning")
        subprocess.Popen(
            f"rsync -avm -e 'ssh -i {CONFIG.instance_key}' "
            f"--include '*/' --include '*.py' --include '*.ipynb' --include '*.sh' --exclude '*' "
            f". ubuntu@{host}:/home/ubuntu/project",
            shell=True,
        ).communicate()
    else:
        output, error = subprocess.Popen(
            "git ls-tree -r HEAD --name-only", stdout=PIPE, shell=True
        ).communicate()
        git_tracked_files = output.decode("utf-8").strip().splitlines()
        include_files = [f"--include '{file_name}'" for file_name in git_tracked_files]
        include_string = " ".join(include_files)
        subprocess.Popen(
            f"rsync -amr -e 'ssh -i {CONFIG.instance_key}' "
            f"--include '*/' {include_string} --exclude '*' "
            f". ubuntu@{host}:/home/ubuntu/project",
            shell=True,
        ).communicate()


def sync_notebooks(instance_id):
    host = utils.check_instance_host(instance_id)

    subprocess.Popen(
        f"rsync -avm -e 'ssh -i {CONFIG.instance_key}' "
        f"--include '*/' --include '*.ipynb' --exclude '*' "
        f"ubuntu@{host}:/home/ubuntu/project/ .",
        shell=True
    ).communicate()


def run_remote_script(ssh_cmd, scp_cmd, host, instance_id, job_cmd, script):
    remote_script = join(NIMBO_ROOT, "scripts", script)
    subprocess.check_output(
        f"{scp_cmd} {remote_script} ubuntu@{host}:/home/ubuntu/", shell=True
    )

    nimbo_log = "/home/ubuntu/nimbo-log.txt"
    bash_cmd = f"bash {script}"
    if CONFIG.run_in_background:
        full_command = (
            f"nohup {bash_cmd} {instance_id} {job_cmd} </dev/null >{nimbo_log} 2>&1 &"
        )
    else:
        full_command = f"{bash_cmd} {instance_id} {job_cmd}"

    subprocess.Popen(
        f'{ssh_cmd} ubuntu@{host} "{full_command}"', shell=True
    ).communicate()


def run_job(job_cmd, dry_run=False):
    if dry_run:
        return {"message": job_cmd + "_dry_run"}

    # access.verify_nimbo_instance_profile(session)

    # Launch instance with new volume for anaconda
    ec2 = CONFIG.get_session().client("ec2")
    telemetry.record_event("run")

    start_t = time.monotonic()

    instance = launch_instance(ec2)
    instance_id = instance["InstanceId"]

    try:
        # Wait for the instance to be running
        wait_for_instance_running(instance_id)
        end_t = time.monotonic()
        print_header(f"Instance running. ({round((end_t-start_t), 2)} s)")
        print_header(f"InstanceId: [green]{instance_id}[/green]")
        print()

        time.sleep(5)
        host = utils.check_instance_host(instance_id)

        block_until_ssh_ready(host)

        if job_cmd == "_nimbo_launch":
            print_header(
                f"Run [cyan]nimbo ssh {instance_id}[/cyan] to log onto the instance"
            )
            return {"message": job_cmd + "_success", "instance_id": instance_id}

        ssh = (
            f"ssh -i {CONFIG.instance_key} -o 'StrictHostKeyChecking no'"
            " -o ServerAliveInterval=5 "
        )
        scp = f"scp -i {CONFIG.instance_key} -o 'StrictHostKeyChecking no'"

        local_env = "/tmp/local_env.yml"
        user_conda_yml = CONFIG.conda_env
        # TODO: Replace this with shutil
        subprocess.check_output(f"cp {user_conda_yml} {local_env}", shell=True)

        # Send conda env yaml and setup scripts to instance
        print()
        print_header(f"Syncing conda, config, and setup files...")
        write_nimbo_vars()

        # Create project folder and send env and config files there
        subprocess.check_output(f"{ssh} ubuntu@{host} mkdir project", shell=True)
        subprocess.check_output(
            f"{scp} {local_env} {CONFIG.nimbo_config_file} {NIMBO_VARS}"
            f" ubuntu@{host}:/home/ubuntu/project/",
            shell=True,
        )

        # Sync code with instance
        print()
        print_header(f"Syncing code...")
        sync_code(host)

        print_header(f"Running setup code on the instance from here on.")
        # Run remote_setup script on instance
        run_remote_script(ssh, scp, host, instance_id, job_cmd, "remote_setup.sh")

        if job_cmd == "_nimbo_notebook":
            subprocess.Popen(
                f"{ssh} -o 'ExitOnForwardFailure yes' "
                f"ubuntu@{host} -NfL 57467:localhost:57467 >/dev/null 2>&1", 
                shell=True).communicate()
            print_header(
                "Make sure to run 'nimbo sync-notebooks <instance_id>' frequently to sync "
                "the notebook to your local folder, as the remote notebooks will be lost "
                "once the instance is terminated."
            )
        return {"message": job_cmd + "_success", "instance_id": instance_id}

    except BaseException as e:
        if type(e) != KeyboardInterrupt and type(e) != subprocess.CalledProcessError:
            print(e, style="error")

        if not CONFIG.persist:
            print_header(f"Deleting instance {instance_id} (from local)... ")
            utils.delete_instance(instance_id)

        return {"message": job_cmd + "_error", "instance_id": instance_id}


def run_access_test(dry_run=False):
    if dry_run:
        return

    CONFIG.instance_type = "t3.medium"
    CONFIG.run_in_background = False
    CONFIG.persist = False

    try:
        # Send test file to s3 results path and delete it
        profile = CONFIG.aws_profile
        region = CONFIG.region_name
        results_path = CONFIG.s3_results_path

        subprocess.check_output(
            "echo 'Hello World' > nimbo-access-test.txt", shell=True
        )

        command = s3_cp_command("nimbo-access-test.txt", results_path)
        subprocess.check_output(command, shell=True)

        command = f"aws s3 ls {results_path} --profile {profile} --region {region}"
        subprocess.check_output(command, shell=True)
        command = (
            f"aws s3 rm {results_path}/nimbo-access-test.txt "
            f"--profile {profile} --region {region}"
        )
        subprocess.check_output(command, shell=True)

        print(
            "You have the necessary S3 read/write permissions from your computer \u2713"
        )

    except subprocess.CalledProcessError as e:
        print(e, style="error")
        sys.exit(1)

    # access.verify_nimbo_instance_profile(session)
    # print("Instance profile 'NimboInstanceProfile' found \u2713")

    # Launch instance with new volume for anaconda
    print("Launching test instance... ")
    ec2 = CONFIG.get_session().client("ec2")

    instance = launch_instance(ec2)
    instance_id = instance["InstanceId"]

    try:
        # Wait for the instance to be running
        wait_for_instance_running(instance_id)
        print(f"Instance running. Instance creation allowed \u2713")
        print(f"InstanceId: {instance_id}")
        print()

        print("Trying to delete this instance...")
        utils.delete_instance(instance_id)

        print("Instance deletion allowed \u2713")
        print("\nLaunching another instance...")
        instance = launch_instance(ec2)
        instance_id = instance["InstanceId"]
        print(f"Instance running. InstanceId: {instance_id}")

        time.sleep(5)
        host = utils.check_instance_host(instance_id)
        ssh = (
            f"ssh -i {CONFIG.instance_key} -o 'StrictHostKeyChecking no' "
            "-o ServerAliveInterval=20"
        )
        scp = f"scp -i {CONFIG.instance_key} -o 'StrictHostKeyChecking no'"

        block_until_ssh_ready(host)

        print("Instance key allows ssh access to remote instance \u2713")
        print("Security group allows ssh access to remote instance \u2713")

        write_nimbo_vars()

        subprocess.check_output(
            f"{scp} {CONFIG.nimbo_config_file} {NIMBO_VARS} ubuntu@{host}:/home/ubuntu/",
            shell=True,
        )
        run_remote_script(ssh, scp, host, instance_id, "", "remote_s3_test.sh")

    except BaseException as e:
        if type(e) != KeyboardInterrupt and type(e) != subprocess.CalledProcessError:
            print(e, style="error")

        if not CONFIG.persist:
            print_header(f"Deleting instance {instance_id} (from local)...")
            utils.delete_instance(instance_id)

        sys.exit(1)


def run_commands_on_instance(commands, instance_ids):
    """Runs commands on remote linux instances
    :param commands: a list of strings, each one a command to execute on the instances
    :param instance_ids: a list of instance_id strings, of the instances on which
                         to execute the command
    :return: the response from the send_command function (check the boto3 docs
             for ssm client.send_command() )
    """

    ssm = CONFIG.get_session().client("ssm")
    resp = ssm.send_command(
        DocumentName="AWS-RunShellScript",  # One of AWS' preconfigured documents
        Parameters={"commands": commands},
        InstanceIds=instance_ids,
    )
    return resp
