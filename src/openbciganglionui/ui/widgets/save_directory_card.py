from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import QFileDialog, QWidget
from qfluentwidgets import PushSettingCard
from qfluentwidgets import FluentIcon as FIF

from ...backend import GanglionBackendBase, SaveDirEvent


class SaveDirectoryCard(PushSettingCard):
    def __init__(
        self,
        backend: GanglionBackendBase,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            "选择",
            FIF.FOLDER,
            "文件保存目录",
            str(Path(backend.default_save_dir)),
            parent,
        )
        self.backend = backend
        self.button.setFixedWidth(120)
        self.clicked.connect(self._choose_directory)
        self.backend.sig_save_dir.connect(self._on_save_dir_changed)

        self._refresh_content(self.backend.default_save_dir)
        self.backend.load_save_dir()

    def _choose_directory(self) -> None:
        current_dir = self.backend.default_save_dir
        selected_dir = QFileDialog.getExistingDirectory(
            self.window(),
            "选择默认保存目录",
            current_dir,
        )
        if not selected_dir:
            return

        self.backend.set_save_dir(selected_dir)

    def _on_save_dir_changed(self, event: SaveDirEvent) -> None:
        self._refresh_content(event.save_dir)

    def _refresh_content(self, save_dir: str) -> None:
        normalized = str(Path(save_dir))
        self.setContent(self._format_for_card(normalized))
        self.setToolTip(normalized)

    def _format_for_card(self, save_dir: str, max_length: int = 42) -> str:
        if len(save_dir) <= max_length:
            return save_dir
        return f"{save_dir[:20]}...{save_dir[-19:]}"
