from __future__ import annotations

import os
import shutil
import sys
import unittest
from pathlib import Path
from uuid import uuid4

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

from modlink_core.settings import SettingsStore
from modlink_qt_bridge import QtSettingsBridge
from modlink_sdk import StreamDescriptor
from modlink_ui_qt_widgets.widgets.main.preview.settings import PreviewSettingsRuntime
from modlink_ui_qt_widgets.widgets.main.preview.settings.models import (
    FieldPreviewSettings,
    RasterPreviewSettings,
    SignalFilterSettings,
    SignalPreviewSettings,
    VideoPreviewSettings,
)
from modlink_ui_qt_widgets.widgets.main.preview.settings.sections import (
    FieldPayloadSettingsPanel,
    RasterPayloadSettingsPanel,
    SignalPayloadSettingsPanel,
    VideoPayloadSettingsPanel,
)
from modlink_ui_qt_widgets.widgets.main.preview.settings.store import (
    PreviewStreamSettingsStore,
)
from modlink_ui_qt_widgets.widgets.main.preview.views import (
    FieldStreamView,
    RasterStreamView,
    SignalStreamView,
    VideoStreamView,
)


class _RecordingSignalStreamView(SignalStreamView):
    def __init__(self, descriptor: StreamDescriptor, settings: QtSettingsBridge) -> None:
        super().__init__(descriptor, settings)
        self.applied_settings: list[SignalPreviewSettings] = []

    def apply_preview_settings(self, settings: SignalPreviewSettings) -> None:
        self.applied_settings.append(settings)
        super().apply_preview_settings(settings)


class _RecordingRasterStreamView(RasterStreamView):
    def __init__(self, descriptor: StreamDescriptor, settings: QtSettingsBridge) -> None:
        super().__init__(descriptor, settings)
        self.applied_settings: list[RasterPreviewSettings] = []

    def apply_preview_settings(self, settings: RasterPreviewSettings) -> None:
        self.applied_settings.append(settings)
        super().apply_preview_settings(settings)


class _RecordingFieldStreamView(FieldStreamView):
    def __init__(self, descriptor: StreamDescriptor, settings: QtSettingsBridge) -> None:
        super().__init__(descriptor, settings)
        self.applied_settings: list[FieldPreviewSettings] = []

    def apply_preview_settings(self, settings: FieldPreviewSettings) -> None:
        self.applied_settings.append(settings)
        super().apply_preview_settings(settings)


class _RecordingVideoStreamView(VideoStreamView):
    def __init__(self, descriptor: StreamDescriptor, settings: QtSettingsBridge) -> None:
        super().__init__(descriptor, settings)
        self.applied_settings: list[VideoPreviewSettings] = []

    def apply_preview_settings(self, settings: VideoPreviewSettings) -> None:
        self.applied_settings.append(settings)
        super().apply_preview_settings(settings)


class PreviewSettingsRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        test_tmp_root = WORKSPACE_ROOT / ".tmp-tests"
        test_tmp_root.mkdir(exist_ok=True)
        self._temp_dir = test_tmp_root / f"preview-settings-{uuid4().hex}"
        self._temp_dir.mkdir()
        self._settings = SettingsStore(path=self._temp_dir / "preview-settings.json")
        self._settings_bridge = QtSettingsBridge(self._settings)

    def tearDown(self) -> None:
        shutil.rmtree(self._temp_dir, ignore_errors=True)

    @staticmethod
    def _descriptor(stream_key: str, payload_type: str) -> StreamDescriptor:
        return StreamDescriptor(
            device_id="test.01",
            stream_key=stream_key,
            payload_type=payload_type,
            nominal_sample_rate_hz=60.0,
            chunk_size=4,
            channel_names=("c1", "c2"),
        )

    def test_runtime_loads_normalized_settings_and_applies_to_view(self) -> None:
        descriptor = self._descriptor("raster", "raster")
        PreviewStreamSettingsStore(self._settings_bridge)
        self._settings.ui.preview.streams = {
            descriptor.stream_id: {
                "payload_type": "raster",
                "settings": {
                    "window_seconds": 12,
                    "colormap": "turbo",
                    "value_range_mode": "manual",
                    "manual_min": 8,
                    "manual_max": 2,
                    "interpolation": "bicubic",
                    "transform": "rotate_180",
                },
            }
        }

        view = _RecordingRasterStreamView(descriptor, self._settings_bridge)
        runtime = PreviewSettingsRuntime(descriptor, self._settings_bridge, view)

        expected = RasterPreviewSettings(
            window_seconds=12,
            colormap="turbo",
            value_range_mode="manual",
            manual_min=2.0,
            manual_max=8.0,
            interpolation="bicubic",
            transform="rotate_180",
        )
        self.assertIsInstance(runtime.payload_section_widget, RasterPayloadSettingsPanel)
        self.assertEqual(view.applied_settings[-1], expected)
        self.assertEqual(runtime.payload_section_widget.state(), expected)

    def test_runtime_persists_changes_and_reapplies_to_view(self) -> None:
        descriptor = self._descriptor("video", "video")
        view = _RecordingVideoStreamView(descriptor, self._settings_bridge)
        runtime = PreviewSettingsRuntime(descriptor, self._settings_bridge, view)

        updated = VideoPreviewSettings(
            color_format="bgr",
            scale_mode="fill",
            aspect_mode="stretch",
            transform="rotate_90",
        )
        self.assertIsInstance(runtime.payload_section_widget, VideoPayloadSettingsPanel)
        runtime.payload_section_widget.sig_state_changed.emit(updated)

        self.assertEqual(view.applied_settings[-1], updated)
        self.assertEqual(
            PreviewStreamSettingsStore(self._settings_bridge).load(descriptor),
            updated,
        )

    def test_runtime_falls_back_to_default_on_payload_type_mismatch(self) -> None:
        descriptor = self._descriptor("video", "video")
        PreviewStreamSettingsStore(self._settings_bridge)
        self._settings.ui.preview.streams = {
            descriptor.stream_id: {
                "payload_type": "signal",
                "settings": {
                    "window_seconds": 20,
                },
            }
        }

        view = _RecordingVideoStreamView(descriptor, self._settings_bridge)
        runtime = PreviewSettingsRuntime(descriptor, self._settings_bridge, view)

        self.assertEqual(view.applied_settings[-1], VideoPreviewSettings())
        self.assertEqual(runtime.payload_section_widget.state(), VideoPreviewSettings())

    def test_runtime_creates_signal_section_and_applies_to_signal_view(self) -> None:
        descriptor = self._descriptor("eeg", "signal")
        view = _RecordingSignalStreamView(descriptor, self._settings_bridge)
        runtime = PreviewSettingsRuntime(descriptor, self._settings_bridge, view)

        self.assertIsInstance(runtime.payload_section_widget, SignalPayloadSettingsPanel)
        self.assertEqual(view.applied_settings[-1], SignalPreviewSettings())

    def test_runtime_creates_field_section_and_applies_to_field_view(self) -> None:
        descriptor = self._descriptor("field", "field")
        view = _RecordingFieldStreamView(descriptor, self._settings_bridge)
        runtime = PreviewSettingsRuntime(descriptor, self._settings_bridge, view)

        self.assertIsInstance(runtime.payload_section_widget, FieldPayloadSettingsPanel)
        self.assertEqual(view.applied_settings[-1], FieldPreviewSettings())

    def test_runtime_rejects_unsupported_payload_type(self) -> None:
        descriptor = self._descriptor("mystery", "tensor")
        view = _RecordingRasterStreamView(
            self._descriptor("raster", "raster"),
            self._settings_bridge,
        )

        with self.assertRaises(ValueError):
            PreviewSettingsRuntime(descriptor, self._settings_bridge, view)

    def test_runtime_rejects_wrong_settings_type(self) -> None:
        descriptor = self._descriptor("video", "video")
        view = _RecordingVideoStreamView(descriptor, self._settings_bridge)
        runtime = PreviewSettingsRuntime(descriptor, self._settings_bridge, view)

        with self.assertRaises(TypeError):
            runtime._on_section_state_changed(RasterPreviewSettings())

    def test_signal_section_state_contract_uses_typed_settings(self) -> None:
        descriptor = self._descriptor("eeg", "signal")
        section = SignalPayloadSettingsPanel(descriptor)
        expected = SignalPreviewSettings(
            window_seconds=12,
            antialias_enabled=False,
            visible_channel_indices=(0, 1),
            filter=SignalFilterSettings(high_cutoff_hz=30.0),
        )

        section.set_state(expected)

        self.assertEqual(section.state(), expected)

    def test_raster_section_state_contract_uses_typed_settings(self) -> None:
        descriptor = self._descriptor("raster", "raster")
        section = RasterPayloadSettingsPanel(descriptor)
        expected = RasterPreviewSettings(
            window_seconds=12,
            colormap="plasma",
            value_range_mode="manual",
            manual_min=2.0,
            manual_max=12.0,
            interpolation="bicubic",
            transform="rotate_180",
        )

        section.set_state(expected)

        self.assertEqual(section.state(), expected)

    def test_section_rejects_wrong_settings_type(self) -> None:
        descriptor = self._descriptor("video", "video")
        section = VideoPayloadSettingsPanel(descriptor)

        with self.assertRaises(TypeError):
            section.set_state(RasterPreviewSettings())

    def test_field_section_state_contract_uses_typed_settings(self) -> None:
        descriptor = self._descriptor("field", "field")
        section = FieldPayloadSettingsPanel(descriptor)
        expected = FieldPreviewSettings(
            colormap="magma",
            value_range_mode="manual",
            manual_min=1.0,
            manual_max=9.0,
            interpolation="bilinear",
            transform="flip_vertical",
        )

        section.set_state(expected)

        self.assertEqual(section.state(), expected)

    def test_video_section_state_contract_uses_typed_settings(self) -> None:
        descriptor = self._descriptor("video", "video")
        section = VideoPayloadSettingsPanel(descriptor)
        expected = VideoPreviewSettings(
            color_format="yuv",
            scale_mode="fill",
            aspect_mode="stretch",
            transform="rotate_270",
        )

        section.set_state(expected)

        self.assertEqual(section.state(), expected)


if __name__ == "__main__":
    unittest.main()
