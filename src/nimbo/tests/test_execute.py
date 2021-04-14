import os

from click.testing import CliRunner

from nimbo.main import *
from nimbo.tests.utils import copy_assets, set_yaml_value


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


def test_launch():
    runner = CliRunner()
    with runner.isolated_filesystem():
        copy_assets(["config", "key", "env"])

        dst = os.getcwd()
        instance_keys = [p[:-4] for p in os.listdir(dst) if p[-4:] == ".pem"]

        for instance_key in instance_keys:
            region_name = instance_key[:9]
            set_yaml_value("nimbo-config.yml", "region_name", region_name)
            set_yaml_value("nimbo-config.yml", "instance_key", instance_key)
            session, config = get_session_and_config_full_check()
            response = execute.run_job(session, config, "_nimbo_launch", dry_run=False)

            assert response["message"] == "_nimbo_launch_success"
            instance_id = response["instance_id"]

            result = runner.invoke(
                cli, f"delete-instance {instance_id}", catch_exceptions=False
            )
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

        result = runner.invoke(
            cli, f"delete-instance {instance_id}", catch_exceptions=False
        )
        assert result.exit_code == 0
