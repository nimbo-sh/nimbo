import os
from os.path import join
from shutil import copy
import pytest
from click.testing import CliRunner
from botocore.exceptions import ClientError

from nimbo.main import cli
from nimbo.core.config_utils import generate_config, load_config
from nimbo.tests.utils import copy_assets


def write_fake_file(path, text):
    with open(path, 'w') as f:
        f.write(text)


def test_generate_config():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["generate-config"], catch_exceptions=False)
        assert result.exit_code == 0, result.exception


def test_ssh():
    runner = CliRunner()
    with runner.isolated_filesystem():
        copy_assets(["config"])

        # Test without a key
        with pytest.raises(FileNotFoundError):
            result = runner.invoke(cli, "ssh i-0be1989edd819b442 --dry-run", catch_exceptions=False)

        # Test with a key
        copy_assets(["key"])
        result = runner.invoke(cli, "ssh i-0be1989edd819b442 --dry-run", catch_exceptions=False)
        assert result.exit_code == 0


def test_list_prices():
    runner = CliRunner()
    with runner.isolated_filesystem():
        copy_assets(["config"])

        result = runner.invoke(cli, "list-gpu-prices --dry-run", catch_exceptions=False)
        assert result.exit_code == 0

        result = runner.invoke(cli, "list-spot-gpu-prices --dry-run", catch_exceptions=False)
        assert result.exit_code == 0


def test_list_instances():
    runner = CliRunner()
    with runner.isolated_filesystem():
        copy_assets(["config"])

        result = runner.invoke(cli, "list-active --dry-run", catch_exceptions=False)
        assert result.exit_code == 0

        result = runner.invoke(cli, "list-stopped --dry-run", catch_exceptions=False)
        assert result.exit_code == 0


def test_instance_actions():
    runner = CliRunner()
    with runner.isolated_filesystem():
        copy_assets(["config"])

        try:
            result = runner.invoke(cli, "check-instance-status i-0be1989edd819b442 --dry-run", catch_exceptions=False)
        except ClientError as e:
            if 'InvalidInstanceID.NotFound' not in str(e):
                raise

        try:
            result = runner.invoke(cli, "stop-instance i-0be1989edd819b442 --dry-run", catch_exceptions=False)
        except ClientError as e:
            if 'InvalidInstanceID.NotFound' not in str(e):
                raise

        try:
            result = runner.invoke(cli, "delete-instance i-0be1989edd819b442 --dry-run", catch_exceptions=False)
        except ClientError as e:
            if 'InvalidInstanceID.NotFound' not in str(e):
                raise

        result = runner.invoke(cli, "delete-all-instances --dry-run", input="y", catch_exceptions=False)
        assert result.exit_code == 0


def test_run_job():
    runner = CliRunner()
    with runner.isolated_filesystem():
        copy_assets(["config", "env", "key"])

        result = runner.invoke(cli, "run 'python --version' --dry-run", catch_exceptions=False)
        assert result.exit_code == 0

        result = runner.invoke(cli, "launch --dry-run", catch_exceptions=False)
        assert result.exit_code == 0

        result = runner.invoke(cli, "launch-and-setup --dry-run", catch_exceptions=False)
        assert result.exit_code == 0

        result = runner.invoke(cli, "test-access --dry-run", catch_exceptions=False)
        assert result.exit_code == 0


def test_push_pull():
    runner = CliRunner()
    with runner.isolated_filesystem():
        copy_assets(["config"])

        config = load_config()

        # Run the code below for both datasets and results folders
        for mode in ["datasets", "results"]:
            folder = config[f"local_{mode}_path"]
            os.mkdir(folder)
            file_name = f"{folder}/mnist.txt"
    
            # Add a dataset to local and push it to S3        
            write_fake_file(file_name, "Fake dataset")
            result = runner.invoke(cli, f"push {mode}", catch_exceptions=False)
            assert result.exit_code == 0

            # Delete that datasets locally and import it from S3
            os.remove(file_name)
            result = runner.invoke(cli, f"pull {mode}", catch_exceptions=False)
            assert result.exit_code == 0
            assert os.listdir(folder) == ["mnist.txt"]

            # Delete that dataset locally and push --delete to S3
            os.remove(file_name)
            result = runner.invoke(cli, f"push {mode} --delete", catch_exceptions=False)
            assert result.exit_code == 0

            # Pull from S3 and check that the dataset is still deleted
            result = runner.invoke(cli, f"pull {mode}", catch_exceptions=False)
            assert result.exit_code == 0
            assert os.listdir(folder) == []