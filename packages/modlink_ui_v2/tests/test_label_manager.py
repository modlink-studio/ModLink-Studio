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
    WORKSPACE_ROOT / "packages" / "modlink_core",
):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from PyQt6.QtWidgets import QApplication

from modlink_core.settings import SettingsStore
from modlink_ui_v2.bridge import QtSettingsBridge
from modlink_ui_v2.features.settings.cards.label_manager import LabelManagerCard


class LabelManagerCardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        test_tmp_root = WORKSPACE_ROOT / ".tmp-tests"
        test_tmp_root.mkdir(exist_ok=True)
        self._temp_dir = test_tmp_root / f"label-manager-{uuid4().hex}"
        self._temp_dir.mkdir()
        settings = SettingsStore(path=self._temp_dir / "label-manager-settings.json")
        self._settings_bridge = QtSettingsBridge(settings)

    def tearDown(self) -> None:
        self._pump_events()
        shutil.rmtree(self._temp_dir, ignore_errors=True)

    def _pump_events(self) -> None:
        for _ in range(5):
            self._app.processEvents()

    def test_dialog_is_destroyed_on_close_and_recreated_on_reopen(self) -> None:
        card = LabelManagerCard(self._settings_bridge)
        card.show()
        self._pump_events()

        card._open_dialog()
        self._pump_events()

        dialog = card._dialog
        self.assertIsNotNone(dialog)
        destroyed: list[bool] = []
        dialog.destroyed.connect(lambda *_args: destroyed.append(True))

        dialog.accept()
        self._pump_events()

        self.assertTrue(destroyed)
        self.assertIsNone(card._dialog)

        card._open_dialog()
        self._pump_events()

        reopened_dialog = card._dialog
        self.assertIsNotNone(reopened_dialog)
        self.assertIsNot(reopened_dialog, dialog)

        reopened_dialog.close()
        card.close()
        self._pump_events()


if __name__ == "__main__":
    unittest.main()
