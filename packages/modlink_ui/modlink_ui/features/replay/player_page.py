from __future__ import annotations

from PyQt6.QtCore import QEvent, QObject, QPoint, Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    ComboBox,
    PrimaryPushButton,
    PushButton,
    SimpleCardWidget,
)
from qfluentwidgets import (
    FluentIcon as FIF,
)

from modlink_core.models import ReplayMarker, ReplaySegment, ReplaySnapshot
from modlink_sdk import FrameEnvelope
from modlink_ui.bridge import QtReplayBridge, QtSettingsBridge
from modlink_ui.shared import BasePage, EmptyStateMessage
from modlink_ui.shared.preview.cards import DetachableStreamPreviewCard

from .timeline import ReplayAnnotationTimeline, format_time_ns


class ReplayPreviewPanel(QWidget):
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
        self.setObjectName("replay-preview-panel")
        self.setMinimumHeight(320)
        self.empty_state = EmptyStateMessage(
            "当前还没有打开 recording",
            "先从 recordings 页打开一条 recording，再进入这里查看流预览。",
            self,
        )
        self.empty_state_container = QWidget(self)
        empty_layout = QVBoxLayout(self.empty_state_container)
        empty_layout.setContentsMargins(0, 0, 0, 0)
        empty_layout.addStretch(1)
        empty_layout.addWidget(self.empty_state, 0, Qt.AlignmentFlag.AlignCenter)
        empty_layout.addStretch(1)
        self.cards_container = QWidget(self)
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(14)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.empty_state_container, 1)
        layout.addWidget(self.cards_container, 1)

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
        self.empty_state_container.setVisible(not has_cards)
        self.cards_container.setVisible(has_cards)


def can_reset_replay(snapshot: ReplaySnapshot) -> bool:
    return snapshot.recording_id is not None and (
        snapshot.state in {"paused", "finished"}
        or (snapshot.state == "ready" and snapshot.position_ns > 0)
    )


class ReplayPlaybackPanel(QWidget):
    def __init__(
        self,
        replay: QtReplayBridge,
        settings: QtSettingsBridge,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.position_badge = CaptionLabel("00:00.000 / 00:00.000", self)
        self.position_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.position_badge.setMinimumWidth(180)
        self.timeline = ReplayAnnotationTimeline(self)

        self.play_button = PrimaryPushButton("播放", self)
        self.play_button.setIcon(FIF.PLAY_SOLID)
        self.play_button.setToolTip("播放")
        self.play_button.setAccessibleName("播放")
        self.pause_reset_button = PushButton("复位", self)
        self.pause_reset_button.setIcon(FIF.SYNC)
        self.pause_reset_button.setToolTip("复位")
        self.pause_reset_button.setAccessibleName("复位")
        self.speed_label = BodyLabel("倍速", self)

        self.speed_combo = ComboBox(self)
        self.speed_combo.addItem("1x", userData=1.0)
        self.speed_combo.addItem("2x", userData=2.0)
        self.speed_combo.addItem("4x", userData=4.0)

        self.preview_panel = ReplayPreviewPanel(replay, settings, self)
        self.preview_panel.setMinimumHeight(360)

        self.transport_bar = SimpleCardWidget(self)
        self.transport_bar.setObjectName("replay-transport-bar")
        self.transport_bar.setBorderRadius(18)
        self.transport_bar.hide()
        transport_layout = QVBoxLayout(self.transport_bar)
        transport_layout.setContentsMargins(18, 18, 18, 18)
        transport_layout.setSpacing(8)
        transport_layout.addWidget(self.timeline)

        controls_row = QHBoxLayout()
        controls_row.setContentsMargins(0, 0, 0, 0)
        controls_row.setSpacing(8)
        controls_row.addWidget(self.play_button)
        controls_row.addWidget(self.pause_reset_button)
        controls_row.addSpacing(6)
        controls_row.addWidget(self.speed_label)
        controls_row.addWidget(self.speed_combo)
        controls_row.addStretch(1)
        controls_row.addWidget(self.position_badge)
        transport_layout.addLayout(controls_row)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.preview_panel, 1)

    def selected_speed(self) -> float | None:
        value = self.speed_combo.currentData()
        if isinstance(value, (float, int)):
            return float(value)
        return None

    def apply_snapshot(self, snapshot: ReplaySnapshot) -> None:
        self.sync_playback_progress(snapshot)
        self.play_button.setEnabled(
            snapshot.recording_id is not None and snapshot.state != "playing"
        )
        if snapshot.state == "playing":
            self.pause_reset_button.setIcon(FIF.PAUSE_BOLD)
            self.pause_reset_button.setText("暂停")
            self.pause_reset_button.setToolTip("暂停")
            self.pause_reset_button.setAccessibleName("暂停")
        else:
            self.pause_reset_button.setIcon(FIF.SYNC)
            self.pause_reset_button.setText("复位")
            self.pause_reset_button.setToolTip("复位")
            self.pause_reset_button.setAccessibleName("复位")
        self.pause_reset_button.setEnabled(
            snapshot.state == "playing" or can_reset_replay(snapshot)
        )

    def set_annotations(
        self,
        markers: tuple[ReplayMarker, ...],
        segments: tuple[ReplaySegment, ...],
    ) -> None:
        self.timeline.set_annotations(markers, segments)

    def sync_playback_progress(self, snapshot: ReplaySnapshot) -> None:
        duration_ns = max(0, snapshot.duration_ns)
        position_ns = min(max(0, snapshot.position_ns), duration_ns)
        progress_text = f"{format_time_ns(position_ns)} / {format_time_ns(duration_ns)}"
        self.position_badge.setText(progress_text)
        self.timeline.set_playback(position_ns, duration_ns)

