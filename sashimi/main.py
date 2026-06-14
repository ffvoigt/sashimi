import click
from pathlib import Path


@click.command()
@click.option("--scopeless", is_flag=True, help="Scopeless mode for simulated hardware")
@click.option("--scanning", default="mock", help="The scanning interface")
@click.option(
    "--config",
    "config_path",
    default=None,
    type=click.Path(exists=True),
    help="Path to a specific config TOML file",
)
def main(scopeless, scanning, config_path):
    from sashimi.config import set_config_path, write_config_value

    if config_path:
        set_config_path(config_path)

    write_config_value("scopeless", scopeless)
    write_config_value("scanning", scanning)

    from PyQt5.QtWidgets import QApplication
    import qdarkstyle
    from sashimi.gui.main_gui import MainWindow
    from PyQt5.QtGui import QIcon
    from sashimi.state import State

    app = QApplication([])
    style = qdarkstyle.load_stylesheet_pyqt5()
    app.setStyleSheet(style)
    app.setApplicationName("Sashimi")
    st = State()
    main_window = MainWindow(st, style)
    icon_dir = (Path(__file__).parents[0]).resolve() / "icons/main_icon.png"
    app.setWindowIcon(QIcon(str(icon_dir)))
    main_window.show()
    app.exec()
