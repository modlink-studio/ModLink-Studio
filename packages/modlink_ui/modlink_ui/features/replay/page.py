from __future__ import annotations

from pathlib import Path
from typing import Literal

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QListWidgetItem,
    QStackedWidget,
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
    ExportJobSnapshot,
    ReplayMarker,
    ReplayRecordingSummary,
    ReplaySegment,
    ReplaySnapshot,
)
from modlink_sdk import FrameEnvelope
from modlink_ui.bridge import QtModLinkBridge, QtReplayBridge, QtSettingsBridge
from modlink_ui.shared import BasePage, EmptyStateMessage
from modlink_ui.shared.preview.cards import DetachableStreamPreviewCard

type ReplayRoute = Literal["recordings", "player", "export"]


class _CurrentReplayStack(QStackedWidget):
    def sizeHint(self):
        current_widget = self.currentWidget()
        if current_widget is None:
            return super().sizeHint()
        return current_widget.sizeHint()

    def minimumSizeHint(self):
        current_widget = self.currentWidget()
        if current_widget is None:
            return super().minimumSizeHint()
        return current_widget.minimumSizeHint()


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
            "先从 recordings 页打开一条 recording，再进入这里查看流预览。",
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


class _ReplayRecordingsPanel(SimpleCardWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.recording_list = ListWidget(self)
        self.recording_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.recording_list.setWordWrap(True)

        self.open_button = PrimaryPushButton("打开所选 recording", self)
        self.open_button.setIcon(FIF.FOLDER)
        self.refresh_button = PushButton("刷新列表", self)
        self.refresh_button.setIcon(FIF.SYNC)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(StrongBodyLabel("Recordings", self))
        layout.addWidget(self.recording_list, 1)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.setSpacing(8)
        button_row.addWidget(self.open_button, 1)
        button_row.addWidget(self.refresh_button)
        layout.addLayout(button_row)

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
            item = QListWidgetItem(f"{title}\n{subtitle}")
            item.setData(Qt.ItemDataRole.UserRole, summary.recording_id)
            item.setData(Qt.ItemDataRole.UserRole + 1, summary.recording_path)
            self.recording_list.addItem(item)
            if summary.recording_id == selected_recording_id:
                self.recording_list.setCurrentItem(item)


class _ReplayRecordingsPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.empty_state = EmptyStateMessage(
            "当前还没有发现 recording",
            "点击“刷新列表”重新扫描 storage.root_dir/recordings。",
            self,
        )
        self.recordings_panel = _ReplayRecordingsPanel(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(self.empty_state)
        layout.addWidget(self.recordings_panel)

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


class _ReplayPlaybackPanel(SimpleCardWidget):
    def __init__(
        self,
        replay: QtReplayBridge,
        settings: QtSettingsBridge,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.status_label = BodyLabel("尚未打开 recording。", self)
        self.status_hint = CaptionLabel("先从 recordings 页打开一条 recording。", self)
        self.playback_progress = ProgressBar(self)
        self.playback_progress.setRange(0, 1000)
        self.playback_progress.setValue(0)
        self.playback_progress.setFormat("00:00.000 / 00:00.000")

        self.play_button = PrimaryPushButton("播放", self)
        self.play_button.setIcon(FIF.PLAY_SOLID)
        self.pause_button = PushButton("暂停", self)
        self.pause_button.setIcon(FIF.PAUSE_BOLD)
        self.stop_button = PushButton("停止", self)
        self.stop_button.setIcon(FIF.STOP_WATCH)

        self.speed_combo = ComboBox(self)
        self.speed_combo.addItem("1x", userData=1.0)
        self.speed_combo.addItem("2x", userData=2.0)
        self.speed_combo.addItem("4x", userData=4.0)

        self.preview_panel = _ReplayPreviewPanel(replay, settings, self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(StrongBodyLabel("回放", self))
        layout.addWidget(self.status_label)
        layout.addWidget(self.status_hint)
        layout.addWidget(self.playback_progress)

        control_row = QHBoxLayout()
        control_row.setContentsMargins(0, 0, 0, 0)
        control_row.setSpacing(8)
        control_row.addWidget(self.play_button)
        control_row.addWidget(self.pause_button)
        control_row.addWidget(self.stop_button)
        control_row.addWidget(BodyLabel("倍速", self))
        control_row.addWidget(self.speed_combo)
        control_row.addStretch(1)
        layout.addLayout(control_row)
        layout.addWidget(self.preview_panel, 1)

    def selected_speed(self) -> float | None:
        value = self.speed_combo.currentData()
        if isinstance(value, (float, int)):
            return float(value)
        return None

    def set_status_hint(self, text: str) -> None:
        self.status_hint.setText(text)

    def apply_snapshot(self, snapshot: ReplaySnapshot, *, export_root_dir: object) -> None:
        recording_id = snapshot.recording_id or "未打开"
        position_text = _format_time_ns(snapshot.position_ns)
        duration_text = _format_time_ns(snapshot.duration_ns)
        self.status_label.setText(
            f"状态：{snapshot.state} · recording：{recording_id} · 位置：{position_text} / {duration_text}"
        )
        self.status_hint.setText(f"导出根目录：{export_root_dir}")
        self.sync_playback_progress(snapshot)
        self.play_button.setEnabled(snapshot.recording_id is not None and snapshot.state != "playing")
        self.pause_button.setEnabled(snapshot.state == "playing")
        self.stop_button.setEnabled(snapshot.recording_id is not None and snapshot.state != "idle")

    def sync_playback_progress(self, snapshot: ReplaySnapshot) -> None:
        duration_ns = max(0, snapshot.duration_ns)
        position_ns = min(max(0, snapshot.position_ns), duration_ns)
        progress = 0 if duration_ns == 0 else int(round(position_ns / duration_ns * 1000))
        self.playback_progress.setValue(progress)
        self.playback_progress.setFormat(
            f"{_format_time_ns(position_ns)} / {_format_time_ns(duration_ns)}"
        )


class _ReplayAnnotationsCard(SimpleCardWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self._markers: tuple[ReplayMarker, ...] = ()
        self._segments: tuple[ReplaySegment, ...] = ()

        self.markers_list = ListWidget(self)
        self.markers_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.markers_list.setWordWrap(True)

        self.segments_list = ListWidget(self)
        self.segments_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.segments_list.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(StrongBodyLabel("Annotations", self))
        layout.addWidget(BodyLabel("Markers", self))
        layout.addWidget(self.markers_list, 1)
        layout.addWidget(BodyLabel("Segments", self))
        layout.addWidget(self.segments_list, 1)

    def reload_annotations(
        self,
        markers: tuple[ReplayMarker, ...],
        segments: tuple[ReplaySegment, ...],
    ) -> None:
        self._markers = markers
        self._segments = segments

        self.markers_list.clear()
        self.segments_list.clear()
        for marker in markers:
            item = QListWidgetItem(f"{_format_time_ns(marker.timestamp_ns)} · {marker.label or '未命名'}")
            item.setData(Qt.ItemDataRole.UserRole, marker.timestamp_ns)
            self.markers_list.addItem(item)
        for segment in segments:
            item = QListWidgetItem(
                f"{_format_time_ns(segment.start_ns)} → {_format_time_ns(segment.end_ns)} · {segment.label or '未命名'}"
            )
            item.setData(Qt.ItemDataRole.UserRole, (segment.start_ns, segment.end_ns))
            self.segments_list.addItem(item)

    def highlight_position(self, position_ns: int) -> None:
        self.markers_list.clearSelection()
        self.segments_list.clearSelection()

        active_marker_index = -1
        for index, marker in enumerate(self._markers):
            if marker.timestamp_ns <= position_ns:
                active_marker_index = index
        if active_marker_index >= 0:
            self.markers_list.setCurrentRow(active_marker_index)
            item = self.markers_list.item(active_marker_index)
            if item is not None:
                item.setSelected(True)

        active_segment_index = -1
        for index, segment in enumerate(self._segments):
            if segment.start_ns <= position_ns <= segment.end_ns:
                active_segment_index = index
                break
        if active_segment_index >= 0:
            self.segments_list.setCurrentRow(active_segment_index)
            item = self.segments_list.item(active_segment_index)
            if item is not None:
                item.setSelected(True)


class _ReplayPlayerPage(QWidget):
    def __init__(
        self,
        replay: QtReplayBridge,
        settings: QtSettingsBridge,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.playback_panel = _ReplayPlaybackPanel(replay, settings, self)
        self.annotations_card = _ReplayAnnotationsCard(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(self.playback_panel)
        layout.addWidget(self.annotations_card)

    @property
    def status_label(self) -> BodyLabel:
        return self.playback_panel.status_label

    @property
    def status_hint(self) -> CaptionLabel:
        return self.playback_panel.status_hint

    @property
    def playback_progress(self) -> ProgressBar:
        return self.playback_panel.playback_progress

    @property
    def play_button(self) -> PrimaryPushButton:
        return self.playback_panel.play_button

    @property
    def pause_button(self) -> PushButton:
        return self.playback_panel.pause_button

    @property
    def stop_button(self) -> PushButton:
        return self.playback_panel.stop_button

    @property
    def speed_combo(self) -> ComboBox:
        return self.playback_panel.speed_combo

    @property
    def preview_panel(self) -> _ReplayPreviewPanel:
        return self.playback_panel.preview_panel

    @property
    def markers_list(self) -> ListWidget:
        return self.annotations_card.markers_list

    @property
    def segments_list(self) -> ListWidget:
        return self.annotations_card.segments_list

    def selected_speed(self) -> float | None:
        return self.playback_panel.selected_speed()

    def set_status_hint(self, text: str) -> None:
        self.playback_panel.set_status_hint(text)

    def apply_snapshot(self, snapshot: ReplaySnapshot, *, export_root_dir: object) -> None:
        self.playback_panel.apply_snapshot(snapshot, export_root_dir=export_root_dir)
        self.annotations_card.highlight_position(snapshot.position_ns)

    def reload_annotations(
        self,
        markers: tuple[ReplayMarker, ...],
        segments: tuple[ReplaySegment, ...],
        snapshot: ReplaySnapshot,
    ) -> None:
        self.annotations_card.reload_annotations(markers, segments)
        self.annotations_card.highlight_position(snapshot.position_ns)


class _ReplayExportSummaryCard(SimpleCardWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.status_label = BodyLabel("尚未打开 recording。", self)
        self.status_hint = CaptionLabel("先从 recordings 页打开一条 recording，再进入导出。", self)
        self.status_hint.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)
        layout.addWidget(StrongBodyLabel("导出上下文", self))
        layout.addWidget(self.status_label)
        layout.addWidget(self.status_hint)

    def apply_snapshot(self, snapshot: ReplaySnapshot, *, export_root_dir: object) -> None:
        if snapshot.recording_id is None:
            self.status_label.setText("尚未打开 recording。")
            self.status_hint.setText(
                f"先回到 recordings 页打开一条 recording。导出根目录：{export_root_dir}"
            )
            return

        self.status_label.setText(
            f"当前 recording：{snapshot.recording_id} · 状态：{snapshot.state}"
        )
        self.status_hint.setText(
            f"recording_path：{snapshot.recording_path} · 导出根目录：{export_root_dir}"
        )

    def set_status_hint(self, text: str) -> None:
        self.status_hint.setText(text)


class _ReplayExportCard(SimpleCardWidget):
    def __init__(self, export_root_dir: object, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.export_format_combo = ComboBox(self)
        for format_id, label in _EXPORT_LABELS.items():
            self.export_format_combo.addItem(label, userData=format_id)

        self.export_button = PrimaryPushButton("开始导出", self)
        self.export_button.setIcon(FIF.SAVE)
        self.export_hint = CaptionLabel("", self)
        self.set_export_root_dir(export_root_dir)

        self.export_progress = ProgressBar(self)
        self.export_progress.setRange(0, 1000)
        self.export_progress.setValue(0)
        self.export_progress.setFormat("尚未开始导出")

        self.jobs_list = ListWidget(self)
        self.jobs_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.jobs_list.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(StrongBodyLabel("Export", self))
        layout.addWidget(self.export_format_combo)
        layout.addWidget(self.export_button)
        layout.addWidget(self.export_hint)
        layout.addWidget(self.export_progress)
        layout.addWidget(BodyLabel("Jobs", self))
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
                f"{_EXPORT_LABELS.get(job.format_id, job.format_id)} · {job.state} · {int(job.progress * 100)}%{output_text}{error_text}"
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
            f"{_EXPORT_LABELS.get(latest_job.format_id, latest_job.format_id)} · {latest_job.state} · {int(latest_job.progress * 100)}%"
        )


class _ReplayExportPage(QWidget):
    def __init__(self, export_root_dir: object, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.empty_state = EmptyStateMessage(
            "还没有可导出的 recording",
            "先回到 recordings 页打开一条 recording，再开始导出。",
            self,
        )
        self.summary_card = _ReplayExportSummaryCard(self)
        self.export_card = _ReplayExportCard(export_root_dir, self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(self.empty_state)
        layout.addWidget(self.summary_card)
        layout.addWidget(self.export_card)

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
        self.summary_card.set_status_hint(text)

    def apply_snapshot(self, snapshot: ReplaySnapshot, *, export_root_dir: object) -> None:
        self.summary_card.apply_snapshot(snapshot, export_root_dir=export_root_dir)
        self.export_card.set_export_root_dir(export_root_dir)
        self.export_card.set_export_enabled(snapshot.recording_id is not None)
        self.empty_state.setVisible(snapshot.recording_id is None)

    def reload_jobs(self, jobs: tuple[ExportJobSnapshot, ...]) -> None:
        self.export_card.reload_jobs(jobs)


class ReplayPage(BasePage):
    def __init__(self, engine: QtModLinkBridge, parent: QWidget | None = None) -> None:
        super().__init__(
            page_key="replay-page",
            title="回放 recordings",
            description="浏览已有 recordings，打开其中一条进入单独的回放页或导出页。",
            parent=parent,
        )
        self.engine = engine
        self._replay = engine.replay
        self._route: ReplayRoute = "recordings"
        self._pending_open_recording_path: str | None = None

        self._recordings_route_button = PushButton("Recordings", self)
        self._recordings_route_button.clicked.connect(self._show_recordings_page)
        self._player_route_button = PushButton("回放", self)
        self._player_route_button.clicked.connect(self._show_player_page)
        self._export_route_button = PushButton("导出", self)
        self._export_route_button.clicked.connect(self._show_export_page)
        self.header_action_layout.addWidget(self._recordings_route_button)
        self.header_action_layout.addWidget(self._player_route_button)
        self.header_action_layout.addWidget(self._export_route_button)

        self._page_stack = _CurrentReplayStack(self.scroll_widget)
        self._recordings_page = _ReplayRecordingsPage(self._page_stack)
        self._player_page = _ReplayPlayerPage(self._replay, self.engine.settings, self._page_stack)
        self._export_page = _ReplayExportPage(self._replay.export_root_dir, self._page_stack)
        self._page_stack.addWidget(self._recordings_page)
        self._page_stack.addWidget(self._player_page)
        self._page_stack.addWidget(self._export_page)
        self.content_layout.addWidget(self._page_stack)

        self._recording_list = self._recordings_page.recording_list
        self._open_button = self._recordings_page.open_button
        self._refresh_button = self._recordings_page.refresh_button
        self._status_label = self._player_page.status_label
        self._status_hint = self._player_page.status_hint
        self._playback_progress = self._player_page.playback_progress
        self._play_button = self._player_page.play_button
        self._pause_button = self._player_page.pause_button
        self._stop_button = self._player_page.stop_button
        self._speed_combo = self._player_page.speed_combo
        self._preview_panel = self._player_page.preview_panel
        self._markers_list = self._player_page.markers_list
        self._segments_list = self._player_page.segments_list
        self._export_format_combo = self._export_page.export_format_combo
        self._export_button = self._export_page.export_button
        self._export_hint = self._export_page.export_hint
        self._export_progress = self._export_page.export_progress
        self._jobs_list = self._export_page.jobs_list

        self._recording_list.itemDoubleClicked.connect(lambda _item: self._open_selected_recording())
        self._open_button.clicked.connect(self._open_selected_recording)
        self._refresh_button.clicked.connect(self._replay.refresh_recordings)
        self._play_button.clicked.connect(self._replay.play)
        self._pause_button.clicked.connect(self._replay.pause)
        self._stop_button.clicked.connect(self._replay.stop)
        self._speed_combo.currentIndexChanged.connect(self._on_speed_changed)
        self._export_button.clicked.connect(self._start_export)

        self._replay.sig_recordings_changed.connect(self._reload_recordings)
        self._replay.sig_snapshot_changed.connect(self._on_snapshot_changed)
        self._replay.sig_annotations_changed.connect(self._reload_annotations)
        self._replay.sig_export_jobs_changed.connect(self._reload_export_jobs)
        self._replay.sig_error.connect(self._on_error)

        self._reload_recordings()
        self._on_snapshot_changed(self._replay.snapshot())
        self._reload_annotations()
        self._reload_export_jobs()
        self._set_route("recordings")
        self._replay.refresh_recordings()

    def _current_snapshot(self) -> ReplaySnapshot:
        snapshot = self._replay.snapshot()
        if isinstance(snapshot, ReplaySnapshot):
            return snapshot
        return ReplaySnapshot(
            state="idle",
            is_started=False,
            recording_id=None,
            recording_path=None,
            position_ns=0,
            duration_ns=0,
            speed_multiplier=1.0,
        )

    def _set_route(self, route: ReplayRoute) -> None:
        snapshot = self._current_snapshot()
        if route in {"player", "export"} and snapshot.recording_id is None:
            route = "recordings"

        self._route = route
        if route == "recordings":
            self._page_stack.setCurrentWidget(self._recordings_page)
        elif route == "player":
            self._page_stack.setCurrentWidget(self._player_page)
        else:
            self._page_stack.setCurrentWidget(self._export_page)

        self._sync_header(snapshot)
        self._page_stack.updateGeometry()
        self.scroll_widget.updateGeometry()

    def _show_recordings_page(self) -> None:
        self._set_route("recordings")

    def _show_player_page(self) -> None:
        self._set_route("player")

    def _show_export_page(self) -> None:
        self._set_route("export")

    def _sync_header(self, snapshot: ReplaySnapshot) -> None:
        if self._route == "recordings":
            self.title_label.setText("回放 recordings")
            self.description_label.setText(
                "浏览已有 recordings，打开其中一条进入单独的回放页或导出页。"
            )
        elif self._route == "player":
            recording_id = snapshot.recording_id or "未打开"
            self.title_label.setText("Recording 回放")
            self.description_label.setText(
                f"当前查看 {recording_id}，在这里完成播放和 annotations 复盘。"
            )
        else:
            recording_id = snapshot.recording_id or "未打开"
            self.title_label.setText("Recording 导出")
            self.description_label.setText(
                f"当前 recording：{recording_id}。导出配置和 jobs 单独放在这一页。"
            )

        has_recording = snapshot.recording_id is not None
        self._recordings_route_button.setVisible(self._route != "recordings")
        self._player_route_button.setVisible(self._route != "player" and has_recording)
        self._player_route_button.setEnabled(has_recording)
        self._export_route_button.setVisible(self._route != "export" and has_recording)
        self._export_route_button.setEnabled(has_recording)

    def _reload_recordings(self) -> None:
        self._recordings_page.reload_recordings(self._replay.recordings())

    def _reload_annotations(self) -> None:
        self._player_page.reload_annotations(
            self._replay.markers(),
            self._replay.segments(),
            self._current_snapshot(),
        )

    def _reload_export_jobs(self) -> None:
        self._export_page.reload_jobs(self._replay.export_jobs())

    def _open_selected_recording(self) -> None:
        recording_path = self._recordings_page.selected_recording_path()
        if recording_path is None:
            return
        self._pending_open_recording_path = recording_path
        self._replay.open_recording(recording_path)

    def _on_snapshot_changed(self, snapshot: object) -> None:
        if not isinstance(snapshot, ReplaySnapshot):
            snapshot = self._current_snapshot()

        self._player_page.apply_snapshot(snapshot, export_root_dir=self._replay.export_root_dir)
        self._export_page.apply_snapshot(snapshot, export_root_dir=self._replay.export_root_dir)
        self._sync_header(snapshot)

        if self._pending_open_recording_path is None:
            return

        recording_path = str(snapshot.recording_path or "").strip()
        if not recording_path:
            return

        if Path(recording_path) != Path(self._pending_open_recording_path):
            return

        self._pending_open_recording_path = None
        self._set_route("player")

    def _on_speed_changed(self) -> None:
        value = self._player_page.selected_speed()
        if value is not None:
            self._replay.set_speed(value)

    def _start_export(self) -> None:
        format_id = self._export_page.selected_format_id()
        if format_id is not None:
            self._replay.start_export(format_id)

    def _on_error(self, message: str) -> None:
        if self._pending_open_recording_path is not None:
            self._pending_open_recording_path = None
        self._player_page.set_status_hint(message)
        self._export_page.set_status_hint(message)
        parent = self.window() if isinstance(self.window(), QWidget) else self
        InfoBar.error(
            title="回放错误",
            content=message,
            duration=4500,
            position=InfoBarPosition.TOP_RIGHT,
            parent=parent,
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
