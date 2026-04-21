from __future__ import annotations

import queue
from threading import RLock, Thread

from modlink_core.bus import FrameStream
from modlink_core.event_stream import StreamClosedError
from modlink_sdk import FrameEnvelope

from .bus import QtBusBridge


class LatestFramePump:
    """Owns one frame-stream worker and emits only the latest frame per stream."""

    def __init__(
        self,
        bus: QtBusBridge,
        *,
        thread_name: str,
        read_timeout: float | None = None,
    ) -> None:
        self._bus = bus
        self._thread_name = str(thread_name)
        self._read_timeout = None if read_timeout is None else max(0.0, float(read_timeout))
        self._frame_stream: FrameStream | None = None
        self._thread: Thread | None = None
        self._shutdown = False
        self._lock = RLock()

    def attach_stream(self, frame_stream: FrameStream) -> None:
        self.stop_stream()
        with self._lock:
            if self._shutdown:
                frame_stream.close()
                return
            self._frame_stream = frame_stream
            thread = Thread(
                target=self._run,
                args=(frame_stream,),
                name=self._thread_name,
                daemon=True,
            )
            self._thread = thread
        thread.start()

    def stop_stream(self, *, join_timeout: float = 1.0) -> None:
        with self._lock:
            frame_stream = self._frame_stream
            thread = self._thread
            self._frame_stream = None
            self._thread = None
        if frame_stream is not None:
            frame_stream.close()
        if thread is not None and thread.is_alive():
            thread.join(join_timeout)

    def shutdown(self, *, join_timeout: float = 1.0) -> None:
        with self._lock:
            if self._shutdown:
                return
            self._shutdown = True
        self.stop_stream(join_timeout=join_timeout)

    def _run(self, frame_stream: FrameStream) -> None:
        while True:
            try:
                first_frame = self._read_first_frame(frame_stream)
            except queue.Empty:
                continue
            except StreamClosedError:
                return

            try:
                frames = [first_frame, *frame_stream.read_many()]
            except StreamClosedError:
                self._bus._emit_frames(_coalesce_latest_frames([first_frame]))
                return
            self._bus._emit_frames(_coalesce_latest_frames(frames))

    def _read_first_frame(self, frame_stream: FrameStream) -> FrameEnvelope:
        if self._read_timeout is None:
            return frame_stream.read()
        return frame_stream.read(timeout=self._read_timeout)


def _coalesce_latest_frames(frames: list[object]) -> list[FrameEnvelope]:
    latest_by_stream: dict[str, FrameEnvelope] = {}
    for frame in frames:
        if isinstance(frame, FrameEnvelope):
            latest_by_stream[frame.stream_id] = frame
    return list(latest_by_stream.values())
