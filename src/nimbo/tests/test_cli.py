import os
from os.path import join

import pytest
from botocore.exceptions import ClientError
from click.testing import CliRunner

from nimbo import CONFIG
from nimbo.main import cli
from nimbo.core.config import RequiredCase
from nimbo.tests.utils import isolated_filesystem, make_file


@pytest.fixture
def runner():
    return ""


@isolated_filesystem(RequiredCase.NONE)
def test_generate_config(runner: CliRunner):
    result = runner.invoke(cli, "generate-config", catch_exceptions=False)
    assert result.exit_code == 0, result.exception


@isolated_filesystem(RequiredCase.MINIMAL)
def test_ssh_fails_with_minimal(runner: CliRunner):
    result = runner.invoke(
        cli, "ssh i-0be1989edd819b442 --dry-run", catch_exceptions=False
    )
    assert result.exit_code == 1


@isolated_filesystem(RequiredCase.INSTANCE)
def test_ssh_passes_with_instance(runner: CliRunner):
    result = runner.invoke(
        cli, "ssh i-0be1989edd819b442 --dry-run", catch_exceptions=False
    )
    assert result.exit_code == 0


@isolated_filesystem(RequiredCase.MINIMAL)
def test_list_prices(runner: CliRunner):
    result = runner.invoke(cli, "list-gpu-prices", catch_exceptions=False)
    assert result.exit_code == 0
    result = runner.invoke(cli, "list-spot-gpu-prices", catch_exceptions=False)
    assert result.exit_code == 0

    # Check if it works for us-east-2 region
    CONFIG.region_name = "us-east-2"

    result = runner.invoke(cli, "list-gpu-prices", catch_exceptions=False)
    assert result.exit_code == 0
    result = runner.invoke(cli, "list-spot-gpu-prices", catch_exceptions=False)
    assert result.exit_code == 0


@isolated_filesystem(RequiredCase.MINIMAL)
def test_list_instances(runner: CliRunner):
    result = runner.invoke(cli, "list-active --dry-run", catch_exceptions=False)
    assert result.exit_code == 0

    result = runner.invoke(cli, "list-stopped --dry-run", catch_exceptions=False)
    assert result.exit_code == 0


@isolated_filesystem(RequiredCase.MINIMAL)
def test_instance_actions(runner: CliRunner):
    try:
        runner.invoke(
            cli,
            "check-instance-status i-0be1989edd819b442 --dry-run",
            catch_exceptions=False,
        )
    except ClientError as e:
        if "InvalidInstanceID.NotFound" not in str(e):
            raise

    try:
        runner.invoke(
            cli,
            "stop-instance i-0be1989edd819b442 --dry-run",
            catch_exceptions=False,
        )
    except ClientError as e:
        if "InvalidInstanceID.NotFound" not in str(e):
            raise

    try:
        runner.invoke(
            cli,
            "delete-instance i-0be1989edd819b442 --dry-run",
            catch_exceptions=False,
        )
    except ClientError as e:
        if "InvalidInstanceID.NotFound" not in str(e):
            raise

    result = runner.invoke(
        cli, "delete-all-instances --dry-run", input="y", catch_exceptions=False
    )
    assert result.exit_code == 0


@isolated_filesystem(RequiredCase.JOB)
def test_run_job(runner: CliRunner):
    result = runner.invoke(
        cli, "run 'python --version' --dry-run", catch_exceptions=False
    )
    assert result.exit_code == 0

    result = runner.invoke(cli, "launch --dry-run", catch_exceptions=False)
    assert result.exit_code == 0

    result = runner.invoke(cli, "launch-and-setup --dry-run", catch_exceptions=False)
    assert result.exit_code == 0

    result = runner.invoke(cli, "test-access --dry-run", catch_exceptions=False)
    assert result.exit_code == 0


@isolated_filesystem(RequiredCase.STORAGE)
def test_push_pull(runner: CliRunner):
    os.mkdir(CONFIG.local_datasets_path)
    os.mkdir(CONFIG.local_results_path)
    result = runner.invoke(
        cli, "push datasets --delete", input="y", catch_exceptions=False
    )
    assert result.exit_code == 0
    result = runner.invoke(
        cli, "push results --delete", input="y", catch_exceptions=False
    )
    assert result.exit_code == 0

    # Run the code below for both datasets and results folders
    for mode in ["datasets", "results"]:
        if mode == "datasets":
            folder = CONFIG.local_datasets_path
        else:
            folder = CONFIG.local_results_path

        file_name = join(folder, "mnist.txt")

        # Add a dataset to local and push it to S3
        make_file(file_name, "Mock data")
        result = runner.invoke(cli, f"push {mode}", catch_exceptions=False)
        assert result.exit_code == 0

        # Delete that datasets locally and import it from S3
        os.remove(file_name)
        result = runner.invoke(cli, f"pull {mode}", catch_exceptions=False)
        assert result.exit_code == 0
        assert os.listdir(folder) == ["mnist.txt"]

        # Delete that dataset locally and push --delete to S3
        os.remove(file_name)
        result = runner.invoke(
            cli, f"push {mode} --delete", input="y", catch_exceptions=False
        )
        assert result.exit_code == 0

        # Pull from S3 and check that the dataset is still deleted
        result = runner.invoke(cli, f"pull {mode}", catch_exceptions=False)
        assert result.exit_code == 0
        assert os.listdir(folder) == []

    logs_folder = join(CONFIG.local_results_path, "nimbo-logs")
    os.mkdir(logs_folder)
    file_name = join(logs_folder, "log.txt")
    make_file(file_name, "Mock log")
    assert os.listdir(logs_folder) == ["log.txt"]

    result = runner.invoke(cli, "push logs", catch_exceptions=False)
    assert result.exit_code == 0

    os.remove(file_name)
    assert os.listdir(logs_folder) == []

    result = runner.invoke(cli, "pull logs", catch_exceptions=False)
    assert result.exit_code == 0
    assert os.listdir(logs_folder) == ["log.txt"]

    os.remove(file_name)
    result = runner.invoke(cli, "push logs --delete", input="y", catch_exceptions=False)
    assert result.exit_code == 0
    os.rmdir(logs_folder)
    result = runner.invoke(
        cli, "push results --delete", input="y", catch_exceptions=False
    )
    assert result.exit_code == 0