from __future__ import annotations

import csv
import io
import queue
import threading
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import numpy as np

from ..models import ExportJobSnapshot
from ..storage._internal.files import write_json
from .reader import RecordingReader

SUPPORTED_EXPORT_FORMATS = (
    "signal_csv",
    "signal_npz",
    "raster_npz",
    "field_npz",
    "video_frames_zip",
    "recording_bundle_zip",
)

ExportProgress = Callable[[float], None]
Exporter = Callable[[RecordingReader, Path, ExportProgress], None]


@dataclass(slots=True)
class _ExportRequest:
    job_id: str
    reader: RecordingReader
    format_id: str
    output_dir: Path


class ExportService:
    def __init__(self) -> None:
        self._jobs: dict[str, ExportJobSnapshot] = {}
        self._job_order: list[str] = []
        self._lock = threading.RLock()
        self._queue: queue.Queue[_ExportRequest | object] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._shutdown_sentinel = object()
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        self._thread = threading.Thread(
            target=self._run,
            name="modlink.replay.export",
            daemon=True,
        )
        self._started = True
        self._thread.start()

    def shutdown(self, *, timeout_ms: int = 3000) -> None:
        if not self._started:
            return
        self._queue.put(self._shutdown_sentinel)
        thread = self._thread
        if thread is not None:
            thread.join(max(0, timeout_ms) / 1000)
            if thread.is_alive():
                raise TimeoutError(f"replay export shutdown timed out after {timeout_ms}ms")
        self._thread = None
        self._started = False

    def jobs(self) -> tuple[ExportJobSnapshot, ...]:
        with self._lock:
            return tuple(self._jobs[job_id] for job_id in self._job_order)

    def enqueue(
        self,
        reader: RecordingReader,
        format_id: str,
        output_root_dir: Path,
    ) -> ExportJobSnapshot:
        if format_id not in SUPPORTED_EXPORT_FORMATS:
            raise RuntimeError(f"REPLAY_EXPORT_FORMAT_UNSUPPORTED: {format_id}")

        job_id = uuid4().hex
        output_dir = Path(output_root_dir) / reader.recording_id / job_id
        snapshot = ExportJobSnapshot(
            job_id=job_id,
            recording_id=reader.recording_id,
            format_id=format_id,
            state="queued",
            progress=0.0,
            output_path=None,
            error=None,
        )
        with self._lock:
            self._jobs[job_id] = snapshot
            self._job_order.append(job_id)
        self._queue.put(
            _ExportRequest(
                job_id=job_id,
                reader=reader,
                format_id=format_id,
                output_dir=output_dir,
            )
        )
        return snapshot

    def _run(self) -> None:
        while True:
            item = self._queue.get()
            if item is self._shutdown_sentinel:
                return
            self._process_request(item)

    def _process_request(self, request: _ExportRequest) -> None:
        self._update_job(
            request.job_id,
            state="running",
            progress=0.0,
            output_path=None,
            error=None,
        )

        try:
            request.output_dir.mkdir(parents=True, exist_ok=False)
            exporter = _EXPORTERS[request.format_id]
            exporter(request.reader, request.output_dir, lambda value: self._update_progress(request.job_id, value))
        except Exception as exc:
            self._update_job(
                request.job_id,
                state="failed",
                progress=1.0,
                output_path=None,
                error=f"{type(exc).__name__}: {exc}",
            )
            return

        self._update_job(
            request.job_id,
            state="completed",
            progress=1.0,
            output_path=str(request.output_dir),
            error=None,
        )

    def _update_progress(self, job_id: str, value: float) -> None:
        with self._lock:
            snapshot = self._jobs[job_id]
            self._jobs[job_id] = ExportJobSnapshot(
                job_id=snapshot.job_id,
                recording_id=snapshot.recording_id,
                format_id=snapshot.format_id,
                state=snapshot.state,
                progress=min(1.0, max(0.0, float(value))),
                output_path=snapshot.output_path,
                error=snapshot.error,
            )

    def _update_job(
        self,
        job_id: str,
        *,
        state: str,
        progress: float,
        output_path: str | None,
        error: str | None,
    ) -> None:
        with self._lock:
            snapshot = self._jobs[job_id]
            self._jobs[job_id] = ExportJobSnapshot(
                job_id=snapshot.job_id,
                recording_id=snapshot.recording_id,
                format_id=snapshot.format_id,
                state=state,
                progress=min(1.0, max(0.0, float(progress))),
                output_path=output_path,
                error=error,
            )


