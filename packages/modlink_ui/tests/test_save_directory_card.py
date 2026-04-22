from __future__ import annotations

import os
import unittest
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from modlink_core.events import SettingChangedEvent
from modlink_core.settings import SettingsStore, declare_core_settings
from modlink_ui.bridge import QtSettingsBridge
from modlink_ui.features.settings.cards.save_directory import SaveDirectoryCard

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class SaveDirectoryCardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def test_card_uses_storage_settings_root_and_refreshes_on_change(self) -> None:
        settings = SettingsStore()
        declare_core_settings(settings)
        settings.storage.root_dir = str(Path("C:/tmp/modlink-data").expanduser())
        bridge = QtSettingsBridge(settings)
        card = SaveDirectoryCard(bridge)

        self.assertEqual(str(Path("C:/tmp/modlink-data").expanduser()), card.current_save_dir)
        self.assertEqual(str(Path("C:/tmp/modlink-data").expanduser()), card.toolTip())

        bridge.storage.root_dir = str(Path("C:/tmp/modlink-updated").expanduser())
        card._on_setting_changed(
            SettingChangedEvent(
                key="storage.root_dir",
                value=str(Path("C:/tmp/modlink-updated").expanduser()),
                ts=0.0,
            )
        )

        self.assertEqual(str(Path("C:/tmp/modlink-updated").expanduser()), card.current_save_dir)
        self.assertEqual(str(Path("C:/tmp/modlink-updated").expanduser()), card.toolTip())
