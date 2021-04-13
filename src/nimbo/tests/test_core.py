import os
from os.path import join
from shutil import copy, rmtree
import subprocess
import pytest
from click.testing import CliRunner
from botocore.exceptions import ClientError

from nimbo.core.config_utils import load_config
from nimbo.core.ami import get_image_id
from nimbo.tests.utils import copy_assets


def test_get_image_id():
    runner = CliRunner()
    with runner.isolated_filesystem():
        copy_assets(["config"])

        reference_image = "ubuntu18-latest-drivers"
        reference_region = "eu-west-1"

        config = load_config()
        config["image"] = reference_image
        config["region_name"] = reference_region
        get_image_id(config)

        config["image"] = "awdghiuadgwui"
        with pytest.raises(ValueError):
            get_image_id(config)

        config["image"] = reference_image
        config["region_name"] = "us-east-2"
        get_image_id(config)

        config["region_name"] = "us-et-2"
        with pytest.raises(ValueError):
            get_image_id(config)

        config["image"] = "ami-198571934781039"
        config["region_name"] = reference_region
        get_image_id(config)
