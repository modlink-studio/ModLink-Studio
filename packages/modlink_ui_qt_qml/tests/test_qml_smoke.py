from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest
from PyQt6.QtCore import QObject, QUrl
from PyQt6.QtQml import QQmlComponent, QQmlEngine
from PyQt6.QtWidgets import QApplication

from modlink_ui_qt_qml import create_application
from modlink_ui_qt_qml.preview.signal_controller import SignalStreamController
from modlink_sdk import Driver, StreamDescriptor

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Universal")
os.environ.setdefault("QT_QUICK_CONTROLS_FALLBACK_STYLE", "Fusion")


class PreviewDemoDriver(Driver):
    supported_providers = ("demo",)

    @property
    def device_id(self) -> str:
        return "qml_demo.01"

    def descriptors(self) -> list[StreamDescriptor]:
        return [
            StreamDescriptor(
                device_id=self.device_id,
                stream_key="demo",
                payload_type="signal",
                nominal_sample_rate_hz=10.0,
                chunk_size=4,
                channel_names=("ch1", "ch2"),
            )
        ]

    def search(self, provider: str) -> list[object]:
        _ = provider
        return []

    def connect_device(self, config: object) -> None:
        _ = config

    def disconnect_device(self) -> None:
        return

    def start_streaming(self) -> None:
        return

    def stop_streaming(self) -> None:
        return


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    return create_application([])


def _drain_qt(app: QApplication) -> None:
    app.processEvents()
    app.sendPostedEvents()
    app.processEvents()


def test_qml_window_loads(qapp: QApplication) -> None:
    _ = qapp
    script = """
from modlink_core import ModLinkEngine, SettingsService
from modlink_ui_qt_qml import create_application, load_window
from modlink_qt_bridge import QtModLinkBridge
from modlink_sdk import Driver, StreamDescriptor

class PreviewDemoDriver(Driver):
    supported_providers = ("demo",)

    @property
    def device_id(self) -> str:
        return "qml_demo.01"

    def descriptors(self) -> list[StreamDescriptor]:
        return [
            StreamDescriptor(
                device_id=self.device_id,
                stream_key="demo",
                payload_type="signal",
                nominal_sample_rate_hz=10.0,
                chunk_size=4,
                channel_names=("ch1", "ch2"),
            )
        ]

    def search(self, provider: str) -> list[object]:
        _ = provider
        return []

    def connect_device(self, config: object) -> None:
        _ = config

    def disconnect_device(self) -> None:
        return

    def start_streaming(self) -> None:
        return

    def stop_streaming(self) -> None:
        return

app = create_application([])
settings = SettingsService(parent=app)
runtime = ModLinkEngine(driver_factories=[PreviewDemoDriver], settings=settings, parent=app)
bridge = QtModLinkBridge(runtime, parent=app)
qml_engine, controller = load_window(bridge, parent=app)
app.processEvents()
assert qml_engine.rootObjects()
assert controller.mainPage is not None
assert controller.devicePage is not None
assert controller.settingsPage is not None
import sys
print("QML_WINDOW_LOADED")
sys.stdout.flush()
import os
os._exit(0)
"""
    env = os.environ.copy()
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    env.setdefault("QT_QUICK_CONTROLS_STYLE", "Universal")
    env.setdefault("QT_QUICK_CONTROLS_FALLBACK_STYLE", "Fusion")
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[3],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert "QML_WINDOW_LOADED" in completed.stdout


def test_preview_card_settings_dialog_opens(qapp: QApplication) -> None:
    qml_engine = QQmlEngine(qapp)
    descriptor = PreviewDemoDriver().descriptors()[0]
    controller = SignalStreamController(descriptor, parent=qapp)
    component = QQmlComponent(
        qml_engine,
        QUrl.fromLocalFile(
            str(
                Path(__file__).resolve().parents[1]
                / "modlink_ui_qt_qml"
                / "qml"
                / "preview"
                / "StreamPreviewCard.qml"
            )
        ),
    )

    assert component.status() == QQmlComponent.Status.Ready, component.errors()

    card = component.createWithInitialProperties(
        {
            "streamData": {
                "streamId": descriptor.stream_id,
                "objectName": "streamPreviewCard_qml_demo_01_demo",
                "displayName": descriptor.stream_id,
                "payloadType": descriptor.payload_type,
                "summaryText": "等待数据",
                "frameCount": 0,
                "channelSummary": "ch1, ch2",
                "sampleRateText": "10 Hz",
                "controller": controller,
            }
        }
    )
    _drain_qt(qapp)

    assert card is not None

    object_name = "streamPreviewCard_qml_demo_01_demo"
    dialog = card.findChild(QObject, object_name + "_settingsDialog")
    assert dialog is not None

    card.deleteLater()
    qml_engine.deleteLater()
    _drain_qt(qapp)


def test_page_header_component_instantiates(qapp: QApplication) -> None:
    qml_engine = QQmlEngine(qapp)
    component = QQmlComponent(
        qml_engine,
        QUrl.fromLocalFile(
            str(
                Path(__file__).resolve().parents[1]
                / "modlink_ui_qt_qml"
                / "qml"
                / "components"
                / "PageHeader.qml"
            )
        ),
    )

    assert component.status() == QQmlComponent.Status.Ready, component.errors()
    header = component.createWithInitialProperties(
        {
            "title": "实时展示",
            "subtitle": "统一查看所有可预览流。",
        }
    )
    _drain_qt(qapp)

    assert header is not None
    header.deleteLater()
    qml_engine.deleteLater()
    _drain_qt(qapp)


def test_gpu_items_importable() -> None:
    from modlink_ui_qt_qml.gpu import TextureItem, WaveformItem

    assert WaveformItem is not None
    assert TextureItem is not None


def test_preview_controllers_importable() -> None:
    from modlink_ui_qt_qml.preview.stream_controller_factory import (
        create_stream_controller,
    )

    assert create_stream_controller is not None
