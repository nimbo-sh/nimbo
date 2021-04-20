import enum
import os
from typing import Dict, Optional

import botocore.exceptions
import botocore.session
import pydantic
import yaml

_NIMBO_CONFIG_FILE = "nimbo-config.yml"
_TELEMETRY_URL = "https://nimbotelemetry-8ef4c-default-rtdb.firebaseio.com/events.json"
_FULL_REGION_NAMES = {
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


class _DiskType(str, enum.Enum):
    STANDARD = "standard"
    IO1 = "io1"
    IO2 = "io2"
    GP2 = "gp2"
    SC1 = "sc1"
    ST1 = "st1"
    GP3 = "gp3"


class RequiredCase(int, enum.Enum):
    NONE = enum.auto()
    MINIMAL = enum.auto()
    STORAGE = enum.auto()
    INSTANCE = enum.auto()
    JOB = enum.auto()


class _NimboConfig(pydantic.BaseModel):
    class Config:
        title = "Nimbo configuration"
        validate_assignment = True
        extra = "forbid"

    aws_profile: Optional[str] = None
    region_name: Optional[str] = None

    local_datasets_path: Optional[str] = None
    local_results_path: Optional[str] = None
    s3_datasets_path: Optional[str] = None
    s3_results_path: Optional[str] = None

    instance_type: Optional[str] = None
    image: str = "ubuntu18-latest-drivers"
    disk_size: Optional[int] = None
    disk_iops: pydantic.conint(ge=0) = None
    disk_type: _DiskType = _DiskType.STANDARD
    spot: bool = False
    spot_duration: pydantic.conint(ge=60, le=360, multiple_of=60) = None
    security_group: Optional[str] = None
    instance_key: Optional[str] = None

    conda_env: Optional[str] = None
    run_in_background: bool = False
    persist: bool = False

    ssh_timeout: pydantic.conint(strict=True, ge=0) = 120
    telemetry: bool = True

    # The following are defined internally
    nimbo_config_file: str = _NIMBO_CONFIG_FILE
    _nimbo_config_file_exists: bool = pydantic.PrivateAttr(
        default=os.path.isfile(_NIMBO_CONFIG_FILE)
    )
    user_id: Optional[str] = None
    telemetry_url: str = _TELEMETRY_URL
    full_region_names: Dict[str, str] = _FULL_REGION_NAMES

    def assert_required_config_exists(self, case: RequiredCase) -> None:
        """ Designed to be used with the assert_required_config annotation """

        required_config = {}

        if case == RequiredCase.NONE:
            return
        elif not self._nimbo_config_file_exists:
            raise FileNotFoundError(
                f"Nimbo configuration file '{self.nimbo_config_file}' not found.\n"
                "Run 'nimbo generate-config' to create the default config file."
            )

        minimal_required_config = {
            "aws_profile": self.aws_profile,
            "region_name": self.region_name,
        }
        storage_required_config = {
            "local_results_path": self.local_results_path,
            "local_datasets_path": self.local_datasets_path,
            "s3_results_path": self.s3_results_path,
            "s3_datasets_path": self.s3_datasets_path,
        }
        instance_required_config = {
            "instance_type": self.instance_type,
            "disk_size": self.disk_size,
            "instance_key": self.instance_key,
            "security_group": self.security_group,
        }
        job_required_config = {"conda_env": self.conda_env}

        if case == RequiredCase.STORAGE:
            required_config = {**minimal_required_config, **storage_required_config}
        if case == RequiredCase.INSTANCE:
            required_config = {**minimal_required_config, **instance_required_config}
        if case == RequiredCase.JOB:
            required_config = {
                **minimal_required_config,
                **storage_required_config,
                **instance_required_config,
                **job_required_config,
            }

        if unspecified := [key for key, value in required_config.items() if not value]:
            raise AssertionError(
                f"For running this command {', '.join(unspecified)} should"
                f" be specified in {self.nimbo_config_file}"
            )

    @pydantic.validator("aws_profile")
    def _aws_profile_exists(cls, value):
        if value not in botocore.session.Session().available_profiles:
            raise ValueError(f"AWS Profile {value} could not be found")
        return value

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
        if not value:
            return None

        region_names = _FULL_REGION_NAMES.keys()
        if value not in region_names:
            raise ValueError(
                f"received {value}, expected to be one of {', '.join(region_names)}"
            )
        return value

    @pydantic.validator("local_results_path", "local_datasets_path")
    def _results_path_not_outside_project(cls, value):
        if not value:
            return None

        if os.path.isabs(value):
            raise ValueError("should be a relative path")
        if ".." in value:
            raise ValueError("should not be outside of the project directory")
        return value

    @pydantic.validator("disk_type")
    def _disk_iops_specified_when_needed(cls, value, values):
        if value in [_DiskType.IO1, _DiskType.IO2] and not values["disk_iops"]:
            raise ValueError(
                "for disk types io1 or io2, the 'disk_iops' parameter has "
                "to be specified.\nPlease visit "
                "https://docs.nimbo.sh/nimbo-config-file-options for more details."
            )
        return value

    @pydantic.validator("nimbo_config_file")
    def _nimbo_config_file_unchanged(cls, value):
        if value != _NIMBO_CONFIG_FILE:
            raise ValueError("overriding nimbo config file name is forbidden")
        return value

    @pydantic.validator("telemetry_url")
    def _nimbo_telemetry_url_unchanged(cls, value):
        if value != _TELEMETRY_URL:
            raise ValueError("overriding telemetry url is forbidden")
        return value


def _load_yaml():
    if os.path.isfile(_NIMBO_CONFIG_FILE):
        with open(_NIMBO_CONFIG_FILE, "r") as f:
            return yaml.safe_load(f)

    return {}


def make_config():
    return _NimboConfig(**_load_yaml())
