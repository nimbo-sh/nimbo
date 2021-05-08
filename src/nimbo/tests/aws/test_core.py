import pytest
from click.testing import CliRunner

from nimbo import CONFIG
from nimbo.core.cloud_provider.provider_impl.aws.aws_provider import AwsProvider
from nimbo.core.config import RequiredCase
from nimbo.tests.aws.utils import isolated_filesystem


@pytest.fixture
def runner():
    return ""


@isolated_filesystem(RequiredCase.MINIMAL)
def test_get_image_id(runner: CliRunner):
    reference_image = "ubuntu18-latest-drivers"
    reference_region = "eu-west-1"

    CONFIG.image = reference_image
    CONFIG.region_name = reference_region

    AwsProvider._get_image_id()

    CONFIG.image = "awdghiuadgwui"
    with pytest.raises(ValueError):
        AwsProvider._get_image_id()

    CONFIG.image = reference_image
    CONFIG.region_name = "us-east-2"
    AwsProvider._get_image_id()

    with pytest.raises(ValueError):
        CONFIG.region_name = "us-et-2"
        AwsProvider._get_image_id()

    CONFIG.image = "ami-198571934781039"
    CONFIG.region_name = reference_region
    AwsProvider._get_image_id()
