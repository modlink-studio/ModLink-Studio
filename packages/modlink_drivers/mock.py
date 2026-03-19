from __future__ import annotations

import math
import time

from PyQt6.QtCore import QTimer, pyqtSignal

from packages.modlink_shared import FrameEnvelope, StreamDescriptor

from .base import Driver

MOCK_EEG_STREAM_ID = "mock.eeg"
MOCK_MOTION_STREAM_ID = "mock.motion"


class MockDriver(Driver):
    """Small self-contained driver used for local development."""

    sig_eeg_frame = pyqtSignal(object)
    sig_motion_frame = pyqtSignal(object)

    def __init__(
        self,
        *,
        device_id: str = "mock.driver",
        display_name: str = "Mock Driver",
        eeg_stream_id: str = MOCK_EEG_STREAM_ID,
        motion_stream_id: str = MOCK_MOTION_STREAM_ID,
        auto_start_on_bootstrap: bool = True,
    ) -> None:
        super().__init__()
        self._device_id = device_id
        self._display_name = display_name
        self._eeg_stream_id = eeg_stream_id
        self._motion_stream_id = motion_stream_id
        self._auto_start_on_bootstrap = auto_start_on_bootstrap
        self._connected = False
        self._streaming = False
        self._stream_timer: QTimer | None = None
        self._eeg_seq = 0
        self._motion_seq = 0
        self._eeg_sample_index = 0
        self._motion_sample_index = 0

    @property
    def device_id(self) -> str:
        return self._device_id

    @property
    def display_name(self) -> str:
        return self._display_name

    def stream_descriptors(self) -> tuple[StreamDescriptor, ...]:
        return (
            StreamDescriptor(
                stream_id=self._eeg_stream_id,
                modality="eeg",
                payload_type="timeseries",
                display_name="Mock EEG",
                metadata={
                    "sample_rate_hz": 250.0,
                    "channel_names": ["C3", "C4", "P3", "P4"],
                    "unit": "uV",
                },
            ),
            StreamDescriptor(
                stream_id=self._motion_stream_id,
                modality="motion",
                payload_type="timeseries",
                display_name="Mock Motion",
                metadata={
                    "sample_rate_hz": 50.0,
                    "channel_names": ["ax", "ay", "az"],
                    "unit": "g",
                },
            ),
        )

    def shutdown(self) -> None:
        self.stop_streaming()
        self.disconnect_device()

    def search(self, request: object | None = None) -> None:
        self.sig_event.emit(
            {
                "kind": "search_started",
                "request": request,
                "device_id": self._device_id,
                "ts": time.time(),
            }
        )
        results = (
            {
                "device_id": f"{self._device_id}.1",
                "name": f"{self._display_name} #1",
                "transport": "mock",
                "address": "MOCK-01",
            },
            {
                "device_id": f"{self._device_id}.2",
                "name": f"{self._display_name} #2",
                "transport": "mock",
                "address": "MOCK-02",
            },
        )
        self.sig_event.emit(
            {
                "kind": "search_finished",
                "results": results,
                "device_id": self._device_id,
                "ts": time.time(),
            }
        )

    def connect_device(self, config: object | None = None) -> None:
        if self._connected:
            return
        self._connected = True
        self.sig_event.emit(
            {
                "kind": "connected",
                "device_id": self._device_id,
                "config": config,
                "ts": time.time(),
            }
        )

    def disconnect_device(self) -> None:
        if self._streaming:
            self.stop_streaming()
        if not self._connected:
            return
        self._connected = False
        self.sig_event.emit(
            {
                "kind": "disconnected",
                "device_id": self._device_id,
                "ts": time.time(),
            }
        )

    def start_streaming(self) -> None:
        if not self._connected:
            self.connect_device()
        if self._streaming:
            return

        self._ensure_stream_timer().start(40)
        self._streaming = True
        self.sig_event.emit(
            {
                "kind": "streaming_started",
                "device_id": self._device_id,
                "ts": time.time(),
            }
        )

    def stop_streaming(self) -> None:
        if self._stream_timer is not None:
            self._stream_timer.stop()
        if not self._streaming:
            return
        self._streaming = False
        self.sig_event.emit(
            {
                "kind": "streaming_stopped",
                "device_id": self._device_id,
                "ts": time.time(),
            }
        )

    def _ensure_stream_timer(self) -> QTimer:
        if self._stream_timer is None:
            self._stream_timer = QTimer(self)
            self._stream_timer.timeout.connect(self._emit_next_chunk)
        return self._stream_timer

    def _emit_next_chunk(self) -> None:
        timestamp_ns = time.time_ns()
        self.sig_eeg_frame.emit(self._build_eeg_frame(timestamp_ns))
        self.sig_motion_frame.emit(self._build_motion_frame(timestamp_ns))

    def _build_eeg_frame(self, timestamp_ns: int) -> FrameEnvelope:
        samples = []
        for offset in range(10):
            sample_index = self._eeg_sample_index + offset
            phase = sample_index / 250.0
            samples.append(
                [
                    45.0 * math.sin(2.0 * math.pi * 8.0 * phase),
                    35.0 * math.sin(2.0 * math.pi * 10.0 * phase + 0.4),
                    30.0 * math.sin(2.0 * math.pi * 12.0 * phase + 0.8),
                    25.0 * math.sin(2.0 * math.pi * 15.0 * phase + 1.2),
                ]
            )

        frame = FrameEnvelope(
            stream_id=self._eeg_stream_id,
            timestamp_ns=timestamp_ns,
            payload={
                "sample_rate_hz": 250.0,
                "sample_index0": self._eeg_sample_index,
                "channel_names": ["C3", "C4", "P3", "P4"],
                "unit": "uV",
                "samples": samples,
            },
            seq=self._eeg_seq,
        )
        self._eeg_seq += 1
        self._eeg_sample_index += 10
        return frame

    def _build_motion_frame(self, timestamp_ns: int) -> FrameEnvelope:
        samples = []
        for offset in range(10):
            sample_index = self._motion_sample_index + offset
            phase = sample_index / 50.0
            samples.append(
                [
                    0.2 * math.sin(2.0 * math.pi * 0.7 * phase),
                    0.15 * math.sin(2.0 * math.pi * 1.2 * phase + 0.6),
                    1.0 + 0.1 * math.sin(2.0 * math.pi * 0.3 * phase + 1.1),
                ]
            )

        frame = FrameEnvelope(
            stream_id=self._motion_stream_id,
            timestamp_ns=timestamp_ns,
            payload={
                "sample_rate_hz": 50.0,
                "sample_index0": self._motion_sample_index,
                "channel_names": ["ax", "ay", "az"],
                "unit": "g",
                "samples": samples,
            },
            seq=self._motion_seq,
        )
        self._motion_seq += 1
        self._motion_sample_index += 10
        return frame
