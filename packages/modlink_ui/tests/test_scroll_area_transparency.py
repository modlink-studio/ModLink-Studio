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
):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from PyQt6.QtWidgets import QApplication, QWidget

from modlink_sdk import StreamDescriptor
from modlink_ui.shared.page import BasePage
from modlink_ui.shared.preview.settings.dialog import (
    StreamPreviewSettingsPanel,
)


class ScrollAreaTransparencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def test_base_page_does_not_apply_cascading_transparent_widget_rule(self) -> None:
        page = BasePage(
            page_key="settings",
            title="Settings",
            description="Settings page description",
        )

        self.assertNotIn("QWidget{background: transparent}", page.scroll_area.styleSheet())
        self.assertNotIn("QWidget { background: transparent }", page.scroll_area.styleSheet())
        self.assertIn(
            "QWidget#settings-scroll-widget { background: transparent; }",
            page.scroll_widget.styleSheet(),
        )

    def test_preview_settings_panel_does_not_apply_cascading_transparent_widget_rule(self) -> None:
        descriptor = StreamDescriptor(
            device_id="test.01",
            stream_key="signal",
            payload_type="signal",
            nominal_sample_rate_hz=250.0,
            chunk_size=16,
            channel_names=("c1",),
        )
        panel = StreamPreviewSettingsPanel(descriptor, QWidget())

        self.assertNotIn("QWidget{background: transparent}", panel.styleSheet())
        self.assertNotIn("QWidget { background: transparent }", panel.styleSheet())
        self.assertIn(
            "QWidget#stream-preview-settings-scroll-widget { background: transparent; }",
            panel.scroll_widget.styleSheet(),
        )


if __name__ == "__main__":
    unittest.main()
