import functools
import os
import sys

import botocore
import botocore.errorfactory
import click

from nimbo import CONFIG
from nimbo.core.config import RequiredCase
from nimbo.core.constants import (
    IS_TEST_ENV,
    NIMBO_DEFAULT_CONFIG,
)
from nimbo.core.print import nprint


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


def handle_errors(func):
    """
    Decorator for catching boto3 ClientErrors, ValueError or KeyboardInterrupts.
    In case of error print the error message and stop Nimbo.
    """

    @functools.wraps(func)
    def decorated(*args, **kwargs):
        if IS_TEST_ENV:
            return func(*args, **kwargs)
        else:
            try:
                return func(*args, **kwargs)
            except botocore.errorfactory.ClientError as e:
                nprint(e, style="error")
                sys.exit(1)
            except ValueError as e:
                nprint(e, style="error")
                sys.exit(1)
            except KeyboardInterrupt:
                print("Aborting...")
                sys.exit(1)

    return decorated


def generate_config(quiet=False) -> None:
    """ Create an example Nimbo config in the project root """

    if os.path.isfile(CONFIG.nimbo_config_file):
        should_overwrite = click.confirm(
            f"{CONFIG.nimbo_config_file} already exists, do you want to overwrite it?"
        )
        if not should_overwrite:
            print("Leaving Nimbo config intact")
            return

    with open(CONFIG.nimbo_config_file, "w") as f:
        f.write(NIMBO_DEFAULT_CONFIG)

    if not quiet:
        print(f"Example config written to {CONFIG.nimbo_config_file}")
