from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import QApplication, QLineEdit, QPlainTextEdit, QTextEdit, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    SingleDirectionScrollArea,
    SmoothMode,
    SubtitleLabel,
)

from ...backend import (
    DeviceState,
    GanglionBackendBase,
    LabelsEvent,
    MarkerEvent,
    RecordEvent,
    RecordSession,
    SaveDirEvent,
    StateEvent,
    StreamChunk,
)
from ..display_settings import DisplaySettings
from ..widgets import AcquisitionControlBar, StreamPlotWidget


class AcquisitionPage(QWidget):
    def __init__(
        self,
        backend: GanglionBackendBase,
        display_settings: DisplaySettings,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.backend = backend
        self.display_settings = display_settings
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
        scroll_layout.setSpacing(8)

        self.default_save_dir = self.backend.default_save_dir
        self.control_bar = AcquisitionControlBar(self.backend.labels, self.scroll_widget)
        self.control_bar.set_state(self.current_state)
        self.control_bar.startRecordRequested.connect(self._start_recording)
        self.control_bar.stopRecordRequested.connect(self.backend.stop_record)
        self.control_bar.markerRequested.connect(self.backend.add_marker)

        self.stream_plot = StreamPlotWidget(
            max_samples=self.display_settings.max_samples,
            display_settings=self.display_settings,
            parent=self.scroll_widget,
        )
        self.control_bar.displayPauseChanged.connect(self.stream_plot.set_paused)

        scroll_layout.addWidget(self.control_bar)
        scroll_layout.addWidget(self.stream_plot)
        scroll_layout.addStretch(1)

        self.scroll_area.setWidget(self.scroll_widget)
        root_layout.addWidget(self.scroll_area, 1)

        self.backend.sig_record.connect(self._on_record_changed)
        self.backend.sig_marker.connect(self._on_marker_added)
        self.backend.sig_labels.connect(self._on_labels_changed)
        self.backend.sig_save_dir.connect(self._on_save_dir_changed)
        self.backend.sig_stream.connect(self._on_stream_received)

        self.marker_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        self.marker_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.marker_shortcut.activated.connect(self._trigger_marker_shortcut)

    def update_state(self, event: StateEvent) -> None:
        self.current_state = event.state
        self.control_bar.set_state(event.state)
        self.stream_plot.set_state(event)

    def _start_recording(self, subject_id: str, label: str) -> None:
        session_id = self.control_bar.make_session_id()
        normalized_subject_id = subject_id.strip() or f"session_{session_id}"
        self.backend.start_record(
            RecordSession(
                session_id=session_id,
                save_dir=self.default_save_dir,
                subject_id=normalized_subject_id,
                task_name=label.strip() or "default_label",
            )
        )

    def _on_record_changed(self, event: RecordEvent) -> None:
        self.control_bar.set_recording_enabled(event.is_recording)
        self.stream_plot.update_record_state(event)

    def _on_marker_added(self, event: MarkerEvent) -> None:
        self.stream_plot.add_marker(event)

    def _on_labels_changed(self, event: LabelsEvent) -> None:
        self.control_bar.set_available_labels(
            event.labels,
            preferred_label=self.control_bar.current_label(fallback=""),
        )

    def _on_save_dir_changed(self, event: SaveDirEvent) -> None:
        self.default_save_dir = event.save_dir

    def _on_stream_received(self, chunk: StreamChunk) -> None:
        self.stream_plot.update_stream(chunk)

    def _trigger_marker_shortcut(self) -> None:
        if self.current_state != DeviceState.RECORDING:
            return

        focus_widget = QApplication.focusWidget()
        if isinstance(focus_widget, (QLineEdit, QTextEdit, QPlainTextEdit)):
            return

        self.backend.add_marker(self.control_bar.current_marker_label())
