import functools
import json
import os
import subprocess
import sys
from pprint import pprint

from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta

import botocore
import botocore.errorfactory
import requests
from botocore.exceptions import ClientError

from nimbo import CONFIG
from nimbo.core.config import RequiredCase
from nimbo.core.environment import is_test_environment
from nimbo.core.statics import FULL_REGION_NAMES, INSTANCE_GPU_MAP, NIMBO_DEFAULT_CONFIG
from nimbo.core.print import print, print_header


def ec2_instance_types():
    """Yield all available EC2 instance types in region CONFIG.region_name"""
    describe_args = {}
    client = CONFIG.get_session().client("ec2")
    while True:
        describe_result = client.describe_instance_types(**describe_args)
        yield from [i["InstanceType"] for i in describe_result["InstanceTypes"]]
        if "NextToken" not in describe_result:
            break
        describe_args["NextToken"] = describe_result["NextToken"]


def format_price_string(instance_type, price, gpus, cpus, mem):
    string = "\t{0: <16} {1: <15} {2: <10} {3: <5} {4:<7}".format(
        instance_type, price, gpus, cpus, mem
    )
    return string


def list_gpu_prices(dry_run=False):
    if dry_run:
        return

    instance_types = list(sorted(ec2_instance_types()))
    instance_types = [
        inst
        for inst in instance_types
        if inst[:2] in ["p2", "p3", "p4"] or inst[:3] in ["g4d"]
    ]
    full_region_name = FULL_REGION_NAMES[CONFIG.region_name]

    pricing = CONFIG.get_session().client("pricing", region_name="us-east-1")

    string = format_price_string(
        "InstanceType", "Price ($/hour)", "GPUs", "CPUs", "Mem (Gb)"
    )
    print()
    print(string, style="bold")

    for instance_type in instance_types:
        response = pricing.get_products(
            ServiceCode="AmazonEC2",
            MaxResults=100,
            FormatVersion="aws_v1",
            Filters=[
                {"Type": "TERM_MATCH", "Field": "instanceType", "Value": instance_type},
                {"Type": "TERM_MATCH", "Field": "location", "Value": full_region_name},
                {"Type": "TERM_MATCH", "Field": "operatingSystem", "Value": "Linux"},
                {"Type": "TERM_MATCH", "Field": "capacitystatus", "Value": "Used"},
                {"Type": "TERM_MATCH", "Field": "preInstalledSw", "Value": "NA"},
                {"Type": "TERM_MATCH", "Field": "tenancy", "Value": "shared"},
            ],
        )

        inst = json.loads(response["PriceList"][0])
        inst = inst["terms"]["OnDemand"]
        inst = list(inst.values())[0]
        inst = list(inst["priceDimensions"].values())[0]
        inst = inst["pricePerUnit"]
        currency = list(inst.keys())[0]
        price = float(inst[currency])

        num_gpus, gpu_type, mem, cpus = INSTANCE_GPU_MAP[instance_type]
        string = format_price_string(
            instance_type, round(price, 2), f"{num_gpus} x {gpu_type}", cpus, mem
        )
        print(string)
    print()


def list_spot_gpu_prices(dry_run=False):
    if dry_run:
        return

    instance_types = list(sorted(ec2_instance_types()))
    instance_types = [
        inst
        for inst in instance_types
        if inst[:2] in ["p2", "p3", "p4"] or inst[:3] in ["g4d"]
    ]

    ec2 = CONFIG.get_session().client("ec2")

    string = format_price_string(
        "InstanceType", "Price ($/hour)", "GPUs", "CPUs", "Mem (Gb)"
    )
    print()
    print(string, style="bold")

    for instance_type in instance_types:
        response = ec2.describe_spot_price_history(
            InstanceTypes=[instance_type],
            Filters=[{"Name": "product-description", "Values": ["Linux/UNIX"]}],
        )

        price = float(response["SpotPriceHistory"][0]["SpotPrice"])

        num_gpus, gpu_type, mem, cpus = INSTANCE_GPU_MAP[instance_type]
        string = format_price_string(
            instance_type, round(price, 2), f"{num_gpus} x {gpu_type}", cpus, mem
        )
        print(string)
    print()


