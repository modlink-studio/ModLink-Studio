from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from PyQt6.QtCore import QTimer, pyqtSignal

from packages.modlink_shared import FrameEnvelope, StreamDescriptor

from .base import Device
from .portal import DriverPortal, StreamRegistry

MOCK_EEG_STREAM_ID = "mock.multimodal.eeg"
MOCK_MOTION_STREAM_ID = "mock.multimodal.motion"


class MockDriverState(str, Enum):
    DISCONNECTED = "disconnected"
    SEARCHING = "searching"
    CONNECTED = "connected"
    STREAMING = "streaming"


@dataclass(slots=True)
class MockDiscoveryResult:
    device_id: str
    name: str
    transport: str
    address: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class MockSearchRequest:
    device_count: int = 2


@dataclass(slots=True)
class MockConnectConfig:
    eeg_sample_rate_hz: float = 250.0
    motion_sample_rate_hz: float = 50.0
    chunk_size: int = 10
    emit_eeg: bool = True
    emit_motion: bool = True
    timer_interval_ms: int = 40


@dataclass(slots=True)
class MockDriverEvent:
    kind: str
    ts: float
    state: MockDriverState
    message: str = ""
    payload: object | None = None


class MockMultimodalDriver(Device):
    """Reference driver used as the baseline backend for ongoing development.

    It behaves like a small real device:
    - can be searched
    - can connect/disconnect
    - can start/stop streaming
    - emits two streams: EEG and motion
    """

    sig_eeg_frame = pyqtSignal(object)
    sig_motion_frame = pyqtSignal(object)

    def __init__(
        self,
        *,
        device_id: str = "mock.multimodal",
        display_name: str = "Mock Multimodal Device",
        auto_start_on_bootstrap: bool = True,
        default_config: MockConnectConfig | None = None,
    ) -> None:
        super().__init__()
        self._device_id = device_id
        self._display_name = display_name
        self._auto_start_on_bootstrap = auto_start_on_bootstrap
        self._config = default_config or MockConnectConfig()
        self._state = MockDriverState.DISCONNECTED
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
                stream_id=MOCK_EEG_STREAM_ID,
                modality="eeg",
                payload_type="timeseries",
                display_name="Mock EEG",
                metadata={
                    "sample_rate_hz": self._config.eeg_sample_rate_hz,
                    "channel_names": ["C3", "C4", "P3", "P4"],
                    "unit": "uV",
                },
            ),
            StreamDescriptor(
                stream_id=MOCK_MOTION_STREAM_ID,
                modality="motion",
                payload_type="timeseries",
                display_name="Mock Motion",
                metadata={
                    "sample_rate_hz": self._config.motion_sample_rate_hz,
                    "channel_names": ["ax", "ay", "az"],
                    "unit": "g",
                },
            ),
        )

    def frame_signal(self, stream_id: str):
        if stream_id == MOCK_EEG_STREAM_ID:
            return self.sig_eeg_frame
        if stream_id == MOCK_MOTION_STREAM_ID:
            return self.sig_motion_frame
        raise KeyError(f"unknown stream_id '{stream_id}'")

    def bootstrap(self) -> None:
        if not self._auto_start_on_bootstrap:
            return
        self.connect_device()
        self.start_streaming()

    def search(self, request: object | None = None) -> None:
        payload = request if isinstance(request, MockSearchRequest) else MockSearchRequest()
        self._emit_event(
            "search_started",
            MockDriverState.SEARCHING,
            message="mock search started",
            payload=payload,
        )
        results = tuple(
            MockDiscoveryResult(
                device_id=f"{self._device_id}-{index + 1}",
                name=f"{self._display_name} #{index + 1}",
                transport="mock",
                address=f"MOCK-{index + 1:02d}",
                metadata={"index": index},
            )
            for index in range(max(1, payload.device_count))
        )
        self._emit_event(
            "search_finished",
            self._state,
            message=f"mock search finished with {len(results)} result(s)",
            payload=results,
        )

    def connect_device(self, config: object | None = None) -> None:
        if isinstance(config, MockConnectConfig):
            self._config = config
        if self._state in {MockDriverState.CONNECTED, MockDriverState.STREAMING}:
            return
        self._reset_counters()
        self._state = MockDriverState.CONNECTED
        self._emit_event(
            "connected",
            self._state,
            message="mock device connected",
            payload=self._config,
        )

    def disconnect_device(self) -> None:
        if self._state == MockDriverState.DISCONNECTED:
            return
        self.stop_streaming()
        self._state = MockDriverState.DISCONNECTED
        self._emit_event(
            "disconnected",
            self._state,
            message="mock device disconnected",
        )

    def start_streaming(self) -> None:
        if self._state == MockDriverState.DISCONNECTED:
            self.connect_device()
        if self._state == MockDriverState.STREAMING:
            return

        timer = self._ensure_stream_timer()
        timer.start(max(1, int(self._config.timer_interval_ms)))
        self._state = MockDriverState.STREAMING
        self._emit_event(
            "streaming_started",
            self._state,
            message="mock streaming started",
            payload=self._config,
        )

    def stop_streaming(self) -> None:
        if self._stream_timer is not None:
            self._stream_timer.stop()
        if self._state != MockDriverState.STREAMING:
            return
        self._state = MockDriverState.CONNECTED
        self._emit_event(
            "streaming_stopped",
            self._state,
            message="mock streaming stopped",
        )

    def _ensure_stream_timer(self) -> QTimer:
        if self._stream_timer is None:
            self._stream_timer = QTimer(self)
            self._stream_timer.timeout.connect(self._emit_next_chunk)
        return self._stream_timer

    def _emit_next_chunk(self) -> None:
        timestamp_ns = time.time_ns()
        if self._config.emit_eeg:
            self.sig_eeg_frame.emit(self._build_eeg_frame(timestamp_ns))
        if self._config.emit_motion:
            self.sig_motion_frame.emit(self._build_motion_frame(timestamp_ns))

    def _build_eeg_frame(self, timestamp_ns: int) -> FrameEnvelope:
        channel_names = ["C3", "C4", "P3", "P4"]
        samples: list[list[float]] = []
        base_index = self._eeg_sample_index
        for offset in range(self._config.chunk_size):
            sample_index = base_index + offset
            phase = sample_index / max(1.0, self._config.eeg_sample_rate_hz)
            samples.append(
                [
                    45.0 * math.sin(2.0 * math.pi * 8.0 * phase),
                    35.0 * math.sin(2.0 * math.pi * 10.0 * phase + 0.4),
                    30.0 * math.sin(2.0 * math.pi * 12.0 * phase + 0.8),
                    25.0 * math.sin(2.0 * math.pi * 15.0 * phase + 1.2),
                ]
            )

        payload = {
            "sample_rate_hz": self._config.eeg_sample_rate_hz,
            "sample_index0": self._eeg_sample_index,
            "channel_names": channel_names,
            "unit": "uV",
            "samples": samples,
        }
        frame = FrameEnvelope(
            stream_id=MOCK_EEG_STREAM_ID,
            timestamp_ns=timestamp_ns,
            payload=payload,
            seq=self._eeg_seq,
        )
        self._eeg_seq += 1
        self._eeg_sample_index += self._config.chunk_size
        return frame

    def _build_motion_frame(self, timestamp_ns: int) -> FrameEnvelope:
        channel_names = ["ax", "ay", "az"]
        samples: list[list[float]] = []
        base_index = self._motion_sample_index
        for offset in range(self._config.chunk_size):
            sample_index = base_index + offset
            phase = sample_index / max(1.0, self._config.motion_sample_rate_hz)
            samples.append(
                [
                    0.2 * math.sin(2.0 * math.pi * 0.7 * phase),
                    0.15 * math.sin(2.0 * math.pi * 1.2 * phase + 0.6),
                    1.0 + 0.1 * math.sin(2.0 * math.pi * 0.3 * phase + 1.1),
                ]
            )

        payload = {
            "sample_rate_hz": self._config.motion_sample_rate_hz,
            "sample_index0": self._motion_sample_index,
            "channel_names": channel_names,
            "unit": "g",
            "samples": samples,
        }
        frame = FrameEnvelope(
            stream_id=MOCK_MOTION_STREAM_ID,
            timestamp_ns=timestamp_ns,
            payload=payload,
            seq=self._motion_seq,
        )
        self._motion_seq += 1
        self._motion_sample_index += self._config.chunk_size
        return frame

    def _reset_counters(self) -> None:
        self._eeg_seq = 0
        self._motion_seq = 0
        self._eeg_sample_index = 0
        self._motion_sample_index = 0

    def _emit_event(
        self,
        kind: str,
        state: MockDriverState,
        *,
        message: str = "",
        payload: object | None = None,
    ) -> None:
        self.sig_event.emit(
            MockDriverEvent(
                kind=kind,
                ts=time.time(),
                state=state,
                message=message,
                payload=payload,
            )
        )


def create_mock_driver_portal(
    stream_registry: StreamRegistry,
    *,
    auto_bootstrap: bool = True,
    parent=None,
) -> DriverPortal:
    return DriverPortal(
        MockMultimodalDriver(auto_start_on_bootstrap=auto_bootstrap),
        stream_registry,
        auto_bootstrap=auto_bootstrap,
        parent=parent,
    )
