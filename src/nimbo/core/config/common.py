import enum
import os
from typing import Any, Dict, Optional, Set

import pydantic
import yaml

from nimbo.core.constants import NIMBO_CONFIG_FILE, TELEMETRY_URL


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


class CloudProvider(str, enum.Enum):
    AWS = "AWS"
    GCP = "GCP"


class BaseConfig(pydantic.BaseModel):
    class Config:
        title = "Nimbo configuration"
        extra = "forbid"

    provider: Optional[CloudProvider] = None

    local_datasets_path: Optional[str] = None
    local_results_path: Optional[str] = None

    conda_env: Optional[str] = None
    run_in_background: bool = False
    persist: bool = False

    ssh_timeout: pydantic.conint(strict=True, ge=0) = 180
    telemetry: bool = True

    # The following are defined internally
    nimbo_config_file: str = NIMBO_CONFIG_FILE
    user_id: Optional[str] = None
    _nimbo_config_file_exists: bool = pydantic.PrivateAttr(
        default=os.path.isfile(NIMBO_CONFIG_FILE)
    )
    telemetry_url: str = TELEMETRY_URL

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


def load_yaml_from_file(file: str) -> Dict[str, Any]:
    if os.path.isfile(file):
        with open(file, "r") as f:
            return yaml.safe_load(f)

    return {}
