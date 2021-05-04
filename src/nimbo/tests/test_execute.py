import os

import pytest
from click.testing import CliRunner

from nimbo import CONFIG
from nimbo.main import cli
from nimbo.core import execute
from nimbo.core.statics import FULL_REGION_NAMES
from nimbo.core.config import RequiredCase
from nimbo.tests.utils import isolated_filesystem


@pytest.fixture
def runner():
    return ""


@isolated_filesystem(RequiredCase.INSTANCE, RequiredCase.STORAGE)
def test_test_access(runner: CliRunner):
    result = runner.invoke(cli, "test-access", catch_exceptions=False)
    assert result.exit_code == 0


@isolated_filesystem(RequiredCase.JOB)
def test_run_no_code(runner: CliRunner):
    result = runner.invoke(
        cli, "delete-all-instances", input="y", catch_exceptions=False
    )
    assert result.exit_code == 0
    result = runner.invoke(cli, "run 'python --version'", catch_exceptions=False)
    assert result.exit_code == 0
    result = runner.invoke(
        cli, "delete-all-instances", input="y", catch_exceptions=False
    )
    assert result.exit_code == 0


@isolated_filesystem(RequiredCase.JOB)
def test_launch(runner: CliRunner):
    dst = os.getcwd()
    instance_keys = [p for p in os.listdir(dst) if p[-4:] == ".pem"]

    for instance_key in instance_keys:
        for region_name in FULL_REGION_NAMES.keys():
            if instance_key.startswith(region_name):
                CONFIG.region_name = region_name
                break
        else:
            raise Exception(
                f"Instance key {instance_key} does not begin with a valid region name"
            )

        CONFIG.instance_key = instance_key
        response = execute.run_job("_nimbo_launch", dry_run=False)

        assert response["message"] == "_nimbo_launch_success"
        instance_id = response["instance_id"]

        result = runner.invoke(
            cli, f"delete-instance {instance_id}", catch_exceptions=False
        )
        assert result.exit_code == 0


@isolated_filesystem(RequiredCase.JOB)
def test_spot_launch(runner: CliRunner):
    CONFIG.spot = True
    response = execute.run_job("_nimbo_launch", dry_run=False)

    assert response["message"] == "_nimbo_launch_success"
    instance_id = response["instance_id"]

    result = runner.invoke(
        cli, f"delete-instance {instance_id}", catch_exceptions=False
    )
    assert result.exit_code == 0


@isolated_filesystem(RequiredCase.JOB)
def test_notebook(runner: CliRunner):
    CONFIG.spot = True
    response = execute.run_job("_nimbo_notebook", dry_run=False)

    assert response["message"] == "_nimbo_notebook_success"
    instance_id = response["instance_id"]

    result = runner.invoke(
        cli, f"delete-instance {instance_id}", catch_exceptions=False
    )
    assert result.exit_code == 0
