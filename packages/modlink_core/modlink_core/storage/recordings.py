from __future__ import annotations

import csv
import json
from pathlib import Path
from time import time_ns
from typing import Any, Iterator

import numpy as np

from modlink_sdk import FrameEnvelope, StreamDescriptor

from ..models import RecordingStartSummary, RecordingStopSummary
from .io import read_csv_rows, read_json, to_json_text, to_json_value, write_json, write_npz
from .layout import (
    SCHEMA_VERSION,
    generate_storage_id,
    recording_dir,
    recording_manifest_path,
    recordings_dir,
    safe_path_component,
    validate_storage_id,
)


class RecordingStore:
    def __init__(self, root_dir: Path) -> None:
        self.root_dir = Path(root_dir)

    def open_writer(
        self,
        recording_descriptors: dict[str, StreamDescriptor],
        *,
        recording_label: str | None = None,
        started_at_ns: int | None = None,
        recording_id: str | None = None,
    ) -> RecordingWriteSession:
        return RecordingWriteSession(
            self.root_dir,
            recording_label=recording_label,
            recording_descriptors=recording_descriptors,
            started_at_ns=int(time_ns() if started_at_ns is None else started_at_ns),
            recording_id=recording_id,
        )

    def read_recording_manifest(self, recording_id: str) -> dict[str, Any]:
        return read_json(recording_manifest_path(self.root_dir, recording_id))

    def read_stream_manifest(self, recording_id: str, stream_id: str) -> dict[str, Any]:
        return read_json(self._stream_dir(recording_id, stream_id) / "stream.json")

    def read_descriptor_snapshot(self, recording_id: str) -> dict[str, StreamDescriptor]:
        manifest = self.read_recording_manifest(recording_id)
        snapshot = manifest.get("descriptor_snapshot", [])
        if not isinstance(snapshot, list):
            raise ValueError(f"recording '{recording_id}' has invalid descriptor_snapshot payload")
        descriptors = [descriptor_from_dict(item) for item in snapshot if isinstance(item, dict)]
        return {descriptor.stream_id: descriptor for descriptor in descriptors}

    def read_markers(self, recording_id: str) -> list[dict[str, Any]]:
        rows = read_csv_rows(recording_dir(self.root_dir, recording_id) / "annotations" / "markers.csv")
        return [
            {
                "timestamp_ns": int(row["timestamp_ns"]),
                "label": row["label"] or None,
            }
            for row in rows
        ]

    def read_segments(self, recording_id: str) -> list[dict[str, Any]]:
        rows = read_csv_rows(recording_dir(self.root_dir, recording_id) / "annotations" / "segments.csv")
        return [
            {
                "start_ns": int(row["start_ns"]),
                "end_ns": int(row["end_ns"]),
                "label": row["label"] or None,
            }
            for row in rows
        ]

    def iter_stream_frames(self, recording_id: str, stream_id: str) -> Iterator[FrameEnvelope]:
        stream_manifest = self.read_stream_manifest(recording_id, stream_id)
        descriptor_payload = stream_manifest.get("descriptor")
        if not isinstance(descriptor_payload, dict):
            raise ValueError(
                f"recording '{recording_id}' stream '{stream_id}' has invalid descriptor payload"
            )
        descriptor = descriptor_from_dict(descriptor_payload)
        stream_dir = self._stream_dir(recording_id, stream_id)
        chunk_rows = read_csv_rows(stream_dir / "chunks.csv")
        chunk_rows.sort(key=lambda row: int(row["chunk_index"]))
        for row in chunk_rows:
            chunk_path = stream_dir / "chunks" / row["file_name"]
            with np.load(chunk_path) as archive:
                data = np.asarray(archive["data"])
                timestamps_ns = np.asarray(archive["timestamps_ns"], dtype=np.int64)
                manifest = json.loads(str(archive["manifest_json"].tolist()))
            extra = manifest.get("extra")
            yield FrameEnvelope(
                device_id=descriptor.device_id,
                modality=descriptor.modality,
                timestamp_ns=int(timestamps_ns[0]),
                data=np.ascontiguousarray(data),
                seq=None if manifest.get("chunk_seq") is None else int(manifest["chunk_seq"]),
                extra={} if not isinstance(extra, dict) else dict(extra),
            )

    def list_recordings(self) -> list[dict[str, Any]]:
        manifests: list[dict[str, Any]] = []
        base_dir = recordings_dir(self.root_dir)
        if not base_dir.is_dir():
            return manifests
        for path in sorted(base_dir.iterdir(), key=lambda item: item.name):
            manifest_path = path / "recording.json"
            if manifest_path.is_file():
                manifests.append(read_json(manifest_path))
        return manifests

    def _stream_dir(self, recording_id: str, stream_id: str) -> Path:
        manifest = self.read_recording_manifest(recording_id)
        streams = manifest.get("streams", [])
        if not isinstance(streams, list):
            raise ValueError(f"recording '{recording_id}' has invalid streams payload")
        for item in streams:
            if not isinstance(item, dict):
                continue
            if item.get("stream_id") != stream_id:
                continue
            relative_path = item.get("path")
            if not isinstance(relative_path, str):
                raise ValueError(
                    f"recording '{recording_id}' stream '{stream_id}' has invalid path payload"
                )
            return recording_dir(self.root_dir, recording_id) / relative_path
        raise KeyError(stream_id)


