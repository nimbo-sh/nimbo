import enum
import os
import typing as t

import pydantic

from nimbo.core.constants import NIMBO_CONFIG_FILE, TELEMETRY_URL


class RequiredCase(str, enum.Enum):
    # First digit is a unique ID, other digits are the IDs of dependencies
    NONE = "0"
    MINIMAL = "10"
    STORAGE = "210"
    INSTANCE = "310"
    JOB = "43210"

    @classmethod
    def decompose(cls, *cases: "RequiredCase") -> t.Set["RequiredCase"]:
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

    cloud_provider: CloudProvider = None

    local_datasets_path: t.Optional[str] = None
    local_results_path: t.Optional[str] = None

    conda_env: t.Optional[str] = None
    run_in_background: bool = False
    persist: bool = False

    ip_cidr_range: pydantic.conint(strict=True, ge=0, le=32) = 32
    ssh_timeout: pydantic.conint(strict=True, ge=0) = 180
    telemetry: bool = True

    # The following are defined internally
    nimbo_config_file: str = NIMBO_CONFIG_FILE
    user_id: t.Optional[str] = None
    _nimbo_config_file_exists: bool = pydantic.PrivateAttr(
        default=os.path.isfile(NIMBO_CONFIG_FILE)
    )
    telemetry_url: str = TELEMETRY_URL

    def _local_results_not_outside_project(self) -> t.Optional[str]:
        return self._validate_directory(self.local_results_path, "local_results_path")

    def _local_datasets_not_outside_project(self) -> t.Optional[str]:
        return self._validate_directory(self.local_datasets_path, "local_datasets_path")

    @staticmethod
    def _validate_directory(directory: str, config_key: str) -> t.Optional[str]:
        if not os.path.isdir(directory):
            return f"{config_key} does not exist or is not a directory"
        if os.path.isabs(directory):
            return f"{config_key} should be a relative path"
        if ".." in directory:
            return f"{config_key} should not be outside of the project directory"

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
