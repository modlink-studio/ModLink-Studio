from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal

from packages.modlink_shared import FrameEnvelope

from ..bus import FrameSubscription, StreamBus


class RecordingState(str, Enum):
    IDLE = "idle"
    RECORDING = "recording"


@dataclass(slots=True)
class RecordingRequest:
    save_dir: str
    label: str = ""
    subject_id: str = ""
    recording_id: str = ""
    stream_ids: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class MarkerRecord:
    marker_id: str
    label: str
    timestamp_ns: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SegmentRecord:
    segment_id: str
    label: str
    start_timestamp_ns: int
    end_timestamp_ns: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RecordingStateEvent:
    state: RecordingState
    ts: float
    recording_id: str = ""
    message: str = ""


class AcquisitionTask(QObject):
    """Recording owner for the new architecture.

    This object consumes selected streams from the bus, captures frames during
    recording, and writes output as part of the recording workflow itself.
    """

    sig_recording = pyqtSignal(object)
    sig_marker = pyqtSignal(object)
    sig_segment = pyqtSignal(object)
    sig_error = pyqtSignal(str)

    def __init__(self, bus: StreamBus, parent: QObject | None = None) -> None:
        super().__init__(parent=parent)
        self._bus = bus
        self._state = RecordingState.IDLE
        self._request: RecordingRequest | None = None
        self._frames_by_stream: dict[str, list[FrameEnvelope]] = {}
        self._markers: list[MarkerRecord] = []
        self._segments: list[SegmentRecord] = []
        self._active_segment: SegmentRecord | None = None
        self._frame_subscription: FrameSubscription | None = None
        self._started_at_ns = 0
        self._stopped_at_ns = 0

    @property
    def state(self) -> RecordingState:
        return self._state

    @property
    def is_recording(self) -> bool:
        return self._state == RecordingState.RECORDING

    def start_recording(self, request: RecordingRequest) -> None:
        if self.is_recording:
            return

        recording_id = request.recording_id.strip() or self._generate_recording_id()
        selected_streams = request.stream_ids or tuple(
            descriptor.stream_id for descriptor in self._bus.descriptors().values()
        )
        if not selected_streams:
            self._emit_error(
                code="NO_STREAMS_SELECTED",
                message="cannot start recording without streams",
                detail="stream bus has no registered streams",
            )
            return

        self._request = RecordingRequest(
            save_dir=request.save_dir,
            label=request.label,
            subject_id=request.subject_id,
            recording_id=recording_id,
            stream_ids=tuple(selected_streams),
            metadata=dict(request.metadata),
        )
        self._frames_by_stream = {
            stream_id: [] for stream_id in self._request.stream_ids
        }
        self._markers.clear()
        self._segments.clear()
        self._active_segment = None
        self._started_at_ns = time.time_ns()
        self._stopped_at_ns = 0
        self._frame_subscription = self._bus.subscribe(self._on_frame)
        self._state = RecordingState.RECORDING
        self.sig_recording.emit(
            RecordingStateEvent(
                state=self._state,
                ts=time.time(),
                recording_id=self._request.recording_id,
                message="recording started",
            )
        )

    def stop_recording(self) -> None:
        if not self.is_recording or self._request is None:
            return

        if self._active_segment is not None:
            self.stop_segment()

        self._stopped_at_ns = time.time_ns()
        request = self._request
        try:
            self._write_recording(request)
        except OSError as exc:
            self._emit_error(
                code="WRITE_FAILED",
                message="failed to write recording",
                detail=str(exc),
            )
        finally:
            self._clear_subscriptions()
            self._request = None
            self._state = RecordingState.IDLE
            self.sig_recording.emit(
                RecordingStateEvent(
                    state=self._state,
                    ts=time.time(),
                    recording_id=request.recording_id,
                    message="recording stopped",
                )
            )

    def insert_marker(
        self,
        label: str,
        *,
        timestamp_ns: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MarkerRecord | None:
        if not self.is_recording:
            return None

        marker = MarkerRecord(
            marker_id=f"marker_{uuid.uuid4().hex[:8]}",
            label=label.strip() or "marker",
            timestamp_ns=timestamp_ns or time.time_ns(),
            metadata=dict(metadata or {}),
        )
        self._markers.append(marker)
        self.sig_marker.emit(marker)
        return marker

    def start_segment(
        self,
        label: str,
        *,
        timestamp_ns: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SegmentRecord | None:
        if not self.is_recording or self._active_segment is not None:
            return None

        segment = SegmentRecord(
            segment_id=f"segment_{uuid.uuid4().hex[:8]}",
            label=label.strip() or "segment",
            start_timestamp_ns=timestamp_ns or time.time_ns(),
            metadata=dict(metadata or {}),
        )
        self._segments.append(segment)
        self._active_segment = segment
        self.sig_segment.emit(segment)
        return segment

    def stop_segment(self, *, timestamp_ns: int | None = None) -> SegmentRecord | None:
        if not self.is_recording or self._active_segment is None:
            return None

        self._active_segment.end_timestamp_ns = timestamp_ns or time.time_ns()
        segment = self._active_segment
        self._active_segment = None
        self.sig_segment.emit(segment)
        return segment

    def _on_frame(self, frame: FrameEnvelope) -> None:
        if not self.is_recording or self._request is None:
            return
        if frame.stream_id not in self._frames_by_stream:
            return
        self._frames_by_stream[frame.stream_id].append(frame)

    def _write_recording(self, request: RecordingRequest) -> None:
        root = self._recording_root(request)
        streams_dir = root / "streams"
        streams_dir.mkdir(parents=True, exist_ok=True)

        for stream_id, frames in self._frames_by_stream.items():
            stream_file = streams_dir / f"{self._safe_name(stream_id)}.jsonl"
            with stream_file.open("w", encoding="utf-8") as handle:
                for frame in frames:
                    handle.write(
                        json.dumps(self._to_jsonable(frame), ensure_ascii=False)
                    )
                    handle.write("\n")

        meta = {
            "recording_id": request.recording_id,
            "label": request.label,
            "subject_id": request.subject_id,
            "started_at_ns": self._started_at_ns,
            "stopped_at_ns": self._stopped_at_ns,
            "stream_ids": list(request.stream_ids),
            "metadata": self._to_jsonable(request.metadata),
            "markers": [self._to_jsonable(marker) for marker in self._markers],
            "segments": [self._to_jsonable(segment) for segment in self._segments],
            "frame_counts": {
                stream_id: len(frames)
                for stream_id, frames in self._frames_by_stream.items()
            },
        }
        (root / "recording_meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _recording_root(self, request: RecordingRequest) -> Path:
        base = Path(request.save_dir).expanduser()
        subject = self._safe_name(request.subject_id or "unknown_subject")
        label = self._safe_name(request.label or "unlabeled")
        return base / subject / label / request.recording_id

    def _clear_subscriptions(self) -> None:
        if self._frame_subscription is None:
            return
        self._frame_subscription.close()
        self._frame_subscription = None

    def _emit_error(self, code: str, message: str, detail: str = "") -> None:
        parts = [code, message]
        if detail:
            parts.append(detail)
        self.sig_error.emit(": ".join(parts))

    def _generate_recording_id(self) -> str:
        return time.strftime("%Y%m%d_%H%M%S")

    def _safe_name(self, value: str) -> str:
        text = str(value).strip() or "unknown"
        for char in '<>:"/\\|?*':
            text = text.replace(char, "_")
        return text.rstrip(". ") or "unknown"

    def _to_jsonable(self, value: Any) -> Any:
        if is_dataclass(value):
            return {key: self._to_jsonable(item) for key, item in asdict(value).items()}
        if isinstance(value, dict):
            return {str(key): self._to_jsonable(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._to_jsonable(item) for item in value]
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return repr(value)