class ReplayPlayerPage(BasePage):
    sig_show_recordings_requested = pyqtSignal()
    sig_show_export_requested = pyqtSignal()
    sig_play_requested = pyqtSignal()
    sig_pause_requested = pyqtSignal()
    sig_reset_requested = pyqtSignal()
    sig_speed_changed = pyqtSignal(float)

    def __init__(
        self,
        replay: QtReplayBridge,
        settings: QtSettingsBridge,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            page_key="replay-player-page",
            title="回放",
            description="打开一条 recording 后，在这里预览流、浏览标注并控制播放。",
            parent=parent,
        )
        self.playback_panel = ReplayPlaybackPanel(replay, settings, self.scroll_widget)
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
        self.export_route_button = PushButton("导出", self)
        self.export_route_button.setIcon(FIF.SAVE)
        for button in (self.recordings_route_button, self.export_route_button):
            button.setMinimumWidth(88)
            self.header_action_layout.addWidget(button)

        self.content_layout.addWidget(self.playback_panel)
        self._floating_panel_spacer = QWidget(self.scroll_widget)
        self._floating_panel_spacer.setFixedHeight(0)
        self.content_layout.addWidget(self._floating_panel_spacer)

        self.transport_bar.setParent(self)
        self.transport_bar.hide()
        self.transport_bar.raise_()
        self.scroll_area.viewport().installEventFilter(self)
        self.transport_bar.installEventFilter(self)

        self.play_button.clicked.connect(self.sig_play_requested.emit)
        self.pause_reset_button.clicked.connect(self._emit_pause_or_reset)
        self.speed_combo.currentIndexChanged.connect(self._emit_speed_changed)
        self.recordings_route_button.clicked.connect(self.sig_show_recordings_requested.emit)
        self.export_route_button.clicked.connect(self.sig_show_export_requested.emit)

    @property
    def play_button(self) -> PrimaryPushButton:
        return self.playback_panel.play_button

    @property
    def pause_reset_button(self) -> PushButton:
        return self.playback_panel.pause_reset_button

    @property
    def speed_combo(self) -> ComboBox:
        return self.playback_panel.speed_combo

    @property
    def preview_panel(self) -> ReplayPreviewPanel:
        return self.playback_panel.preview_panel

    @property
    def timeline(self) -> ReplayAnnotationTimeline:
        return self.playback_panel.timeline

    @property
    def transport_bar(self) -> SimpleCardWidget:
        return self.playback_panel.transport_bar

    def selected_speed(self) -> float | None:
        return self.playback_panel.selected_speed()

    def apply_snapshot(self, snapshot: ReplaySnapshot) -> None:
        self._snapshot = snapshot
        self.playback_panel.apply_snapshot(snapshot)
        self.export_route_button.setEnabled(snapshot.recording_id is not None)
        self._sync_header(snapshot)
        self._sync_floating_transport_bar()

    def reload_annotations(
        self,
        markers: tuple[ReplayMarker, ...],
        segments: tuple[ReplaySegment, ...],
        snapshot: ReplaySnapshot,
    ) -> None:
        self.playback_panel.set_annotations(markers, segments)
        self.playback_panel.sync_playback_progress(snapshot)
        self._sync_floating_transport_bar()

    def _emit_pause_or_reset(self) -> None:
        if self._snapshot.state == "playing":
            self.sig_pause_requested.emit()
            return
        if can_reset_replay(self._snapshot):
            self.sig_reset_requested.emit()

    def _emit_speed_changed(self) -> None:
        value = self.selected_speed()
        if value is not None:
            self.sig_speed_changed.emit(value)

    def _sync_header(self, snapshot: ReplaySnapshot) -> None:
        recording_id = _format_recording_badge(snapshot.recording_id)
        self.title_label.setText("回放")
        self.description_label.setText(
            f"当前 recording：{recording_id} · 预览流、浏览标注并控制播放。"
        )

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched in {self.scroll_area.viewport(), self.transport_bar} and event.type() in {
            QEvent.Type.Resize,
            QEvent.Type.Show,
            QEvent.Type.Hide,
            QEvent.Type.LayoutRequest,
        }:
            QTimer.singleShot(0, self._sync_floating_transport_bar)
        return super().eventFilter(watched, event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._sync_floating_transport_bar()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        QTimer.singleShot(0, self._sync_floating_transport_bar)

    def hideEvent(self, event) -> None:
        self.transport_bar.hide()
        super().hideEvent(event)

    def _sync_floating_transport_bar(self) -> None:
        viewport = self.scroll_area.viewport()
        if not self.isVisible() or not viewport.isVisible():
            self.transport_bar.hide()
            return

        panel_height = max(
            self.transport_bar.minimumSizeHint().height(),
            self.transport_bar.sizeHint().height(),
        )
        reserve_height = panel_height + 24
        if self._floating_panel_spacer.height() != reserve_height:
            self._floating_panel_spacer.setFixedHeight(reserve_height)

        viewport_top_left = viewport.mapTo(self, QPoint(0, 0))
        side_margin = 16
        bottom_margin = 12
        max_panel_width = 1160
        panel_width = min(
            max_panel_width,
            max(420, viewport.width() - side_margin * 2),
        )
        panel_x = viewport_top_left.x() + max(0, (viewport.width() - panel_width) // 2)
        panel_y = viewport_top_left.y() + viewport.height() - panel_height - bottom_margin

        self.transport_bar.setGeometry(
            panel_x,
            panel_y,
            panel_width,
            panel_height,
        )
        if not self.transport_bar.isVisible():
            self.transport_bar.show()
        self.transport_bar.raise_()


def _format_recording_badge(recording_id: str | None) -> str:
    if recording_id is None or not str(recording_id).strip():
        return "未打开 recording"
    normalized = str(recording_id).strip()
    if len(normalized) <= 26:
        return normalized
    return f"{normalized[:14]}...{normalized[-8:]}"


__all__ = ["ReplayPlayerPage", "can_reset_replay"]
