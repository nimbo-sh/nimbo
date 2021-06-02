import json
from datetime import date, datetime
from typing import Generator

from dateutil.relativedelta import relativedelta

from nimbo import CONFIG
from nimbo.core.cloud_provider.provider.services.utils import Utils
from nimbo.core.constants import FULL_REGION_NAMES, INSTANCE_GPU_MAP
from nimbo.core.print import nprint


class AwsUtils(Utils):
    @staticmethod
    def ls_gpu_prices(dry_run=False) -> None:
        if dry_run:
            return

        full_region_name = FULL_REGION_NAMES[CONFIG.region_name]

        pricing = CONFIG.get_session().client("pricing", region_name="us-east-1")

        string = AwsUtils._format_price_string(
            "InstanceType", "Price ($/hour)", "GPUs", "CPUs", "Mem (Gb)"
        )
        print()
        nprint(string, style="bold")

        for instance_type in AwsUtils._instance_types():
            response = pricing.get_products(
                ServiceCode="AmazonEC2",
                MaxResults=100,
                FormatVersion="aws_v1",
                Filters=[
                    {
                        "Type": "TERM_MATCH",
                        "Field": "instanceType",
                        "Value": instance_type,
                    },
                    {
                        "Type": "TERM_MATCH",
                        "Field": "location",
                        "Value": full_region_name,
                    },
                    {
                        "Type": "TERM_MATCH",
                        "Field": "operatingSystem",
                        "Value": "Linux",
                    },
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
            string = AwsUtils._format_price_string(
                instance_type, round(price, 2), f"{num_gpus} x {gpu_type}", cpus, mem
            )
            print(string)
        print()

    @staticmethod
    def ls_spot_gpu_prices(dry_run=False) -> None:
        if dry_run:
            return

        ec2 = CONFIG.get_session().client("ec2")

        string = AwsUtils._format_price_string(
            "InstanceType", "Price ($/hour)", "GPUs", "CPUs", "Mem (Gb)"
        )
        print()
        nprint(string, style="bold")

        for instance_type in AwsUtils._instance_types():
            response = ec2.describe_spot_price_history(
                InstanceTypes=[instance_type],
                Filters=[{"Name": "product-description", "Values": ["Linux/UNIX"]}],
            )

            price = float(response["SpotPriceHistory"][0]["SpotPrice"])

            num_gpus, gpu_type, mem, cpus = INSTANCE_GPU_MAP[instance_type]
            string = AwsUtils._format_price_string(
                instance_type, round(price, 2), f"{num_gpus} x {gpu_type}", cpus, mem
            )
            print(string)
        print()

    @staticmethod
    def _instance_types() -> Generator[str, None, None]:
        """Yield all relevant EC2 instance types in region CONFIG.region_name"""

        describe_args = {}
        client = CONFIG.get_session().client("ec2")

        def instance_type_generator():
            while True:
                describe_result = client.describe_instance_types(**describe_args)
                yield from (i["InstanceType"] for i in describe_result["InstanceTypes"])
                if "NextToken" not in describe_result:
                    break
                describe_args["NextToken"] = describe_result["NextToken"]

        return (
            inst
            for inst in sorted(instance_type_generator())
            if inst.startswith(("p2", "p3", "p4", "g4d"))
        )

    @staticmethod
    def _format_price_string(instance_type, price, gpus, cpus, mem) -> str:
        string = "\t{0: <16} {1: <15} {2: <10} {3: <5} {4:<7}".format(
            instance_type, price, gpus, cpus, mem
        )
        return string

    @staticmethod
    def spending(qty: int, timescale: str, dry_run=False) -> None:
        today = date.today()
        time_format = "%Y-%m-%d"

        if timescale == "months":
            start_date = (today - relativedelta(months=qty)).replace(day=1)
            start = start_date.strftime(time_format)
            end = today.strftime(time_format)
            granularity = "monthly"
        elif timescale == "days":
            start_date = today - relativedelta(days=qty)
            start = start_date.strftime(time_format)
            end = today.strftime(time_format)
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
                    {"Dimensions": {"Key": "SERVICE", "Values": services}},
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
            if not groups:
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
