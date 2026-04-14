from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

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

from PyQt6.QtWidgets import QApplication

from modlink_core import SettingsService
from modlink_qt_bridge import QtSettingsBridge
from modlink_sdk import StreamDescriptor
from modlink_ui_qt_widgets.widgets.main.preview.settings.models import (
    FieldPreviewSettings,
    RasterPreviewSettings,
    SignalPreviewSettings,
    VideoPreviewSettings,
)
from modlink_ui_qt_widgets.widgets.main.preview.views import (
    FieldStreamView,
    RasterStreamView,
    VideoStreamView,
)


class PreviewViewSettingsTypeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def _bridge(self) -> QtSettingsBridge:
        return QtSettingsBridge(SettingsService(parent=self._app))

    @staticmethod
    def _descriptor(payload_type: str) -> StreamDescriptor:
        return StreamDescriptor(
            device_id="test.01",
            stream_key=payload_type,
            payload_type=payload_type,
            nominal_sample_rate_hz=60.0,
            chunk_size=4,
            channel_names=("c1", "c2"),
        )

    def test_raster_view_rejects_other_payload_settings(self) -> None:
        view = RasterStreamView(self._descriptor("raster"), self._bridge())

        with self.assertRaises(TypeError):
            view.apply_preview_settings(VideoPreviewSettings())

    def test_field_view_rejects_other_payload_settings(self) -> None:
        view = FieldStreamView(self._descriptor("field"), self._bridge())

        with self.assertRaises(TypeError):
            view.apply_preview_settings(SignalPreviewSettings())

    def test_video_view_rejects_other_payload_settings(self) -> None:
        view = VideoStreamView(self._descriptor("video"), self._bridge())

        with self.assertRaises(TypeError):
            view.apply_preview_settings(RasterPreviewSettings())

    def test_field_view_accepts_field_settings(self) -> None:
        view = FieldStreamView(self._descriptor("field"), self._bridge())
        settings = FieldPreviewSettings(
            colormap="magma",
            value_range_mode="manual",
            manual_min=2.0,
            manual_max=12.0,
            interpolation="bicubic",
            transform="rotate_180",
        )

        view.apply_preview_settings(settings)


if __name__ == "__main__":
    unittest.main()
