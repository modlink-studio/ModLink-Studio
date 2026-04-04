from __future__ import annotations

import traceback

from PyQt6.QtWidgets import QMessageBox

from modlink_core import ModLinkEngine
from modlink_core.drivers import discover_driver_factories
from modlink_core.settings.service import SettingsService
from modlink_qt_bridge import QtModLinkBridge
from modlink_new_ui import create_application, load_window


def _show_shutdown_error(message: str) -> None:
    QMessageBox.critical(
        None,
        "ModLink Studio",
        message,
    )


def _shutdown_bridge(bridge: QtModLinkBridge) -> None:
    try:
        bridge.shutdown()
    except Exception as exc:
        traceback.print_exc()
        _show_shutdown_error(f"关闭应用时有后台资源未正常停止：{exc}")


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
    app.aboutToQuit.connect(lambda: _shutdown_bridge(bridge))
    qml_engine, controller = load_window(bridge, parent=app)
    qml_engine.setObjectName("modlink-qml-engine")
    controller.setObjectName("modlink-qml-controller")
    raise SystemExit(app.exec())