def show_spending(qty, timescale, dry_run=False):

    today = date.today()
    timeformat = "%Y-%m-%d"

    if timescale == "months":
        start_date = (today - relativedelta(months=qty)).replace(day=1)
        start = start_date.strftime(timeformat)
        end = today.strftime(timeformat)
        granularity = "monthly"
    elif timescale == "days":
        start_date = today - relativedelta(days=qty)
        start = start_date.strftime(timeformat)
        end = today.strftime(timeformat)
        granularity = "daily"
    else:
        raise ValueError("Timescale must be 'daily' or 'monthly'.")

    services = [
        "Amazon Elastic Compute Cloud - Compute",
        "EC2 - Other",
        "Amazon Simple Storage Service",
    ]

    client = CONFIG.get_session().client("ce")
    results = client.get_cost_and_usage(
        TimePeriod={"End": end, "Start": start},
        Granularity=granularity.upper(),
        Filter={
            "And": [
                {
                    "Not": {
                        "Dimensions": {
                            "Key": "RECORD_TYPE",
                            "Values": ["Credit", "Refund"],
                        }
                    }
                },
                {
                    "Dimensions": {
                        "Key": "SERVICE",
                        "Values": services,
                    }
                },
            ]
        },
        Metrics=["UnblendedCost"],
        GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
    )["ResultsByTime"]

    table = []
    print()
    for interval in results:
        period_start_date = datetime.strptime(
            interval["TimePeriod"]["Start"], "%Y-%m-%d"
        )
        if granularity == "monthly":
            period_string = period_start_date.strftime("%b %Y")
        else:
            period_string = period_start_date.strftime("%d %b")

        groups = interval["Groups"]
        if groups == []:
            table.append([period_string, 0, 0])
        else:
            ec2_cost = 0
            s3_cost = 0
            for group in groups:
                group_cost = float(group["Metrics"]["UnblendedCost"]["Amount"])
                if group["Keys"] == ["Amazon Elastic Compute Cloud - Compute"]:
                    ec2_cost += group_cost
                elif group["Keys"] == ["EC2 - Other"]:
                    ec2_cost += group_cost
                elif group["Keys"] == ["Amazon Simple Storage Service"]:
                    s3_cost += group_cost

            table.append([period_string, ec2_cost, s3_cost])

    def row_string(x):
        string = f"\t{x[0]:>10}"
        for xi in x[1:]:
            if type(xi) == float:
                string += f" {xi:>10.2f}"
            else:
                string += f" {xi:>10}"
        return string

    print(f"\tSpending for region {CONFIG.region_name}:")
    print()
    print(row_string(["", "EC2", "S3"]))
    for row in table:
        # round before passing to row_string
        print(row_string(row))

    ec2_total = sum([row[1] for row in table])
    s3_total = sum([row[2] for row in table])
    print("\t" + "-" * 32)
    print(row_string(["Total", ec2_total, s3_total]))
    print()


def show_active_instances(dry_run=False):
    ec2 = CONFIG.get_session().client("ec2")
    try:
        response = ec2.describe_instances(
            Filters=[{"Name": "instance-state-name", "Values": ["running", "pending"]}]
            + make_instance_filters(),
            DryRun=dry_run,
        )
        for reservation in response["Reservations"]:
            for inst in reservation["Instances"]:
                print(
                    f"Id: [bright_green]{inst['InstanceId']}[/bright_green]\n"
                    f"Status: {inst['State']['Name']}\n"
                    f"Launch Time: {inst['LaunchTime']}\n"
                    f"InstanceType: {inst['InstanceType']}\n"
                    f"IP Address: {inst['PublicIpAddress']}\n"
                )

    except ClientError as e:
        if "DryRunOperation" not in str(e):
            raise


def show_stopped_instances(dry_run=False):
    ec2 = CONFIG.get_session().client("ec2")
    try:
        response = ec2.describe_instances(
            Filters=[{"Name": "instance-state-name", "Values": ["stopped", "stopping"]}]
            + make_instance_filters(),
            DryRun=dry_run,
        )
        for reservation in response["Reservations"]:
            for inst in reservation["Instances"]:
                print(
                    f"ID: {inst['InstanceId']}\n"
                    f"Launch Time: {inst['LaunchTime']}\n"
                    f"InstanceType: {inst['InstanceType']}\n"
                )
    except ClientError as e:
        if "DryRunOperation" not in str(e):
            raise


def check_instance_status(instance_id, dry_run=False):
    ec2 = CONFIG.get_session().client("ec2")
    try:
        response = ec2.describe_instances(
            InstanceIds=[instance_id], Filters=make_instance_filters(), DryRun=dry_run
        )
        status = response["Reservations"][0]["Instances"][0]["State"]["Name"]
        return status
    except ClientError as e:
        if "DryRunOperation" not in str(e):
            raise


def stop_instance(instance_id, dry_run=False):
    ec2 = CONFIG.get_session().client("ec2")
    try:
        response = ec2.stop_instances(InstanceIds=[instance_id], DryRun=dry_run)
        pprint(response)
    except ClientError as e:
        if "DryRunOperation" not in str(e):
            raise


def delete_instance(instance_id, dry_run=False):
    ec2 = CONFIG.get_session().client("ec2")
    try:
        response = ec2.terminate_instances(InstanceIds=[instance_id], DryRun=dry_run)
        status = response["TerminatingInstances"][0]["CurrentState"]["Name"]
        print_header(f"Instance [green]{instance_id}[/green]: {status}")
    except ClientError as e:
        if "DryRunOperation" not in str(e):
            raise


