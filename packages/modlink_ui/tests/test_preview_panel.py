from __future__ import annotations

import os
import shutil
import sys
import unittest
from pathlib import Path
from uuid import uuid4

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PACKAGE_ROOT.parents[1]
for path in (
    PACKAGE_ROOT,
    WORKSPACE_ROOT / "packages" / "modlink_sdk",
    WORKSPACE_ROOT / "packages" / "modlink_core",
    WORKSPACE_ROOT / "packages" / "modlink_qt_bridge",
):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication

from modlink_core.settings.service import SettingsService
from modlink_qt_bridge import QtSettingsBridge
from modlink_sdk import FrameEnvelope, StreamDescriptor
from modlink_ui.widgets.main.preview import StreamPreviewPanel


class _BusStub(QObject):
    sig_frame = pyqtSignal(object)

    def __init__(self) -> None:
        super().__init__()
        self._descriptors: dict[str, StreamDescriptor] = {}

    def add_descriptor(self, descriptor: StreamDescriptor) -> None:
        self._descriptors[descriptor.stream_id] = descriptor

    def add_descriptors(self, descriptors: tuple[StreamDescriptor, ...]) -> None:
        for descriptor in descriptors:
            self.add_descriptor(descriptor)

    def descriptor(self, stream_id: str) -> StreamDescriptor | None:
        return self._descriptors.get(stream_id)

    def descriptors(self) -> dict[str, StreamDescriptor]:
        return dict(self._descriptors)


class _EngineStub:
    def __init__(self, bus: _BusStub, settings: QtSettingsBridge) -> None:
        self.bus = bus
        self.settings = settings


class StreamPreviewPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        test_tmp_root = WORKSPACE_ROOT / ".tmp-tests"
        test_tmp_root.mkdir(exist_ok=True)
        self._temp_dir = test_tmp_root / f"preview-panel-{uuid4().hex}"
        self._temp_dir.mkdir()
        self._settings = SettingsService(self._temp_dir / "preview-panel-settings.json")
        self._settings_bridge = QtSettingsBridge(self._settings)

    def tearDown(self) -> None:
        shutil.rmtree(self._temp_dir, ignore_errors=True)

    @staticmethod
    def _descriptor(modality: str, payload_type: str) -> StreamDescriptor:
        return StreamDescriptor(
            device_id="test.01",
            modality=modality,
            payload_type=payload_type,
            nominal_sample_rate_hz=30.0,
            chunk_size=1,
            channel_names=("c1",),
            display_name=f"{modality} preview",
        )

    def test_initial_snapshot_creates_cards_for_existing_descriptors(self) -> None:
        bus = _BusStub()
        descriptors = (
            self._descriptor("video", "video"),
            self._descriptor("field", "field"),
        )
        bus.add_descriptors(descriptors)

        panel = StreamPreviewPanel(_EngineStub(bus, self._settings_bridge))

        self.assertEqual(set(panel._cards), {item.stream_id for item in descriptors})
        panel.close()

    def test_all_detached_cards_hide_embedded_container(self) -> None:
        bus = _BusStub()
        descriptor = self._descriptor("video", "video")
        bus.add_descriptor(descriptor)

        panel = StreamPreviewPanel(_EngineStub(bus, self._settings_bridge))
        panel.show()
        self._app.processEvents()
        self.assertTrue(panel.cards_container.isVisible())

        card = panel._cards[descriptor.stream_id]
        card.detach_content()
        self._app.processEvents()
        self.assertFalse(panel.cards_container.isVisible())

        card.attach_content()
        self._app.processEvents()
        self.assertTrue(panel.cards_container.isVisible())
        panel.close()

    def test_late_stream_frame_raises_snapshot_violation(self) -> None:
        bus = _BusStub()
        initial_descriptor = self._descriptor("video", "video")
        bus.add_descriptor(initial_descriptor)
        panel = StreamPreviewPanel(_EngineStub(bus, self._settings_bridge))

        late_descriptor = self._descriptor("aux_video", "video")
        bus.add_descriptor(late_descriptor)
        frame = FrameEnvelope(
            device_id=late_descriptor.device_id,
            modality=late_descriptor.modality,
            timestamp_ns=123,
            data=np.zeros((1, 1, 1, 1), dtype=np.uint8),
        )

        with self.assertRaisesRegex(RuntimeError, "PREVIEW_STREAM_SNAPSHOT_VIOLATION"):
            panel._on_frame(frame)
        panel.close()


if __name__ == "__main__":
    unittest.main()
