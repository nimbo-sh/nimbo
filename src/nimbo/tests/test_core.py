import pytest
from click.testing import CliRunner

from nimbo.core.globals import CONFIG
from nimbo.core.utils import get_image_id
from nimbo.tests.utils import copy_assets


def test_get_image_id():
    runner = CliRunner()
    with runner.isolated_filesystem():
        copy_assets(["config"])

        reference_image = "ubuntu18-latest-drivers"
        reference_region = "eu-west-1"

        CONFIG.image = reference_image
        CONFIG.region_name = reference_region
        get_image_id()

        CONFIG.image = "awdghiuadgwui"
        with pytest.raises(ValueError):
            get_image_id()

        CONFIG.image = reference_image
        CONFIG.region_name = "us-east-2"
        get_image_id()

        CONFIG.region_name = "us-et-2"
        with pytest.raises(ValueError):
            get_image_id()

        CONFIG.image = "ami-198571934781039"
        CONFIG.region_name = reference_region
        get_image_id()
