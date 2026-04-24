from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QListWidgetItem,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    FluentIcon as FIF,
)
from qfluentwidgets import (
    ListWidget,
    PrimaryPushButton,
    PushButton,
    SimpleCardWidget,
    StrongBodyLabel,
)

from modlink_core.models import ReplayRecordingSummary
from modlink_ui.shared import BasePage, EmptyStateMessage


class ReplayRecordingsPanel(SimpleCardWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.recording_list = ListWidget(self)
        self.recording_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        layout.addWidget(StrongBodyLabel("Recordings", self))
        layout.addWidget(self.recording_list, 1)

    def selected_recording_id(self) -> str | None:
        item = self.recording_list.currentItem()
        if item is None:
            return None
        recording_id = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(recording_id, str) and recording_id:
            return recording_id
        return None

    def selected_recording_path(self) -> str | None:
        item = self.recording_list.currentItem()
        if item is None:
            return None
        recording_path = item.data(Qt.ItemDataRole.UserRole + 1)
        if isinstance(recording_path, str) and recording_path:
            return recording_path
        return None

    def reload_recordings(self, recordings: tuple[ReplayRecordingSummary, ...]) -> None:
        selected_recording_id = self.selected_recording_id()
        self.recording_list.clear()
        for summary in recordings:
            title = (summary.recording_label or "").strip() or summary.recording_id
            stream_count = len(summary.stream_ids)
            stream_text = f"{stream_count} {'stream' if stream_count == 1 else 'streams'}"
            item_text = f"{title} · {stream_text}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, summary.recording_id)
            item.setData(Qt.ItemDataRole.UserRole + 1, summary.recording_path)
            item.setToolTip(item_text)
            self.recording_list.addItem(item)
            if summary.recording_id == selected_recording_id:
                self.recording_list.setCurrentItem(item)


class ReplayRecordingsPage(BasePage):
    sig_open_recording_requested = pyqtSignal(str)
    sig_refresh_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            page_key="replay-recordings-page",
            title="回放",
            description="浏览已有 recordings，打开其中一条进入回放或导出工作台。",
            parent=parent,
        )
        self._open_button = PrimaryPushButton("打开", self)
        self._open_button.setIcon(FIF.FOLDER)
        self._refresh_button = PushButton("刷新", self)
        self._refresh_button.setIcon(FIF.SYNC)
        for button in (self._open_button, self._refresh_button):
            button.setMinimumWidth(88)
            self.header_action_layout.addWidget(button)

        self.empty_state = EmptyStateMessage(
            "当前还没有发现 recording",
            "点击“刷新”重新扫描 storage.root_dir/recordings。",
            self.scroll_widget,
        )
        self.recordings_panel = ReplayRecordingsPanel(self.scroll_widget)
        self.content_layout.addWidget(self.empty_state)
        self.content_layout.addWidget(self.recordings_panel, 1)

        self.recording_list.itemDoubleClicked.connect(lambda _item: self._emit_open_requested())
        self.open_button.clicked.connect(self._emit_open_requested)
        self.refresh_button.clicked.connect(self.sig_refresh_requested.emit)

    @property
    def recording_list(self) -> ListWidget:
        return self.recordings_panel.recording_list

    @property
    def open_button(self) -> PrimaryPushButton:
        return self._open_button

    @property
    def refresh_button(self) -> PushButton:
        return self._refresh_button

    def selected_recording_id(self) -> str | None:
        return self.recordings_panel.selected_recording_id()

    def selected_recording_path(self) -> str | None:
        return self.recordings_panel.selected_recording_path()

    def reload_recordings(self, recordings: tuple[ReplayRecordingSummary, ...]) -> None:
        self.recordings_panel.reload_recordings(recordings)
        self.empty_state.setVisible(not recordings)

    def _emit_open_requested(self) -> None:
        recording_path = self.selected_recording_path()
        if recording_path is not None:
            self.sig_open_recording_requested.emit(recording_path)


__all__ = ["ReplayRecordingsPage"]
