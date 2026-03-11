from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    ComboBox,
    FluentIcon as FIF,
    PrimaryPushButton,
    SubtitleLabel,
)

from ...backend import GanglionBackendBase, LabelsEvent, RecordEvent, RecordSession, StateEvent
from ..widgets import PanelWidget


class AcquisitionPage(QWidget):
    def __init__(self, backend: GanglionBackendBase, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.backend = backend
        self.setObjectName("acquisition-page")

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(36, 28, 36, 28)
        root_layout.setSpacing(20)

        header_label = SubtitleLabel("采集", self)
        intro_label = BodyLabel(
            "这个页面用于承接设备连接、实时预览、marker、录制控制和波形区域。",
            self,
        )
        intro_label.setWordWrap(True)

        root_layout.addWidget(header_label)
        root_layout.addWidget(intro_label)

        self.recording_enabled = False
        self.available_labels = list(self.backend.labels)
        self.control_bar = QFrame(self)
        self.control_bar.setObjectName("acquisition-control-bar")
        self.control_bar.setStyleSheet(
            """
            QFrame#acquisition-control-bar {
                background: rgba(255, 255, 255, 0.72);
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: 16px;
            }
            """
        )
        control_row = QHBoxLayout(self.control_bar)
        control_row.setContentsMargins(20, 16, 20, 16)
        control_row.setSpacing(12)

        label = BodyLabel("标签 / Label:", self.control_bar)

        self.label_selector = ComboBox(self.control_bar)
        self.label_selector.setMinimumWidth(260)
        self._refresh_label_selector()

        self.record_button = PrimaryPushButton("开始录制", self)
        self.record_button.setMinimumWidth(140)
        self.record_button.clicked.connect(self._toggle_recording)

        control_row.addWidget(label, 0, Qt.AlignmentFlag.AlignVCenter)
        control_row.addWidget(self.label_selector, 1)
        control_row.addWidget(self.record_button, 0, Qt.AlignmentFlag.AlignRight)

        root_layout.addWidget(self.control_bar)

        metrics_layout = QGridLayout()
        metrics_layout.setHorizontalSpacing(16)
        metrics_layout.setVerticalSpacing(16)

        self.backend_panel = PanelWidget("后端状态", "等待 backend 状态信号...", self)
        self.session_panel = PanelWidget(
            "采集会话",
            "这里预留受试者、任务名、保存目录和录制状态。",
            self,
        )
        self.signal_panel = PanelWidget(
            "信号区",
            "这里预留实时波形、通道状态、采样率、缓冲区统计。",
            self,
        )

        metrics_layout.addWidget(self.backend_panel, 0, 0)
        metrics_layout.addWidget(self.session_panel, 0, 1)
        metrics_layout.addWidget(self.signal_panel, 1, 0, 1, 2)
        metrics_layout.setColumnStretch(0, 1)
        metrics_layout.setColumnStretch(1, 1)

        root_layout.addLayout(metrics_layout)

        footer = CaptionLabel(
            "当前先保留结构和状态占位，后面可以逐步替换成图表、表单和操作按钮。",
            self,
        )
        footer.setWordWrap(True)
        root_layout.addWidget(footer)

        self.backend.sig_record.connect(self._on_record_changed)
        self.backend.sig_labels.connect(self._on_labels_changed)
        self._sync_record_button()
        self._update_session_panel()

    def update_state(self, event: StateEvent) -> None:
        self.backend_panel.set_description(
            f"后端实现: {type(self.backend).__name__}\n"
            f"设备名称: {event.device_name}\n"
            f"当前状态: {event.state.value}\n"
            f"最近消息: {event.message or '-'}"
        )

    def _toggle_recording(self) -> None:
        if self.recording_enabled:
            self.backend.stop_record()
            self.recording_enabled = False
        else:
            session_id = self._current_label()
            self.backend.start_record(
                RecordSession(
                    session_id=session_id,
                    save_dir="./mock_data",
                )
            )
            self.recording_enabled = True
        self._sync_record_button()
        self._update_session_panel()

    def _on_record_changed(self, event: RecordEvent) -> None:
        self.recording_enabled = event.is_recording
        self._sync_record_button()
        self._update_session_panel(
            session_id=event.session_id or self._current_label(),
            save_dir=event.save_dir or "./mock_data",
        )

    def _on_labels_changed(self, event: LabelsEvent) -> None:
        current_label = self._current_label()
        self.available_labels = list(event.labels)
        self._refresh_label_selector(current_label)
        self._update_session_panel()

    def _sync_record_button(self) -> None:
        if self.recording_enabled:
            self.record_button.setText("结束录制")
            self.record_button.setIcon(FIF.PAUSE_BOLD)
            return

        self.record_button.setText("开始录制")
        self.record_button.setIcon(FIF.PLAY_SOLID)

    def _update_session_panel(
        self,
        session_id: str | None = None,
        save_dir: str = "./mock_data",
    ) -> None:
        current_session = session_id or self._current_label()
        self.session_panel.set_description(
            f"当前 session: {current_session}\n"
            f"保存目录: {save_dir}\n"
            f"录制状态: {'recording' if self.recording_enabled else 'idle'}"
        )

    def _refresh_label_selector(self, preferred_label: str | None = None) -> None:
        current = preferred_label or self._current_label(fallback="")
        labels = self.available_labels or ["default_label"]

        self.label_selector.blockSignals(True)
        self.label_selector.clear()
        self.label_selector.addItems(labels)

        target = current if current in labels else labels[0]
        self.label_selector.setCurrentText(target)
        self.label_selector.blockSignals(False)

    def _current_label(self, fallback: str = "default_label") -> str:
        text = self.label_selector.currentText().strip() if hasattr(self, "label_selector") else ""
        return text or fallback
