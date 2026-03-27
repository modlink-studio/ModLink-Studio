from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PACKAGE_ROOT.parents[1]
for path in (
    PACKAGE_ROOT,
    WORKSPACE_ROOT / "packages" / "modlink_sdk",
    WORKSPACE_ROOT / "packages" / "modlink_core",
):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from PyQt6.QtWidgets import QApplication

from modlink_core.bus.stream_bus import StreamBus
from modlink_core.settings.service import SettingsService
from modlink_sdk import FrameEnvelope, StreamDescriptor
from modlink_ui.widgets.main.preview import StreamPreviewPanel


class _EngineStub:
    def __init__(self, bus: StreamBus) -> None:
        self.bus = bus


class StreamPreviewPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        SettingsService._instance = None
        self._settings = SettingsService(
            Path(self._temp_dir.name) / "preview-panel-settings.json"
        )

    def tearDown(self) -> None:
        SettingsService._instance = None
        self._temp_dir.cleanup()

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
        bus = StreamBus()
        descriptors = (
            self._descriptor("video", "video"),
            self._descriptor("field", "field"),
        )
        bus.add_descriptors(descriptors)

        panel = StreamPreviewPanel(_EngineStub(bus))

        self.assertEqual(set(panel._cards), {item.stream_id for item in descriptors})
        panel.close()

    def test_all_detached_cards_hide_embedded_container(self) -> None:
        bus = StreamBus()
        descriptor = self._descriptor("video", "video")
        bus.add_descriptor(descriptor)

        panel = StreamPreviewPanel(_EngineStub(bus))
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
        bus = StreamBus()
        initial_descriptor = self._descriptor("video", "video")
        bus.add_descriptor(initial_descriptor)
        panel = StreamPreviewPanel(_EngineStub(bus))

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
