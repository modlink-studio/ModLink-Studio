from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QListWidgetItem,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    ComboBox,
    InfoBar,
    InfoBarPosition,
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

from modlink_core.models import (
    ReplaySnapshot,
)
from modlink_qt_bridge import QtModLinkBridge, QtReplayBridge, QtSettingsBridge
from modlink_sdk import FrameEnvelope
from modlink_ui_qt_widgets.widgets.main.preview.cards import DetachableStreamPreviewCard
from modlink_ui_qt_widgets.widgets.shared import BasePage, EmptyStateMessage


class _ReplayPreviewPanel(QWidget):
    def __init__(
        self,
        replay: QtReplayBridge,
        settings: QtSettingsBridge,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self._replay = replay
        self._settings = settings
        self._cards: dict[str, DetachableStreamPreviewCard] = {}
        self.empty_state = EmptyStateMessage(
            "当前还没有打开 recording",
            "从左侧选择一条 recording，然后点击“打开所选 recording”。",
            self,
        )
        self.cards_container = QWidget(self)
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(14)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.empty_state)
        layout.addWidget(self.cards_container)

        self._replay.bus.sig_frame.connect(self._on_frame)
        self._replay.sig_bus_reset.connect(self.rebuild_from_bus)
        self.rebuild_from_bus()

    def rebuild_from_bus(self) -> None:
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._cards.clear()

        descriptors = list(self._replay.bus.descriptors().values())
        descriptors.sort(key=lambda descriptor: descriptor.display_name or descriptor.stream_id)
        for descriptor in descriptors:
            card = DetachableStreamPreviewCard(
                descriptor,
                self._settings,
                self.cards_container,
            )
            self._cards[descriptor.stream_id] = card
            self.cards_layout.addWidget(card)

        self._sync_visibility()

    def _on_frame(self, frame: FrameEnvelope) -> None:
        card = self._cards.get(frame.stream_id)
        if card is None:
            descriptor = self._replay.bus.descriptor(frame.stream_id)
            if descriptor is None:
                return
            self.rebuild_from_bus()
            card = self._cards.get(frame.stream_id)
            if card is None:
                return
        card.push_frame(frame)

    def _sync_visibility(self) -> None:
        has_cards = bool(self._cards)
        self.empty_state.setVisible(not has_cards)
        self.cards_container.setVisible(has_cards)