class RecordingWriteSession:
    def __init__(
        self,
        root_dir: Path,
        *,
        recording_label: str | None,
        recording_descriptors: dict[str, StreamDescriptor],
        started_at_ns: int,
        recording_id: str | None = None,
    ) -> None:
        self.root_dir = Path(root_dir)
        self.recording_label = recording_label
        self.recording_descriptors = recording_descriptors
        self.started_at_ns = int(started_at_ns)
        self.recording_id = (
            generate_storage_id("rec", self.started_at_ns)
            if recording_id is None
            else validate_storage_id(recording_id, "rec")
        )
        self.recording_dir = recording_dir(self.root_dir, self.recording_id)
        self.annotations_dir = self.recording_dir / "annotations"
        self.streams_dir = self.recording_dir / "streams"
        self._frame_counts_by_stream: dict[str, int] = {
            stream_id: 0 for stream_id in recording_descriptors
        }
        self._stream_writers: dict[str, StreamRecordingWriter] = {}
        self._stream_dir_names: dict[str, str] = {}
        used_stream_dirs: set[str] = set()

        recordings_dir(self.root_dir).mkdir(parents=True, exist_ok=True)
        self.recording_dir.mkdir(parents=True, exist_ok=False)
        self.annotations_dir.mkdir(parents=True, exist_ok=False)
        self.streams_dir.mkdir(parents=True, exist_ok=False)
        self._annotation_writer = AnnotationWriter(self.annotations_dir)

        for descriptor in self.recording_descriptors.values():
            stream_dir_name = safe_path_component(descriptor.stream_id)
            if stream_dir_name in used_stream_dirs:
                raise ValueError(
                    f"stream directory collision for stream_id={descriptor.stream_id!r}"
                )
            used_stream_dirs.add(stream_dir_name)
            self._stream_dir_names[descriptor.stream_id] = stream_dir_name
            self._stream_writers[descriptor.stream_id] = StreamRecordingWriter(
                self.streams_dir / stream_dir_name,
                descriptor,
            )

    @property
    def frame_counts_by_stream(self) -> dict[str, int]:
        return dict(self._frame_counts_by_stream)

    def start_summary(self) -> RecordingStartSummary:
        return RecordingStartSummary(
            recording_id=self.recording_id,
            recording_path=str(self.recording_dir),
            started_at_ns=self.started_at_ns,
        )

    def append_frame(self, frame: FrameEnvelope) -> None:
        writer = self._stream_writers.get(frame.stream_id)
        if writer is None:
            raise ValueError(
                f"unexpected stream_id '{frame.stream_id}' outside recording descriptors"
            )
        writer.append_frame(frame)
        self._frame_counts_by_stream[frame.stream_id] += 1

    def add_marker(self, *, timestamp_ns: int, label: str | None = None) -> None:
        self._annotation_writer.add_marker(timestamp_ns=timestamp_ns, label=label)

    def add_segment(self, *, start_ns: int, end_ns: int, label: str | None = None) -> None:
        self._annotation_writer.add_segment(start_ns=start_ns, end_ns=end_ns, label=label)

    def finalize(
        self,
        *,
        stopped_at_ns: int,
        status: str = "completed",
    ) -> RecordingStopSummary:
        first_error: Exception | None = None
        for writer in self._stream_writers.values():
            try:
                writer.close()
            except Exception as exc:
                if first_error is None:
                    first_error = exc
        try:
            self._annotation_writer.close()
        except Exception as exc:
            if first_error is None:
                first_error = exc
        try:
            self.write_manifest(stopped_at_ns=stopped_at_ns, status=status)
        except Exception as exc:
            if first_error is None:
                first_error = exc
        summary = RecordingStopSummary(
            recording_id=self.recording_id,
            recording_path=str(self.recording_dir),
            started_at_ns=self.started_at_ns,
            stopped_at_ns=int(stopped_at_ns),
            status=status,
            frame_counts_by_stream=self.frame_counts_by_stream,
        )
        if first_error is not None:
            raise first_error
        return summary

    def write_manifest(self, *, stopped_at_ns: int | None, status: str) -> None:
        write_json(
            self.recording_dir / "recording.json",
            {
                "schema_version": SCHEMA_VERSION,
                "recording_id": self.recording_id,
                "recording_label": self.recording_label,
                "started_at_ns": self.started_at_ns,
                "stopped_at_ns": stopped_at_ns,
                "status": status,
                "streams": [
                    {
                        "stream_id": descriptor.stream_id,
                        "path": f"streams/{self._stream_dir_names[descriptor.stream_id]}",
                    }
                    for descriptor in self.recording_descriptors.values()
                ],
                "descriptor_snapshot": [
                    descriptor_to_dict(descriptor)
                    for descriptor in self.recording_descriptors.values()
                ],
                "frame_counts_by_stream": self.frame_counts_by_stream,
            },
        )


