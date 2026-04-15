from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

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
from modlink_qt_bridge import QtSettingsBridge
from modlink_sdk import StreamDescriptor
from modlink_ui_qt_widgets.widgets.main.preview.views.field import FieldStreamView
from modlink_ui_qt_widgets.widgets.main.preview.views.raster import RasterStreamView
from modlink_ui_qt_widgets.widgets.main.preview.views.signal import SignalStreamView


class PreviewThemeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def _bridge(self) -> QtSettingsBridge:
        return QtSettingsBridge(SettingsStore())

    @staticmethod
    def _signal_descriptor() -> StreamDescriptor:
        return StreamDescriptor(
            device_id="test_signal.01",
            stream_key="eeg",
            payload_type="signal",
            nominal_sample_rate_hz=256.0,
            chunk_size=16,
            channel_names=("C3", "C4"),
        )

    @staticmethod
    def _field_descriptor() -> StreamDescriptor:
        return StreamDescriptor(
            device_id="test_field.01",
            stream_key="field",
            payload_type="field",
            nominal_sample_rate_hz=30.0,
            chunk_size=1,
            channel_names=("value",),
        )

    @staticmethod
    def _raster_descriptor() -> StreamDescriptor:
        return StreamDescriptor(
            device_id="test_raster.01",
            stream_key="raster",
            payload_type="raster",
            nominal_sample_rate_hz=100.0,
            chunk_size=8,
            channel_names=("value",),
        )

    def test_signal_view_applies_dark_theme_colors(self) -> None:
        with patch(
            "modlink_ui_qt_widgets.widgets.main.preview.views.signal.isDarkTheme",
            return_value=True,
        ):
            view = SignalStreamView(self._signal_descriptor(), self._bridge())
            view._ensure_channels(2)
            view._ensure_plot_layout(2)
            view._apply_theme()

        self.assertEqual("#2b2b2b", view._graphics_widget.backgroundBrush().color().name())
        self.assertEqual(
            "#d4d4d4",
            str(view._plot_bundles[0].plot_item.titleLabel.opts["color"]).lower(),
        )
        self.assertEqual("#4da3ff", view._plot_bundles[0].curves[0].opts["pen"].color().name())

    def test_field_view_applies_dark_theme_background(self) -> None:
        with patch(
            "modlink_ui_qt_widgets.widgets.main.preview.views.image.isDarkTheme",
            return_value=True,
        ):
            view = FieldStreamView(self._field_descriptor(), self._bridge())
            view._apply_theme()

        self.assertEqual("#2b2b2b", view._graphics_widget.backgroundBrush().color().name())

    def test_raster_view_applies_dark_theme_background(self) -> None:
        with patch(
            "modlink_ui_qt_widgets.widgets.main.preview.views.raster.isDarkTheme",
            return_value=True,
        ):
            view = RasterStreamView(self._raster_descriptor(), self._bridge())
            view._apply_theme()

        self.assertEqual("#2b2b2b", view._graphics_widget.backgroundBrush().color().name())


if __name__ == "__main__":
    unittest.main()
