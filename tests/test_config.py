import pytest
import tempfile
from pathlib import Path
import shutil
from sashimi import config
from click.testing import CliRunner


@pytest.fixture
def conf_path():
    temp_dir = Path(tempfile.mkdtemp())
    conf_path = temp_dir / "test_config.toml"
    config.write_default_config(conf_path)

    yield conf_path

    shutil.rmtree(temp_dir)


def test_config_creation(conf_path):
    conf = config.read_config(file_path=conf_path)
    assert conf == config.TEMPLATE_CONF_DICT


def test_write_config_val(conf_path):
    val = 6
    config.write_config_value(["z_board", "read", "min_val"], val, file_path=conf_path)
    conf = config.read_config(file_path=conf_path)
    assert conf["z_board"]["read"]["min_val"] == val


def test_config_cli_show(conf_path):
    runner = CliRunner()
    result = runner.invoke(config.cli_modify_config, ["show", "-p", str(conf_path)])
    assert result.exit_code == 0
    assert result.output == config._print_config(file_path=conf_path) + "\n"


def test_config_cli_edit(conf_path):
    runner = CliRunner()
    runner.invoke(
        config.cli_modify_config,
        ["edit", "-n", "z_board.read.min_val", "-v", "7", "-p", str(conf_path)],
    )
    conf = config.read_config(conf_path)
    assert conf["z_board"]["read"]["min_val"] == 7


def test_resolve_single_config():
    config._config_path = None
    resolved = config._resolve_config_path()
    assert resolved.exists()
    assert resolved.suffix == ".toml"
    config._config_path = None


def test_set_config_path(conf_path):
    config._config_path = None
    config.set_config_path(conf_path)
    assert config._resolve_config_path() == conf_path
    config._config_path = None