def _export_signal_csv(reader: RecordingReader, output_dir: Path, update_progress: ExportProgress) -> None:
    signal_streams = _streams_by_type(reader, "signal")
    if not signal_streams:
        raise RuntimeError("recording does not contain signal streams")

    total_frames = sum(len(reader.frames_for_stream(stream_id)) for stream_id in signal_streams)
    processed_frames = 0
    for stream_id in signal_streams:
        descriptor = reader.descriptor(stream_id)
        if descriptor is None:
            continue
        frame_refs = reader.frames_for_stream(stream_id)
        output_path = output_dir / f"{_export_name(reader, stream_id)}.csv"
        channel_names = list(descriptor.channel_names) or [f"ch{index}" for index in range(_channel_count(reader, frame_refs))]
        with output_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["chunk_timestamp_ns", "seq", "sample_offset", *channel_names])
            for ref in frame_refs:
                data = reader.load_frame(ref).data
                normalized = _normalize_signal_frame(data)
                for sample_offset in range(normalized.shape[1]):
                    writer.writerow(
                        [
                            ref.timestamp_ns,
                            "" if ref.seq is None else ref.seq,
                            sample_offset,
                            *normalized[:, sample_offset].tolist(),
                        ]
                    )
                processed_frames += 1
                update_progress(processed_frames / max(1, total_frames))


def _export_signal_npz(reader: RecordingReader, output_dir: Path, update_progress: ExportProgress) -> None:
    signal_streams = _streams_by_type(reader, "signal")
    if not signal_streams:
        raise RuntimeError("recording does not contain signal streams")

    for index, stream_id in enumerate(signal_streams, start=1):
        descriptor = reader.descriptor(stream_id)
        frame_refs = reader.frames_for_stream(stream_id)
        data = np.stack([_normalize_signal_frame(reader.load_frame(ref).data) for ref in frame_refs])
        timestamps_ns = np.asarray([ref.timestamp_ns for ref in frame_refs], dtype=np.int64)
        seq = np.asarray([(-1 if ref.seq is None else ref.seq) for ref in frame_refs], dtype=np.int64)
        export_name = _export_name(reader, stream_id)
        np.savez_compressed(
            output_dir / f"{export_name}.npz",
            data=data,
            timestamps_ns=timestamps_ns,
            seq=seq,
        )
        write_json(
            output_dir / f"{export_name}.json",
            {
                "stream_id": stream_id,
                "payload_type": descriptor.payload_type if descriptor is not None else "signal",
                "channel_names": [] if descriptor is None else list(descriptor.channel_names),
            },
        )
        update_progress(index / max(1, len(signal_streams)))


def _export_raster_npz(reader: RecordingReader, output_dir: Path, update_progress: ExportProgress) -> None:
    _export_stacked_npz(reader, output_dir, update_progress, payload_type="raster")


def _export_field_npz(reader: RecordingReader, output_dir: Path, update_progress: ExportProgress) -> None:
    _export_stacked_npz(reader, output_dir, update_progress, payload_type="field")


def _export_video_frames_zip(reader: RecordingReader, output_dir: Path, update_progress: ExportProgress) -> None:
    video_streams = _streams_by_type(reader, "video")
    if not video_streams:
        raise RuntimeError("recording does not contain video streams")

    for index, stream_id in enumerate(video_streams, start=1):
        zip_path = output_dir / f"{_export_name(reader, stream_id)}.zip"
        frame_refs = reader.frames_for_stream(stream_id)
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            index_buffer = io.StringIO()
            writer = csv.writer(index_buffer)
            writer.writerow(["frame_index", "timestamp_ns", "seq", "file_name"])
            for ref in frame_refs:
                file_name = f"{ref.frame_index:06d}.npy"
                writer.writerow(
                    [
                        ref.frame_index,
                        ref.timestamp_ns,
                        "" if ref.seq is None else ref.seq,
                        file_name,
                    ]
                )
                frame_buffer = io.BytesIO()
                np.save(frame_buffer, reader.load_frame(ref).data)
                archive.writestr(file_name, frame_buffer.getvalue())
            archive.writestr("index.csv", index_buffer.getvalue())
        update_progress(index / max(1, len(video_streams)))


