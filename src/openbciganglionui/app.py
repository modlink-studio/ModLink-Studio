import sys

from PyQt6.QtWidgets import QApplication
from qfluentwidgets import Theme, setTheme

from .backend import MockGanglionBackend
from .ui import MainWindow


def create_application() -> QApplication:
    app = QApplication(sys.argv)
    app.setApplicationName("OpenBCI Ganglion UI")
    app.setOrganizationName("OpenBCI")
    setTheme(Theme.AUTO)
    return app


def main() -> None:
    app = create_application()
    backend = MockGanglionBackend()
    window = MainWindow(backend=backend)
    window.show()
    sys.exit(app.exec())
