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

from PyQt6.QtWidgets import QApplication, QWidget

from modlink_core.settings import SettingsStore
from modlink_ui.bridge import QtSettingsBridge
from modlink_ui.features.settings.cards.ai_assistant import (
    AiAssistantSettingsCard,
    _AiAssistantSettingsDialog,
)
from modlink_ui.shared.ui_settings.ai import (
    declare_ai_assistant_settings,
    load_ai_assistant_config,
)


class AiAssistantSettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        test_tmp_root = WORKSPACE_ROOT / ".tmp-tests"
        test_tmp_root.mkdir(exist_ok=True)
        self._temp_dir = test_tmp_root / f"ai-settings-{uuid4().hex}"
        self._temp_dir.mkdir()
        self._settings_path = self._temp_dir / "settings.json"

    def tearDown(self) -> None:
        self._pump_events()
        shutil.rmtree(self._temp_dir, ignore_errors=True)

    def _pump_events(self) -> None:
        for _ in range(5):
            self._app.processEvents()

    def _bridge(self) -> QtSettingsBridge:
        return QtSettingsBridge(SettingsStore(path=self._settings_path))

    def test_ai_settings_declaration_is_idempotent(self) -> None:
        bridge = self._bridge()

        declare_ai_assistant_settings(bridge)
        declare_ai_assistant_settings(bridge)

        self.assertFalse(load_ai_assistant_config(bridge).is_configured)

    def test_ai_settings_card_keeps_standard_content_height_when_unconfigured(self) -> None:
        card = AiAssistantSettingsCard(self._bridge())

        self.assertEqual(70, card.minimumHeight())
        self.assertEqual(70, card.maximumHeight())
        card.close()

    def test_settings_dialog_saves_and_config_reloads_from_file(self) -> None:
        bridge = self._bridge()
        parent = QWidget()
        parent.resize(800, 600)
        dialog = _AiAssistantSettingsDialog(bridge, parent)
        dialog.base_url_input.setText(" https://api.example.com/v1 ")
        dialog.api_key_input.setText(" secret-key ")
        dialog.model_input.setText(" gpt-test ")

        self.assertTrue(dialog.validate())

        reloaded_bridge = self._bridge()
        config = load_ai_assistant_config(reloaded_bridge)

        self.assertEqual("https://api.example.com/v1", config.base_url)
        self.assertEqual("secret-key", config.api_key)
        self.assertEqual("gpt-test", config.model)
        self.assertTrue(config.is_configured)
        dialog.close()
        parent.close()


if __name__ == "__main__":
    unittest.main()
