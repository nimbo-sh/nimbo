import os
import re
from typing import Any, Dict

import pydantic
import yaml

# pattern for extracting env variables
from nimbo.core.config.common_config import BaseConfig

RE_PATTERN = re.compile(
    r"(\$(?:{(?P<env>(.*?))(\|(?P<env_default>.*?))?}))",
    re.MULTILINE | re.UNICODE | re.IGNORECASE | re.VERBOSE,
)


def _substitute_env_vars(key: str, value: str) -> str:
    """
    Take in a string optionally containing "${ENV_VARIABLE|optional-default}"
    and return a new string with substituted environment variables
    """

    replacements = []

    for env_var in RE_PATTERN.finditer(value):
        groups = env_var.groupdict()
        variable, default = groups["env"], groups["env_default"]

        to_replace = "${" + variable
        to_replace += "|" + default if default else ""
        to_replace += "}"

        replace_with = default
        try:
            replace_with = os.environ[variable]
        except KeyError:
            if not replace_with:
                raise pydantic.ValidationError(
                    [
                        pydantic.error_wrappers.ErrorWrapper(
                            Exception(f"Environment variable {variable} not defined"),
                            key,
                        )
                    ],
                    BaseConfig,
                )

        replacements.append([to_replace, replace_with])

    if replacements:
        for to_replace, replace_with in replacements:
            value = value.replace(to_replace, replace_with)

    return value


def from_file(file: str) -> Dict[str, Any]:
    """ Load YAML into a dictionary, inject environment variables """

    if os.path.isfile(file):
        with open(file, "r") as f:
            config = yaml.safe_load(f)

        for key, value in config.items():
            if type(value) == str and "${" in value:
                config[key] = _substitute_env_vars(key, value)

        return config

    return {}
