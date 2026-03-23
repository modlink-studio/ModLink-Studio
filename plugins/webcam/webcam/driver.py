from __future__ import annotations

import threading
import time

import cv2
import numpy as np

from modlink_sdk import Driver, FrameEnvelope, SearchResult, StreamDescriptor

DEFAULT_DEVICE_ID = "webcam.01"
DEFAULT_FRAME_RATE_FPS = 30.0
DEFAULT_WIDTH = 640
DEFAULT_HEIGHT = 480


class WebcamDriver(Driver):
    supported_providers = ("video",)

    def __init__(self) -> None:
        super().__init__()
        self._camera_index: int | None = None
        self._cap: cv2.VideoCapture | None = None
        self._thread: threading.Thread | None = None
        self._running = False
        self._seq = 0

    @property
    def device_id(self) -> str:
        return DEFAULT_DEVICE_ID

    @property
    def display_name(self) -> str:
        return "Webcam"

    def descriptors(self) -> list[StreamDescriptor]:
        return [
            StreamDescriptor(
                device_id=self.device_id,
                modality="video",
                payload_type="video",
                nominal_sample_rate_hz=DEFAULT_FRAME_RATE_FPS,
                chunk_size=1,
                channel_names=("red", "green", "blue"),
                unit=None,
                display_name="Webcam RGB Stream",
                metadata={"width": DEFAULT_WIDTH, "height": DEFAULT_HEIGHT},
            )
        ]

    def search(self, provider: str) -> list[SearchResult]:
        if provider != "video":
            raise ValueError("Webcam driver provider must be 'video'")

        results: list[SearchResult] = []
        for index in range(10):
            # Try to open camera with default backend
            cap = cv2.VideoCapture(index)
            if cap.isOpened():
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                backend_name = cap.getBackendName()
                cap.release()

                results.append(
                    SearchResult(
                        title=f"Camera {index}",
                        subtitle=f"{width}x{height} | {backend_name}",
                        extra={
                            "camera_index": index,
                            "width": width,
                            "height": height,
                        },
                    )
                )
            else:
                break

        return results

    def connect_device(self, config: SearchResult) -> None:
        self._camera_index = int(config.extra["camera_index"])
        self._seq = 0

    def disconnect_device(self) -> None:
        self.stop_streaming()
        self._camera_index = None
        self._seq = 0

    def start_streaming(self) -> None:
        if self._camera_index is None:
            raise RuntimeError("device is not connected")
        if self._running:
            return

        # Open camera with default backend (auto-detect best backend)
        self._cap = cv2.VideoCapture(self._camera_index)
        if not self._cap.isOpened():
            raise RuntimeError(f"Failed to open camera {self._camera_index}")

        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, DEFAULT_WIDTH)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, DEFAULT_HEIGHT)
        self._cap.set(cv2.CAP_PROP_FPS, DEFAULT_FRAME_RATE_FPS)

        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def stop_streaming(self) -> None:
        if not self._running:
            return

        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def _capture_loop(self) -> None:
        while self._running and self._cap is not None:
            ret, frame = self._cap.read()
            if not ret:
                self.sig_connection_lost.emit(
                    {
                        "code": "WEBCAM_READ_FAILED",
                        "message": "Failed to read frame from webcam",
                        "detail": "Camera connection lost or disconnected",
                    }
                )
                break

            # Convert BGR to RGB (HWC format)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Normalize to 0-1 range and transpose to (channels, height, width)
            chw = (rgb_frame.astype(np.float32) / 255.0).transpose(2, 0, 1)

            # Format for VideoStreamView: (batch=3, time=1, height, width)
            # where batch dimension represents RGB channels
            data = np.ascontiguousarray(
                chw[:, np.newaxis, :, :],  # (3, 1, height, width)
                dtype=np.float32,
            )

            self.sig_frame.emit(
                FrameEnvelope(
                    device_id=self.device_id,
                    modality="video",
                    timestamp_ns=time.time_ns(),
                    data=data,
                    seq=self._seq,
                )
            )
            self._seq += 1

        self._running = False
