from __future__ import annotations

import time

from packages.modlink_shared import StreamDescriptor

from .base import Driver
from .sources import FrameSource, MicrophoneFrameSource

MINIMAL_STREAM_ID = "minimal.microphone"


class MinimalDriver(Driver):
    """Smallest driver shell with data capture delegated to a source."""

    def __init__(
        self,
        *,
        device_id: str = "minimal.driver",
        display_name: str = "Minimal Driver",
        stream_id: str = MINIMAL_STREAM_ID,
        source: FrameSource | None = None,
    ) -> None:
        super().__init__()
        self._device_id = device_id
        self._display_name = display_name
        self._source = source or MicrophoneFrameSource(
            stream_id=stream_id,
            display_name="Minimal Microphone",
            parent=self,
        )
        if self._source.parent() is None:
            self._source.setParent(self)
        elif self._source.parent() is not self:
            raise ValueError(
                "MinimalDriver source must not already belong to another QObject"
            )

        self._source.sig_frame.connect(self.sig_frame)
        self._source.sig_event.connect(self._forward_source_event)

        self._connected = False
        self._streaming = False

    @property
    def device_id(self) -> str:
        return self._device_id

    @property
    def display_name(self) -> str:
        return self._display_name

    def descriptors(self) -> list[StreamDescriptor]:
        return [self._source.descriptor]

    def search(self, request: object | None = None) -> None:
        self.sig_event.emit(
            {
                "kind": "search_finished",
                "request": request,
                "device_id": self._device_id,
                "results": (
                    {
                        "device_id": self._device_id,
                        "name": f"{self._display_name} ({self._source.source_name})",
                        "transport": self._source.transport,
                    },
                ),
                "ts": time.time(),
            }
        )

    def connect_device(self, config: object | None = None) -> None:
        if self._connected:
            return

        try:
            self._source.connect_source(config)
        except Exception as exc:
            self._emit_driver_error("connect_device", exc)
            return

        self._connected = True
        descriptor = self._source.descriptor
        self.sig_event.emit(
            {
                "kind": "connected",
                "device_id": self._device_id,
                "streams": {
                    descriptor.stream_id: {
                        "nominal_sample_rate_hz": descriptor.nominal_sample_rate_hz,
                        "chunk_size": descriptor.chunk_size,
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

        try:
            self._source.disconnect_source()
        except Exception as exc:
            self._emit_driver_error("disconnect_device", exc)
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
        if self._streaming or not self._connected:
            return

        try:
            self._source.start()
        except Exception as exc:
            self._emit_driver_error("start_streaming", exc)
            return

        self._streaming = True
        self.sig_event.emit(
            {
                "kind": "streaming_started",
                "device_id": self._device_id,
                "ts": time.time(),
            }
        )

    def stop_streaming(self) -> None:
        try:
            self._source.stop()
        except Exception as exc:
            self._emit_driver_error("stop_streaming", exc)
            return

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

    def _forward_source_event(self, event: object) -> None:
        if not isinstance(event, dict):
            self.sig_event.emit(event)
            return

        enriched_event = dict(event)
        enriched_event.setdefault("device_id", self._device_id)
        enriched_event.setdefault("source_name", self._source.source_name)
        enriched_event.setdefault("ts", time.time())
        self.sig_event.emit(enriched_event)

    def _emit_driver_error(self, action: str, exc: Exception) -> None:
        self.sig_event.emit(
            {
                "kind": "driver_error",
                "device_id": self._device_id,
                "action": action,
                "message": str(exc),
                "error_type": type(exc).__name__,
                "ts": time.time(),
            }
        )


def create_minimal_driver() -> MinimalDriver:
    return MinimalDriver()
