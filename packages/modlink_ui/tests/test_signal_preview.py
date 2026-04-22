from __future__ import annotations

import os
import sys
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

from modlink_core import SettingsStore
from modlink_sdk import StreamDescriptor
from modlink_ui.bridge import QtSettingsBridge
from modlink_ui.shared.preview.settings.models import (
    RasterPreviewSettings,
    SignalPreviewSettings,
    normalize_preview_settings,
)
from modlink_ui.shared.preview.views.signal import SignalStreamView
from modlink_ui.shared.preview.views.signal_layout import (
    compute_expanded_signal_ranges,
    compute_signal_auto_range,
    compute_stacked_signal_range,
    resolve_signal_view_height,
)


class SignalPreviewSettingsTests(unittest.TestCase):
    def test_multi_channel_defaults_to_expanded(self) -> None:
        normalized = normalize_preview_settings(
            "signal",
            SignalPreviewSettings(),
            256.0,
            ("C3", "C4"),
        )
        self.assertIsInstance(normalized, SignalPreviewSettings)
        assert isinstance(normalized, SignalPreviewSettings)
        self.assertEqual(normalized.layout_mode, "expanded")
        self.assertEqual(normalized.visible_channel_indices, (0, 1))

    def test_invalid_visible_channel_indices_fall_back_to_all_channels(self) -> None:
        normalized = normalize_preview_settings(
            "signal",
            SignalPreviewSettings(
                layout_mode="stacked",
                visible_channel_indices=(9, -1),
            ),
            256.0,
            ("C3", "C4", "Cz"),
        )
        assert isinstance(normalized, SignalPreviewSettings)
        self.assertEqual(normalized.visible_channel_indices, (0, 1, 2))

    def test_single_channel_degrades_to_single_plot_behavior(self) -> None:
        normalized = normalize_preview_settings(
            "signal",
            SignalPreviewSettings(
                layout_mode="expanded",
                visible_channel_indices=(0, 3),
            ),
            256.0,
            ("C3",),
        )
        assert isinstance(normalized, SignalPreviewSettings)
        self.assertEqual(normalized.layout_mode, "stacked")
        self.assertEqual(normalized.visible_channel_indices, (0,))


class SignalRangeLogicTests(unittest.TestCase):
    def test_compute_signal_auto_range_adds_padding(self) -> None:
        lower, upper = compute_signal_auto_range(np.asarray([0.0, 10.0], dtype=np.float32))
        self.assertAlmostEqual(lower, -0.8)
        self.assertAlmostEqual(upper, 10.8)

    def test_stacked_range_uses_all_visible_channels(self) -> None:
        values = np.asarray([[0.0, 10.0], [2.0, 8.0]], dtype=np.float32)
        lower, upper = compute_stacked_signal_range(values)
        self.assertAlmostEqual(lower, -0.8)
        self.assertAlmostEqual(upper, 10.8)

    def test_expanded_range_is_per_channel(self) -> None:
        ranges = compute_expanded_signal_ranges(
            [
                np.asarray([0.0, 10.0], dtype=np.float32),
                np.asarray([5.0, 5.0], dtype=np.float32),
            ]
        )
        self.assertEqual(len(ranges), 2)
        self.assertAlmostEqual(ranges[0][0], -0.8)
        self.assertAlmostEqual(ranges[0][1], 10.8)
        self.assertAlmostEqual(ranges[1][0], 4.999, places=3)
        self.assertAlmostEqual(ranges[1][1], 5.001, places=3)

    def test_embedded_height_helper(self) -> None:
        self.assertEqual(resolve_signal_view_height("stacked", 4), 260)
        self.assertEqual(resolve_signal_view_height("expanded", 3), 780)


class SignalViewGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    @staticmethod
    def _descriptor() -> StreamDescriptor:
        return StreamDescriptor(
            device_id="test.01",
            stream_key="eeg",
            payload_type="signal",
            nominal_sample_rate_hz=256.0,
            chunk_size=16,
            channel_names=("C3", "C4", "Cz"),
        )

    def _create_view(self, descriptor: StreamDescriptor) -> SignalStreamView:
        settings = SettingsStore()
        bridge = QtSettingsBridge(settings)
        return SignalStreamView(descriptor, bridge)

    def test_expanded_height_tracks_visible_channel_count(self) -> None:
        descriptor = self._descriptor()
        view = self._create_view(descriptor)

        settings = normalize_preview_settings(
            "signal",
            SignalPreviewSettings(
                layout_mode="expanded",
                visible_channel_indices=(0, 2),
            ),
            descriptor.nominal_sample_rate_hz,
            descriptor.channel_names,
        )
        assert isinstance(settings, SignalPreviewSettings)
        view.apply_preview_settings(settings)
        self.assertEqual(view.minimumHeight(), 520)
        self.assertEqual(view.maximumHeight(), 520)

        settings = normalize_preview_settings(
            "signal",
            SignalPreviewSettings(
                layout_mode="expanded",
                visible_channel_indices=(1,),
            ),
            descriptor.nominal_sample_rate_hz,
            descriptor.channel_names,
        )
        assert isinstance(settings, SignalPreviewSettings)
        view.apply_preview_settings(settings)
        self.assertEqual(view.minimumHeight(), 260)
        self.assertEqual(view.maximumHeight(), 260)

    def test_stacked_height_stays_fixed(self) -> None:
        descriptor = self._descriptor()
        view = self._create_view(descriptor)

        settings = normalize_preview_settings(
            "signal",
            SignalPreviewSettings(
                layout_mode="stacked",
                visible_channel_indices=(0, 1, 2),
            ),
            descriptor.nominal_sample_rate_hz,
            descriptor.channel_names,
        )
        assert isinstance(settings, SignalPreviewSettings)
        view.apply_preview_settings(settings)
        self.assertEqual(view.minimumHeight(), 260)
        self.assertEqual(view.maximumHeight(), 260)

    def test_detached_mode_relaxes_embedded_height_lock(self) -> None:
        descriptor = self._descriptor()
        view = self._create_view(descriptor)

        settings = normalize_preview_settings(
            "signal",
            SignalPreviewSettings(
                layout_mode="expanded",
                visible_channel_indices=(0, 1, 2),
            ),
            descriptor.nominal_sample_rate_hz,
            descriptor.channel_names,
        )
        assert isinstance(settings, SignalPreviewSettings)
        view.apply_preview_settings(settings)
        self.assertEqual(view.minimumHeight(), 780)
        self.assertEqual(view.maximumHeight(), 780)

        view.set_embedded_mode(False)
        self.assertEqual(view.minimumHeight(), 260)
        self.assertGreater(view.maximumHeight(), 780)

    def test_signal_view_rejects_other_payload_settings(self) -> None:
        descriptor = self._descriptor()
        view = self._create_view(descriptor)

        with self.assertRaises(TypeError):
            view.apply_preview_settings(RasterPreviewSettings())


if __name__ == "__main__":
    unittest.main()
