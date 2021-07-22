import functools
import re
import sys
import typing as t

import pkg_resources
import pydantic

import nimbo.core.config
import nimbo.tests.aws.config
from nimbo.core.config import RequiredCase
from nimbo.core.config.aws_config import AwsConfig
from nimbo.core.config.common_config import CloudProvider
from nimbo.core.config.gcp_config import GcpConfig
from nimbo.core.constants import IS_TEST_ENV
from nimbo.core.print import nprint

version = pkg_resources.get_distribution("nimbo").version


CONFIG: t.Optional[t.Union[AwsConfig, GcpConfig]] = None
_CLOUD = None


def set_config(config_factory, config_path):
    global CONFIG, _CLOUD

    try:
        CONFIG = config_factory(config_path)
    except pydantic.error_wrappers.ValidationError as e:
        e_msg = str(e)
        e_num = len(e.errors())
        title_end = e_msg.index("\n", 1)
        new_title = (
            f"{e_num} error{'' if e_num == 1 else 's'} in "
            f"{config_path if config_path else 'nimbo-config.yml'}\n"
        )
        print(new_title + re.sub(r"\(type=.*\)", "", e_msg[title_end:]))
        sys.exit(1)

    # Both of these imports depend on this file
    from nimbo.core.cloud_provider.provider_impl.aws.aws_provider import AwsProvider
    from nimbo.core.cloud_provider.provider_impl.gcp.gcp_provider import GcpProvider

    if CONFIG.cloud_provider == CloudProvider.AWS:
        _CLOUD = AwsProvider()
    else:
        _CLOUD = GcpProvider()


if IS_TEST_ENV:
    set_config(nimbo.tests.aws.config.make_config, "nimbo-config.yml")


def assert_required_config(*cases: RequiredCase):
    """
    Decorator for ensuring that required config is present
    """

    def decorator(func):
        @functools.wraps(func)
        def decorated(*args, **kwargs):
            try:
                CONFIG.assert_required_config_exists(*cases)
                return func(*args, **kwargs)
            except AssertionError as e:
                nprint(e, style="error")
                sys.exit(1)
            except FileNotFoundError as e:
                # Happens when nimbo config file is not found
                nprint(e, style="error")
                sys.exit(1)

        return decorated

    return decorator


def cloud_context(func):
    """
    Decorator for injecting a key-value argument cloud of type AwsProvider|GcpProvider
    """

    @functools.wraps(func)
    def decorated(*args, **kwargs):
        kwargs["cloud"] = _CLOUD
        return func(*args, **kwargs)

    return decorated
