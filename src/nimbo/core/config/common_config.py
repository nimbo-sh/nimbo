import enum
import os
from typing import Optional, Set

import pydantic


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

    config_path: str
    cloud_provider: CloudProvider = None

    local_datasets_path: Optional[str] = None
    local_results_path: Optional[str] = None

    conda_env: Optional[str] = None
    run_in_background: bool = False
    persist: bool = False

    ip_cidr_range: pydantic.conint(strict=True, ge=0, le=32) = 32
    ssh_timeout: pydantic.conint(strict=True, ge=0) = 180

    user_id: Optional[str] = None

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
