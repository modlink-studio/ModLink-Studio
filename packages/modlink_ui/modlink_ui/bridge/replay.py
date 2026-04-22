from __future__ import annotations

from concurrent.futures import Future
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QObject, Qt, QTimer, pyqtSignal, pyqtSlot

from modlink_core.models import (
    ExportJobSnapshot,
    ReplayMarker,
    ReplayRecordingSummary,
    ReplaySegment,
    ReplaySnapshot,
)
from modlink_core.replay.backend import ReplayBackend
from modlink_core.settings import (
    STORAGE_ROOT_DIR_KEY,
    resolved_export_root_dir,
    resolved_storage_root_dir,
)

from ._futures import watch_future_completion
from .bus import QtBusBridge
from .frame_pump import LatestFramePump
from .settings import QtSettingsBridge

_REPLAY_POLL_INTERVAL_MS = 100
_REPLAY_FRAME_STREAM_MAXSIZE = 256


@dataclass(slots=True)
class _ReplayCache:
    snapshot: ReplaySnapshot
    recordings: tuple[ReplayRecordingSummary, ...]
    markers: tuple[ReplayMarker, ...]
    segments: tuple[ReplaySegment, ...]
    export_jobs: tuple[ExportJobSnapshot, ...]


class QtReplayBridge(QObject):
    sig_snapshot_changed = pyqtSignal(object)
    sig_recordings_changed = pyqtSignal()
    sig_annotations_changed = pyqtSignal()
    sig_export_jobs_changed = pyqtSignal()
    sig_bus_reset = pyqtSignal()
    sig_error = pyqtSignal(str)
    _sig_command_succeeded = pyqtSignal(object, bool)
    _sig_error_requested = pyqtSignal(str)

    def __init__(
        self,
        backend: ReplayBackend,
        settings: QtSettingsBridge,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self._backend = backend
        self._settings = settings
        self._cache = _ReplayCache(
            snapshot=backend.snapshot(),
            recordings=backend.recordings(),
            markers=backend.markers(),
            segments=backend.segments(),
            export_jobs=backend.export_jobs(),
        )
        self.bus = QtBusBridge(backend.bus, parent=self)
        self._is_shutdown = False
        self._frame_pump = LatestFramePump(
            self.bus,
            thread_name="modlink.qt_bridge.replay_frames",
            read_timeout=0.1,
        )
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(_REPLAY_POLL_INTERVAL_MS)
        self._poll_timer.timeout.connect(self._poll_backend)
        self._poll_timer.start()
        self._settings.sig_setting_changed.connect(self._on_setting_changed)
        self._sig_command_succeeded.connect(
            self._handle_command_succeeded,
            Qt.ConnectionType.QueuedConnection,
        )
        self._sig_error_requested.connect(
            self._emit_error_message,
            Qt.ConnectionType.QueuedConnection,
        )
        self._reset_bus_from_backend()

    @property
    def root_dir(self) -> Path:
        return resolved_storage_root_dir(self._settings)

    @property
    def export_root_dir(self) -> Path:
        return resolved_export_root_dir(self._settings)

    def snapshot(self) -> ReplaySnapshot:
        return self._cache.snapshot

    def recordings(self) -> tuple[ReplayRecordingSummary, ...]:
        return self._cache.recordings

    def markers(self) -> tuple[ReplayMarker, ...]:
        return self._cache.markers

    def segments(self) -> tuple[ReplaySegment, ...]:
        return self._cache.segments

    def export_jobs(self) -> tuple[ExportJobSnapshot, ...]:
        return self._cache.export_jobs

    def resync_from_backend(self) -> None:
        self._sync_snapshot()
        self._sync_recordings()
        self._sync_annotations()
        self._sync_export_jobs()

    def refresh_recordings(self) -> None:
        self._watch_command(self._backend.refresh_recordings())

    def open_recording(self, recording_path: str | Path) -> None:
        self._watch_command(self._backend.open_recording(recording_path), reset_bus=True)

    def play(self) -> None:
        self._watch_command(self._backend.play())

    def pause(self) -> None:
        self._watch_command(self._backend.pause())

    def stop(self) -> None:
        self._watch_command(self._backend.stop())

    def set_speed(self, multiplier: float) -> None:
        self._watch_command(self._backend.set_speed(multiplier))

    def start_export(self, format_id: str) -> None:
        self._watch_command(self._backend.start_export(format_id))

    def shutdown(self) -> None:
        if self._is_shutdown:
            return
        self._is_shutdown = True
        self._poll_timer.stop()
        self._frame_pump.shutdown()

    def _sync_snapshot(self) -> None:
        snapshot = self._backend.snapshot()
        if snapshot == self._cache.snapshot:
            return
        self._cache.snapshot = snapshot
        self.sig_snapshot_changed.emit(snapshot)

    def _sync_recordings(self) -> None:
        recordings = self._backend.recordings()
        if recordings == self._cache.recordings:
            return
        self._cache.recordings = recordings
        self.sig_recordings_changed.emit()

    def _sync_annotations(self) -> None:
        markers = self._backend.markers()
        segments = self._backend.segments()
        if markers == self._cache.markers and segments == self._cache.segments:
            return
        self._cache.markers = markers
        self._cache.segments = segments
        self.sig_annotations_changed.emit()

    def _sync_export_jobs(self) -> None:
        export_jobs = self._backend.export_jobs()
        if export_jobs == self._cache.export_jobs:
            return
        self._cache.export_jobs = export_jobs
        self.sig_export_jobs_changed.emit()

    def _poll_backend(self) -> None:
        self._sync_snapshot()
        self._sync_export_jobs()

    def _reset_bus_from_backend(self) -> None:
        self.bus._set_descriptors(self._backend.bus.descriptors())
        self._frame_pump.attach_stream(
            self._backend.bus.open_frame_stream(
                maxsize=_REPLAY_FRAME_STREAM_MAXSIZE,
                drop_policy="drop_oldest",
                consumer_name="qt_replay_bridge",
            )
        )
        self.sig_bus_reset.emit()

    @pyqtSlot(str)
    def _emit_error_message(self, message: str) -> None:
        self.sig_error.emit(message)

    @pyqtSlot(object, bool)
    def _handle_command_succeeded(self, _result: object, reset_bus: bool) -> None:
        self.resync_from_backend()
        if reset_bus:
            self._reset_bus_from_backend()

    @pyqtSlot(object)
    def _on_setting_changed(self, event: object) -> None:
        if getattr(event, "key", None) == STORAGE_ROOT_DIR_KEY:
            self.refresh_recordings()

    def _watch_command(self, future: Future[object], *, reset_bus: bool = False) -> None:
        watch_future_completion(
            future,
            on_success=lambda result: self._sig_command_succeeded.emit(result, reset_bus),
            on_error=self._sig_error_requested.emit,
            cancelled_message="REPLAY_COMMAND_CANCELLED",
        )
