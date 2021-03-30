import os
import traceback
from click.testing import CliRunner
import pytest

from nimbo.main import cli
from nimbo.core.config_utils import generate_config


def write_fake_key():
    with open('my-ec2-key-pair.pem', 'w') as f:
        f.write('Mock key')


def test_generate_config():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["generate-config"], catch_exceptions=False)
        assert result.exit_code == 0, result.exception


def test_ssh():
    runner = CliRunner()
    with runner.isolated_filesystem():
        generate_config(quiet=True)

        # Test without a key
        with pytest.raises(FileNotFoundError):
            result = runner.invoke(cli, "ssh i-0be1989edd819b442 --dry-run", catch_exceptions=False)

        # Test with a key
        write_fake_key()
        result = runner.invoke(cli, "ssh i-0be1989edd819b442 --dry-run", catch_exceptions=False)
        assert result.exit_code == 0


def test_list_prices():
    runner = CliRunner()
    with runner.isolated_filesystem():
        generate_config(quiet=True)

        result = runner.invoke(cli, "list-gpu-prices --dry-run", catch_exceptions=False)
        assert result.exit_code == 0

        result = runner.invoke(cli, "list-spot-gpu-prices --dry-run", catch_exceptions=False)
        assert result.exit_code == 0


def test_list_instances():
    runner = CliRunner()
    with runner.isolated_filesystem():
        generate_config(quiet=True)

        result = runner.invoke(cli, "list-active --dry-run", catch_exceptions=False)
        assert result.exit_code == 0

        result = runner.invoke(cli, "list-stopped --dry-run", catch_exceptions=False)
        assert result.exit_code == 0


def test_instance_actions():
    runner = CliRunner()
    with runner.isolated_filesystem():
        generate_config(quiet=True)

        result = runner.invoke(cli, "check-instance-status i-0be1989edd819b442 --dry-run", catch_exceptions=False)
        assert result.exit_code == 0

        result = runner.invoke(cli, "stop-instance i-0be1989edd819b442 --dry-run", catch_exceptions=False)
        assert result.exit_code == 0

        result = runner.invoke(cli, "delete-instance i-0be1989edd819b442 --dry-run", catch_exceptions=False)
        assert result.exit_code == 0

        result = runner.invoke(cli, "delete-all-instances --dry-run", catch_exceptions=False)
        assert result.exit_code == 0