def _export_recording_bundle_zip(
    reader: RecordingReader,
    output_dir: Path,
    update_progress: ExportProgress,
) -> None:
    zip_path = output_dir / f"{reader.recording_id}.zip"
    paths = [path for path in sorted(reader.recording_path.rglob("*")) if path.is_file()]
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for index, path in enumerate(paths, start=1):
            archive.write(path, path.relative_to(reader.recording_path.parent.parent))
            update_progress(index / max(1, len(paths)))


def _export_stacked_npz(
    reader: RecordingReader,
    output_dir: Path,
    update_progress: ExportProgress,
    *,
    payload_type: str,
) -> None:
    stream_ids = _streams_by_type(reader, payload_type)
    if not stream_ids:
        raise RuntimeError(f"recording does not contain {payload_type} streams")

    for index, stream_id in enumerate(stream_ids, start=1):
        descriptor = reader.descriptor(stream_id)
        frame_refs = reader.frames_for_stream(stream_id)
        arrays = [reader.load_frame(ref).data for ref in frame_refs]
        if not arrays:
            raise RuntimeError(f"stream '{stream_id}' does not contain any frames")
        shape = arrays[0].shape
        if any(array.shape != shape for array in arrays[1:]):
            raise RuntimeError(f"stream '{stream_id}' has inconsistent frame shapes")
        export_name = _export_name(reader, stream_id)
        np.savez_compressed(
            output_dir / f"{export_name}.npz",
            data=np.stack(arrays),
            timestamps_ns=np.asarray([ref.timestamp_ns for ref in frame_refs], dtype=np.int64),
            seq=np.asarray([(-1 if ref.seq is None else ref.seq) for ref in frame_refs], dtype=np.int64),
        )
        write_json(
            output_dir / f"{export_name}.json",
            {
                "stream_id": stream_id,
                "payload_type": payload_type,
                "channel_names": [] if descriptor is None else list(descriptor.channel_names),
            },
        )
        update_progress(index / max(1, len(stream_ids)))


def _streams_by_type(reader: RecordingReader, payload_type: str) -> list[str]:
    stream_ids: list[str] = []
    for stream_id, descriptor in reader.descriptors().items():
        if descriptor.payload_type == payload_type:
            stream_ids.append(stream_id)
    return stream_ids


def _normalize_signal_frame(data: np.ndarray) -> np.ndarray:
    array = np.asarray(data)
    if array.ndim == 1:
        return array.reshape(1, array.shape[0])
    if array.ndim != 2:
        raise RuntimeError(f"signal export expects 1D or 2D frames, got shape {array.shape!r}")
    return array


def _channel_count(reader: RecordingReader, frame_refs: tuple[object, ...]) -> int:
    if not frame_refs:
        return 0
    first_frame = reader.load_frame(frame_refs[0]).data  # type: ignore[arg-type]
    return _normalize_signal_frame(first_frame).shape[0]


def _export_name(reader: RecordingReader, stream_id: str) -> str:
    descriptor = reader.descriptor(stream_id)
    base = stream_id if descriptor is None else descriptor.stream_key
    cleaned = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in base)
    cleaned = cleaned.strip("_")
    return cleaned or "stream"


_EXPORTERS: dict[str, Exporter] = {
    "signal_csv": _export_signal_csv,
    "signal_npz": _export_signal_npz,
    "raster_npz": _export_raster_npz,
    "field_npz": _export_field_npz,
    "video_frames_zip": _export_video_frames_zip,
    "recording_bundle_zip": _export_recording_bundle_zip,
}
