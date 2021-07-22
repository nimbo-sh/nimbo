import abc
import os
import random
import string
from typing import Any, Dict, Optional, Union

import pydantic

from nimbo.core.config import (
    AwsConfig,
    CloudProvider,
    GcpConfig,
    RequiredCase,
    yaml_loader,
)

CONDA_ENV = "env.yml"
ASSETS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


def _random_string_of_len(length: int) -> str:
    return "".join(random.choice(string.ascii_letters) for _ in range(length))


S3_DATASETS_PATH = f"s3://nimbo-test-bucket/{_random_string_of_len(20)}"
S3_RESULTS_PATH = f"s3://nimbo-test-bucket/{_random_string_of_len(20)}"


class CommonTestConfigMixin(abc.ABC, pydantic.BaseModel):
    # Can't use pydantic.PrivateAttr here as pydantic complains about overlap later
    # user_id and _initial_state fields defined here to prevent undefined warnings
    user_id: Optional[str] = None
    _initial_state: Dict[str, Any] = {}

    def save_initial_state(self):
        self._initial_state = self.dict()

    def reset_required_config(self) -> None:
        if len(self._initial_state) <= 1:
            raise ValueError(
                "You must run save_initial_state to use reset_required_config"
            )

        # user_id is set after save_initial_state
        if not self._initial_state["user_id"]:
            self._initial_state["user_id"] = self.user_id

        for key, value in self._initial_state.items():
            setattr(self, key, value)

    @abc.abstractmethod
    def inject_required_config(self, *cases: RequiredCase) -> None:
        ...


class AwsTestConfig(CommonTestConfigMixin, AwsConfig):
    _initial_state: Dict[str, Any] = pydantic.PrivateAttr(default_factory=dict)

    def inject_required_config(self, *cases: RequiredCase) -> None:
        cases = RequiredCase.decompose(*cases)

        if RequiredCase.NONE in cases:
            self.telemetry = False
        if RequiredCase.MINIMAL in cases:
            self.region_name = "eu-west-1"
        if RequiredCase.STORAGE in cases:
            self.local_datasets_path = "random_datasets"
            self.local_results_path = "random_results"
            self.s3_datasets_path = S3_DATASETS_PATH
            self.s3_results_path = S3_RESULTS_PATH
        if RequiredCase.INSTANCE in cases:
            self.image = "ubuntu18-latest-drivers"
            self.disk_size = 64
            self.instance_type = "p2.xlarge"
            self.instance_key = self._find_instance_key(ASSETS_PATH, self.region_name)
        if RequiredCase.JOB in cases:
            self.conda_env = CONDA_ENV

    @staticmethod
    def _find_instance_key(directory: str, region_name: str) -> str:
        # Instance keys are supposed to be prefixed with region name for testing
        for file in os.listdir(directory):
            if file.startswith(region_name) and file.endswith(".pem"):
                return file


class GcpTestConfig(CommonTestConfigMixin, GcpConfig):
    _initial_state: Dict[str, Any] = pydantic.PrivateAttr(default_factory=dict)

    def inject_required_config(self, *cases: RequiredCase) -> None:
        pass


def make_config(config_path: str) -> Union[AwsTestConfig, GcpTestConfig]:
    raw_config = yaml_loader.from_file(os.path.join(ASSETS_PATH, config_path))
    raw_config["config_path"] = config_path

    cloud_provider = CloudProvider(raw_config["cloud_provider"].upper())

    if cloud_provider == CloudProvider.AWS:
        config = AwsTestConfig(**raw_config)
    else:
        config = GcpTestConfig(**raw_config)

    config.save_initial_state()

    return config
