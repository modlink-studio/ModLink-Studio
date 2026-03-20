from __future__ import annotations

from dataclasses import dataclass
import time

import cv2
import numpy as np

from packages.modlink_shared import FrameEnvelope, StreamDescriptor


@dataclass(slots=True)
class VideoStreamProfile:
    stream_id: str
    device_id: str
    display_name: str
    camera_index: int
    frame_width: int
    frame_height: int
    nominal_fps: float

    def descriptor(self) -> StreamDescriptor:
        return StreamDescriptor(
            stream_id=self.stream_id,
            modality="video",
            payload_type="video",
            nominal_sample_rate_hz=self.nominal_fps,
            chunk_size=1,
            display_name=self.display_name,
            metadata={
                "camera_index": self.camera_index,
                "frame_width": self.frame_width,
                "frame_height": self.frame_height,
                "color_space": "rgb8",
            },
        )

    def make_envelope(self, frame_rgb: np.ndarray, sequence: int) -> FrameEnvelope:
        return FrameEnvelope(
            stream_id=self.stream_id,
            timestamp_ns=time.time_ns(),
            data=np.ascontiguousarray(frame_rgb),
            seq=sequence,
            extra={
                "camera_index": self.camera_index,
                "frame_width": int(frame_rgb.shape[1]),
                "frame_height": int(frame_rgb.shape[0]),
            },
        )


class WebcamCaptureSource:
    def __init__(
        self,
        *,
        camera_index: int,
        frame_width: int,
        frame_height: int,
        nominal_fps: float,
    ) -> None:
        self._camera_index = int(camera_index)
        self._frame_width = int(frame_width)
        self._frame_height = int(frame_height)
        self._nominal_fps = float(nominal_fps)
        self._capture: cv2.VideoCapture | None = None

    @property
    def is_open(self) -> bool:
        return self._capture is not None

    def open(self) -> None:
        if self._capture is not None:
            return

        capture = cv2.VideoCapture(self._camera_index)
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self._frame_width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self._frame_height)
        capture.set(cv2.CAP_PROP_FPS, self._nominal_fps)
        if not capture.isOpened():
            capture.release()
            raise RuntimeError(f"unable to open camera index {self._camera_index}")
        self._capture = capture

    def close(self) -> None:
        if self._capture is None:
            return
        self._capture.release()
        self._capture = None

    def read_rgb(self) -> np.ndarray:
        if self._capture is None:
            raise RuntimeError("camera source is not open")

        ok, frame = self._capture.read()
        if not ok or frame is None:
            raise RuntimeError(f"unable to read frame from camera index {self._camera_index}")
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
