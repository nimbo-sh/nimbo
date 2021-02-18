import sys
import json
import yaml
import boto3
import argparse
from pprint import pprint
from pkg_resources import resource_filename

from core import utils, storage, launch

parser = argparse.ArgumentParser(description='Nimbo utilities.')
parser.add_argument('command', nargs='+', default='list_active')
parser.add_argument('--id', type=str, default='')
args = parser.parse_args()

# Load yaml config file
with open("./config.yml", "r") as f:
    config = yaml.load(f, Loader=yaml.FullLoader)

print("Config:")
pprint(config)

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
    launch.run_job(session)
elif args.command[0] == "show_gpu_prices":
    utils.show_gpu_prices(session)
elif args.command[0] == "list_active":
    utils.show_active_instances(session)
elif args.command[0] == "list_stopped":
    utils.show_stopped_instances(session)
elif args.command[0] == "check_instance":
    assert args.id != "", "--id must not be empty"
    utils.check_instance(session, args.id)
elif args.command[0] == "stop_instance":
    assert args.id != "", "--id must not be empty"
    utils.stop_instance(session, args.id)
elif args.command[0] == "delete_instance":
    assert args.id != "", "--id must not be empty"
    utils.delete_instance(session, args.id)
elif args.command[0] == "delete_all_instances":
    utils.delete_all_instances(session, args.id)
elif args.command[0] == "check_instance":
    assert args.id != "", "--id must not be empty"
    utils.check_instance(session, args.instance_id)
elif args.command[0] == "push":
    storage.push(session, config, args.command[1])
elif args.command[0] == "pull":
    storage.pull(session, config, args.command[1])
elif args.command[0] == "ls":
    storage.ls(session, config, args.command[1])



# Get current price for a given instance, region and os
#price = get_price(get_region_name('eu-west-1'), 'c5.xlarge', 'Linux')
# print(price)

