import sys
from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication
from qfluentwidgets import Theme, setTheme

from .backend import create_backend
from .ui import MainWindow
from .ui.settings import AppSettingsStore


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
    settings_store = AppSettingsStore()
    backend = create_backend()
    window = MainWindow(backend=backend, settings_store=settings_store)
    window.show()
    sys.exit(app.exec())
