from __future__ import annotations

import time
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

from modlink_core.runtime.engine import ModLinkEngine
from modlink_core.settings.service import SettingsService

from .constants import DEFAULT_LABELS, UI_LABELS_KEY, normalize_labels


class AcquisitionController(QObject):
    sessionNameChanged = pyqtSignal()
    recordingLabelChanged = pyqtSignal()
    markerLabelChanged = pyqtSignal()
    segmentLabelChanged = pyqtSignal()
    isRecordingChanged = pyqtSignal()
    isSegmentActiveChanged = pyqtSignal()
    recordingLabelsChanged = pyqtSignal()
    outputDirectoryChanged = pyqtSignal()
    primaryActionTextChanged = pyqtSignal()
    toggleSegmentTextChanged = pyqtSignal()
    messageRaised = pyqtSignal(str)

    def __init__(self, engine: ModLinkEngine, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._engine = engine
        self._settings = SettingsService.instance()
        self._session_name = ""
        self._recording_label = ""
        self._marker_label = ""
        self._segment_label = ""
        self._segment_started_ns: int | None = None

        self._engine.acquisition.sig_state_changed.connect(
            self._on_recording_state_changed
        )
        self._engine.acquisition.sig_error.connect(self._on_error)
        self._settings.sig_setting_changed.connect(self._on_setting_changed)

    @pyqtProperty(str, notify=sessionNameChanged)
    def sessionName(self) -> str:
        return self._session_name

    @pyqtProperty(str, notify=recordingLabelChanged)
    def recordingLabel(self) -> str:
        return self._recording_label

    @pyqtProperty(str, notify=markerLabelChanged)
    def markerLabel(self) -> str:
        return self._marker_label

    @pyqtProperty(str, notify=segmentLabelChanged)
    def segmentLabel(self) -> str:
        return self._segment_label

    @pyqtProperty(bool, notify=isRecordingChanged)
    def isRecording(self) -> bool:
        return self._engine.acquisition.is_recording

    @pyqtProperty(bool, notify=isSegmentActiveChanged)
    def isSegmentActive(self) -> bool:
        return self._segment_started_ns is not None

    @pyqtProperty("QVariantList", notify=recordingLabelsChanged)
    def recordingLabels(self) -> list[str]:
        return list(
            normalize_labels(self._settings.get(UI_LABELS_KEY, DEFAULT_LABELS))
        )

    @pyqtProperty(str, notify=outputDirectoryChanged)
    def outputDirectory(self) -> str:
        session_name = self._session_name.strip() or "<session_name>"
        return str(Path(self._engine.acquisition.root_dir) / f"session_{session_name}")

    @pyqtProperty(str, notify=primaryActionTextChanged)
    def primaryActionText(self) -> str:
        return "停止采集" if self.isRecording else "开始采集"

    @pyqtProperty(str, notify=toggleSegmentTextChanged)
    def toggleSegmentText(self) -> str:
        return "结束区间" if self.isSegmentActive else "开始区间"

    @pyqtSlot(str)
    def setSessionName(self, value: str) -> None:
        normalized = str(value)
        if normalized == self._session_name:
            return
        self._session_name = normalized
        self.sessionNameChanged.emit()
        self.outputDirectoryChanged.emit()

    @pyqtSlot(str)
    def setRecordingLabel(self, value: str) -> None:
        normalized = str(value)
        if normalized == self._recording_label:
            return
        self._recording_label = normalized
        self.recordingLabelChanged.emit()

    @pyqtSlot(str)
    def setMarkerLabel(self, value: str) -> None:
        normalized = str(value)
        if normalized == self._marker_label:
            return
        self._marker_label = normalized
        self.markerLabelChanged.emit()

    @pyqtSlot(str)
    def setSegmentLabel(self, value: str) -> None:
        normalized = str(value)
        if normalized == self._segment_label:
            return
        self._segment_label = normalized
        self.segmentLabelChanged.emit()

    @pyqtSlot()
    def toggleRecording(self) -> None:
        if self.isRecording:
            self._clear_segment(notify=True)
            self._engine.acquisition.stop_recording()
            return

        session_name = self._session_name.strip()
        if not session_name:
            session_name = time.strftime("session_%Y%m%d_%H%M%S")
            self.setSessionName(session_name)

        recording_label = self._recording_label.strip() or None
        self._engine.acquisition.start_recording(session_name, recording_label)

    @pyqtSlot()
    def insertMarker(self) -> None:
        session_name = self._session_name.strip()
        if not session_name:
            session_name = time.strftime("session_%Y%m%d_%H%M%S")
            self.setSessionName(session_name)

        marker_label = self._marker_label.strip() or session_name
        self._engine.acquisition.add_marker(marker_label)

    @pyqtSlot()
    def toggleSegment(self) -> None:
        if self._segment_started_ns is None:
            self._segment_started_ns = time.time_ns()
            self.isSegmentActiveChanged.emit()
            self.toggleSegmentTextChanged.emit()
            return

        start_ns = self._segment_started_ns
        end_ns = time.time_ns()
        label = self._segment_label.strip() or None
        self._clear_segment(notify=True)
        self._engine.acquisition.add_segment(
            start_ns=start_ns,
            end_ns=end_ns,
            label=label,
        )

    @pyqtSlot()
    def resetSegment(self) -> None:
        self._clear_segment(notify=True)

    def _clear_segment(self, *, notify: bool) -> None:
        if self._segment_started_ns is None:
            return
        self._segment_started_ns = None
        if notify:
            self.isSegmentActiveChanged.emit()
            self.toggleSegmentTextChanged.emit()

    def _on_recording_state_changed(self, _state: str) -> None:
        if not self.isRecording:
            self._clear_segment(notify=True)
        self.isRecordingChanged.emit()
        self.primaryActionTextChanged.emit()

    def _on_setting_changed(self, event: object) -> None:
        if getattr(event, "key", None) == UI_LABELS_KEY:
            self.recordingLabelsChanged.emit()

    def _on_error(self, message: str) -> None:
        normalized = str(message or "").strip()
        if not normalized:
            self.messageRaised.emit("发生了未知采集错误。")
            return

        prefix, separator, detail = normalized.partition(":")
        friendly = {
            "ACQ_NOT_STARTED": "采集后端还没有启动。",
            "ACQ_ALREADY_RECORDING": "采集已经在进行中。",
            "ACQ_INVALID_SESSION_NAME": "Session 名称不能为空。",
            "ACQ_MARKER_REJECTED": "请先开始采集，再写入 Marker。",
            "ACQ_SEGMENT_REJECTED": "请先开始采集，再记录区间。",
            "ACQ_INVALID_SEGMENT_RANGE": "区间时间范围无效。",
            "ACQ_START_FAILED": "开始采集失败。",
            "ACQ_STOP_FAILED": "停止采集失败。",
            "ACQ_WRITE_FAILED": "写入采集数据失败。",
            "ACQ_MARKER_FAILED": "写入 Marker 失败。",
            "ACQ_SEGMENT_FAILED": "写入区间失败。",
            "ACQ_STOP_TIMEOUT": "停止采集超时。",
        }.get(prefix.strip())
        if friendly is None:
            self.messageRaised.emit(normalized)
            return
        cleaned_detail = detail.strip() if separator else ""
        if cleaned_detail and cleaned_detail != "not recording":
            self.messageRaised.emit(f"{friendly} 详情：{cleaned_detail}")
            return
        self.messageRaised.emit(friendly)
