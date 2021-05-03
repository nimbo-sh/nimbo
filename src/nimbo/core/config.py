import enum
import os
import sys
from typing import Any, Dict, Optional, Set

import boto3
import botocore.exceptions
import botocore.session
import pydantic
import yaml

from nimbo.core.statics import FULL_REGION_NAMES, NIMBO_CONFIG_FILE, TELEMETRY_URL


class _DiskType(str, enum.Enum):
    STANDARD = "standard"
    IO1 = "io1"
    IO2 = "io2"
    GP2 = "gp2"
    SC1 = "sc1"
    ST1 = "st1"
    GP3 = "gp3"


class _Encryption(str, enum.Enum):
    AES256 = "AES256"
    AWSKMS = "aws:kms"


class RequiredCase(str, enum.Enum):
    # First digit is a unique ID, other digits are the IDs of dependencies
    NONE = "0"
    MINIMAL = "10"
    STORAGE = "210"
    INSTANCE = "310"
    JOB = "43210"

    @classmethod
    def decompose(cls, *cases: "RequiredCase") -> Set["RequiredCase"]:
        """ Gets all cases that compose each case and the case itself """

        decomposed = set()

        for case in cases:
            for c in RequiredCase:
                if c[0] in case.value:
                    decomposed.add(c)

        # noinspection PyTypeChecker
        return decomposed


