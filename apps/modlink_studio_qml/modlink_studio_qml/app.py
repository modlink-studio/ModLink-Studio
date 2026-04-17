from __future__ import annotations

import logging
import traceback

from PyQt6.QtWidgets import QMessageBox

from modlink_core import ModLinkEngine, configure_host_logging
from modlink_qt_bridge import QtModLinkBridge
from modlink_ui_qt_qml import create_application, load_window

logger = logging.getLogger(__name__)


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
    log_path = configure_host_logging(log_filename="modlink-studio-qml.log")
    logger.info("Starting ModLink Studio QML")
    logger.info("Desktop logs will be written to %s", log_path)
    app = create_application()
    runtime = ModLinkEngine(
        parent=app,
    )
    bridge = QtModLinkBridge(runtime, parent=app)
    app.aboutToQuit.connect(lambda: _shutdown_bridge(bridge))
    qml_engine, controller = load_window(bridge, parent=app)
    qml_engine.setObjectName("modlink-qml-engine")
    controller.setObjectName("modlink-qml-controller")
    raise SystemExit(app.exec())