class AnnotationWriter:
    def __init__(self, annotations_dir: Path) -> None:
        self._markers_file = (annotations_dir / "markers.csv").open(
            "w",
            encoding="utf-8",
            newline="",
        )
        self._markers_writer = csv.writer(self._markers_file)
        self._markers_writer.writerow(["timestamp_ns", "label"])
        self._markers_file.flush()

        self._segments_file = (annotations_dir / "segments.csv").open(
            "w",
            encoding="utf-8",
            newline="",
        )
        self._segments_writer = csv.writer(self._segments_file)
        self._segments_writer.writerow(["start_ns", "end_ns", "label"])
        self._segments_file.flush()

    def add_marker(self, *, timestamp_ns: int, label: str | None) -> None:
        self._markers_writer.writerow([int(timestamp_ns), "" if label is None else label])
        self._markers_file.flush()

    def add_segment(self, *, start_ns: int, end_ns: int, label: str | None) -> None:
        self._segments_writer.writerow([int(start_ns), int(end_ns), "" if label is None else label])
        self._segments_file.flush()

    def close(self) -> None:
        self._markers_file.close()
        self._segments_file.close()


class StreamRecordingWriter:
    def __init__(self, stream_dir: Path, descriptor: StreamDescriptor) -> None:
        expected_ndim, shape_kind = resolve_payload_layout(descriptor.payload_type)
        self.stream_dir = stream_dir
        self.descriptor = descriptor
        self._expected_ndim = expected_ndim
        self._shape_kind = shape_kind
        self._frame_count = 0
        self._sample_count = 0
        self._declared_chunk_size = declared_chunk_size(descriptor)
        self._nominal_sample_rate_hz = nominal_sample_rate_hz(descriptor)
        self._sample_period_ns = int(round(1_000_000_000 / self._nominal_sample_rate_hz))
        self._chunk_index = 0
        self._channel_count: int | None = None
        self._sample_shape: tuple[int, ...] | None = None
        self._dtype_str: str | None = None

        self.stream_dir.mkdir(parents=True, exist_ok=True)
        self.chunks_dir = self.stream_dir / "chunks"
        self.chunks_dir.mkdir(parents=True, exist_ok=True)
        self._chunks_file = (self.stream_dir / "chunks.csv").open(
            "w",
            encoding="utf-8",
            newline="",
        )
        self._chunks_writer = csv.writer(self._chunks_file)
        self._chunks_writer.writerow(
            [
                "chunk_index",
                "chunk_seq",
                "chunk_start_timestamp_ns",
                "sample_count",
                "file_name",
                "shape_json",
                "dtype",
                "extra_json",
            ]
        )
        self._chunks_file.flush()
        self._write_stream_manifest()

    @property
    def frame_count(self) -> int:
        return self._frame_count

    @property
    def sample_count(self) -> int:
        return self._sample_count

    @property
    def chunk_count(self) -> int:
        return self._chunk_index

    def append_frame(self, frame: FrameEnvelope) -> None:
        data = normalize_data_array(frame, expected_ndim=self._expected_ndim)
        channel_count = int(data.shape[0])
        chunk_size = int(data.shape[1])
        sample_shape = tuple(int(value) for value in data.shape[2:])
        self._validate_chunk_size(frame, chunk_size)
        self._validate_fixed_shape(frame, channel_count, sample_shape, data.dtype.str)

        self._chunk_index += 1
        file_name = f"chunk-{self._chunk_index:06d}.npz"
        timestamps_ns = np.asarray(int(frame.timestamp_ns), dtype=np.int64) + (
            np.arange(chunk_size, dtype=np.int64) * int(self._sample_period_ns)
        )
        chunk_manifest = {
            "chunk_index": self._chunk_index,
            "chunk_seq": None if frame.seq is None else int(frame.seq),
            "chunk_start_timestamp_ns": int(frame.timestamp_ns),
            "sample_count": chunk_size,
            "shape": [int(value) for value in data.shape],
            "dtype": data.dtype.str,
            "extra": to_json_value(frame.extra),
        }
        write_npz(
            self.chunks_dir / file_name,
            data=np.ascontiguousarray(data),
            timestamps_ns=timestamps_ns,
            manifest_json=np.asarray(to_json_text(chunk_manifest)),
        )
        self._chunks_writer.writerow(
            [
                self._chunk_index,
                "" if frame.seq is None else int(frame.seq),
                int(frame.timestamp_ns),
                chunk_size,
                file_name,
                to_json_text([int(value) for value in data.shape]),
                data.dtype.str,
                to_json_text(frame.extra),
            ]
        )
        self._chunks_file.flush()
        self._frame_count += 1
        self._sample_count += chunk_size

    def close(self) -> None:
        self._chunks_file.close()
        self._write_stream_manifest()

    def _validate_chunk_size(self, frame: FrameEnvelope, chunk_size: int) -> None:
        if chunk_size != self._declared_chunk_size:
            raise ValueError(
                f"stream_id={frame.stream_id}: chunk_size changed from {self._declared_chunk_size} to {chunk_size}"
            )

    def _validate_fixed_shape(
        self,
        frame: FrameEnvelope,
        channel_count: int,
        sample_shape: tuple[int, ...],
        dtype_str: str,
    ) -> None:
        if self._channel_count is None:
            self._channel_count = channel_count
            self._sample_shape = sample_shape
            self._dtype_str = dtype_str
            return

        if channel_count != self._channel_count:
            raise ValueError(
                f"stream_id={frame.stream_id}: channel count changed from {self._channel_count} to {channel_count}"
            )
        if sample_shape != self._sample_shape:
            raise ValueError(
                f"stream_id={frame.stream_id}: sample shape changed from {self._sample_shape} to {sample_shape}"
            )
        if dtype_str != self._dtype_str:
            raise ValueError(
                f"stream_id={frame.stream_id}: dtype changed from {self._dtype_str} to {dtype_str}"
            )

    def _write_stream_manifest(self) -> None:
        write_json(
            self.stream_dir / "stream.json",
            {
                "schema_version": SCHEMA_VERSION,
                "stream_id": self.descriptor.stream_id,
                "modality": self.descriptor.modality,
                "display_name": self.descriptor.display_name,
                "payload_type": self.descriptor.payload_type,
                "descriptor": descriptor_to_dict(self.descriptor),
                "storage_kind": "npz_chunks",
                "shape_kind": self._shape_kind,
                "dtype": self._dtype_str,
                "frame_count": self.frame_count,
                "sample_count": self.sample_count,
                "chunk_count": self.chunk_count,
                "channel_count": self._channel_count,
                "sample_shape": list(self._sample_shape or ()),
                "nominal_sample_rate_hz": self._nominal_sample_rate_hz,
                "declared_chunk_size": self._declared_chunk_size,
                "chunks_index_path": "chunks.csv",
                "chunks_path": "chunks",
            },
        )


