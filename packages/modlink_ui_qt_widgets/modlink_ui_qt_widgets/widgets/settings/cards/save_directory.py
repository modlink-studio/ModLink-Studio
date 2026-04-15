from __future__ import annotations

from PyQt6.QtWidgets import QFileDialog, QWidget
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import PushSettingCard

from modlink_core.storage import STORAGE_ROOT_DIR_KEY, StorageSettings
from modlink_qt_bridge import QtSettingsBridge


class SaveDirectoryCard(PushSettingCard):
    def __init__(
        self,
        settings: QtSettingsBridge,
        parent: QWidget | None = None,
    ) -> None:
        storage_settings = StorageSettings(settings)
        initial_save_dir = str(storage_settings.resolved_storage_root_dir())

        super().__init__(
            "选择",
            FIF.FOLDER,
            "文件保存目录",
            self._format_for_card(initial_save_dir),
            parent,
        )
        self._settings = settings
        self._storage_settings = storage_settings

        self.button.setFixedWidth(120)
        self.clicked.connect(self._choose_directory)
        self._settings.sig_setting_changed.connect(self._on_setting_changed)

        self._refresh_content(self.current_save_dir)

    @property
    def current_save_dir(self) -> str:
        return str(self._storage_settings.resolved_storage_root_dir())

    def _choose_directory(self) -> None:
        selected_dir = QFileDialog.getExistingDirectory(
            self.window(),
            "选择默认保存目录",
            self.current_save_dir,
        )
        if not selected_dir:
            return

        self._storage_settings.set_storage_root_dir(selected_dir)

    def _on_setting_changed(self, event: object) -> None:
        if getattr(event, "key", None) != STORAGE_ROOT_DIR_KEY:
            return
        self._refresh_content(self.current_save_dir)

    def _refresh_content(self, save_dir: str) -> None:
        normalized = str(save_dir)
        self.setContent(self._format_for_card(normalized))
        self.setToolTip(normalized)

    @staticmethod
    def _format_for_card(save_dir: str, max_length: int = 42) -> str:
        if len(save_dir) <= max_length:
            return save_dir
        return f"{save_dir[:20]}...{save_dir[-19:]}"
