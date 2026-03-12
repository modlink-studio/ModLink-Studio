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

from ...backend import DeviceState
from ..style_constants import DEFAULT_RADIUS


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


class AcquisitionControlBar(QFrame):
    startRecordRequested = pyqtSignal(str, str)
    stopRecordRequested = pyqtSignal()
    markerRequested = pyqtSignal(str)
    displayPauseChanged = pyqtSignal(bool)

    def __init__(
        self,
        labels: list[str] | tuple[str, ...],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.available_labels = list(labels)
        self.current_state = DeviceState.DISCONNECTED
        self.recording_enabled = False
        self.display_paused = False

        self.setObjectName("acquisition-control-bar")
        self.setStyleSheet(
            f"""
            QFrame#acquisition-control-bar {{
                background: rgba(255, 255, 255, 0.78);
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: {DEFAULT_RADIUS}px;
            }}
            """
        )

        control_layout = QVBoxLayout(self)
        control_layout.setContentsMargins(18, 16, 18, 16)
        control_layout.setSpacing(12)

        form_row = QHBoxLayout()
        form_row.setContentsMargins(0, 0, 0, 0)
        form_row.setSpacing(14)

        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 0, 0, 0)
        action_row.setSpacing(14)

        self.subject_input = LineEdit(self)
        self.subject_input.setPlaceholderText("例如 S01，留空则自动生成")
        self.subject_input.setClearButtonEnabled(True)
        self.subject_input.setMinimumWidth(260)
        self.subject_input.setMinimumHeight(36)
        self.subject_input.setMaximumHeight(36)

        self.label_selector = ComboBox(self)
        self.label_selector.setMinimumWidth(220)
        self.label_selector.setMinimumHeight(36)
        self.label_selector.setMaximumHeight(36)
        self.set_available_labels(self.available_labels)

        self.record_button = PrimaryPushButton("开始录制", self)
        self.record_button.setMinimumWidth(152)
        self.record_button.setFixedHeight(36)
        self.record_button.clicked.connect(self._toggle_recording)

        self.marker_button = PushButton("插入 Marker", self)
        self.marker_button.setMinimumWidth(132)
        self.marker_button.setFixedHeight(36)
        self.marker_button.setIcon(FIF.TAG)
        self.marker_button.clicked.connect(self._insert_marker)

        self.pause_button = PushButton("暂停显示", self)
        self.pause_button.setMinimumWidth(124)
        self.pause_button.setFixedHeight(36)
        self.pause_button.setIcon(FIF.PAUSE_BOLD)
        self.pause_button.clicked.connect(self._toggle_display_pause)

        self.custom_marker_input = LineEdit(self)
        self.custom_marker_input.setPlaceholderText("输入临时 Marker 文本，留空时使用当前标签")
        self.custom_marker_input.setClearButtonEnabled(True)
        self.custom_marker_input.setMinimumHeight(36)
        self.custom_marker_input.setMaximumHeight(36)

        subject_block = FieldBlock("受试编号", self.subject_input, parent=self)
        label_block = FieldBlock("标签 / Label", self.label_selector, parent=self)
        marker_block = FieldBlock("Marker", self.custom_marker_input, parent=self)

        button_group = QWidget(self)
        button_group_layout = QHBoxLayout(button_group)
        button_group_layout.setContentsMargins(0, 0, 0, 0)
        button_group_layout.setSpacing(10)
        button_group_layout.addWidget(self.marker_button)
        button_group_layout.addWidget(self.pause_button)
        button_group_layout.addWidget(self.record_button)

        form_row.addWidget(subject_block, 3)
        form_row.addWidget(label_block, 2)

        action_row.addWidget(marker_block, 1)
        action_row.addWidget(button_group, 0, Qt.AlignmentFlag.AlignBottom)

        control_layout.addLayout(form_row)
        control_layout.addLayout(action_row)
        self._sync_buttons()

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

    def set_display_paused(self, is_paused: bool) -> None:
        if self.display_paused == is_paused:
            return

        self.display_paused = is_paused
        self._sync_buttons()
        self.displayPauseChanged.emit(is_paused)

    def current_label(self, fallback: str = "default_label") -> str:
        text = self.label_selector.currentText().strip()
        return text or fallback

    def current_subject_id(self, fallback: str = "") -> str:
        text = self.subject_input.text().strip()
        return text or fallback

    def current_marker_label(self) -> str:
        return self.custom_marker_input.text().strip() or self.current_label()

    def make_session_id(self) -> str:
        return time.strftime("%Y%m%d_%H%M%S")

    def _toggle_recording(self) -> None:
        if self.recording_enabled:
            self.stopRecordRequested.emit()
            return

        self.startRecordRequested.emit(
            self.current_subject_id(fallback=""),
            self.current_label(),
        )

    def _insert_marker(self) -> None:
        if self.current_state != DeviceState.RECORDING:
            return

        self.markerRequested.emit(self.current_marker_label())

    def _toggle_display_pause(self) -> None:
        self.set_display_paused(not self.display_paused)

    def _sync_buttons(self) -> None:
        can_record = self.current_state in {DeviceState.PREVIEWING, DeviceState.RECORDING}
        can_mark = self.current_state == DeviceState.RECORDING
        can_pause = self.current_state in {DeviceState.PREVIEWING, DeviceState.RECORDING}

        self.record_button.setEnabled(can_record)
        self.marker_button.setEnabled(can_mark)
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
            return

        if self.current_state == DeviceState.CONNECTING:
            self.record_button.setText("连接中")
            self.record_button.setIcon(FIF.SYNC)
            return

        if self.current_state in {
            DeviceState.DISCONNECTED,
            DeviceState.DISCONNECTING,
            DeviceState.ERROR,
        }:
            self.record_button.setText("等待连接")
            self.record_button.setIcon(FIF.PLAY_SOLID)
            return

        self.record_button.setText("开始录制")
        self.record_button.setIcon(FIF.PLAY_SOLID)