def descriptor_to_dict(descriptor: StreamDescriptor) -> dict[str, Any]:
    return {
        "device_id": descriptor.device_id,
        "stream_id": descriptor.stream_id,
        "modality": descriptor.modality,
        "payload_type": descriptor.payload_type,
        "nominal_sample_rate_hz": descriptor.nominal_sample_rate_hz,
        "chunk_size": descriptor.chunk_size,
        "channel_names": to_json_value(descriptor.channel_names),
        "display_name": descriptor.display_name,
        "metadata": to_json_value(descriptor.metadata),
    }


def descriptor_from_dict(payload: dict[str, Any]) -> StreamDescriptor:
    return StreamDescriptor(
        device_id=str(payload["device_id"]),
        modality=str(payload["modality"]),
        payload_type=str(payload["payload_type"]),  # type: ignore[arg-type]
        nominal_sample_rate_hz=float(payload["nominal_sample_rate_hz"]),
        chunk_size=int(payload["chunk_size"]),
        channel_names=tuple(str(item) for item in payload.get("channel_names", [])),
        display_name=None if payload.get("display_name") is None else str(payload["display_name"]),
        metadata={} if not isinstance(payload.get("metadata"), dict) else dict(payload["metadata"]),
    )


def normalize_data_array(frame: FrameEnvelope, *, expected_ndim: int) -> np.ndarray:
    data = np.asarray(frame.data)
    if data.dtype == np.dtype("O"):
        raise ValueError(f"stream_id={frame.stream_id}: object dtype arrays are not supported")
    if data.ndim != expected_ndim:
        raise ValueError(
            f"stream_id={frame.stream_id}: expected data.ndim == {expected_ndim}, got {data.ndim}"
        )
    return np.ascontiguousarray(data)


