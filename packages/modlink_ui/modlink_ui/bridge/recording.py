from __future__ import annotations

from concurrent.futures import Future
from pathlib import Path

from PyQt6.QtCore import QObject, Qt, pyqtSignal, pyqtSlot

from modlink_core.events import RecordingFailedEvent
from modlink_core.models import RecordingSnapshot, RecordingStopSummary
from modlink_core.recording.backend import RecordingBackend
from modlink_core.settings import resolved_storage_root_dir

from ._futures import watch_future_completion
from .settings import QtSettingsBridge


class QtRecordingBridge(QObject):
    sig_state_changed = pyqtSignal(str)
    sig_error = pyqtSignal(str)
    sig_recording_failed = pyqtSignal(object)
    sig_recording_completed = pyqtSignal(object)
    _sig_command_succeeded = pyqtSignal(object)
    _sig_error_requested = pyqtSignal(str)

    def __init__(
        self,
        backend: RecordingBackend,
        settings: QtSettingsBridge,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self._backend = backend
        self._settings = settings
        self._snapshot = backend.snapshot()
        self._sig_command_succeeded.connect(
            self._handle_command_succeeded,
            Qt.ConnectionType.QueuedConnection,
        )
        self._sig_error_requested.connect(
            self._emit_error_message,
            Qt.ConnectionType.QueuedConnection,
        )

    @property
    def root_dir(self) -> Path:
        return resolved_storage_root_dir(self._settings)

    @property
    def state(self) -> str:
        return self._snapshot.state

    @property
    def is_started(self) -> bool:
        return self._snapshot.is_started

    @property
    def is_recording(self) -> bool:
        return self._snapshot.is_recording

    def snapshot(self) -> RecordingSnapshot:
        return self._snapshot

    def resync_from_backend(self) -> None:
        self._apply_snapshot(self._backend.snapshot())

    def handle_recording_failed(self, event: RecordingFailedEvent) -> None:
        self.resync_from_backend()
        self.sig_recording_failed.emit(event)

    def start_recording(self, recording_label: str | None = None) -> None:
        self._watch_command(self._backend.start_recording(recording_label))

    def stop_recording(self) -> None:
        self._watch_command(self._backend.stop_recording())

    def add_marker(self, label: str | None = None) -> None:
        self._watch_command(self._backend.add_marker(label))

    def add_segment(
        self,
        start_ns: int,
        end_ns: int,
        label: str | None = None,
    ) -> None:
        self._watch_command(
            self._backend.add_segment(start_ns=start_ns, end_ns=end_ns, label=label)
        )

    def _apply_snapshot(self, snapshot: RecordingSnapshot) -> None:
        self._snapshot = snapshot
        self.sig_state_changed.emit(snapshot.state)

    @pyqtSlot(str)
    def _emit_error_message(self, message: str) -> None:
        self.sig_error.emit(message)

    @pyqtSlot(object)
    def _handle_command_succeeded(self, result: object) -> None:
        self.resync_from_backend()
        if isinstance(result, RecordingStopSummary):
            self.sig_recording_completed.emit(result)

    def _watch_command(self, future: Future[object]) -> None:
        watch_future_completion(
            future,
            on_success=self._sig_command_succeeded.emit,
            on_error=self._sig_error_requested.emit,
            cancelled_message="ACQ_COMMAND_CANCELLED",
        )
