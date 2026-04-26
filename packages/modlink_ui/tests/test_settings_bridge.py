from __future__ import annotations

import unittest

from modlink_core.settings import SettingsStore, declare_core_settings
from modlink_ui.bridge import QtSettingsBridge


class QtSettingsBridgeTests(unittest.TestCase):
    def test_resync_from_backend_emits_leaf_setting_events(self) -> None:
        settings = SettingsStore()
        declare_core_settings(settings)
        settings.storage.root_dir = "C:/tmp/modlink-data"
        settings.storage.export_root_dir = "C:/tmp/modlink-export"
        bridge = QtSettingsBridge(settings)
        events: list[tuple[str, object]] = []
        bridge.sig_setting_changed.connect(lambda event: events.append((event.key, event.value)))

        bridge.resync_from_backend()

        self.assertIn(("storage.root_dir", "C:/tmp/modlink-data"), events)
        self.assertIn(("storage.export_root_dir", "C:/tmp/modlink-export"), events)


if __name__ == "__main__":
    unittest.main()
