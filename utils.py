from pprint import pprint
import boto3
import json
from pkg_resources import resource_filename
import sys


full_region_names = {"eu-west-1": "EU (Ireland)"}


def ec2_instance_types(session):
    '''Yield all available EC2 instance types in region <region_name>'''
    describe_args = {}
    client = session.client('ec2')
    while True:
        describe_result = client.describe_instance_types(**describe_args)
        yield from [i['InstanceType'] for i in describe_result['InstanceTypes']]
        if 'NextToken' not in describe_result:
            break
        describe_args['NextToken'] = describe_result['NextToken']


def get_full_region_name(region_name):
    default_region = 'EU (Ireland)'
    endpoint_file = resource_filename('botocore', 'data/endpoints.json')
    try:
        with open(endpoint_file, 'r') as f:
            data = json.load(f)
        return data['partitions'][0]['regions'][region_name]['description']
    except IOError:
        return default_region


def show_gpu_prices(session):
    instance_types = list(sorted(ec2_instance_types(session)))
    instance_types = [inst for inst in instance_types if inst[0] in ["p", "g"]]
    full_region_name = full_region_names[session.region_name]

    pricing = session.client('pricing', region_name='us-east-1')

    for instance_type in instance_types:
        response = pricing.get_products(
            ServiceCode='AmazonEC2',
            MaxResults=100,
            FormatVersion='aws_v1',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': full_region_name},
                {'Type': 'TERM_MATCH', 'Field': 'operatingSystem', 'Value': 'Linux'},
                {'Type': 'TERM_MATCH', 'Field': 'capacitystatus', 'Value': 'Used'},
                {'Type': 'TERM_MATCH', 'Field': 'preInstalledSw', 'Value': 'NA'},
                {'Type': 'TERM_MATCH', 'Field': 'tenancy', 'Value': 'shared'}
            ]
        )

        inst = json.loads(response["PriceList"][0])
        inst = inst['terms']['OnDemand']
        inst = list(inst.values())[0]
        inst = list(inst["priceDimensions"].values())[0]
        inst = inst['pricePerUnit']
        currency = list(inst.keys())[0]
        price = float(inst[currency])
        print(instance_type + ": " + "%0.3f %s" % (price, currency))


def show_active_instances(session):
    ec2 = session.client('ec2')
    response = ec2.describe_instances()
    pprint(response)


def show_active_buckets(session):
    s3 = session.client('s3')
    response = s3.list_buckets()
    pprint(response)