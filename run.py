from os.path import join
import sys
import json
import yaml
import boto3
import argparse
from pprint import pprint
from pkg_resources import resource_filename

from core import utils, storage, launch
from core.paths import NIMBO

parser = argparse.ArgumentParser(description='Nimbo utilities.')
parser.add_argument('command', nargs='+', default='list_active')
args = parser.parse_args()

# Load yaml config file
with open(join(NIMBO, "config.yml"), "r") as f:
    config = yaml.load(f, Loader=yaml.FullLoader)

print("Config:")
pprint(config)
utils.verify_correctness(config)
print()

session = boto3.Session(profile_name='nimbo')

"""
for attr in pricing.describe_services(ServiceCode='AmazonEC2')["Services"][0]["AttributeNames"]:

    response = pricing.get_attribute_values(
        AttributeName=attr,
        MaxResults=100,
        ServiceCode='AmazonEC2',
    )
    print(attr)
    pprint(response)
    print()
sys.exit()
"""

if args.command[0] == "run":
    assert len(args.commands[1:]) > 0, "No command passed to nimbo run."
    launch.run_job(session, config, " ".join(args.commands[1:]))

elif args.command[0] == "launch":
    launch.run_job(session, config, "_nimbo_launch")

elif args.command[0] == "launch-and-setup":
    launch.run_job(session, config, "_nimbo_launch_and_setup") 

elif args.command[0] == "ssh":
    utils.ssh(session, args.command[1])

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

elif args.command[0] == "check_instance":
    utils.check_instance(session, args.instance_id)

elif args.command[0] == "push":
    storage.push(session, config, args.command[1])

elif args.command[0] == "pull":
    storage.pull(session, config, args.command[1])

elif args.command[0] == "ls":
    storage.ls(session, config, args.command[1])

else:
    raise Exception(f"Command --{args.command[0]} not recognized.")
