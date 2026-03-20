from __future__ import annotations

import time
from dataclasses import dataclass

from PyQt6.QtCore import QObject, pyqtSignal

from ..backend import (
    DeviceState,
    ErrorEvent,
    GanglionBackendBase,
    MarkerEvent,
    RecordEvent,
    RecordSession,
    RecordingMode,
    SegmentEvent,
)
from ..core.contracts import RecordingMode as ContractRecordingMode
from ..core.contracts import SessionControllerBase, SessionPlan
from .models import SessionState, SessionStateEvent, build_session_state_event


@dataclass(slots=True)
class SessionStartRequest:
    """Compatibility request used by the transitional session controller."""

    subject_id: str
    label: str
    save_dir: str
    recording_mode: RecordingMode
    session_id: str = ""


class SessionController(SessionControllerBase):
    """Transitional session facade toward `docs/platform_contract.md`.

    This layer keeps session assembly out of the UI while delegating to the
    current legacy backend contract. It is intentionally small so we can migrate
    the app in slices without changing the recording backend yet.
    """

    sig_session = pyqtSignal(object)
    sig_recording = pyqtSignal(object)
    sig_marker = pyqtSignal(object)
    sig_segment = pyqtSignal(object)
    sig_error = pyqtSignal(object)

    def __init__(
        self,
        backend: GanglionBackendBase,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.backend = backend
        self._session_state = SessionState.IDLE
        self._active_session_id = ""
        self._active_recording_mode: RecordingMode | None = None
        self._active_segment_label = ""

        self.backend.sig_record.connect(self._on_backend_record)
        self.backend.sig_marker.connect(self._on_backend_marker)
        self.backend.sig_segment.connect(self._on_backend_segment)
        self.backend.sig_error.connect(self._on_backend_error)

    @property
    def session_state(self) -> SessionState:
        return self._session_state

    @property
    def active_session_id(self) -> str:
        return self._active_session_id

    @property
    def active_recording_mode(self) -> RecordingMode | None:
        return self._active_recording_mode

    @property
    def active_segment_label(self) -> str:
        return self._active_segment_label

    @property
    def is_recording(self) -> bool:
        return self._session_state in {
            SessionState.STARTING,
            SessionState.ACTIVE,
            SessionState.STOPPING,
        }

    def start_acquisition(
        self,
        subject_id: str,
        label: str,
        recording_mode: RecordingMode,
        save_dir: str,
        session_id: str = "",
    ) -> None:
        self.start_session(
            SessionPlan(
                session_id=session_id or self._generate_session_id(),
                save_dir=save_dir,
                subject_id=subject_id.strip() or "",
                task_name=label.strip() or "default_label",
                recording_mode=self._to_contract_recording_mode(recording_mode),
            )
        )

    def start_session(self, plan: SessionPlan) -> None:
        if self.backend.state != DeviceState.PREVIEWING:
            return

        request = SessionStartRequest(
            subject_id=plan.subject_id,
            label=plan.task_name,
            save_dir=plan.save_dir,
            recording_mode=self._to_legacy_recording_mode(plan.recording_mode),
            session_id=plan.session_id or self._generate_session_id(),
        )
        self._emit_session_state(
            SessionState.STARTING,
            session_id=request.session_id,
            recording_mode=request.recording_mode,
            message="session start requested",
        )
        self.backend.start_record(self._build_record_session(request))

    def stop_acquisition(self) -> None:
        self.stop_session()

    def stop_session(self) -> None:
        if self.is_recording:
            self._emit_session_state(
                SessionState.STOPPING,
                session_id=self._active_session_id,
                recording_mode=self._active_recording_mode,
                active_segment_label=self._active_segment_label,
                message="session stop requested",
            )
        self.backend.stop_record()

    def add_marker(self, label: str, note: str = "", source: str = "ui") -> None:
        self.backend.add_marker(label, note=note, source=source)

    def insert_marker(self, marker) -> None:
        self.add_marker(
            getattr(marker, "label", "") or "marker",
            note=getattr(marker, "note", ""),
            source=getattr(marker, "source", "ui"),
        )

    def start_segment(self, label: str, note: str = "", source: str = "ui") -> None:
        self.backend.start_segment(label, note=note, source=source)

    def stop_segment(self, note: str = "", source: str = "ui") -> None:
        self.backend.stop_segment(note=note, source=source)

    def get_session_state(self) -> SessionStateEvent:
        return build_session_state_event(
            self._session_state,
            session_id=self._active_session_id,
            recording_mode=self._active_recording_mode,
            active_segment_label=self._active_segment_label,
        )

    def _build_record_session(self, request: SessionStartRequest) -> RecordSession:
        subject_id = request.subject_id.strip()
        label = request.label.strip()
        session_id = request.session_id.strip() or self._generate_session_id()
        normalized_label = label or "default_label"
        task_name = (
            normalized_label
            if request.recording_mode == RecordingMode.CLIP
            else "continuous_session"
        )

        return RecordSession(
            session_id=session_id,
            save_dir=request.save_dir,
            subject_id=subject_id or f"session_{session_id}",
            task_name=task_name,
            recording_mode=request.recording_mode,
        )

    def _generate_session_id(self) -> str:
        return time.strftime("%Y%m%d_%H%M%S")

    def _to_contract_recording_mode(self, mode: RecordingMode) -> ContractRecordingMode:
        if mode == RecordingMode.CONTINUOUS:
            return ContractRecordingMode.CONTINUOUS
        return ContractRecordingMode.CLIP

    def _to_legacy_recording_mode(self, mode: ContractRecordingMode) -> RecordingMode:
        if mode == ContractRecordingMode.CONTINUOUS:
            return RecordingMode.CONTINUOUS
        return RecordingMode.CLIP

    def _on_backend_record(self, event: RecordEvent) -> None:
        self.sig_recording.emit(event)
        if event.is_recording:
            self._active_session_id = event.session_id or self._active_session_id
            self._active_recording_mode = event.recording_mode
            self._emit_session_state(
                SessionState.ACTIVE,
                session_id=self._active_session_id,
                recording_mode=self._active_recording_mode,
                active_segment_label=self._active_segment_label,
                message="session started",
            )
            return

        session_id = event.session_id or self._active_session_id
        recording_mode = event.recording_mode or self._active_recording_mode
        self._active_session_id = ""
        self._active_recording_mode = None
        self._active_segment_label = ""
        self._emit_session_state(
            SessionState.IDLE,
            session_id=session_id,
            recording_mode=recording_mode,
            message="session stopped",
        )

    def _on_backend_marker(self, event: MarkerEvent) -> None:
        self.sig_marker.emit(event)

    def _on_backend_segment(self, event: SegmentEvent) -> None:
        if event.action == "started":
            self._active_segment_label = event.label
        elif event.action == "stopped":
            self._active_segment_label = ""

        self.sig_segment.emit(event)
        if self._session_state == SessionState.ACTIVE:
            self._emit_session_state(
                SessionState.ACTIVE,
                session_id=self._active_session_id,
                recording_mode=self._active_recording_mode,
                active_segment_label=self._active_segment_label,
                message="segment updated",
            )

    def _on_backend_error(self, event: ErrorEvent) -> None:
        self.sig_error.emit(event)
        if self._session_state not in {
            SessionState.STARTING,
            SessionState.ACTIVE,
            SessionState.STOPPING,
        }:
            return

        self._emit_session_state(
            SessionState.ERROR,
            session_id=self._active_session_id,
            recording_mode=self._active_recording_mode,
            active_segment_label=self._active_segment_label,
            message=event.message,
        )

    def _emit_session_state(
        self,
        state: SessionState,
        *,
        session_id: str = "",
        recording_mode: RecordingMode | None = None,
        active_segment_label: str = "",
        message: str = "",
    ) -> None:
        self._session_state = state
        self.sig_session.emit(
            build_session_state_event(
                state,
                session_id=session_id,
                recording_mode=recording_mode,
                active_segment_label=active_segment_label,
                message=message,
            )
        )
