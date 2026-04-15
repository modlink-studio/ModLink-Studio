from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import QFileDialog, QWidget
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import PushSettingCard

from modlink_core.recording.backend import STORAGE_ROOT_DIR_KEY
from modlink_qt_bridge import QtSettingsBridge


class SaveDirectoryCard(PushSettingCard):
    def __init__(
        self,
        settings: QtSettingsBridge,
        default_dir: str | Path,
        parent: QWidget | None = None,
    ) -> None:
        default_dir_str = str(Path(default_dir).expanduser())
        configured = settings.get(STORAGE_ROOT_DIR_KEY)
        initial_save_dir = str(Path(configured or default_dir_str).expanduser())

        super().__init__(
            "选择",
            FIF.FOLDER,
            "文件保存目录",
            self._format_for_card(initial_save_dir),
            parent,
        )
        self._settings = settings
        self._default_dir = default_dir_str

        self.button.setFixedWidth(120)
        self.clicked.connect(self._choose_directory)
        self._settings.sig_setting_changed.connect(self._on_setting_changed)

        self._refresh_content(self.current_save_dir)

    @property
    def current_save_dir(self) -> str:
        configured = self._settings.get(STORAGE_ROOT_DIR_KEY)
        return str(Path(configured or self._default_dir).expanduser())

    def _choose_directory(self) -> None:
        selected_dir = QFileDialog.getExistingDirectory(
            self.window(),
            "选择默认保存目录",
            self.current_save_dir,
        )
        if not selected_dir:
            return

        self._settings.set(STORAGE_ROOT_DIR_KEY, str(Path(selected_dir)))

    def _on_setting_changed(self, event: object) -> None:
        if getattr(event, "key", None) != STORAGE_ROOT_DIR_KEY:
            return
        self._refresh_content(self.current_save_dir)

    def _refresh_content(self, save_dir: str) -> None:
        normalized = str(Path(save_dir))
        self.setContent(self._format_for_card(normalized))
        self.setToolTip(normalized)

    @staticmethod
    def _format_for_card(save_dir: str, max_length: int = 42) -> str:
        if len(save_dir) <= max_length:
            return save_dir
        return f"{save_dir[:20]}...{save_dir[-19:]}"
