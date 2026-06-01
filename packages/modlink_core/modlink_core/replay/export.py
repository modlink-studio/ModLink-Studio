from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from ..models import ExportJobSnapshot
from .reader import RecordingReader


@dataclass(slots=True)
class _ExportRequest:
    job_id: str
    reader: RecordingReader
    request_summary: str
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
        request_summary: str,
        output_root_dir: Path,
    ) -> ExportJobSnapshot:
        job_id = uuid4().hex
        output_dir = Path(output_root_dir) / reader.recording_id / job_id
        snapshot = ExportJobSnapshot(
            job_id=job_id,
            recording_id=reader.recording_id,
            state="queued",
            progress=0.0,
            output_path=None,
            error=None,
            request_summary=request_summary,
        )
        with self._lock:
            self._jobs[job_id] = snapshot
            self._job_order.append(job_id)
        self._queue.put(
            _ExportRequest(
                job_id=job_id,
                reader=reader,
                request_summary=request_summary,
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

        # Validate that the format prefix matches at least one stream's payload type.
        # Summary is either a bare format_id ("signal_csv") or "stream_id:format_id".
        # Format IDs are prefixed by payload type: signal_*, raster_*, field_*, video_*
        summary = request.request_summary
        format_id = summary.split(":")[-1] if ":" in summary else summary
        required_payload = format_id.split("_")[0]
        available_payload_types = {
            d.payload_type for d in request.reader.descriptors().values()
        }
        if available_payload_types and required_payload not in available_payload_types:
            self._update_job(
                request.job_id,
                state="failed",
                progress=1.0,
                output_path=None,
                error=f"no {required_payload!r} streams in recording",
            )
            return

        try:
            request.output_dir.mkdir(parents=True, exist_ok=True)
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
                state=snapshot.state,
                progress=min(1.0, max(0.0, float(value))),
                output_path=snapshot.output_path,
                error=snapshot.error,
                request_summary=snapshot.request_summary,
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
                state=state,
                progress=min(1.0, max(0.0, float(progress))),
                output_path=output_path,
                error=error,
                request_summary=snapshot.request_summary,
            )

