import pathlib
import os

IS_TEST_ENV = "NIMBO_ENV" in os.environ and os.environ["NIMBO_ENV"] == "test"

NIMBO_ROOT = str(pathlib.Path(__file__).parent.parent.absolute())
NIMBO_CONFIG_FILE = "nimbo-config.yml"
TELEMETRY_URL = "https://nimbotelemetry-8ef4c-default-rtdb.firebaseio.com/events.json"

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


FULL_REGION_NAMES = {
    "af-south-1": "Africa (Cape Town)",
    "ap-east-1": "Asia Pacific (Hong Kong)",
    "ap-south-1": "Asia Pacific (Mumbai)",
    "ap-northeast-3": "Asia Pacific (Osaka)",
    "ap-northeast-2": "Asia Pacific (Seoul)",
    "ap-southeast-1": "Asia Pacific (Singapore)",
    "ap-southeast-2": "Asia Pacific (Sydney)",
    "ap-northeast-1": "Asia Pacific (Tokyo)",
    "ca-central-1": "Canada (Central)",
    "eu-central-1": "EU (Frankfurt)",
    "eu-west-1": "EU (Ireland)",
    "eu-west-2": "EU (London)",
    "eu-south-1": "EU (Milan)",
    "eu-west-3": "EU (Paris)",
    "eu-north-1": "EU (Stockholm)",
    "me-south-1": "Middle East (Bahrain)",
    "sa-east-1": "South America (Sao Paulo)",
    "us-east-1": "US East (N. Virginia)",
    "us-east-2": "US East (Ohio)",
    "us-west-1": "US West (N. California)",
    "us-west-2": "US West (Oregon)",
}
