from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    ComboBox,
    FluentIcon as FIF,
    PrimaryPushButton,
    SingleDirectionScrollArea,
    SmoothMode,
    SubtitleLabel,
)

from ...backend import (
    DeviceState,
    GanglionBackendBase,
    LabelsEvent,
    RecordEvent,
    RecordSession,
    SaveDirEvent,
    StateEvent,
    StreamChunk,
)
from ..widgets import StreamPlotWidget


class AcquisitionPage(QWidget):
    def __init__(self, backend: GanglionBackendBase, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.backend = backend
        self.setObjectName("acquisition-page")
        self.current_state = backend.state

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

        self.scroll_area = SingleDirectionScrollArea(self, orient=Qt.Orientation.Vertical)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setSmoothMode(SmoothMode.NO_SMOOTH)
        self.scroll_area.enableTransparentBackground()

        self.scroll_widget = QWidget(self.scroll_area)
        self.scroll_widget.setObjectName("acquisition-scroll-widget")
        self.scroll_widget.setStyleSheet(
            "QWidget#acquisition-scroll-widget { background: transparent; }"
        )

        scroll_layout = QVBoxLayout(self.scroll_widget)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(20)

        self.recording_enabled = False
        self.available_labels = list(self.backend.labels)
        self.default_save_dir = self.backend.default_save_dir

        self.control_bar = QFrame(self.scroll_widget)
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

        self.stream_plot = StreamPlotWidget(parent=self.scroll_widget)

        scroll_layout.addWidget(self.control_bar)
        scroll_layout.addWidget(self.stream_plot)
        scroll_layout.addStretch(1)

        self.scroll_area.setWidget(self.scroll_widget)
        root_layout.addWidget(self.scroll_area, 1)

        self.backend.sig_record.connect(self._on_record_changed)
        self.backend.sig_labels.connect(self._on_labels_changed)
        self.backend.sig_save_dir.connect(self._on_save_dir_changed)
        self.backend.sig_stream.connect(self._on_stream_received)

        self._sync_record_button()

    def update_state(self, event: StateEvent) -> None:
        self.current_state = event.state
        self.stream_plot.set_state(event)
        self._sync_record_button()

    def _toggle_recording(self) -> None:
        if self.recording_enabled:
            self.backend.stop_record()
        else:
            session_id = self._current_label()
            self.backend.start_record(
                RecordSession(
                    session_id=session_id,
                    save_dir=self.default_save_dir,
                )
            )

    def _on_record_changed(self, event: RecordEvent) -> None:
        self.recording_enabled = event.is_recording
        self.stream_plot.update_record_state(event)
        self._sync_record_button()

    def _on_labels_changed(self, event: LabelsEvent) -> None:
        current_label = self._current_label()
        self.available_labels = list(event.labels)
        self._refresh_label_selector(current_label)

    def _on_save_dir_changed(self, event: SaveDirEvent) -> None:
        self.default_save_dir = event.save_dir

    def _on_stream_received(self, chunk: StreamChunk) -> None:
        self.stream_plot.update_stream(chunk)

    def _sync_record_button(self) -> None:
        can_record = self.current_state in {DeviceState.PREVIEWING, DeviceState.RECORDING}
        self.record_button.setEnabled(can_record)

        if self.recording_enabled:
            self.record_button.setText("结束录制")
            self.record_button.setIcon(FIF.PAUSE_BOLD)
            return

        if self.current_state == DeviceState.CONNECTING:
            self.record_button.setText("连接中")
            self.record_button.setIcon(FIF.SYNC)
            return

        if self.current_state in {DeviceState.DISCONNECTED, DeviceState.DISCONNECTING, DeviceState.ERROR}:
            self.record_button.setText("等待连接")
            self.record_button.setIcon(FIF.PLAY_SOLID)
            return

        self.record_button.setText("开始录制")
        self.record_button.setIcon(FIF.PLAY_SOLID)

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
