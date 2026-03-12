from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget
from qfluentwidgets import FluentIcon as FIF, TogglePushButton
from qfluentwidgets.components.settings.setting_card import SettingCard

from ....backend import DeviceState, GanglionBackendBase, RecordEvent, RecordingMode
from ...recording_settings import RecordingSettings


class RecordingModeSettingCard(SettingCard):
    _MODE_TO_TEXT = {
        RecordingMode.CLIP: "片段录制",
        RecordingMode.CONTINUOUS: "连续录制",
    }

    def __init__(
        self,
        recording_settings: RecordingSettings,
        backend: GanglionBackendBase,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            FIF.EDIT,
            "录制模式",
            "切换“整段即标签”和“连续录制内片段标签”两种采集方式。",
            parent,
        )
        self.recording_settings = recording_settings
        self.backend = backend
        self.toggle_button = TogglePushButton(self)
        self.toggle_button.setFixedWidth(120)
        self.toggle_button.setFixedHeight(32)

        self.hBoxLayout.addWidget(self.toggle_button, 0, Qt.AlignmentFlag.AlignRight)
        self.hBoxLayout.addSpacing(16)

        self.toggle_button.clicked.connect(self._toggle_mode)
        self.recording_settings.recordingModeChanged.connect(self._sync_mode)
        self.backend.sig_record.connect(self._on_record_changed)
        self.toggle_button.setEnabled(self.backend.state != DeviceState.RECORDING)
        self._sync_mode(self.recording_settings.recording_mode)

    def _toggle_mode(self) -> None:
        if self.recording_settings.recording_mode == RecordingMode.CLIP:
            self.recording_settings.set_recording_mode(RecordingMode.CONTINUOUS)
            return

        self.recording_settings.set_recording_mode(RecordingMode.CLIP)

    def _sync_mode(self, mode: RecordingMode) -> None:
        self.toggle_button.blockSignals(True)
        self.toggle_button.setChecked(mode == RecordingMode.CONTINUOUS)
        self.toggle_button.blockSignals(False)
        self.toggle_button.setText(self._MODE_TO_TEXT.get(mode, "片段录制"))
        self.toggle_button.setIcon(None)

    def _on_record_changed(self, event: RecordEvent) -> None:
        self.toggle_button.setEnabled(not event.is_recording)
