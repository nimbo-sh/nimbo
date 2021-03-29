import os
from os.path import join
import sys
import json
import yaml
import boto3
import argparse
from pprint import pprint
from pkg_resources import resource_filename

from .core import access, utils, storage, launch, config_utils
from .core.paths import NIMBO, CWD, CONFIG


def parse_args(args):
    parser = argparse.ArgumentParser(description='NimboCLI.')
    parser.add_argument('command', nargs='+')
    return parser.parse_args(args)


def main(args):

    parser = parse_args(args)

    if args.command[0] == "generate-config":
        utils.generate_config()

    else:
        # Load yaml config file
        assert os.path.isfile(CONFIG), \
            f"Nimbo configuration file '{CONFIG}' not found.\n" \
            "You can run 'nimbo generate-config' for guided config file creation."

        with open(CONFIG, "r") as f:
            config = yaml.load(f, Loader=yaml.FullLoader)

        config = config_utils.fill_defaults(config)
        config_utils.verify_correctness(config)
        print()

        session = boto3.Session(profile_name=config["aws_profile"], region_name=config["region_name"])

        # Add user-id to config
        config["user_id"] = session.client("sts").get_caller_identity()["UserId"]

        if args.command[0] == "run":
            launch.run_job(session, config, args.command[1])

        elif args.command[0] == "launch":
            launch.run_job(session, config, "_nimbo_launch")

        elif args.command[0] == "launch-and-setup":
            launch.run_job(session, config, "_nimbo_launch_and_setup")

        elif args.command[0] == "ssh":
            utils.ssh(session, config, args.command[1])

        elif args.command[0] == "list-gpu-prices":
            utils.list_gpu_prices(session)

        elif args.command[0] == "list-spot-gpu-prices":
            utils.list_spot_gpu_prices(session)

        elif args.command[0] == "list-active":
            utils.show_active_instances(session, config)

        elif args.command[0] == "list-stopped":
            utils.show_stopped_instances(session, config)

        elif args.command[0] == "check-instance":
            utils.check_instance(session, args.command[1])

        elif args.command[0] == "stop-instance":
            utils.stop_instance(session, args.command[1])

        elif args.command[0] == "delete-instance":
            utils.delete_instance(session, args.command[1])

        elif args.command[0] == "delete-all-instances":
            utils.delete_all_instances(session, config)

        elif args.command[0] == "create-bucket":
            storage.create_bucket(session, args.command[1])

        elif args.command[0] == "push":
            storage.push(session, config, args.command[1])

        elif args.command[0] == "pull":
            storage.pull(session, config, args.command[1])

        elif args.command[0] == "ls":
            storage.ls(session, config, args.command[1])

        #elif args.command[0] == "create-key-pair":
        #    access.create_key_pair(session, args.command[1])

        #elif args.command[0] == "delete-key-pair":
        #    access.delete_key_pair(session, args.command[1])

        elif args.command[0] == "allow-current-device":
            access.allow_inbound_current_device(session, args.command[1])

        elif args.command[0] == "list-instance-profiles":
            access.list_instance_profiles(session)

        elif args.command[0] == "create-instance-profile":
            access.create_instance_profile(session, args.command[1])

        elif args.command[0] == "create-instance-profile-and-role":
            access.create_instance_profile_and_role(session)

        elif args.command[0] == "test-access":
            launch.run_access_test(session, config)

        else:
            raise Exception(f"Nimbo command '{args.command[0]}' not recognized.")


if __name__ == "__main__": 
    main(sys.argv[1:])
