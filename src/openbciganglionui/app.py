import contextlib
import io
import sys
from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from .backend import create_backend
from .ui.settings import AppSettingsStore


@contextlib.contextmanager
def _suppress_qfluentwidgets_promo() -> None:
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        yield


def _load_app_icon() -> QIcon:
    icon_path = Path(__file__).resolve().parent / "assets" / "app_icon.png"
    return QIcon(str(icon_path))


def create_application() -> QApplication:
    with _suppress_qfluentwidgets_promo():
        from qfluentwidgets import Theme, setTheme

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
    with _suppress_qfluentwidgets_promo():
        from .ui import MainWindow

    window = MainWindow(backend=backend, settings_store=settings_store)
    window.show()
    sys.exit(app.exec())
