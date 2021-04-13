import os
from os.path import join
import sys
from shutil import copy
import pytest
from click.testing import CliRunner

from nimbo.main import *
from nimbo.tests.utils import copy_assets, write_fake_file, set_yaml_value


def test_test_access():
    runner = CliRunner()

    with runner.isolated_filesystem():
        copy_assets(["config", "key"])

        result = runner.invoke(cli, "test-access", catch_exceptions=False)
        assert result.exit_code == 0


def test_run_no_code():
    runner = CliRunner()
    with runner.isolated_filesystem():
        copy_assets(["config", "key", "env"])

        result = runner.invoke(cli, "delete-all-instances", input="y", catch_exceptions=False)
        assert result.exit_code == 0
        result = runner.invoke(cli, "run 'python --version'", catch_exceptions=False)
        assert result.exit_code == 0
        result = runner.invoke(cli, "delete-all-instances", input="y", catch_exceptions=False)
        assert result.exit_code == 0


def test_launch():
    runner = CliRunner()
    with runner.isolated_filesystem():
        copy_assets(["config", "key", "env"])

        session, config = get_session_and_config_full_check()
        response = execute.run_job(session, config, "_nimbo_launch", dry_run=False)

        assert response["message"] == "_nimbo_launch_success"
        instance_id = response["instance_id"]

        result = runner.invoke(cli, f"delete-instance {instance_id}", catch_exceptions=False)
        assert result.exit_code == 0

        set_yaml_value("nimbo-config.yml", "region_name", "us-east-2")
        set_yaml_value("nimbo-config.yml", "instance_key", "us-east-2-instance-key")
        session, config = get_session_and_config_full_check()
        response = execute.run_job(session, config, "_nimbo_launch", dry_run=False)

        assert response["message"] == "_nimbo_launch_success"
        instance_id = response["instance_id"]

        result = runner.invoke(cli, f"delete-instance {instance_id}", catch_exceptions=False)
        assert result.exit_code == 0


def test_spot_launch():
    runner = CliRunner()
    with runner.isolated_filesystem():
        copy_assets(["config", "key", "env"])

        session, config = get_session_and_config_full_check()
        config["spot"] = True
        response = execute.run_job(session, config, "_nimbo_launch", dry_run=False)

        assert response["message"] == "_nimbo_launch_success"
        instance_id = response["instance_id"]

        result = runner.invoke(cli, f"delete-instance {instance_id}", catch_exceptions=False)
        assert result.exit_code == 0
