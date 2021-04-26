from typing import Union

from nimbo.core.config.aws_config import AwsConfig
from nimbo.core.config.common import CloudProvider, load_yaml_from_file
from nimbo.core.config.common import RequiredCase
from nimbo.core.config.gcp_config import GcpConfig
from nimbo.core.constants import NIMBO_CONFIG_FILE


def make_config() -> Union[AwsConfig, GcpConfig]:
    config = load_yaml_from_file(NIMBO_CONFIG_FILE)

    if "provider" not in config:
        raise Exception("TODO")

    try:
        provider = CloudProvider(config["provider"].lower())
    except ValueError:
        raise Exception("TODO")

    if provider == CloudProvider.AWS:
        return AwsConfig(**config)

    return GcpConfig(**config)
