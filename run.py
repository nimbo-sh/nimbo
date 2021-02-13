import sys
import json
import boto3
import argparse
from pprint import pprint
from pkg_resources import resource_filename

from core import utils, launch

parser = argparse.ArgumentParser(description='Nimbo utilities.')
parser.add_argument('command', nargs='?', default='list_active')
parser.add_argument('--id', type=str, default='')
args = parser.parse_args()

session = boto3.Session(profile_name='nimbo')
pricing = session.client('pricing', region_name='us-east-1')

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

if args.command == "show_gpu_prices":
    utils.show_gpu_prices(session)
elif args.command == "list_active":
    utils.show_active_instances(session)
elif args.command == "list_stopped":
    utils.show_stopped_instances(session)
elif args.command == "check_instance":
    assert args.id != "", "--id must not be empty"
    utils.check_instance(session, args.id)
elif args.command == "stop_instance":
    assert args.id != "", "--id must not be empty"
    utils.stop_instance(session, args.id)
elif args.command == "delete_instance":
    assert args.id != "", "--id must not be empty"
    utils.delete_instance(session, args.id)
elif args.command == "check_instance":
    assert args.id != "", "--id must not be empty"
    utils.check_instance(session, args.instance_id)
elif args.command == "run":
    launch.run_job(session)


# Get current price for a given instance, region and os
#price = get_price(get_region_name('eu-west-1'), 'c5.xlarge', 'Linux')
# print(price)

