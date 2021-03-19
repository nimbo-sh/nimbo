import sys
import json
import subprocess
from pprint import pprint
import boto3
from pkg_resources import resource_filename


full_region_names = {"eu-west-1": "EU (Ireland)"}

# Each element is [num_gpus, gpu_type]
instance_gpu_map = {
    "p4d.24xlarge": [8, "A100"],
    "p3.2xlarge": [1, "V100"],
    "p3.8xlarge": [4, "V100"],
    "p3.16xlarge": [8, "V100"],
    "p3dn.24xlarge": [8, "V100"],
    "p2.xlarge": [1, "K80"],
    "p2.xlarge": [1, "K80"],
    "p2.8xlarge": [8, "K80"],
    "p2.16xlarge": [16, "K80"],
    "g4dn.xlarge": [1, "T4"],
    "g4dn.2xlarge": [1, "T4"],
    "g4dn.4xlarge": [1, "T4"],
    "g4dn.8xlarge": [1, "T4"],
    "g4dn.16xlarge": [1, "T4"],
    "g4dn.12xlarge": [4, "T4"],
    "g4dn.metal": [8, "T4"],
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


def list_gpu_prices(session):
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

        if instance_type in instance_gpu_map:
            num_gpus, gpu_type = instance_gpu_map[instance_type]
            string = "{0: <16} {1: <10} {2} x {3}".format(instance_type, round(price, 2), num_gpus, gpu_type) 
        else:
            string = "{0: <16} {1: <10}".format(instance_type, round(price, 2)) 

        print(string)


def show_active_instances(session):
    ec2 = session.client('ec2')
    response = ec2.describe_instances(
        Filters=[
            {'Name': 'instance-state-name', 'Values': ['running']}
        ]
    )
    for reservation in response["Reservations"]:
        for inst in reservation["Instances"]:
            print(f"ID: {inst['InstanceId']}\n"
                  f"Launch Time: {inst['LaunchTime']}\n"
                  f"InstanceType: {inst['InstanceType']}\n"
                  f"Public DNS: {inst['PublicDnsName']}\n")


def show_stopped_instances(session):
    ec2 = session.client('ec2')
    response = ec2.describe_instances(
        Filters=[
            {'Name': 'instance-state-name', 'Values': ['stopped', 'stopping']}
        ]
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
    pprint(response["TerminatingInstances"][0])


def delete_all_instances(session, instance_id):
    ec2 = session.client('ec2')
    response = ec2.describe_instances(
        Filters=[
            {'Name': 'instance-state-name', 'Values': ['running']}
        ]
    )
    for reservation in response["Reservations"]:
        for inst in reservation["Instances"]:
            delete_response = ec2.terminate_instances(
                InstanceIds=[inst['InstanceId']],
            )
            pprint(delete_response["TerminatingInstances"][0])


def check_instance_status(session, instance_id):
    ec2 = session.client('ec2')
    response = ec2.describe_instances(InstanceIds=[instance_id])
    status = response["Reservations"][0]["Instances"][0]["State"]["Name"]
    return status


def check_instance_host(session, instance_id):
    ec2 = session.client('ec2')
    response = ec2.describe_instances(InstanceIds=[instance_id])
    host = response["Reservations"][0]["Instances"][0]["PublicDnsName"]
    return host


def list_active_buckets(session):
    s3 = session.client('s3')
    response = s3.list_buckets()
    pprint(response)


def list_amis(session):
    ec2 = session.client('ec2')
    images = ec2.describe_images(Owners=['self'],
                                 Filters=[{
                                     "Name": "tag:created_by",
                                     "Values": ["nimbo"]
                                 }])["Images"]
    pprint(images)


def get_latest_nimbo_ami(session):
    ec2 = session.client('ec2')
    images = ec2.describe_images(Owners=['self'],
                                 Filters=[{
                                     "Name": "tag:created_by",
                                     "Values": ["nimbo"]
                                 },{
                                     "Name": "state",
                                     "Values": ["available"]
                                 }])["Images"]
    if len(images) > 0:
        sorted_images = sorted(images, key=lambda x: x["CreationDate"])
        return sorted_images[-1]["ImageId"]
    else:
        return None


def delete_ami(session, ami):
    ec2 = session.client('ec2')
    ec2.deregister_image(ImageId=ami)


def ssh(session, instance_id):
    host = check_instance_host(session, instance_id)
    subprocess.Popen(f"ssh -i ./instance-key.pem -o 'StrictHostKeyChecking no' ubuntu@{host}", shell=True).communicate()

