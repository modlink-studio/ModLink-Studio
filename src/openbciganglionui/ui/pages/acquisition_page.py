from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QLineEdit,
    QPlainTextEdit,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    SingleDirectionScrollArea,
    SmoothMode,
    SubtitleLabel,
)

from ...backend import (
    DeviceState,
    GanglionBackendBase,
    MarkerEvent,
    RecordEvent,
    RecordingMode,
    RecordSession,
    SegmentEvent,
    StateEvent,
    StreamChunk,
)
from ..settings import SettingsManager
from ..widgets import (
    ClipAcquisitionControlBar,
    ContinuousAcquisitionControlBar,
    StreamPlotWidget,
)


class AcquisitionPage(QWidget):
    def __init__(
        self,
        backend: GanglionBackendBase,
        settings_manager: SettingsManager,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.backend = backend
        self.settings_manager = settings_manager
        self.display_settings = settings_manager.display_settings
        self.recording_settings = settings_manager.recording_settings
        self.setObjectName("acquisition-page")
        self.current_state = backend.state
        self.is_recording = False

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(36, 28, 36, 28)
        root_layout.setSpacing(20)

        header_label = SubtitleLabel("采集", self)
        intro_label = BodyLabel(
            "这个页面用于设备连接后的实时预览、录制控制、marker 标注和波形查看。",
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

        self.default_save_dir = self.settings_manager.default_save_dir
        initial_labels = self.settings_manager.labels
        self.clip_control_bar = ClipAcquisitionControlBar(initial_labels, self.scroll_widget)
        self.continuous_control_bar = ContinuousAcquisitionControlBar(
            initial_labels, self.scroll_widget
        )

        self.control_stack = QStackedWidget(self.scroll_widget)
        self.control_stack.addWidget(self.clip_control_bar)
        self.control_stack.addWidget(self.continuous_control_bar)

        for control_bar in (self.clip_control_bar, self.continuous_control_bar):
            control_bar.set_state(self.current_state)
            control_bar.startRecordRequested.connect(self._start_recording)
            control_bar.stopRecordRequested.connect(self.backend.stop_record)
            control_bar.displayPauseChanged.connect(self._set_display_paused)

        self.clip_control_bar.markerRequested.connect(self.backend.add_marker)
        self.continuous_control_bar.startSegmentRequested.connect(self.backend.start_segment)
        self.continuous_control_bar.stopSegmentRequested.connect(self.backend.stop_segment)

        self.stream_plot = StreamPlotWidget(
            max_samples=self.display_settings.max_samples,
            display_settings=self.display_settings,
            parent=self.scroll_widget,
        )

        scroll_layout.addWidget(self.control_stack)
        scroll_layout.addWidget(self.stream_plot)
        scroll_layout.addStretch(1)

        self.scroll_area.setWidget(self.scroll_widget)
        root_layout.addWidget(self.scroll_area, 1)

        self.backend.sig_record.connect(self._on_record_changed)
        self.backend.sig_marker.connect(self._on_marker_added)
        self.backend.sig_segment.connect(self._on_segment_changed)
        self.backend.sig_stream.connect(self._on_stream_received)
        self.recording_settings.recordingModeChanged.connect(self._on_recording_mode_changed)
        self.settings_manager.labelsChanged.connect(self._on_labels_changed)
        self.settings_manager.saveDirChanged.connect(self._on_save_dir_changed)

        self.marker_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        self.marker_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.marker_shortcut.activated.connect(self._trigger_marker_shortcut)
        self._on_recording_mode_changed(self.recording_settings.recording_mode)

    def update_state(self, event: StateEvent) -> None:
        self.current_state = event.state
        self.clip_control_bar.set_state(event.state)
        self.continuous_control_bar.set_state(event.state)
        self.stream_plot.set_state(event)

    def _start_recording(self, subject_id: str) -> None:
        session_id = self.active_control_bar.make_session_id()
        normalized_subject_id = subject_id.strip() or f"session_{session_id}"
        recording_mode = self.recording_settings.recording_mode
        self.backend.start_record(
            RecordSession(
                session_id=session_id,
                save_dir=self.default_save_dir,
                subject_id=normalized_subject_id,
                task_name=(
                    self.active_control_bar.current_label()
                    if recording_mode == RecordingMode.CLIP
                    else "continuous_session"
                ),
                recording_mode=recording_mode,
            )
        )

    def _on_record_changed(self, event: RecordEvent) -> None:
        self.is_recording = event.is_recording
        self.clip_control_bar.set_recording_enabled(event.is_recording)
        self.continuous_control_bar.set_recording_enabled(event.is_recording)
        if not event.is_recording:
            self.continuous_control_bar.set_segment_active(False)
        self.stream_plot.update_record_state(event)

    def _on_marker_added(self, event: MarkerEvent) -> None:
        self.stream_plot.add_marker(event)

    def _on_segment_changed(self, event: SegmentEvent) -> None:
        self.stream_plot.update_segment_state(event)
        if event.action == "started":
            self.continuous_control_bar.set_segment_active(True, event.label)
            return
        if event.action == "stopped":
            self.continuous_control_bar.set_segment_active(False)

    def _on_labels_changed(self, labels: tuple[str, ...]) -> None:
        preferred_label = self.active_control_bar.current_label(fallback="")
        self.clip_control_bar.set_available_labels(
            labels,
            preferred_label=preferred_label,
        )
        self.continuous_control_bar.set_available_labels(
            labels,
            preferred_label=preferred_label,
        )

    def _on_save_dir_changed(self, save_dir: str) -> None:
        self.default_save_dir = save_dir

    def _on_stream_received(self, chunk: StreamChunk) -> None:
        self.stream_plot.update_stream(chunk)

    def _trigger_marker_shortcut(self) -> None:
        if self.current_state != DeviceState.RECORDING:
            return

        focus_widget = QApplication.focusWidget()
        if isinstance(focus_widget, (QLineEdit, QTextEdit, QPlainTextEdit)):
            return

        if self.recording_settings.recording_mode == RecordingMode.CLIP:
            self.backend.add_marker(self.clip_control_bar.current_marker_label())
            return

        if self.continuous_control_bar.segment_active:
            self.backend.stop_segment()
        else:
            self.backend.start_segment(self.continuous_control_bar.current_label())

    @property
    def active_control_bar(self) -> ClipAcquisitionControlBar | ContinuousAcquisitionControlBar:
        if self.recording_settings.recording_mode == RecordingMode.CONTINUOUS:
            return self.continuous_control_bar
        return self.clip_control_bar

    def _set_display_paused(self, is_paused: bool) -> None:
        self.stream_plot.set_paused(is_paused)
        for control_bar in (self.clip_control_bar, self.continuous_control_bar):
            if control_bar.display_paused != is_paused:
                control_bar.set_display_paused(is_paused)

    def _on_recording_mode_changed(self, mode: RecordingMode) -> None:
        previous_bar = (
            self.continuous_control_bar
            if self.control_stack.currentWidget() is self.continuous_control_bar
            else self.clip_control_bar
        )
        target_bar = self._control_bar_for_mode(mode)
        target_bar.sync_from(previous_bar)
        target_bar.set_state(self.current_state)
        target_bar.set_recording_enabled(self.is_recording)
        self.control_stack.setCurrentWidget(target_bar)

    def _control_bar_for_mode(
        self,
        mode: RecordingMode,
    ) -> ClipAcquisitionControlBar | ContinuousAcquisitionControlBar:
        if mode == RecordingMode.CONTINUOUS:
            return self.continuous_control_bar
        return self.clip_control_bar
