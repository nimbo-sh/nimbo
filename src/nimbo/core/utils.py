import os

import click

from nimbo.core.constants import NIMBO_DEFAULT_CONFIG


def generate_config(config_path: str) -> None:
    """ Create an example Nimbo config in the project root """

    if os.path.isfile(config_path):
        should_overwrite = click.confirm(
            f"{config_path} already exists, do you want to overwrite it?"
        )
        if not should_overwrite:
            print("Leaving Nimbo config intact")
            return

    with open(config_path, "w") as f:
        f.write(NIMBO_DEFAULT_CONFIG)

    print(f"Example config written to {config_path}")
