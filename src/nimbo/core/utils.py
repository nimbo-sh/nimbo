import os
import sys
import json
import subprocess
from pprint import pprint
import boto3
from pkg_resources import resource_filename

from .paths import CWD
from .ami.catalog import AMI_MAP


full_region_names = {"eu-west-1": "EU (Ireland)"}

# Each element is [num_gpus, gpu_type, ram, vcpus]
instance_gpu_map = {
    "p4d.24xlarge": [8, "A100", 1152, 96],
    "p3.2xlarge": [1, "V100", 61, 8],
    "p3.8xlarge": [4, "V100", 244, 32],
    "p3.16xlarge": [8, "V100", 488, 64],
    "p3dn.24xlarge": [8, "V100", 768, 96],
    "p2.xlarge": [1, "K80", 61, 4],
    "p2.8xlarge": [8, "K80", 488, 32],
    "p2.16xlarge": [16, "K80", 732, 64],
    "g4dn.xlarge": [1, "T4", 16, 4],
    "g4dn.2xlarge": [1, "T4", 32, 8],
    "g4dn.4xlarge": [1, "T4", 64, 16],
    "g4dn.8xlarge": [1, "T4", 128, 32],
    "g4dn.16xlarge": [1, "T4", 256, 64],
    "g4dn.12xlarge": [4, "T4", 192, 48],
    "g4dn.metal": [8, "T4", 384, 96],
}


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


def format_price_string(instance_type, price, gpus, cpus, mem):
    string = "{0: <16} {1: <15} {2: <10} {3: <5} {4:<7}".format(instance_type, price, gpus, cpus, mem)
    return string


def list_gpu_prices(session):
    instance_types = list(sorted(ec2_instance_types(session)))
    instance_types = [inst for inst in instance_types if inst[:2] in
                      ["p2", "p3", "p4"] or inst[:3] in ["g4d"]]
    full_region_name = full_region_names[session.region_name]

    pricing = session.client('pricing', region_name='us-east-1')

    string = format_price_string("InstanceType", "Price ($/hour)", "GPUs", "CPUs", "Mem (Gb)")
    print(string)

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

        num_gpus, gpu_type, mem, cpus = instance_gpu_map[instance_type]
        string = format_price_string(instance_type, round(price, 2), f"{num_gpus} x {gpu_type}", cpus, mem)
        print(string)


def list_spot_gpu_prices(session):
    instance_types = list(sorted(ec2_instance_types(session)))
    instance_types = [inst for inst in instance_types if inst[:2] in
                      ["p2", "p3", "p4"] or inst[:3] in ["g4d"]]
    full_region_name = full_region_names[session.region_name]

    ec2 = session.client('ec2')

    string = format_price_string("InstanceType", "Price ($/hour)", "GPUs", "CPUs", "Mem (Gb)")
    print(string)

    for instance_type in instance_types:
        response = ec2.describe_spot_price_history(
            InstanceTypes=[instance_type],
            Filters=[{"Name": "product-description", "Values": ["Linux/UNIX"]}]
        )

        price = float(response['SpotPriceHistory'][0]["SpotPrice"])

        num_gpus, gpu_type, mem, cpus = instance_gpu_map[instance_type]
        string = format_price_string(instance_type, round(price, 2), f"{num_gpus} x {gpu_type}", cpus, mem)
        print(string)


def show_active_instances(session, config):
    ec2 = session.client('ec2')
    response = ec2.describe_instances(
        Filters=[
            {'Name': 'instance-state-name', 'Values': ['running']},
            {'Name': 'tag:CreatedBy', 'Values': ['nimbo']},
            {'Name': 'tag:Owner', 'Values': [config["user_id"]]}
        ]
    )
    for reservation in response["Reservations"]:
        for inst in reservation["Instances"]:
            print(f"ID: {inst['InstanceId']}\n"
                  f"Launch Time: {inst['LaunchTime']}\n"
                  f"InstanceType: {inst['InstanceType']}\n"
                  f"Public DNS: {inst['PublicDnsName']}\n")


def show_stopped_instances(session, config):
    ec2 = session.client('ec2')
    response = ec2.describe_instances(
        Filters=[
            {'Name': 'instance-state-name', 'Values': ['stopped', 'stopping']}
        ] + instance_filters(config)
    )
    for reservation in response["Reservations"]:
        for inst in reservation["Instances"]:
            print(f"ID: {inst['InstanceId']}\n"
                  f"Launch Time: {inst['LaunchTime']}\n"
                  f"InstanceType: {inst['InstanceType']}\n")


def stop_instance(session, instance_id):
    ec2 = session.client('ec2')
    response = ec2.stop_instances(
        InstanceIds=[instance_id],
    )
    pprint(response)


def delete_instance(session, instance_id):
    ec2 = session.client('ec2')
    response = ec2.terminate_instances(
        InstanceIds=[instance_id],
    )
    status = response["TerminatingInstances"][0]["CurrentState"]["Name"]
    print(f"Instance {instance_id}: {status}")


def delete_all_instances(session, config):
    ec2 = session.client('ec2')
    response = ec2.describe_instances(
        Filters=[
            {'Name': 'instance-state-name', 'Values': ['running']}
        ] + instance_filters(config)
    )
    for reservation in response["Reservations"]:
        for inst in reservation["Instances"]:
            instance_id = inst['InstanceId']
            delete_response = ec2.terminate_instances(
                InstanceIds=[instance_id],
            )
            status = delete_response["TerminatingInstances"][0]["CurrentState"]["Name"]
            print(f"Instance {instance_id}: {status}")


def check_instance_status(session, config, instance_id):
    ec2 = session.client('ec2')
    response = ec2.describe_instances(
        InstanceIds=[instance_id],
        Filters=instance_filters(config)
    )
    status = response["Reservations"][0]["Instances"][0]["State"]["Name"]
    return status


def check_instance_host(session, config, instance_id):
    ec2 = session.client('ec2')
    response = ec2.describe_instances(
        InstanceIds=[instance_id],
        Filters=instance_filters(config)
    )
    host = response["Reservations"][0]["Instances"][0]["PublicIpAddress"]
    return host


def list_active_buckets(session):
    s3 = session.client('s3')
    response = s3.list_buckets()
    pprint(response)


def ssh(session, config, instance_id):
    host = check_instance_host(session, config, instance_id)
    instance_key = config['instance_key']
    subprocess.Popen(f"ssh -i ./{instance_key}.pem -o 'StrictHostKeyChecking no' ubuntu@{host}", shell=True).communicate()


def instance_tags(config):
    tags = [
        {"Key": "CreatedBy", "Value": "nimbo"},
        {"Key": "Owner", "Value": config["user_id"]}
    ]
    return tags


def instance_filters(config):
    tags = instance_tags(config)
    filters = []
    for tag in tags:
        tag_filter = {"Name": "tag:"+tag["Key"], "Values": [tag["Value"]]}
        filters.append(tag_filter)
    return filters
