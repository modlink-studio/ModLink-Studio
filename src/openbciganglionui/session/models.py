from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum

from ..backend import RecordingMode


class SessionState(str, Enum):
    """Transitional session states exposed by the session facade."""

    IDLE = "idle"
    STARTING = "starting"
    ACTIVE = "active"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass(slots=True)
class SessionStateEvent:
    """Session-level state snapshot emitted by the transitional controller."""

    state: SessionState
    ts: float
    session_id: str = ""
    recording_mode: RecordingMode | None = None
    active_segment_label: str = ""
    message: str = ""


def build_session_state_event(
    state: SessionState,
    *,
    session_id: str = "",
    recording_mode: RecordingMode | None = None,
    active_segment_label: str = "",
    message: str = "",
) -> SessionStateEvent:
    return SessionStateEvent(
        state=state,
        ts=time.time(),
        session_id=session_id,
        recording_mode=recording_mode,
        active_segment_label=active_segment_label,
        message=message,
    )
