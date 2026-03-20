from __future__ import annotations

import time

import numpy as np
from PyQt6.QtCore import QTimer

from packages.modlink_shared import FrameEnvelope, StreamDescriptor

from .base import Driver

DEFAULT_SAMPLE_RATE_HZ = 10.0
MINIMAL_STREAM_ID = "minimal.counter"


class MinimalDriver(Driver):
    """Smallest built-in driver that still exercises the current framework."""

    def __init__(
        self,
        *,
        device_id: str = "minimal.driver",
        display_name: str = "Minimal Driver",
        stream_id: str = MINIMAL_STREAM_ID,
        sample_rate_hz: float = DEFAULT_SAMPLE_RATE_HZ,
    ) -> None:
        super().__init__()
        self._device_id = device_id
        self._display_name = display_name
        self._descriptor = StreamDescriptor(
            stream_id=stream_id,
            modality="demo",
            payload_type="line",
            nominal_sample_rate_hz=float(sample_rate_hz),
            chunk_size=1,
            display_name="Minimal Counter",
            metadata={
                "channel_names": ["value"],
                "unit": "count",
            },
        )
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._emit_frame)
        self._connected = False
        self._streaming = False
        self._sequence = 0

    @property
    def device_id(self) -> str:
        return self._device_id

    @property
    def display_name(self) -> str:
        return self._display_name

    def descriptors(self) -> list[StreamDescriptor]:
        return [self._descriptor]

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
                        "transport": "demo",
                    },
                ),
                "ts": time.time(),
            }
        )

    def connect_device(self, config: object | None = None) -> None:
        if config is not None:
            raise ValueError("MinimalDriver does not accept connection config")
        if self._connected:
            return
        self._connected = True
        self.sig_event.emit(
            {
                "kind": "connected",
                "device_id": self._device_id,
                "streams": {
                    self._descriptor.stream_id: {
                        "nominal_sample_rate_hz": self._descriptor.nominal_sample_rate_hz,
                        "chunk_size": self._descriptor.chunk_size,
                    }
                },
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
        interval_ms = max(1, round(1000.0 / self._descriptor.nominal_sample_rate_hz))
        self._timer.start(interval_ms)
        self._streaming = True
        self.sig_event.emit(
            {
                "kind": "streaming_started",
                "device_id": self._device_id,
                "ts": time.time(),
            }
        )

    def stop_streaming(self) -> None:
        self._timer.stop()
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

    def _emit_frame(self) -> None:
        sequence = self._sequence
        self.sig_frame.emit(
            FrameEnvelope(
                stream_id=self._descriptor.stream_id,
                timestamp_ns=time.time_ns(),
                data=np.asarray([[float(sequence)]], dtype=np.float64),
                seq=sequence,
            )
        )
        self._sequence += 1


def create_minimal_driver() -> MinimalDriver:
    return MinimalDriver()