class ReplayPage(BasePage):
    def __init__(self, engine: QtModLinkBridge, parent: QWidget | None = None) -> None:
        super().__init__(
            page_key="replay-page",
            title="回放与导出",
            description="浏览已有 recordings，进行回放、复盘和分析导出。",
            parent=parent,
        )
        self.engine = engine
        self._replay = engine.replay

        self._recording_list = ListWidget(self.scroll_widget)
        self._recording_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._recording_list.setWordWrap(True)
        self._recording_list.itemDoubleClicked.connect(lambda _item: self._open_selected_recording())

        self._markers_list = ListWidget(self.scroll_widget)
        self._markers_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._markers_list.setWordWrap(True)
        self._segments_list = ListWidget(self.scroll_widget)
        self._segments_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._segments_list.setWordWrap(True)
        self._jobs_list = ListWidget(self.scroll_widget)
        self._jobs_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._jobs_list.setWordWrap(True)

        self._status_label = BodyLabel("尚未打开 recording。", self.scroll_widget)
        self._status_hint = CaptionLabel("左侧列表来自 storage.root_dir/recordings。", self.scroll_widget)
        self._playback_progress = ProgressBar(self.scroll_widget)
        self._playback_progress.setRange(0, 1000)
        self._playback_progress.setValue(0)
        self._playback_progress.setFormat("00:00.000 / 00:00.000")
        self._export_progress = ProgressBar(self.scroll_widget)
        self._export_progress.setRange(0, 1000)
        self._export_progress.setValue(0)
        self._export_progress.setFormat("尚未开始导出")

        self._open_button = PrimaryPushButton("打开所选 recording", self.scroll_widget)
        self._open_button.setIcon(FIF.FOLDER)
        self._open_button.clicked.connect(self._open_selected_recording)
        self._refresh_button = PushButton("刷新列表", self.scroll_widget)
        self._refresh_button.setIcon(FIF.SYNC)
        self._refresh_button.clicked.connect(self._replay.refresh_recordings)
        self._play_button = PrimaryPushButton("播放", self.scroll_widget)
        self._play_button.setIcon(FIF.PLAY_SOLID)
        self._play_button.clicked.connect(self._replay.play)
        self._pause_button = PushButton("暂停", self.scroll_widget)
        self._pause_button.setIcon(FIF.PAUSE_BOLD)
        self._pause_button.clicked.connect(self._replay.pause)
        self._stop_button = PushButton("停止", self.scroll_widget)
        self._stop_button.setIcon(FIF.STOP_WATCH)
        self._stop_button.clicked.connect(self._replay.stop)

        self._speed_combo = ComboBox(self.scroll_widget)
        self._speed_combo.addItem("1x", userData=1.0)
        self._speed_combo.addItem("2x", userData=2.0)
        self._speed_combo.addItem("4x", userData=4.0)
        self._speed_combo.currentIndexChanged.connect(self._on_speed_changed)

        self._export_format_combo = ComboBox(self.scroll_widget)
        for format_id, label in _EXPORT_LABELS.items():
            self._export_format_combo.addItem(label, userData=format_id)
        self._export_button = PrimaryPushButton("开始导出", self.scroll_widget)
        self._export_button.setIcon(FIF.SAVE)
        self._export_button.clicked.connect(self._start_export)
        self._export_hint = CaptionLabel(
            f"导出根目录：{self._replay.export_root_dir}",
            self.scroll_widget,
        )

        self._preview_panel = _ReplayPreviewPanel(
            self._replay,
            self.engine.settings,
            self.scroll_widget,
        )

        splitter = QSplitter(Qt.Orientation.Horizontal, self.scroll_widget)
        splitter.addWidget(self._build_recordings_panel(splitter))
        splitter.addWidget(self._build_replay_panel(splitter))
        splitter.addWidget(self._build_side_panel(splitter))
        splitter.setSizes([240, 620, 320])

        self.content_layout.addWidget(splitter, 1)

        self._replay.sig_recordings_changed.connect(self._reload_recordings)
        self._replay.sig_snapshot_changed.connect(self._on_snapshot_changed)
        self._replay.sig_annotations_changed.connect(self._reload_annotations)
        self._replay.sig_export_jobs_changed.connect(self._reload_export_jobs)
        self._replay.sig_error.connect(self._on_error)

        self._reload_recordings()
        self._on_snapshot_changed(self._replay.snapshot())
        self._reload_annotations()
        self._reload_export_jobs()
        self._replay.refresh_recordings()

    def _build_recordings_panel(self, parent: QWidget) -> QWidget:
        card = SimpleCardWidget(parent)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(StrongBodyLabel("Recordings", card))
        layout.addWidget(self._recording_list, 1)
        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.setSpacing(8)
        button_row.addWidget(self._open_button, 1)
        button_row.addWidget(self._refresh_button)
        layout.addLayout(button_row)
        return card

    def _build_replay_panel(self, parent: QWidget) -> QWidget:
        card = SimpleCardWidget(parent)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(StrongBodyLabel("回放", card))
        layout.addWidget(self._status_label)
        layout.addWidget(self._status_hint)
        layout.addWidget(self._playback_progress)

        control_row = QHBoxLayout()
        control_row.setContentsMargins(0, 0, 0, 0)
        control_row.setSpacing(8)
        control_row.addWidget(self._play_button)
        control_row.addWidget(self._pause_button)
        control_row.addWidget(self._stop_button)
        control_row.addWidget(BodyLabel("倍速", card))
        control_row.addWidget(self._speed_combo)
        control_row.addStretch(1)
        layout.addLayout(control_row)
        layout.addWidget(self._preview_panel, 1)
        return card

    def _build_side_panel(self, parent: QWidget) -> QWidget:
        container = QWidget(parent)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        annotations_card = SimpleCardWidget(container)
        annotations_layout = QVBoxLayout(annotations_card)
        annotations_layout.setContentsMargins(18, 18, 18, 18)
        annotations_layout.setSpacing(12)
        annotations_layout.addWidget(StrongBodyLabel("Annotations", annotations_card))
        annotations_layout.addWidget(BodyLabel("Markers", annotations_card))
        annotations_layout.addWidget(self._markers_list, 1)
        annotations_layout.addWidget(BodyLabel("Segments", annotations_card))
        annotations_layout.addWidget(self._segments_list, 1)

        export_card = SimpleCardWidget(container)
        export_layout = QVBoxLayout(export_card)
        export_layout.setContentsMargins(18, 18, 18, 18)
        export_layout.setSpacing(12)
        export_layout.addWidget(StrongBodyLabel("Export", export_card))
        export_layout.addWidget(self._export_format_combo)
        export_layout.addWidget(self._export_button)
        export_layout.addWidget(self._export_hint)
        export_layout.addWidget(self._export_progress)
        export_layout.addWidget(BodyLabel("Jobs", export_card))
        export_layout.addWidget(self._jobs_list, 1)

        layout.addWidget(annotations_card, 1)
        layout.addWidget(export_card, 1)
        return container

    def _reload_recordings(self) -> None:
        selected_item = self._recording_list.currentItem()
        selected_recording_id = None if selected_item is None else selected_item.data(Qt.ItemDataRole.UserRole)
        self._recording_list.clear()
        for summary in self._replay.recordings():
            title = summary.recording_label or summary.recording_id
            subtitle = f"{summary.recording_id} · {len(summary.stream_ids)} streams"
            item = QListWidgetItem(f"{title}\n{subtitle}")
            item.setData(Qt.ItemDataRole.UserRole, summary.recording_id)
            item.setData(Qt.ItemDataRole.UserRole + 1, summary.recording_path)
            self._recording_list.addItem(item)
            if summary.recording_id == selected_recording_id:
                self._recording_list.setCurrentItem(item)

    def _reload_annotations(self) -> None:
        snapshot = self._replay.snapshot()
        self._markers_list.clear()
        self._segments_list.clear()
        for marker in self._replay.markers():
            item = QListWidgetItem(f"{_format_time_ns(marker.timestamp_ns)} · {marker.label or '未命名'}")
            item.setData(Qt.ItemDataRole.UserRole, marker.timestamp_ns)
            self._markers_list.addItem(item)
        for segment in self._replay.segments():
            item = QListWidgetItem(
                f"{_format_time_ns(segment.start_ns)} → {_format_time_ns(segment.end_ns)} · {segment.label or '未命名'}"
            )
            item.setData(Qt.ItemDataRole.UserRole, (segment.start_ns, segment.end_ns))
            self._segments_list.addItem(item)
        self._highlight_annotations(snapshot)

    def _reload_export_jobs(self) -> None:
        self._jobs_list.clear()
        jobs = self._replay.export_jobs()
        for job in jobs:
            output_text = "" if not job.output_path else f" · {job.output_path}"
            error_text = "" if not job.error else f" · {job.error}"
            item = QListWidgetItem(
                f"{_EXPORT_LABELS.get(job.format_id, job.format_id)} · {job.state} · {int(job.progress * 100)}%{output_text}{error_text}"
            )
            self._jobs_list.addItem(item)
        self._sync_export_progress(jobs)

    def _open_selected_recording(self) -> None:
        item = self._recording_list.currentItem()
        if item is None:
            return
        recording_path = item.data(Qt.ItemDataRole.UserRole + 1)
        if not isinstance(recording_path, str) or recording_path == "":
            return
        self._replay.open_recording(recording_path)

    def _on_snapshot_changed(self, snapshot: object) -> None:
        if not isinstance(snapshot, ReplaySnapshot):
            snapshot = self._replay.snapshot()
        recording_id = snapshot.recording_id or "未打开"
        position_text = _format_time_ns(snapshot.position_ns)
        duration_text = _format_time_ns(snapshot.duration_ns)
        self._status_label.setText(
            f"状态：{snapshot.state} · recording：{recording_id} · 位置：{position_text} / {duration_text}"
        )
        self._status_hint.setText(f"导出根目录：{self._replay.export_root_dir}")
        self._sync_playback_progress(snapshot)
        self._play_button.setEnabled(snapshot.recording_id is not None and snapshot.state != "playing")
        self._pause_button.setEnabled(snapshot.state == "playing")
        self._stop_button.setEnabled(snapshot.recording_id is not None and snapshot.state != "idle")
        self._export_button.setEnabled(snapshot.recording_id is not None)
        self._highlight_annotations(snapshot)

    def _highlight_annotations(self, snapshot: ReplaySnapshot) -> None:
        current_position_ns = snapshot.position_ns
        self._markers_list.clearSelection()
        self._segments_list.clearSelection()

        active_marker_index = -1
        for index, marker in enumerate(self._replay.markers()):
            if marker.timestamp_ns <= current_position_ns:
                active_marker_index = index
        if active_marker_index >= 0:
            self._markers_list.setCurrentRow(active_marker_index)
            item = self._markers_list.item(active_marker_index)
            if item is not None:
                item.setSelected(True)

        active_segment_index = -1
        for index, segment in enumerate(self._replay.segments()):
            if segment.start_ns <= current_position_ns <= segment.end_ns:
                active_segment_index = index
                break
        if active_segment_index >= 0:
            self._segments_list.setCurrentRow(active_segment_index)
            item = self._segments_list.item(active_segment_index)
            if item is not None:
                item.setSelected(True)

    def _on_speed_changed(self) -> None:
        value = self._speed_combo.currentData()
        if isinstance(value, float | int):
            self._replay.set_speed(float(value))

    def _start_export(self) -> None:
        format_id = self._export_format_combo.currentData()
        if isinstance(format_id, str) and format_id:
            self._replay.start_export(format_id)

    def _on_error(self, message: str) -> None:
        self._status_hint.setText(message)
        parent = self.window() if isinstance(self.window(), QWidget) else self
        InfoBar.error(
            title="回放错误",
            content=message,
            duration=4500,
            position=InfoBarPosition.TOP_RIGHT,
            parent=parent,
        )

    def _sync_playback_progress(self, snapshot: ReplaySnapshot) -> None:
        duration_ns = max(0, snapshot.duration_ns)
        position_ns = min(max(0, snapshot.position_ns), duration_ns)
        progress = 0 if duration_ns == 0 else int(round(position_ns / duration_ns * 1000))
        self._playback_progress.setValue(progress)
        self._playback_progress.setFormat(
            f"{_format_time_ns(position_ns)} / {_format_time_ns(duration_ns)}"
        )

    def _sync_export_progress(self, jobs: tuple[object, ...]) -> None:
        if not jobs:
            self._export_progress.setValue(0)
            self._export_progress.setFormat("尚未开始导出")
            return
        latest_job = jobs[-1]
        progress = int(round(float(latest_job.progress) * 1000))
        self._export_progress.setValue(progress)
        self._export_progress.setFormat(
            f"{_EXPORT_LABELS.get(latest_job.format_id, latest_job.format_id)} · {latest_job.state} · {int(latest_job.progress * 100)}%"
        )


def _format_time_ns(value: int) -> str:
    total_ms = max(0, int(value // 1_000_000))
    total_seconds, millis = divmod(total_ms, 1000)
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"
    return f"{minutes:02d}:{seconds:02d}.{millis:03d}"


_EXPORT_LABELS = {
    "signal_csv": "Signal CSV",
    "signal_npz": "Signal NPZ",
    "raster_npz": "Raster NPZ",
    "field_npz": "Field NPZ",
    "video_frames_zip": "Video Frames ZIP",
    "recording_bundle_zip": "Recording Bundle ZIP",
}
