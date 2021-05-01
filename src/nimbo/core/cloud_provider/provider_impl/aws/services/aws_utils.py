import json
from typing import Generator

from nimbo import CONFIG
from nimbo.core.cloud_provider.provider.services.utils import Utils
from nimbo.core.constants import FULL_REGION_NAMES, INSTANCE_GPU_MAP


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
        print(string)

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

    @staticmethod
    def ls_spot_gpu_prices(dry_run=False) -> None:
        if dry_run:
            return

        ec2 = CONFIG.get_session().client("ec2")

        string = AwsUtils._format_price_string(
            "InstanceType", "Price ($/hour)", "GPUs", "CPUs", "Mem (Gb)"
        )
        print(string)

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
        string = "{0: <16} {1: <15} {2: <10} {3: <5} {4:<7}".format(
            instance_type, price, gpus, cpus, mem
        )
        return string
