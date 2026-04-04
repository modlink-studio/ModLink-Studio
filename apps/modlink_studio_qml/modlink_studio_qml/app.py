from __future__ import annotations

from modlink_core import ModLinkEngine
from modlink_core.drivers import discover_driver_factories
from modlink_core.settings.service import SettingsService
from modlink_new_ui import create_application, load_window
from modlink_qt_bridge import QtModLinkBridge


def main() -> None:
    app = create_application()
    settings = SettingsService(parent=app)
    driver_factories = discover_driver_factories()
    runtime = ModLinkEngine(
        driver_factories=driver_factories,
        settings=settings,
        parent=app,
    )
    bridge = QtModLinkBridge(runtime, parent=app)
    app.aboutToQuit.connect(bridge.shutdown)
    qml_engine, controller = load_window(bridge, parent=app)
    qml_engine.setObjectName("modlink-qml-engine")
    controller.setObjectName("modlink-qml-controller")
    raise SystemExit(app.exec())