class NimboConfig(pydantic.BaseModel):
    class Config:
        title = "Nimbo configuration"
        extra = "forbid"

    aws_profile: Optional[str] = None
    region_name: Optional[str] = None

    local_datasets_path: Optional[str] = None
    local_results_path: Optional[str] = None
    s3_datasets_path: Optional[str] = None
    s3_results_path: Optional[str] = None
    encryption: _Encryption = None

    instance_type: Optional[str] = None
    image: str = "ubuntu18-latest-drivers"
    disk_size: Optional[int] = None
    disk_iops: pydantic.conint(ge=0) = None
    disk_type: _DiskType = _DiskType.GP2
    spot: bool = False
    spot_duration: pydantic.conint(ge=60, le=360, multiple_of=60) = None
    security_group: Optional[str] = None
    instance_key: Optional[str] = None
    role: Optional[str] = None

    conda_env: Optional[str] = None
    run_in_background: bool = False
    persist: bool = False

    ssh_timeout: pydantic.conint(strict=True, ge=0) = 180
    telemetry: bool = True

    # The following are defined internally
    nimbo_config_file: str = NIMBO_CONFIG_FILE
    _nimbo_config_file_exists: bool = pydantic.PrivateAttr(
        default=os.path.isfile(NIMBO_CONFIG_FILE)
    )
    user_id: Optional[str] = None
    user_arn: Optional[str] = None
    telemetry_url: str = TELEMETRY_URL

    def get_session(self) -> boto3.Session:
        session = boto3.Session(
            profile_name=self.aws_profile, region_name=self.region_name
        )

        caller_identity = session.client("sts").get_caller_identity()
        self.user_id = caller_identity["UserId"]
        self.user_arn = caller_identity["Arn"]
        return session

    def assert_required_config_exists(self, *cases: RequiredCase) -> None:
        """ Designed to be used with the assert_required_config annotation """

        cases = RequiredCase.decompose(*cases)

        if len(cases) == 1 and RequiredCase.NONE in cases:
            return
        elif not self._nimbo_config_file_exists:
            raise FileNotFoundError(
                f"Nimbo configuration file '{self.nimbo_config_file}' not found.\n"
                "Run 'nimbo generate-config' to create the default config file."
            )

        required_config = {}

        if RequiredCase.MINIMAL in cases:
            required_config["aws_profile"] = self.aws_profile
            required_config["region_name"] = self.region_name
        if RequiredCase.STORAGE in cases:
            required_config["local_results_path"] = self.local_results_path
            required_config["local_datasets_path"] = self.local_datasets_path
            required_config["s3_results_path"] = self.s3_results_path
            required_config["s3_datasets_path"] = self.s3_datasets_path
        if RequiredCase.INSTANCE in cases:
            required_config["instance_type"] = self.instance_type
            required_config["disk_size"] = self.disk_size
            required_config["instance_key"] = self.instance_key
            required_config["security_group"] = self.security_group
            required_config["role"] = self.role
        if RequiredCase.JOB in cases:
            required_config["conda_env"] = self.conda_env

        unspecified = [key for key, value in required_config.items() if not value]
        if unspecified:
            raise AssertionError(
                f"For running this command '{', '.join(unspecified)}' should "
                f"be specified in {self.nimbo_config_file}"
            )

        bad_fields = {}

        if RequiredCase.MINIMAL in cases:
            bad_fields["aws_profile"] = self._aws_profile_exists()
            bad_fields["region_name"] = self._region_name_valid()
        if RequiredCase.STORAGE in cases:
            bad_fields["local_results_path"] = self._local_results_not_outside_project()
            bad_fields[
                "local_datasets_path"
            ] = self._local_datasets_not_outside_project()
        if RequiredCase.INSTANCE in cases:
            bad_fields["instance_key"] = self._instance_key_valid()
            bad_fields["disk_iops"] = self._disk_iops_specified_when_needed()
        if RequiredCase.JOB in cases:
            bad_fields["conda_env"] = self._conda_env_valid()

        bad_fields = [(key, error) for key, error in bad_fields.items() if error]

        if bad_fields:
            print(
                f"{len(bad_fields)} error{'' if len(bad_fields) == 1 else 's'} "
                f"in {NIMBO_CONFIG_FILE}\n"
            )
            for key, error in bad_fields:
                print(key)
                print(f"  {error}")
            sys.exit(1)

    def _aws_profile_exists(self) -> Optional[str]:
        if self.aws_profile not in botocore.session.Session().available_profiles:
            return f"AWS Profile '{self.aws_profile}' could not be found"

    def _conda_env_valid(self) -> Optional[str]:
        if os.path.isabs(self.conda_env):
            return "conda_env should be a relative path"
        if ".." in self.conda_env:
            return "conda_env should not be outside of the project directory"
        if not os.path.isfile(self.conda_env):
            return f"file '{self.conda_env}' does not exist in the project directory"

    def _instance_key_valid(self) -> Optional[str]:
        if not os.path.isfile(self.instance_key):
            return f"file '{self.instance_key}' does not exist"

        permission = str(oct(os.stat(self.instance_key).st_mode))[-3:]
        if permission[1:] != "00":
            return (
                f"run 'chmod 400 {self.instance_key}' so that only you can read the key"
            )

    def _region_name_valid(self) -> Optional[str]:
        region_names = FULL_REGION_NAMES.keys()
        if self.region_name not in region_names:
            return (
                f"unknown region '{self.region_name}', "
                f"expected to be one of {', '.join(region_names)}"
            )

    def _local_results_not_outside_project(self) -> Optional[str]:
        if os.path.isabs(self.local_results_path):
            return "local_results_path should be a relative path"
        if ".." in self.local_results_path:
            return "local_results_path should not be outside of the project directory"

    def _local_datasets_not_outside_project(self) -> Optional[str]:
        if os.path.isabs(self.local_datasets_path):
            return "local_datasets_path should be a relative path"
        if ".." in self.local_datasets_path:
            return "local_datasets_path should not be outside of the project directory"

    def _disk_iops_specified_when_needed(self) -> Optional[str]:
        if self.disk_type in [_DiskType.IO1, _DiskType.IO2] and not self.disk_iops:
            return (
                "for disk types io1 or io2, the 'disk_iops' parameter has "
                "to be specified.\nPlease visit "
                "https://docs.nimbo.sh/nimbo-config-file-options for more details."
            )

    @pydantic.validator("nimbo_config_file")
    def _nimbo_config_file_unchanged(cls, value):
        if value != NIMBO_CONFIG_FILE:
            raise ValueError("overriding nimbo config file name is forbidden")
        return value

    @pydantic.validator("telemetry_url")
    def _nimbo_telemetry_url_unchanged(cls, value):
        if value != TELEMETRY_URL:
            raise ValueError("overriding telemetry url is forbidden")
        return value

    def save_initial_state(self) -> None:
        raise NotImplementedError(
            "save_initial_state is only available for NimboTestConfig"
        )

    def reset_required_config(self) -> None:
        raise NotImplementedError(
            "reset_required_config is only available for NimboTestConfig"
        )

    def inject_required_config(self, *cases: RequiredCase) -> None:
        raise NotImplementedError(
            "inject_required_config is only available for NimboTestConfig"
        )


def load_yaml_from_file(file: str) -> Dict[str, Any]:
    if os.path.isfile(file):
        with open(file, "r") as f:
            return yaml.safe_load(f)

    return {}


def make_config() -> NimboConfig:
    return NimboConfig(**load_yaml_from_file(NIMBO_CONFIG_FILE))
