from __future__ import annotations

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QListWidgetItem,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    ListWidget,
    PrimaryPushButton,
    PushButton,
    SimpleCardWidget,
    StrongBodyLabel,
)
from qfluentwidgets import (
    FluentIcon as FIF,
)

from modlink_core.models import ReplayRecordingSummary
from modlink_ui.shared import BasePage, EmptyStateMessage


def _wrap_recording_text_for_display(text: str) -> str:
    if len(text) <= 24:
        return text

    parts: list[str] = []
    chunk_length = 0
    for char in text:
        parts.append(char)
        chunk_length += 1
        if char in "_-/\\.":
            parts.append("\u200b")
            chunk_length = 0
        elif chunk_length >= 16:
            parts.append("\u200b")
            chunk_length = 0
    return "".join(parts)


class ReplayRecordingItemWidget(QWidget):
    def __init__(self, title: str, subtitle: str, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self.title_label = BodyLabel(_wrap_recording_text_for_display(title), self)
        self.subtitle_label = CaptionLabel(_wrap_recording_text_for_display(subtitle), self)
        for label in (self.title_label, self.subtitle_label):
            label.setWordWrap(True)
            label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(4)
        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)


class ReplayRecordingsListWidget(ListWidget):
    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.sync_item_sizes()

    def sync_item_sizes(self) -> None:
        viewport_width = max(self.viewport().width() - 8, 0)
        for row in range(self.count()):
            item = self.item(row)
            widget = self.itemWidget(item)
            if widget is None:
                continue

            height = widget.sizeHint().height()
            layout = widget.layout()
            if layout is not None and layout.hasHeightForWidth():
                height = max(height, layout.totalHeightForWidth(viewport_width))
            elif widget.hasHeightForWidth():
                height = max(height, widget.heightForWidth(viewport_width))

            item.setSizeHint(QSize(viewport_width, height))


class ReplayRecordingsPanel(SimpleCardWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.recording_list = ReplayRecordingsListWidget(self)
        self.recording_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        self.open_button = PrimaryPushButton("打开所选 recording", self)
        self.open_button.setIcon(FIF.FOLDER)
        self.refresh_button = PushButton("刷新列表", self)
        self.refresh_button.setIcon(FIF.SYNC)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)
        header_row.addWidget(StrongBodyLabel("Recordings", self))
        header_row.addStretch(1)
        header_row.addWidget(self.open_button)
        header_row.addWidget(self.refresh_button)
        layout.addLayout(header_row)

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
            title = summary.recording_label or summary.recording_id
            subtitle = f"{summary.recording_id} · {len(summary.stream_ids)} streams"
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, summary.recording_id)
            item.setData(Qt.ItemDataRole.UserRole + 1, summary.recording_path)
            item.setToolTip(f"{title}\n{subtitle}")
            self.recording_list.addItem(item)
            self.recording_list.setItemWidget(
                item,
                ReplayRecordingItemWidget(title, subtitle, self.recording_list),
            )
            if summary.recording_id == selected_recording_id:
                self.recording_list.setCurrentItem(item)
        self.recording_list.sync_item_sizes()


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
        self.empty_state = EmptyStateMessage(
            "当前还没有发现 recording",
            "点击“刷新列表”重新扫描 storage.root_dir/recordings。",
            self.scroll_widget,
        )
        self.recordings_panel = ReplayRecordingsPanel(self.scroll_widget)
        self.content_layout.addWidget(self.empty_state)
        self.content_layout.addWidget(self.recordings_panel)
        self.content_layout.addStretch(1)

        self.recording_list.itemDoubleClicked.connect(lambda _item: self._emit_open_requested())
        self.open_button.clicked.connect(self._emit_open_requested)
        self.refresh_button.clicked.connect(self.sig_refresh_requested.emit)

    @property
    def recording_list(self) -> ListWidget:
        return self.recordings_panel.recording_list

    @property
    def open_button(self) -> PrimaryPushButton:
        return self.recordings_panel.open_button

    @property
    def refresh_button(self) -> PushButton:
        return self.recordings_panel.refresh_button

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