def declared_chunk_size(descriptor: StreamDescriptor) -> int:
    try:
        value = int(descriptor.chunk_size)
    except (TypeError, ValueError):
        raise ValueError(
            f"stream_id={descriptor.stream_id}: descriptor.chunk_size must be a positive integer"
        ) from None
    if value <= 0:
        raise ValueError(
            f"stream_id={descriptor.stream_id}: descriptor.chunk_size must be positive"
        )
    return value


def nominal_sample_rate_hz(descriptor: StreamDescriptor) -> float:
    try:
        value = float(descriptor.nominal_sample_rate_hz)
    except (TypeError, ValueError):
        raise ValueError(
            f"stream_id={descriptor.stream_id}: descriptor.nominal_sample_rate_hz must be positive"
        ) from None
    if value <= 0:
        raise ValueError(
            f"stream_id={descriptor.stream_id}: descriptor.nominal_sample_rate_hz must be positive"
        )
    return value


def resolve_payload_layout(payload_type: str) -> tuple[int, str]:
    if payload_type == "signal":
        return 2, "channels_by_time"
    if payload_type == "raster":
        return 3, "channels_by_time_by_width"
    if payload_type == "field":
        return 4, "channels_by_time_by_height_by_width"
    if payload_type == "video":
        return 4, "channels_by_time_by_height_by_width"
    raise ValueError(f"unsupported payload_type '{payload_type}'")
