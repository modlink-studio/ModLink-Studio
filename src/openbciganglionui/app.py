import sys
from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication
from qfluentwidgets import Theme, setTheme

from .backend import MockGanglionBackend
from .ui import MainWindow


def _load_app_icon() -> QIcon:
    icon_path = Path(__file__).resolve().parent / "assets" / "app_icon.png"
    return QIcon(str(icon_path))


def create_application() -> QApplication:
    app = QApplication(sys.argv)
    app.setApplicationName("OpenBCI Ganglion UI")
    app.setOrganizationName("OpenBCI")
    app.setWindowIcon(_load_app_icon())
    setTheme(Theme.AUTO)
    return app


def main() -> None:
    app = create_application()
    backend = MockGanglionBackend()
    window = MainWindow(backend=backend)
    window.show()
    sys.exit(app.exec())
