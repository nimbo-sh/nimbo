import enum
import functools
import os
import shutil

from click.testing import CliRunner

from nimbo import CONFIG
from nimbo.core.config import RequiredCase
from nimbo.tests.config import ASSETS_PATH, CONDA_ENV, NIMBO_CONFIG_FILE


def make_file(path: str, text: str) -> None:
    with open(path, "w") as f:
        f.write(text)


class AssetType(enum.Enum):
    NIMBO_CONFIG = 0
    INSTANCE_KEYS = 1
    CONDA_ENV = 2


def isolated_filesystem(*cases: RequiredCase):
    """
    Decorator for creating an isolated filesystem,
    copying required files and injecting required config based on RequiredCases

    Requires dummy fixture
    @pytest.fixture
    def runner():
        return ""

    to be specified in each file where this decorator is used.

    @isolated_filesystem passes the click CliRunner as an argument to the function
    that it wraps. Pytest expects all parameters to test functions be fixtures.
    This dummy fixture fools pytest, but in runtime, CliRunner is injected by
    @isolated_filesystem.
    """

    def decorator(func):
        @functools.wraps(func)
        def decorated(*args, **kwargs):
            runner = CliRunner()
            with runner.isolated_filesystem():
                _setup_for_case(*cases)
                return func(runner)

        return decorated

    return decorator


def _setup_for_case(*cases: RequiredCase) -> None:
    """
    Used within CliRunner().isolated_filesystem() for copying what is needed
    from the test assets folder to the filesystem and for injecting the
    testing configuration needed for this particular case
    """

    cases = RequiredCase.decompose(*cases)

    if RequiredCase.MINIMAL in cases:
        _copy_assets(AssetType.NIMBO_CONFIG)
    if RequiredCase.INSTANCE in cases:
        _copy_assets(AssetType.INSTANCE_KEYS)
    if RequiredCase.JOB in cases:
        _copy_assets(AssetType.CONDA_ENV)

    CONFIG.reset_required_config()
    CONFIG.inject_required_config(*cases)


def _copy_assets(*assets: AssetType) -> None:
    dst = os.getcwd()

    if AssetType.NIMBO_CONFIG in assets:
        src = os.path.join(ASSETS_PATH, NIMBO_CONFIG_FILE)
        shutil.copy(src, dst)
    if AssetType.INSTANCE_KEYS in assets:
        keys = [file for file in os.listdir(ASSETS_PATH) if file[-4:] == ".pem"]
        for key in keys:
            shutil.copy(os.path.join(ASSETS_PATH, key), dst)
    if AssetType.CONDA_ENV in assets:
        shutil.copy(os.path.join(ASSETS_PATH, CONDA_ENV), dst)
