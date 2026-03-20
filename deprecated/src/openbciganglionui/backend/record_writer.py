from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np

from .models import MarkerEvent, RecordSegment, RecordingMode, RecordSession


@dataclass(slots=True)
class RecordWriteRequest:
    """Snapshot of one completed recording session to persist to disk."""

    session: RecordSession
    fs: float
    channel_names: tuple[str, ...]
    record_start_sample_index: int
    stream_sample_index: int
    data_chunks: Sequence[np.ndarray]
    markers: Sequence[MarkerEvent]
    segments: Sequence[RecordSegment]
    marker_codebook: Mapping[str, float] | None = None


class SessionRecordWriter:
    """Persist recorded chunks and session metadata using the app's layout."""

    def write(self, request: RecordWriteRequest) -> Path:
        save_root = self.record_root(request.session)
        save_root.mkdir(parents=True, exist_ok=True)

        n_channels = len(request.channel_names)
        if request.data_chunks:
            full_data = np.vstack(request.data_chunks)
            timestamps = np.arange(full_data.shape[0], dtype=np.float64) / float(
                request.fs
            )
        else:
            full_data = np.empty((0, n_channels), dtype=np.float32)
            timestamps = np.empty((0,), dtype=np.float64)

        csv_path = save_root / "stream.csv"
        header = "time_sec," + ",".join(request.channel_names)
        np.savetxt(
            csv_path,
            np.column_stack([timestamps, full_data]),
            delimiter=",",
            header=header,
            comments="",
            fmt="%.6f",
        )

        if request.session.recording_mode == RecordingMode.CLIP:
            self._write_markers_csv(save_root / "markers.csv", request.markers)
        else:
            self._write_segments_csv(
                save_root / "segments.csv",
                request.segments,
                record_start_sample_index=request.record_start_sample_index,
                stream_sample_index=request.stream_sample_index,
                fs=request.fs,
            )

        self._write_session_meta(save_root / "session_meta.txt", request)
        return save_root

    def record_root(self, session: RecordSession) -> Path:
        base = Path(session.save_dir) / session.subject_id
        if session.recording_mode == RecordingMode.CLIP:
            return base / session.task_name / session.session_id
        return base / session.session_id

    def _write_markers_csv(
        self,
        marker_path: Path,
        markers: Sequence[MarkerEvent],
    ) -> None:
        with marker_path.open("w", encoding="utf-8") as file:
            file.write("marker_id,label,wall_time,sample_index,note,source\n")
            for marker in markers:
                file.write(
                    f"{marker.marker_id},{self._csv_value(marker.label)},{marker.wall_time:.6f},"
                    f"{marker.sample_index},{self._csv_value(marker.note)},"
                    f"{self._csv_value(marker.source)}\n"
                )

    def _write_segments_csv(
        self,
        segment_path: Path,
        segments: Sequence[RecordSegment],
        *,
        record_start_sample_index: int,
        stream_sample_index: int,
        fs: float,
    ) -> None:
        with segment_path.open("w", encoding="utf-8") as file:
            file.write(
                "segment_id,label,start_sample_index,end_sample_index,start_offset_sec,"
                "end_offset_sec,note,source\n"
            )
            for segment in segments:
                end_sample_index = (
                    segment.end_sample_index
                    if segment.end_sample_index is not None
                    else stream_sample_index
                )
                start_offset = (
                    segment.start_sample_index - record_start_sample_index
                ) / float(fs)
                end_offset = (end_sample_index - record_start_sample_index) / float(fs)
                file.write(
                    f"{segment.segment_id},{self._csv_value(segment.label)},"
                    f"{segment.start_sample_index},{end_sample_index},"
                    f"{start_offset:.6f},{end_offset:.6f},"
                    f"{self._csv_value(segment.note)},{self._csv_value(segment.source)}\n"
                )

    def _write_session_meta(self, meta_path: Path, request: RecordWriteRequest) -> None:
        session = request.session
        with meta_path.open("w", encoding="utf-8") as file:
            file.write(f"session_id={session.session_id}\n")
            file.write(f"subject_id={session.subject_id}\n")
            file.write(f"task_name={session.task_name}\n")
            file.write(f"recording_mode={session.recording_mode.value}\n")
            file.write(f"operator={session.operator}\n")
            file.write(f"notes={session.notes}\n")
            file.write(f"fs={request.fs}\n")
            file.write(f"n_channels={len(request.channel_names)}\n")
            file.write(f"channel_names={','.join(request.channel_names)}\n")
            file.write(
                f"record_start_sample_index={request.record_start_sample_index}\n"
            )
            file.write(f"segment_count={len(request.segments)}\n")
            file.write(f"marker_count={len(request.markers)}\n")
            if request.marker_codebook:
                encoded = ";".join(
                    f"{self._csv_value(label)}:{float(code):.1f}"
                    for label, code in sorted(
                        request.marker_codebook.items(), key=lambda item: item[1]
                    )
                )
                file.write(f"marker_codebook={encoded}\n")

    def _csv_value(self, value: str) -> str:
        return str(value).replace(",", " ").replace("\n", " ").replace("\r", " ")
