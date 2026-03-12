from __future__ import annotations

import time

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    CaptionLabel,
    ComboBox,
    FluentIcon as FIF,
    LineEdit,
    PrimaryPushButton,
    PushButton,
)

from ....backend import DeviceState
from ...style_constants import DEFAULT_RADIUS


class FieldBlock(QWidget):
    def __init__(
        self,
        title: str,
        widget: QWidget,
        hint: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.title_label = CaptionLabel(title, self)
        self.hint_label = CaptionLabel(hint, self)
        self.field_widget = widget

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.title_label)
        layout.addWidget(self.field_widget)
        if hint:
            layout.addWidget(self.hint_label)

        self.title_label.setStyleSheet("color: rgba(0, 0, 0, 0.72);")
        self.hint_label.setStyleSheet("color: rgba(0, 0, 0, 0.52);")
        self.hint_label.setVisible(bool(hint))


class BaseAcquisitionControlBar(QFrame):
    startRecordRequested = pyqtSignal(str)
    stopRecordRequested = pyqtSignal()
    displayPauseChanged = pyqtSignal(bool)

    def __init__(
        self,
        labels: list[str] | tuple[str, ...],
        object_name: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.available_labels = list(labels)
        self.current_state = DeviceState.DISCONNECTED
        self.recording_enabled = False
        self.display_paused = False

        self.setObjectName(object_name)
        self.setStyleSheet(
            f"""
            QFrame#{object_name} {{
                background: rgba(255, 255, 255, 0.78);
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: {DEFAULT_RADIUS}px;
            }}
            """
        )

        self.control_layout = QVBoxLayout(self)
        self.control_layout.setContentsMargins(18, 16, 18, 16)
        self.control_layout.setSpacing(12)

        self.form_row = QHBoxLayout()
        self.form_row.setContentsMargins(0, 0, 0, 0)
        self.form_row.setSpacing(14)

        self.action_row = QHBoxLayout()
        self.action_row.setContentsMargins(0, 0, 0, 0)
        self.action_row.setSpacing(14)

        self.subject_input = LineEdit(self)
        self.subject_input.setPlaceholderText("例如 S01，留空则自动生成")
        self.subject_input.setClearButtonEnabled(True)
        self.subject_input.setMinimumWidth(220)
        self.subject_input.setFixedHeight(36)

        self.label_selector = ComboBox(self)
        self.label_selector.setMinimumWidth(150)
        self.label_selector.setFixedHeight(36)
        self.set_available_labels(self.available_labels)

        self.record_button = PrimaryPushButton("开始录制", self)
        self.record_button.setMinimumWidth(152)
        self.record_button.setFixedHeight(36)
        self.record_button.clicked.connect(self._toggle_recording)

        self.pause_button = PushButton("暂停显示", self)
        self.pause_button.setMinimumWidth(124)
        self.pause_button.setFixedHeight(36)
        self.pause_button.setIcon(FIF.PAUSE_BOLD)
        self.pause_button.clicked.connect(self._toggle_display_pause)

        self.subject_block = FieldBlock("受试编号", self.subject_input, parent=self)
        self.label_block = FieldBlock("标签 / Label", self.label_selector, parent=self)

        self.form_row.addWidget(self.subject_block, 3)
        self.form_row.addWidget(self.label_block, 2)

        self.control_layout.addLayout(self.form_row)
        self.control_layout.addLayout(self.action_row)

    def set_state(self, state: DeviceState) -> None:
        self.current_state = state
        if state not in {DeviceState.PREVIEWING, DeviceState.RECORDING}:
            self.set_display_paused(False)
        self._sync_buttons()

    def set_recording_enabled(self, is_recording: bool) -> None:
        self.recording_enabled = is_recording
        self._sync_buttons()

    def set_available_labels(
        self,
        labels: list[str] | tuple[str, ...],
        preferred_label: str | None = None,
    ) -> None:
        current = preferred_label or self.current_label(fallback="")
        self.available_labels = list(labels) or ["default_label"]

        self.label_selector.blockSignals(True)
        self.label_selector.clear()
        self.label_selector.addItems(self.available_labels)

        target = current if current in self.available_labels else self.available_labels[0]
        self.label_selector.setCurrentText(target)
        self.label_selector.blockSignals(False)

    def set_current_label(self, label: str) -> None:
        target = label.strip()
        if target and target not in self.available_labels:
            return
        if not target and self.available_labels:
            target = self.available_labels[0]
        if self.label_selector.currentText() == target:
            return
        self.label_selector.setCurrentText(target)

    def current_label(self, fallback: str = "default_label") -> str:
        text = self.label_selector.currentText().strip()
        return text or fallback

    def set_subject_id(self, subject_id: str) -> None:
        self.subject_input.setText(subject_id.strip())

    def current_subject_id(self, fallback: str = "") -> str:
        text = self.subject_input.text().strip()
        return text or fallback

    def set_display_paused(self, is_paused: bool) -> None:
        if self.display_paused == is_paused:
            return

        self.display_paused = is_paused
        self._sync_buttons()
        self.displayPauseChanged.emit(is_paused)

    def make_session_id(self) -> str:
        return time.strftime("%Y%m%d_%H%M%S")

    def sync_from(self, other: "BaseAcquisitionControlBar") -> None:
        self.set_subject_id(other.current_subject_id(fallback=""))
        self.set_available_labels(
            other.available_labels,
            preferred_label=other.current_label(fallback=""),
        )
        self.set_display_paused(other.display_paused)

    def _toggle_recording(self) -> None:
        if self.recording_enabled:
            self.stopRecordRequested.emit()
            return

        self.startRecordRequested.emit(self.current_subject_id(fallback=""))

    def _toggle_display_pause(self) -> None:
        self.set_display_paused(not self.display_paused)

    def _sync_buttons(self) -> None:
        can_record = self.current_state in {DeviceState.PREVIEWING, DeviceState.RECORDING}
        can_pause = self.current_state in {DeviceState.PREVIEWING, DeviceState.RECORDING}

        self.record_button.setEnabled(can_record)
        self.pause_button.setEnabled(can_pause or self.display_paused)

        if self.display_paused:
            self.pause_button.setText("继续显示")
            self.pause_button.setIcon(FIF.PLAY_SOLID)
        else:
            self.pause_button.setText("暂停显示")
            self.pause_button.setIcon(FIF.PAUSE_BOLD)

        if self.recording_enabled:
            self.record_button.setText("结束录制")
            self.record_button.setIcon(FIF.PAUSE_BOLD)
        elif self.current_state == DeviceState.CONNECTING:
            self.record_button.setText("连接中")
            self.record_button.setIcon(FIF.SYNC)
        elif self.current_state in {
            DeviceState.DISCONNECTED,
            DeviceState.DISCONNECTING,
            DeviceState.ERROR,
        }:
            self.record_button.setText("等待连接")
            self.record_button.setIcon(FIF.PLAY_SOLID)
        else:
            self.record_button.setText("开始录制")
            self.record_button.setIcon(FIF.PLAY_SOLID)

        self._sync_action_buttons()

    def _sync_action_buttons(self) -> None:
        raise NotImplementedError


class ClipAcquisitionControlBar(BaseAcquisitionControlBar):
    markerRequested = pyqtSignal(str)

    def __init__(
        self,
        labels: list[str] | tuple[str, ...],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(labels, "clip-acquisition-control-bar", parent=parent)

        self.marker_input = LineEdit(self)
        self.marker_input.setPlaceholderText("输入临时 Marker 文本，留空时使用当前标签")
        self.marker_input.setClearButtonEnabled(True)
        self.marker_input.setFixedHeight(36)

        self.marker_button = PushButton("插入 Marker", self)
        self.marker_button.setMinimumWidth(132)
        self.marker_button.setFixedHeight(36)
        self.marker_button.setIcon(FIF.TAG)
        self.marker_button.clicked.connect(self._insert_marker)

        button_group = QWidget(self)
        button_group_layout = QHBoxLayout(button_group)
        button_group_layout.setContentsMargins(0, 0, 0, 0)
        button_group_layout.setSpacing(10)
        button_group_layout.addWidget(self.marker_button)
        button_group_layout.addWidget(self.pause_button)
        button_group_layout.addWidget(self.record_button)

        marker_block = FieldBlock("Marker", self.marker_input, parent=self)
        self.action_row.addWidget(marker_block, 1)
        self.action_row.addWidget(button_group, 0, Qt.AlignmentFlag.AlignBottom)
        self._sync_buttons()

    def current_marker_label(self) -> str:
        return self.marker_input.text().strip() or self.current_label()

    def sync_from(self, other: BaseAcquisitionControlBar) -> None:
        super().sync_from(other)
        if isinstance(other, ClipAcquisitionControlBar):
            self.marker_input.setText(other.marker_input.text())

    def _insert_marker(self) -> None:
        if self.current_state != DeviceState.RECORDING:
            return
        self.markerRequested.emit(self.current_marker_label())

    def _sync_action_buttons(self) -> None:
        self.marker_button.setEnabled(self.current_state == DeviceState.RECORDING)


class ContinuousAcquisitionControlBar(BaseAcquisitionControlBar):
    startSegmentRequested = pyqtSignal(str, str)
    stopSegmentRequested = pyqtSignal(str)

    def __init__(
        self,
        labels: list[str] | tuple[str, ...],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(labels, "continuous-acquisition-control-bar", parent=parent)
        self.segment_active = False
        self.active_segment_label = ""
        self.form_row.removeWidget(self.label_block)
        self.label_block.setParent(None)

        self.segment_button = PushButton("开始片段", self)
        self.segment_button.setFixedWidth(152)
        self.segment_button.setFixedHeight(36)
        self.segment_button.setIcon(FIF.TAG)
        self.segment_button.clicked.connect(self._toggle_segment)

        button_group = QWidget(self)
        button_group_layout = QHBoxLayout(button_group)
        button_group_layout.setContentsMargins(0, 0, 0, 0)
        button_group_layout.setSpacing(10)
        button_group_layout.addWidget(self.segment_button)
        button_group_layout.addWidget(self.pause_button)
        button_group_layout.addWidget(self.record_button)

        segment_block = FieldBlock("片段 Label", self.label_selector, parent=self)
        self.action_row.addWidget(segment_block, 1)
        self.action_row.addWidget(button_group, 0, Qt.AlignmentFlag.AlignBottom)
        self._sync_buttons()

    def set_segment_active(self, is_active: bool, label: str = "") -> None:
        self.segment_active = is_active
        self.active_segment_label = label.strip()
        self.label_selector.setEnabled(not is_active)
        self._sync_buttons()

    def sync_from(self, other: BaseAcquisitionControlBar) -> None:
        super().sync_from(other)
        if isinstance(other, ContinuousAcquisitionControlBar):
            self.set_segment_active(other.segment_active, other.active_segment_label)
        else:
            self.set_segment_active(False)

    def _toggle_segment(self) -> None:
        if self.current_state != DeviceState.RECORDING:
            return
        if self.segment_active:
            self.stopSegmentRequested.emit("")
            return
        self.startSegmentRequested.emit(
            self.current_label(),
            "",
        )

    def _sync_action_buttons(self) -> None:
        can_segment = self.current_state == DeviceState.RECORDING
        self.segment_button.setEnabled(can_segment)
        if self.segment_active:
            self.segment_button.setText("结束 Label")
            self.segment_button.setIcon(FIF.TAG)
        else:
            self.segment_button.setText("开始 Label")
            self.segment_button.setIcon(FIF.TAG)


AcquisitionControlBar = ClipAcquisitionControlBar

__all__ = [
    "AcquisitionControlBar",
    "BaseAcquisitionControlBar",
    "ClipAcquisitionControlBar",
    "ContinuousAcquisitionControlBar",
]