def delete_all_instances(dry_run=False):
    ec2 = CONFIG.get_session().client("ec2")
    try:
        response = ec2.describe_instances(
            Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
            + make_instance_filters(),
            DryRun=dry_run,
        )
        for reservation in response["Reservations"]:
            for inst in reservation["Instances"]:
                instance_id = inst["InstanceId"]
                delete_response = ec2.terminate_instances(
                    InstanceIds=[instance_id],
                )
                status = delete_response["TerminatingInstances"][0]["CurrentState"][
                    "Name"
                ]
                print_header(f"Instance [green]{instance_id}[/green]: {status}")
    except ClientError as e:
        if "DryRunOperation" not in str(e):
            raise


def check_instance_host(instance_id, dry_run=False):
    ec2 = CONFIG.get_session().client("ec2")
    try:
        response = ec2.describe_instances(
            InstanceIds=[instance_id],
            Filters=make_instance_filters(),
            DryRun=dry_run,
        )
        host = response["Reservations"][0]["Instances"][0]["PublicIpAddress"]
    except ClientError as e:
        if "DryRunOperation" not in str(e):
            raise
        host = "random_host"
    return host


def list_active_buckets():
    s3 = CONFIG.get_session().client("s3")
    response = s3.list_buckets()
    pprint(response)


def ssh(instance_id, dry_run=False):
    host = check_instance_host(instance_id, dry_run)

    if dry_run:
        return

    subprocess.Popen(
        f"ssh -i {CONFIG.instance_key} "
        f"-o 'StrictHostKeyChecking no' -o ServerAliveInterval=20 "
        f"ubuntu@{host}",
        shell=True,
    ).communicate()


def make_instance_tags():
    return [
        {"Key": "CreatedBy", "Value": "nimbo"},
        {"Key": "Owner", "Value": CONFIG.user_id},
    ]


def make_instance_filters():
    tags = make_instance_tags()
    filters = []
    for tag in tags:
        tag_filter = {"Name": "tag:" + tag["Key"], "Values": [tag["Value"]]}
        filters.append(tag_filter)
    return filters


def get_image_id():
    if CONFIG.image[:4] == "ami-":
        image_id = CONFIG.image
    else:
        response = requests.get(
            "https://nimboami-default-rtdb.firebaseio.com/images.json"
        )
        catalog = response.json()
        region = CONFIG.region_name
        if region in catalog:
            region_catalog = catalog[region]
            image_name = CONFIG.image
            if image_name in region_catalog:
                image_id = region_catalog[image_name]
            else:
                raise ValueError(
                    f"The image {image_name} was not found in the"
                    " image catalog managed by Nimbo.\n"
                    "Check https://docs.nimbo.sh/managed-images"
                    " for the list of managed images."
                )
        else:
            raise ValueError(
                f"Currently, Nimbo does not support managed images in {region}."
                " Please use another region."
            )

    return image_id


def assert_required_config(*cases: RequiredCase):
    """
    Decorator for ensuring that required config is present
    """

    def decorator(func):
        @functools.wraps(func)
        def decorated(*args, **kwargs):
            try:
                CONFIG.assert_required_config_exists(*cases)
                return func(*args, **kwargs)
            except AssertionError as e:
                print(e, style="error")
                sys.exit(1)
            except FileNotFoundError as e:
                # Happens when nimbo config file is not found
                print(e, style="error")
                sys.exit(1)

        return decorated

    return decorator


def handle_errors(func):
    """
    Decorator for catching boto3 ClientErrors, ValueError or KeyboardInterrupts.
    In case of error print the error message and stop Nimbo.
    """

    @functools.wraps(func)
    def decorated(*args, **kwargs):
        if is_test_environment():
            return func(*args, **kwargs)
        else:
            try:
                return func(*args, **kwargs)
            except botocore.errorfactory.ClientError as e:
                print(e, style="error")
                sys.exit(1)
            except ValueError as e:
                print(e, style="error")
                sys.exit(1)
            except KeyboardInterrupt:
                print("Aborting...")
                sys.exit(1)

    return decorated


def generate_config(quiet=False) -> None:
    """ Create an example Nimbo config in the project root """

    if os.path.isfile(CONFIG.nimbo_config_file):
        print(
            f"{CONFIG.nimbo_config_file} already exists, do you want to overwrite it?"
        )

        if not _get_user_confirmation():
            print("Leaving Nimbo config intact")
            return

    with open(CONFIG.nimbo_config_file, "w") as f:
        f.write(NIMBO_DEFAULT_CONFIG)

    if not quiet:
        print(f"Example config written to {CONFIG.nimbo_config_file}")


def _get_user_confirmation() -> bool:
    try:
        confirmation = input("Type Y for yes or N for no - ")
        return confirmation.lower() == "y" or confirmation.lower() == "yes"
    except BaseException as e:
        print(e, style="error")
        print("Aborting...")
