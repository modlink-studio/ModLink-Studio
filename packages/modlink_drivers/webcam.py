from __future__ import annotations

import time
from dataclasses import dataclass

from PyQt6.QtCore import QTimer, pyqtBoundSignal, pyqtSignal

from packages.modlink_shared import FrameEnvelope, StreamDescriptor

from .base import Driver
from .video_support import VideoStreamProfile, WebcamCaptureSource

DEFAULT_CAMERA_INDEX = 0
DEFAULT_FRAME_WIDTH = 640
DEFAULT_FRAME_HEIGHT = 480
DEFAULT_FPS = 30.0
WEBCAM_STREAM_ID = "webcam.video"


@dataclass(slots=True)
class WebcamDriverState:
    connected: bool = False
    streaming: bool = False
    sequence: int = 0


class WebcamDriver(Driver):
    """Minimal webcam driver that publishes RGB video frames."""

    sig_video_frame = pyqtSignal(FrameEnvelope)

    def __init__(
        self,
        *,
        camera_index: int = DEFAULT_CAMERA_INDEX,
        frame_width: int = DEFAULT_FRAME_WIDTH,
        frame_height: int = DEFAULT_FRAME_HEIGHT,
        nominal_fps: float = DEFAULT_FPS,
        device_id: str = "webcam.driver",
        display_name: str = "Webcam",
        stream_id: str = WEBCAM_STREAM_ID,
    ) -> None:
        super().__init__()
        self._device_id = device_id
        self._display_name = display_name
        self._profile = VideoStreamProfile(
            stream_id=stream_id,
            device_id=device_id,
            display_name=display_name,
            camera_index=int(camera_index),
            frame_width=int(frame_width),
            frame_height=int(frame_height),
            nominal_fps=float(nominal_fps),
        )
        self._source = WebcamCaptureSource(
            camera_index=int(camera_index),
            frame_width=int(frame_width),
            frame_height=int(frame_height),
            nominal_fps=float(nominal_fps),
        )
        self._state = WebcamDriverState()
        self._timer: QTimer | None = None

    @property
    def device_id(self) -> str:
        return self._device_id

    @property
    def display_name(self) -> str:
        return self._display_name

    def streams(self) -> list[tuple[StreamDescriptor, pyqtBoundSignal]]:
        return [(self._profile.descriptor(), self.sig_video_frame)]

    def search(self, request: object | None = None) -> None:
        self.sig_event.emit(
            {
                "kind": "search_finished",
                "request": request,
                "device_id": self._device_id,
                "results": (
                    {
                        "device_id": self._device_id,
                        "name": self._display_name,
                        "transport": "camera",
                        "index": self._profile.camera_index,
                    },
                ),
                "ts": time.time(),
            }
        )

    def connect_device(self, config: object | None = None) -> None:
        if config is not None:
            raise ValueError("WebcamDriver does not accept connection config")
        if self._state.connected:
            return

        self._source.open()
        self._state.connected = True
        self.sig_event.emit(
            {
                "kind": "connected",
                "device_id": self._device_id,
                "camera_index": self._profile.camera_index,
                "streams": {
                    self._profile.stream_id: {
                        "nominal_sample_rate_hz": self._profile.nominal_fps,
                        "chunk_size": 1,
                        "frame_width": self._profile.frame_width,
                        "frame_height": self._profile.frame_height,
                    }
                },
                "ts": time.time(),
            }
        )

    def disconnect_device(self) -> None:
        if self._state.streaming:
            self.stop_streaming()
        self._source.close()
        if not self._state.connected:
            return
        self._state.connected = False
        self.sig_event.emit(
            {
                "kind": "disconnected",
                "device_id": self._device_id,
                "ts": time.time(),
            }
        )

    def start_streaming(self) -> None:
        if not self._state.connected:
            self.connect_device()
        if self._state.streaming:
            return

        if self._timer is None:
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._emit_frame)

        interval_ms = max(1, round(1000.0 / self._profile.nominal_fps))
        self._timer.start(interval_ms)
        self._state.streaming = True
        self.sig_event.emit(
            {
                "kind": "streaming_started",
                "device_id": self._device_id,
                "ts": time.time(),
            }
        )

    def stop_streaming(self) -> None:
        if self._timer is not None:
            self._timer.stop()
        if not self._state.streaming:
            return
        self._state.streaming = False
        self.sig_event.emit(
            {
                "kind": "streaming_stopped",
                "device_id": self._device_id,
                "ts": time.time(),
            }
        )

    def _emit_frame(self) -> None:
        if not self._source.is_open:
            return

        try:
            rgb_frame = self._source.read_rgb()
        except Exception as exc:
            self.sig_event.emit(
                {
                    "kind": "frame_read_failed",
                    "device_id": self._device_id,
                    "error": f"{type(exc).__name__}: {exc}",
                    "ts": time.time(),
                }
            )
            self.stop_streaming()
            return

        self.sig_video_frame.emit(
            self._profile.make_envelope(rgb_frame, self._state.sequence)
        )
        self._state.sequence += 1


def create_webcam_driver() -> WebcamDriver:
    return WebcamDriver()
