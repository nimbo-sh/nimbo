import enum
import os
import pathlib
import sys
from typing import Dict, Optional

import boto3
import pydantic
import yaml

# TODO: Check what happens if there's a missing field, or missing value
# TODO: Check what happens when you have wrong field names
# TODO: what happens when I have incorrect value for AWS resources
# TODO: test validators
# TODO: test absolute pem path

# TODO: before final commit
# TODO: grep for todo
# TODO: update docs and generated (ssh_timeout), .pem file extension now needed

NIMBO_ROOT = str(pathlib.Path(__file__).parent.parent.absolute())
NIMBO_CONFIG_FILE = "nimbo-config.yml"
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
instance_key: my-ec2-key-pair  # without .pem
"""

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


class RequiredConfigCase(enum.Enum):
    MINIMAL = enum.auto()
    STORAGE = enum.auto()
    INSTANCE = enum.auto()
    JOB = enum.auto()


class _Config(pydantic.BaseModel):
    # TODO: pathlib.Path type?

    local_datasets_path: Optional[str] = None
    local_results_path: Optional[str] = None
    s3_datasets_path: Optional[str] = None
    s3_results_path: Optional[str] = None
    aws_profile: str = "default"
    region_name: str = "eu-west-1"
    instance_type: Optional[str] = None
    spot: bool = False
    image: str = "ubuntu18-cuda10.2-cudnn7.6-conda4.9.2"
    spot_duration: pydantic.conint(ge=60, le=360, multiple_of=60) = 60
    disk_size: int = 128
    run_in_background: bool = False
    persist: bool = False
    security_group: str = "default"
    conda_env: Optional[str] = None
    instance_key: Optional[str] = None
    ssh_timeout: pydantic.conint(ge=0) = 120
    user_id: str = None

    _minimal_required_config: Dict[str, Optional[str]] = pydantic.PrivateAttr(
        default={"aws_profile": aws_profile, "region_name": region_name}
    )
    _storage_required_config: Dict[str, Optional[str]] = pydantic.PrivateAttr(
        default={
            "local_results_path": local_results_path,
            "local_datasets_path": local_datasets_path,
            "s3_results_path": s3_results_path,
            "s3_datasets_path": s3_datasets_path,
        }
    )
    _instance_required_config: Dict[str, Optional[str]] = pydantic.PrivateAttr(
        default={"instance_type": instance_type, "instance_key": instance_key}
    )
    _job_required_config: Dict[str, Optional[str]] = pydantic.PrivateAttr(
        default={"conda_env": conda_env}
    )

    def assert_required_config_exists(self, case: RequiredConfigCase) -> None:
        """ Designed to be used with the assert_required_config annotation """

        config = self._minimal_required_config

        if case == RequiredConfigCase.STORAGE:
            config = {**self._minimal_required_config, **self._storage_required_config}
        if case == RequiredConfigCase.INSTANCE:
            config = {**self._minimal_required_config, **self._instance_required_config}
        if case == RequiredConfigCase.JOB:
            config = {
                **self._minimal_required_config,
                **self._storage_required_config,
                **self._instance_required_config,
                **self._job_required_config,
            }

        if unspecified := [key for key, value in config.items() if not value]:
            raise AssertionError(
                f"For running this command, {', '.join(unspecified)} should"
                f" be specified in {NIMBO_CONFIG_FILE}"
            )

    @pydantic.validator("conda_env")
    def _conda_env_valid(cls, value):
        if not value:
            return None

        if os.path.isabs(value):
            raise ValueError("should be a relative path")
        if ".." in value:
            raise ValueError("should not be outside of the project directory")
        if not os.path.isfile(value):
            raise ValueError(f"file '{value}' does not exist in the project directory")
        return value

    @pydantic.validator("instance_key")
    def _instance_key_valid(cls, value):
        if not value:
            return None

        if not os.path.isfile(value):
            raise ValueError(f"'{value}' does not exist")

        permission = str(oct(os.stat(value).st_mode))[-3:]
        if permission[1] == 0 and permission[2] == 0:
            raise ValueError(
                f"run 'chmod 400 {value}' so that only you can read the key"
            )

        return value

    @pydantic.validator("region_name")
    def _region_name_valid(cls, value):
        region_names = FULL_REGION_NAMES.keys()
        if value not in region_names:
            raise ValueError(f"expected {value} to be one of {region_names}")
        return value

    @pydantic.validator("local_datasets_path")
    def _datasets_path_not_outside_project(cls, value):
        if not value:
            return None

        if os.path.isabs(value):
            raise ValueError("should be a relative path")
        if ".." in value:
            raise ValueError("should not be outside of the project directory")
        return value

    @pydantic.validator("local_results_path")
    def _results_path_not_outside_project(cls, value):
        if not value:
            return None

        if os.path.isabs(value):
            raise ValueError("should be a relative path")
        if ".." in value:
            raise ValueError("should not be outside of the project directory")
        return value

    @pydantic.validator("user_id")
    def _user_id_not_specified(cls, value):
        # user_id is set dynamically and should not be specified in the config
        if value:
            raise ValueError("field not allowed")
        return value


def _load_yaml():
    if not os.path.isfile(NIMBO_CONFIG_FILE):
        raise FileNotFoundError(
            f"Nimbo configuration file '{NIMBO_CONFIG_FILE}' not found.\n"
            "Run 'nimbo generate-config' to create the default config file."
        )

    with open(NIMBO_CONFIG_FILE, "r") as f:
        d = yaml.safe_load(f)

        # TODO: this should not be needed, and right now can potentially break some stuff
        for field in d:
            if type(d[field]) == str:
                d[field] = d[field].rstrip("/")

        return d


try:
    CONFIG = _Config(**_load_yaml())
except pydantic.error_wrappers.ValidationError as e:
    print(e)
    sys.exit(1)
except FileNotFoundError as e:
    print(e)
    sys.exit(1)

SESSION = boto3.Session(profile_name=CONFIG.aws_profile, region_name=CONFIG.region_name)
CONFIG.user_id = SESSION.client("sts").get_caller_identity()["UserId"]
