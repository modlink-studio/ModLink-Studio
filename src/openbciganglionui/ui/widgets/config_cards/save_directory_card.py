from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import QFileDialog, QWidget
from qfluentwidgets import PushSettingCard
from qfluentwidgets import FluentIcon as FIF

from ...settings import SettingsManager


class SaveDirectoryCard(PushSettingCard):
    def __init__(
        self,
        settings_manager: SettingsManager,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            "选择",
            FIF.FOLDER,
            "文件保存目录",
            str(Path(settings_manager.default_save_dir)),
            parent,
        )
        self.settings_manager = settings_manager
        self.button.setFixedWidth(120)
        self.clicked.connect(self._choose_directory)
        self.settings_manager.saveDirChanged.connect(self._on_save_dir_changed)

        self._refresh_content(self.settings_manager.default_save_dir)

    def _choose_directory(self) -> None:
        current_dir = self.settings_manager.default_save_dir
        selected_dir = QFileDialog.getExistingDirectory(
            self.window(),
            "选择默认保存目录",
            current_dir,
        )
        if not selected_dir:
            return

        self.settings_manager.set_default_save_dir(selected_dir)

    def _on_save_dir_changed(self, save_dir: str) -> None:
        self._refresh_content(save_dir)

    def _refresh_content(self, save_dir: str) -> None:
        normalized = str(Path(save_dir))
        self.setContent(self._format_for_card(normalized))
        self.setToolTip(normalized)

    def _format_for_card(self, save_dir: str, max_length: int = 42) -> str:
        if len(save_dir) <= max_length:
            return save_dir
        return f"{save_dir[:20]}...{save_dir[-19:]}"
