import os
from os.path import join
import sys
import json
import yaml
import boto3
import argparse
from pprint import pprint
from pkg_resources import resource_filename

from .core import access, utils, storage, launch
from .core.paths import NIMBO, CWD, CONFIG


def main():
    parser = argparse.ArgumentParser(description='Nimbo utilities.')
    parser.add_argument('command', nargs='+', default='list_active')
    args = parser.parse_args()

    # Load yaml config file
    assert os.path.isfile(CONFIG), \
        f"Nimbo configuration file '{CONFIG}' not found.\n" \
        "You can run 'nimbo create_config' for guided config file creation."

    with open(CONFIG, "r") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    print("Config:")
    pprint(config)

    skip = None
    if args.command[0] in ["create-key-pair", "delete-key-pair"]:
        skip = "instance-key"

    utils.verify_correctness(config, skip)
    print()

    session = boto3.Session(profile_name=config["aws_profile"])

    if args.command[0] == "run":
        launch.run_job(session, config, args.command[1])

    elif args.command[0] == "launch":
        launch.run_job(session, config, "_nimbo_launch")

    elif args.command[0] == "launch-and-setup":
        launch.run_job(session, config, "_nimbo_launch_and_setup")

    elif args.command[0] == "ssh":
        utils.ssh(session, config, args.command[1])

    elif args.command[0] == "list_gpu_prices":
        utils.list_gpu_prices(session)

    elif args.command[0] == "list_spot_gpu_prices":
        utils.list_spot_gpu_prices(session)

    elif args.command[0] == "list_active":
        utils.show_active_instances(session)

    elif args.command[0] == "list_stopped":
        utils.show_stopped_instances(session)

    elif args.command[0] == "list_amis":
        utils.list_amis(session)

    elif args.command[0] == "delete_ami":
        utils.delete_ami(session, args.command[1])

    elif args.command[0] == "check_instance":
        utils.check_instance(session, args.command[1])

    elif args.command[0] == "stop_instance":
        utils.stop_instance(session, args.command[1])

    elif args.command[0] == "delete_instance":
        utils.delete_instance(session, args.command[1])

    elif args.command[0] == "delete_all_instances":
        utils.delete_all_instances(session)

    elif args.command[0] == "create_bucket":
        storage.create_bucket(session, args.command[1])

    elif args.command[0] == "push":
        storage.push(session, config, args.command[1])

    elif args.command[0] == "pull":
        storage.pull(session, config, args.command[1])

    elif args.command[0] == "ls":
        storage.ls(session, config, args.command[1])

    elif args.command[0] == "create_key_pair":
        access.create_key_pair(session, args.command[1])

    elif args.command[0] == "delete_key_pair":
        access.delete_key_pair(session, args.command[1])

    elif args.command[0] == "allow_current_device":
        access.allow_inbound_current_device(session, args.command[1])

    elif args.command[0] == "list_instance_profiles":
        access.list_instance_profiles(session)

    elif args.command[0] == "create_instance_profile":
        access.create_instance_profile(session, args.command[1])

    elif args.command[0] == "create_instance_profile_and_role":
        access.create_instance_profile_and_role(session)

    elif args.command[0] == "generate_config":
        utils.generate_config()

    elif args.command[0] == "test_access":
        launch.run_access_test(session, config)

    else:
        raise Exception(f"Nimbo command '{args.command[0]}' not recognized.")
