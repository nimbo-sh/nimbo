import pathlib
import re
import sys

import boto3
import pydantic

from nimbo.core import config

NIMBO_ROOT = str(pathlib.Path(__file__).parent.parent.absolute())
NIMBO_DEFAULT_CONFIG = """# Data paths
local_datasets_path: my-datasets-folder  # relative to project root
local_results_path: my-results-folder    # relative to project root
s3_datasets_path: s3://my-bucket/my-project/some-datasets-folder
s3_results_path: s3://my-bucket/my-project/some-results-folder

# Device, environment and regions
aws_profile: default
region_name: eu-west-1
instance_type: p2.xlarge
spot: no

image: ubuntu18-latest-drivers
disk_size: 128
conda_env: my-conda-file.yml

# Job options
run_in_background: no
persist: no

# Permissions and credentials
security_group: default
instance_key: my-ec2-key-pair.pem
"""


# Each element is [num_gpus, gpu_type, ram, vcpus]
INSTANCE_GPU_MAP = {
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


try:
    # TODO: test env
    CONFIG = config.make_config()
except pydantic.error_wrappers.ValidationError as e:
    error_msg = str(e)
    title_end = error_msg.index("\n", 1)
    new_title = (
        f"{len(e.errors())} validation "
        + f"error{'' if len(e.errors()) == 1 else 's'} in Nimbo config\n"
    )
    print(new_title + re.sub(r"\(type=.*\)", "", error_msg[title_end:]))
    sys.exit(1)
except FileNotFoundError as e:
    print(e)
    sys.exit(1)

SESSION = boto3.Session(profile_name=CONFIG.aws_profile, region_name=CONFIG.region_name)
CONFIG.user_id = SESSION.client("sts").get_caller_identity()["Arn"]
