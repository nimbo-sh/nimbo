import os
from os.path import join
import sys
from shutil import copy
import pytest
from click.testing import CliRunner

from nimbo.main import cli
from nimbo.tests.utils import copy_assets


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

        result = runner.invoke(cli, "delete-all-instances", catch_exceptions=False)
        assert result.exit_code == 0
        result = runner.invoke(cli, "run 'python --version'", catch_exceptions=False)
        assert result.exit_code == 0
        result = runner.invoke(cli, "delete-all-instances", catch_exceptions=False)
        assert result.exit_code == 0