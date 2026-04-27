from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
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
    ComboBox,
    ListWidget,
    PrimaryPushButton,
    ProgressBar,
    PushButton,
    SimpleCardWidget,
    StrongBodyLabel,
)
from qfluentwidgets import (
    FluentIcon as FIF,
)

from modlink_core.models import ExportJobSnapshot, ReplaySnapshot
from modlink_ui.shared import BasePage, EmptyStateMessage
from modlink_ui.shared.inputs import remove_combo_popup_outer_margin

EXPORT_LABELS = {
    "signal_csv": "Signal CSV",
    "signal_npz": "Signal NPZ",
    "raster_npz": "Raster NPZ",
    "field_npz": "Field NPZ",
    "video_frames_zip": "Video Frames ZIP",
    "recording_bundle_zip": "Recording Bundle ZIP",
}


class ReplayExportCard(SimpleCardWidget):
    def __init__(self, export_root_dir: object, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.export_format_combo = ComboBox(self)
        remove_combo_popup_outer_margin(self.export_format_combo)
        for format_id, label in EXPORT_LABELS.items():
            self.export_format_combo.addItem(label, userData=format_id)

        self.export_button = PrimaryPushButton("开始导出", self)
        self.export_button.setIcon(FIF.SAVE)
        self.export_hint = CaptionLabel("", self)
        self.export_hint.setWordWrap(True)
        self.set_export_root_dir(export_root_dir)

        self.export_progress = ProgressBar(self)
        self.export_progress.setRange(0, 1000)
        self.export_progress.setValue(0)
        self.export_progress.setFormat("尚未开始导出")

        self.jobs_list = ListWidget(self)
        self.jobs_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.jobs_list.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        controls_row = QHBoxLayout()
        controls_row.setContentsMargins(0, 0, 0, 0)
        controls_row.setSpacing(8)
        controls_row.addWidget(BodyLabel("格式", self))
        controls_row.addWidget(self.export_format_combo, 1)
        controls_row.addWidget(self.export_button)

        layout.addWidget(StrongBodyLabel("导出任务", self))
        layout.addLayout(controls_row)
        layout.addWidget(self.export_hint)
        layout.addWidget(self.export_progress)
        layout.addWidget(BodyLabel("任务记录", self))
        layout.addWidget(self.jobs_list, 1)

    def selected_format_id(self) -> str | None:
        format_id = self.export_format_combo.currentData()
        if isinstance(format_id, str) and format_id:
            return format_id
        return None

    def set_export_enabled(self, enabled: bool) -> None:
        self.export_button.setEnabled(enabled)

    def set_export_root_dir(self, export_root_dir: object) -> None:
        self.export_hint.setText(f"导出根目录：{export_root_dir}")

    def reload_jobs(self, jobs: tuple[ExportJobSnapshot, ...]) -> None:
        self.jobs_list.clear()
        for job in jobs:
            output_text = "" if not job.output_path else f" · {job.output_path}"
            error_text = "" if not job.error else f" · {job.error}"
            item = QListWidgetItem(
                f"{EXPORT_LABELS.get(job.format_id, job.format_id)} · {job.state} · {int(job.progress * 100)}%{output_text}{error_text}"
            )
            self.jobs_list.addItem(item)
        self.sync_export_progress(jobs)

    def sync_export_progress(self, jobs: tuple[ExportJobSnapshot, ...]) -> None:
        if not jobs:
            self.export_progress.setValue(0)
            self.export_progress.setFormat("尚未开始导出")
            return
        latest_job = jobs[-1]
        progress = int(round(float(latest_job.progress) * 1000))
        self.export_progress.setValue(progress)
        self.export_progress.setFormat(
            f"{EXPORT_LABELS.get(latest_job.format_id, latest_job.format_id)} · {latest_job.state} · {int(latest_job.progress * 100)}%"
        )


class ReplayExportPage(BasePage):
    sig_show_recordings_requested = pyqtSignal()
    sig_show_player_requested = pyqtSignal()
    sig_export_requested = pyqtSignal(str)

    def __init__(self, export_root_dir: object, parent: QWidget | None = None) -> None:
        super().__init__(
            page_key="replay-export-page",
            title="导出",
            description="打开一条 recording 后，在这里选择格式并导出。",
            parent=parent,
        )
        self._snapshot = ReplaySnapshot(
            state="idle",
            is_started=False,
            recording_id=None,
            recording_path=None,
            position_ns=0,
            duration_ns=0,
            speed_multiplier=1.0,
        )
        self.recordings_route_button = PushButton("列表", self)
        self.recordings_route_button.setIcon(FIF.LIBRARY)
        self.player_route_button = PushButton("回放", self)
        self.player_route_button.setIcon(FIF.PLAY_SOLID)
        for button in (self.recordings_route_button, self.player_route_button):
            button.setMinimumWidth(88)
            self.header_action_layout.addWidget(button)

        self.empty_state = EmptyStateMessage(
            "还没有可导出的 recording",
            "先回到 recordings 页打开一条 recording，再开始导出。",
            self.scroll_widget,
        )
        self.export_card = ReplayExportCard(export_root_dir, self.scroll_widget)
        self.content_layout.addWidget(self.empty_state)
        self.content_layout.addWidget(self.export_card, 1)

        self.export_button.clicked.connect(self._emit_export_requested)
        self.recordings_route_button.clicked.connect(self.sig_show_recordings_requested.emit)
        self.player_route_button.clicked.connect(self.sig_show_player_requested.emit)

    @property
    def export_format_combo(self) -> ComboBox:
        return self.export_card.export_format_combo

    @property
    def export_button(self) -> PrimaryPushButton:
        return self.export_card.export_button

    @property
    def export_hint(self) -> CaptionLabel:
        return self.export_card.export_hint

    @property
    def export_progress(self) -> ProgressBar:
        return self.export_card.export_progress

    @property
    def jobs_list(self) -> ListWidget:
        return self.export_card.jobs_list

    def selected_format_id(self) -> str | None:
        return self.export_card.selected_format_id()

    def set_status_hint(self, text: str) -> None:
        self.export_hint.setText(text)

    def apply_snapshot(self, snapshot: ReplaySnapshot, *, export_root_dir: object) -> None:
        self._snapshot = snapshot
        self.export_card.set_export_root_dir(export_root_dir)
        self.export_card.set_export_enabled(snapshot.recording_id is not None)
        self.player_route_button.setEnabled(snapshot.recording_id is not None)
        self.empty_state.setVisible(snapshot.recording_id is None)
        self._sync_header(snapshot)

    def reload_jobs(self, jobs: tuple[ExportJobSnapshot, ...]) -> None:
        self.export_card.reload_jobs(jobs)

    def _emit_export_requested(self) -> None:
        format_id = self.selected_format_id()
        if format_id is not None:
            self.sig_export_requested.emit(format_id)

    def _sync_header(self, snapshot: ReplaySnapshot) -> None:
        recording_id = _format_recording_badge(snapshot.recording_id)
        self.title_label.setText("导出")
        self.description_label.setText(f"当前 recording：{recording_id} · 选择格式并导出。")


def _format_recording_badge(recording_id: str | None) -> str:
    if recording_id is None or not str(recording_id).strip():
        return "未打开 recording"
    normalized = str(recording_id).strip()
    if len(normalized) <= 26:
        return normalized
    return f"{normalized[:14]}...{normalized[-8:]}"


__all__ = ["ReplayExportPage"]
