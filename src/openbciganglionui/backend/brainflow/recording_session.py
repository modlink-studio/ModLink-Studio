from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Callable, Optional

import numpy as np

from ..models import (
    DeviceState,
    ErrorEvent,
    MarkerEvent,
    RecordEvent,
    RecordSegment,
    RecordSession,
    RecordingMode,
    SegmentEvent,
)
from ..record_writer import RecordWriteRequest, SessionRecordWriter
from .marker_codec import MarkerCodec


class BrainFlowRecordingSessionService:
    """Own recording lifecycle, markers/segments, and session persistence."""

    def __init__(
        self,
        *,
        emit_record: Callable[[RecordEvent], None],
        emit_marker: Callable[[MarkerEvent], None],
        emit_segment: Callable[[SegmentEvent], None],
        emit_error: Callable[[ErrorEvent], None],
        emit_fatal_error: Callable[[str, str, str], None],
        request_insert_marker: Callable[[float], None],
        set_state: Callable[[DeviceState, str], None],
    ) -> None:
        self._emit_record = emit_record
        self._emit_marker = emit_marker
        self._emit_segment = emit_segment
        self._emit_error = emit_error
        self._emit_fatal_error = emit_fatal_error
        self._request_insert_marker = request_insert_marker
        self._set_state = set_state

        self._record_writer = SessionRecordWriter()
        self._marker_codec = MarkerCodec()

        self._is_recording = False
        self._record_session: Optional[RecordSession] = None
        self._record_buffer: list[np.ndarray] = []
        self._markers: list[MarkerEvent] = []
        self._segments: list[RecordSegment] = []
        self._active_segment: Optional[RecordSegment] = None
        self._record_start_sample_index = 0

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    def append_stream_chunk(self, data: np.ndarray) -> None:
        if not self._is_recording:
            return

        if int(data.shape[0]) <= 0:
            return

        self._record_buffer.append(np.array(data, copy=True))

    def start_record(
        self,
        session: Optional[RecordSession],
        *,
        current_state: DeviceState,
        default_save_dir: str,
        sample_index: int,
    ) -> None:
        if current_state != DeviceState.PREVIEWING:
            return

        normalized_session = session
        if normalized_session is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            normalized_session = RecordSession(
                session_id=timestamp,
                save_dir=default_save_dir,
                subject_id=f"session_{timestamp}",
                task_name="default_label",
            )

        built_session = self._build_record_session(
            normalized_session,
            default_save_dir=default_save_dir,
        )

        try:
            Path(built_session.save_dir).mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self._emit_fatal_error(
                "RECORD_DIR_ERROR",
                "无法创建录制目录",
                str(exc),
            )
            return

        self._record_session = built_session
        self._record_buffer.clear()
        self._markers.clear()
        self._segments.clear()
        self._active_segment = None
        self._marker_codec = MarkerCodec()
        self._is_recording = True
        self._record_start_sample_index = sample_index

        self._emit_record(
            RecordEvent(
                is_recording=True,
                ts=time.time(),
                session_id=built_session.session_id,
                save_dir=built_session.save_dir,
                sample_index=sample_index,
                recording_mode=built_session.recording_mode,
            )
        )
        message = (
            "开始片段录制"
            if built_session.recording_mode == RecordingMode.CLIP
            else "开始连续录制"
        )
        self._set_state(DeviceState.RECORDING, message)

    def stop_record(
        self,
        *,
        current_state: DeviceState,
        sample_index: int,
        fs: float,
        channel_names: tuple[str, ...],
    ) -> None:
        if not self._is_recording:
            return

        if (
            self._record_session is not None
            and self._record_session.recording_mode == RecordingMode.CONTINUOUS
        ):
            self.stop_segment(
                note="auto_closed_on_stop",
                source="system",
                current_state=current_state,
                sample_index=sample_index,
            )

        self._persist_record_buffer(
            fs=fs,
            channel_names=channel_names,
            record_start_sample_index=self._record_start_sample_index,
            stream_sample_index=sample_index,
        )

        session = self._record_session
        self._reset_recording_runtime()

        self._emit_record(
            RecordEvent(
                is_recording=False,
                ts=time.time(),
                session_id=session.session_id if session else None,
                save_dir=session.save_dir if session else None,
                sample_index=sample_index,
                recording_mode=(
                    session.recording_mode if session else RecordingMode.CLIP
                ),
            )
        )

        if current_state != DeviceState.DISCONNECTING:
            self._set_state(DeviceState.PREVIEWING, "停止录制")

    def finalize_after_error(
        self,
        *,
        current_state: DeviceState,
        sample_index: int,
        fs: float,
        channel_names: tuple[str, ...],
    ) -> None:
        if not self._is_recording:
            return

        if (
            self._record_session is not None
            and self._record_session.recording_mode == RecordingMode.CONTINUOUS
            and self._active_segment is not None
        ):
            self.stop_segment(
                note="auto_closed_on_error",
                source="system",
                current_state=current_state,
                sample_index=sample_index,
            )

        self._persist_record_buffer(
            fs=fs,
            channel_names=channel_names,
            record_start_sample_index=self._record_start_sample_index,
            stream_sample_index=sample_index,
        )

        session = self._record_session
        self._reset_recording_runtime()

        self._emit_record(
            RecordEvent(
                is_recording=False,
                ts=time.time(),
                session_id=session.session_id if session else None,
                save_dir=session.save_dir if session else None,
                sample_index=sample_index,
                recording_mode=(
                    session.recording_mode if session else RecordingMode.CLIP
                ),
            )
        )

    def add_marker(
        self,
        label: str,
        note: str = "",
        source: str = "ui",
        *,
        current_state: DeviceState,
        sample_index: int,
    ) -> None:
        if current_state != DeviceState.RECORDING or self._record_session is None:
            return

        if self._record_session.recording_mode != RecordingMode.CLIP:
            return

        normalized_label = label.strip() or "marker"
        event = MarkerEvent(
            marker_id=f"m_{uuid.uuid4().hex[:8]}",
            label=normalized_label,
            wall_time=time.time(),
            sample_index=sample_index,
            note=note,
            source=source,
        )
        self._markers.append(event)
        self._emit_marker(event)

        try:
            self._request_insert_marker(self._marker_codec.encode(normalized_label))
        except ValueError:
            pass

    def start_segment(
        self,
        label: str,
        note: str = "",
        source: str = "ui",
        *,
        current_state: DeviceState,
        sample_index: int,
    ) -> None:
        if current_state != DeviceState.RECORDING or self._record_session is None:
            return

        if self._record_session.recording_mode != RecordingMode.CONTINUOUS:
            return

        if self._active_segment is not None:
            return

        normalized_label = self._normalize_record_component(
            label,
            fallback="default_label",
        )
        event_time = time.time()
        segment = RecordSegment(
            segment_id=f"s_{uuid.uuid4().hex[:8]}",
            label=normalized_label,
            start_sample_index=sample_index,
            started_at=event_time,
            note=note,
            source=source,
        )
        self._segments.append(segment)
        self._active_segment = segment
        self._emit_segment(
            SegmentEvent(
                action="started",
                segment_id=segment.segment_id,
                label=segment.label,
                ts=event_time,
                start_sample_index=segment.start_sample_index,
                session_id=self._record_session.session_id,
                note=segment.note,
                source=segment.source,
            )
        )

    def stop_segment(
        self,
        note: str = "",
        source: str = "ui",
        *,
        current_state: DeviceState,
        sample_index: int,
    ) -> None:
        if current_state != DeviceState.RECORDING or self._record_session is None:
            return

        if self._record_session.recording_mode != RecordingMode.CONTINUOUS:
            return

        if self._active_segment is None:
            return

        event_time = time.time()
        self._active_segment.end_sample_index = sample_index
        self._active_segment.ended_at = event_time
        if note:
            self._active_segment.note = (
                f"{self._active_segment.note} | {note}"
                if self._active_segment.note
                else note
            )

        self._emit_segment(
            SegmentEvent(
                action="stopped",
                segment_id=self._active_segment.segment_id,
                label=self._active_segment.label,
                ts=event_time,
                start_sample_index=self._active_segment.start_sample_index,
                end_sample_index=self._active_segment.end_sample_index,
                session_id=self._record_session.session_id,
                note=self._active_segment.note,
                source=source,
            )
        )
        self._active_segment = None

    def _persist_record_buffer(
        self,
        *,
        fs: float,
        channel_names: tuple[str, ...],
        record_start_sample_index: int,
        stream_sample_index: int,
    ) -> None:
        if self._record_session is None:
            return

        try:
            self._record_writer.write(
                RecordWriteRequest(
                    session=self._record_session,
                    fs=fs,
                    channel_names=channel_names,
                    record_start_sample_index=record_start_sample_index,
                    stream_sample_index=stream_sample_index,
                    data_chunks=tuple(self._record_buffer),
                    markers=tuple(self._markers),
                    segments=tuple(self._segments),
                    marker_codebook=self._marker_codec.snapshot(),
                )
            )
        except Exception as exc:
            self._emit_error(
                ErrorEvent(
                    code="RECORD_WRITE_ERROR",
                    message="录制文件写入失败",
                    ts=time.time(),
                    detail=str(exc),
                    recoverable=True,
                )
            )

    def _build_record_session(
        self,
        session: RecordSession,
        *,
        default_save_dir: str,
    ) -> RecordSession:
        recording_mode = self._normalize_recording_mode(session.recording_mode)
        default_task_name = (
            "default_label"
            if recording_mode == RecordingMode.CLIP
            else "continuous_session"
        )

        session_id = self._normalize_record_component(
            session.session_id,
            fallback=time.strftime("%Y%m%d_%H%M%S"),
        )
        return RecordSession(
            session_id=session_id,
            save_dir=session.save_dir or default_save_dir,
            subject_id=self._normalize_record_component(
                session.subject_id,
                fallback=f"session_{session_id}",
            ),
            task_name=self._normalize_record_component(
                session.task_name,
                fallback=default_task_name,
            ),
            recording_mode=recording_mode,
            operator=session.operator,
            notes=session.notes,
        )

    def _normalize_recording_mode(self, value: RecordingMode | str) -> RecordingMode:
        if isinstance(value, RecordingMode):
            return value
        try:
            return RecordingMode(str(value).strip())
        except ValueError:
            return RecordingMode.CLIP

    def _normalize_record_component(self, value: str, fallback: str) -> str:
        normalized = str(value).strip()
        if not normalized:
            normalized = fallback

        for char in '<>:"/\\|?*':
            normalized = normalized.replace(char, "_")

        normalized = normalized.rstrip(". ")
        return normalized or fallback

    def _reset_recording_runtime(self) -> None:
        self._is_recording = False
        self._record_session = None
        self._record_buffer.clear()
        self._markers.clear()
        self._segments.clear()
        self._active_segment = None
