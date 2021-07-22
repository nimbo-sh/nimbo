import enum
import os
import sys
from typing import Optional

import boto3
import botocore
import botocore.session
import pydantic

from nimbo.core.config.common_config import BaseConfig, RequiredCase
from nimbo.core.constants import FULL_REGION_NAMES


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


class AwsConfig(BaseConfig):
    aws_profile: Optional[str] = None
    region_name: Optional[str] = None

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

    # The following are defined internally
    user_arn: Optional[str] = None

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
        elif not os.path.isfile(self.config_path):
            raise FileNotFoundError(
                f"Nimbo configuration file '{self.config_path}' not found.\n"
                "Run 'nimbo generate-config' to create the default config file."
            )

        required_config = {}

        if RequiredCase.MINIMAL in cases:
            required_config["cloud_provider"] = self.cloud_provider
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
                f"For running this command '{', '.join(unspecified)}' should"
                f" be specified in {self.config_path}"
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
                f"in {self.config_path}\n"
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

    def _disk_iops_specified_when_needed(self) -> Optional[str]:
        if self.disk_type in [_DiskType.IO1, _DiskType.IO2] and not self.disk_iops:
            return (
                "for disk types io1 or io2, the 'disk_iops' parameter has "
                "to be specified.\nPlease visit "
                "https://docs.nimbo.sh/nimbo-config-file-options for more details."
            )
