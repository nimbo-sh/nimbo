import typing as t

import pydantic

import nimbo.core.config.yaml_loader
from nimbo.core.config.aws_config import AwsConfig
from nimbo.core.config.common_config import CloudProvider
from nimbo.core.config.common_config import RequiredCase
from nimbo.core.config.gcp_config import GcpConfig


# noinspection PyUnresolvedReferences
def make_config(config_path: str) -> t.Union[AwsConfig, GcpConfig]:
    config = yaml_loader.from_file(config_path)
    config["config_path"] = config_path

    # Provider field validation is postponed. If cloud_provider is not specified,
    # assume AwsConfig for running commands like --help and generate-config.
    if "cloud_provider" not in config:
        return AwsConfig(**config)
    else:
        config["cloud_provider"] = config["cloud_provider"].upper()

    try:
        cloud_provider = CloudProvider(config["cloud_provider"])
    except ValueError:
        permitted_values = ", ".join([f"'{p.value}'" for p in CloudProvider])
        raise pydantic.ValidationError(
            [
                pydantic.error_wrappers.ErrorWrapper(
                    Exception(
                        f"value is not a valid enumeration member; permitted: "
                        f"{permitted_values}"
                    ),
                    "cloud_provider",
                )
            ],
            AwsConfig,
        )

    if cloud_provider == CloudProvider.AWS:
        return AwsConfig(**config)

    return GcpConfig(**config)
