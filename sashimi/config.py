from pathlib import Path
import os
import click
import toml
from lightparam.core import set_nested, get_nested

CONFIG_FILENAME = "hardware_config.toml"

_PACKAGE_CONFIG_DIR = Path(__file__).parent / "config"

_config_path = None

TEMPLATE_CONF_DICT = {
    "scanning": "mock",
    "scopeless": True,
    "sample_rate": 40000,
    "voxel_size": {
        "x": 0.3,
        "y": 0.3,
    },
    "default_paths": {
        "data": str(Path.home()),
        "presets": str(Path.home() / "presets"),
        "log": str(Path.home() / "logs"),
        "scope_instructions": "",
    },
    "z_board": {
        "read": {
            "channel": "Dev1/ai0:0",
            "min_val": 0,
            "max_val": 10,
        },
        "write": {
            "channel": "Dev1/ao0:3",
            "min_val": -10,
            "max_val": 10,
        },
        "sync": {"channel": "/Dev1/ao/StartTrigger"},
    },
    "piezo": {
        "scale": 1 / 40,
        "z_min":0,
        "z_max":250,
        "z_default":125
    },
    "email": {"user": "foo", "password": "foo"},
    "xy_board": {
        "write": {
            "channel": "Dev2/ao0:1",
            "min_val": -10,
            "max_val": 10,
            "display_range_min": -3,
            "display_range_max": 3,
            "lateral_min": -1,
            "lateral_max": 1,
            "lateral_freq": 500,
            "frontal_min": -1,
            "frontal_max": 1,
            "frontal_freq": 500,
        }
    },
    "camera": {
        "id": 0,
        "name": "mock",
        "max_sensor_resolution": [2048, 2048],
        "default_exposure": 60,
        "default_binning": 1,
    },
    "light_source": {"name": "mock", "port": "COM4", "intensity_units": "mock"},
    "shutter": {"name": "mock", "port": "PXI6259/port0/line0"},
    "filterwheel": {
        "name": "mock",
        "port": "COM9",
        "default_filter": "Filter Position 1",
        "filter_options": [
            "Filter Position 1",
            "Filter Position 2",
            "Filter Position 3",
        ],
    },
    "external_communication": {"name": "stytra", "address": "tcp://127.0.0.1:5555"},
    "notifier": "none",
    "notifier_options": {},
    "array_ram_MB": 450,
}


def set_config_path(path):
    global _config_path
    _config_path = Path(path)
    os.environ["SASHIMI_CONFIG_PATH"] = str(_config_path)


def _resolve_config_path():
    global _config_path
    if _config_path is not None:
        return _config_path

    env_path = os.environ.get("SASHIMI_CONFIG_PATH")
    if env_path:
        _config_path = Path(env_path)
        return _config_path

    default_path = _PACKAGE_CONFIG_DIR / "default.toml"
    if default_path.exists():
        _config_path = default_path
    else:
        toml_files = sorted(_PACKAGE_CONFIG_DIR.glob("*.toml"))
        if len(toml_files) == 1:
            _config_path = toml_files[0]
        elif len(toml_files) > 1:
            _config_path = _prompt_config_selection(toml_files)
        else:
            _PACKAGE_CONFIG_DIR.mkdir(exist_ok=True)
            _config_path = default_path
            write_default_config(_config_path)

    os.environ["SASHIMI_CONFIG_PATH"] = str(_config_path)
    return _config_path


def _prompt_config_selection(toml_files):
    click.echo("Multiple configuration files found:")
    for i, f in enumerate(toml_files, 1):
        click.echo(f"  {i}. {f.name}")
    choice = click.prompt(
        "Select configuration",
        type=click.IntRange(1, len(toml_files)),
        default=1,
    )
    return toml_files[choice - 1]


def write_default_config(file_path=None, template=None):
    if file_path is None:
        file_path = _resolve_config_path()
    if template is None:
        template = TEMPLATE_CONF_DICT
    with open(file_path, "w") as f:
        toml.dump(template, f)


def read_config(file_path=None):
    if file_path is None:
        file_path = _resolve_config_path()
    if not file_path.exists():
        write_default_config(file_path)
    return toml.load(file_path)


def write_config_value(dict_path, val, file_path=None):
    if file_path is None:
        file_path = _resolve_config_path()

    if type(dict_path) is str:
        dict_path = [dict_path]

    conf = toml.load(file_path)
    set_nested(conf, dict_path, val)

    with open(file_path, "w") as f:
        toml.dump(conf, f)


@click.command()
@click.argument("command")
@click.option("-n", "--name", help="Path (section/name) of parameter to be changed")
@click.option("-v", "--val", help="Value of parameter to be changed")
@click.option(
    "-p",
    "--file_path",
    default=None,
    help="Path to the config file (optional)",
)
def cli_modify_config(command, name=None, val=None, file_path=None):
    if file_path is not None:
        set_config_path(Path(file_path))

    resolved_path = _resolve_config_path()

    if command == "edit":
        cli_edit_config(name, val, resolved_path)
    elif command == "show":
        click.echo(_print_config(file_path=resolved_path))


def cli_edit_config(name=None, val=None, file_path=None):
    if file_path is None:
        file_path = _resolve_config_path()

    conf = read_config(file_path=file_path)

    dict_path = name.split(".")
    old_val = get_nested(conf, dict_path)
    val = type(old_val)(val)

    write_config_value(dict_path, val, file_path)


def _print_config(file_path=None):
    if file_path is None:
        file_path = _resolve_config_path()
    config = read_config(file_path=file_path)
    return toml.dumps(config)
