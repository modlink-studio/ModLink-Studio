from __future__ import annotations

import math
import time

import numpy as np
from PyQt6.QtCore import QTimer, pyqtBoundSignal, pyqtSignal

from packages.modlink_core.settings.service import SettingsService
from packages.modlink_shared import FrameEnvelope, StreamDescriptor

from .base import Driver
from .chunking import (
    chunk_duration_ns,
    normalize_chunk_size,
    normalize_nominal_sample_rate_hz,
    timer_interval_ms,
)

MOCK_EEG_STREAM_ID = "mock.eeg"
MOCK_MOTION_STREAM_ID = "mock.motion"
MOCK_EEG_NOMINAL_SAMPLE_RATE_HZ = 250.0
MOCK_MOTION_NOMINAL_SAMPLE_RATE_HZ = 50.0
DEFAULT_CHUNK_SIZE = 10


class MockDriver(Driver):
    """Small self-contained driver used for local development."""

    sig_eeg_frame = pyqtSignal(FrameEnvelope)
    sig_motion_frame = pyqtSignal(FrameEnvelope)

    def __init__(
        self,
        *,
        device_id: str = "mock.driver",
        display_name: str = "Mock Driver",
        eeg_stream_id: str = MOCK_EEG_STREAM_ID,
        motion_stream_id: str = MOCK_MOTION_STREAM_ID,
    ) -> None:
        super().__init__()
        self._device_id = device_id
        self._display_name = display_name
        self._eeg_stream_id = eeg_stream_id
        self._motion_stream_id = motion_stream_id
        self._connected = False
        self._streaming = False
        self._eeg_timer: QTimer | None = None
        self._motion_timer: QTimer | None = None
        self._eeg_seq = 0
        self._motion_seq = 0
        self._eeg_sample_index = 0
        self._motion_sample_index = 0
        self._eeg_next_chunk_start_ns: int | None = None
        self._motion_next_chunk_start_ns: int | None = None
        self._eeg_config = _load_stream_config(
            driver_id=self._device_id,
            stream_id=self._eeg_stream_id,
            default_nominal_sample_rate_hz=MOCK_EEG_NOMINAL_SAMPLE_RATE_HZ,
            default_chunk_size=DEFAULT_CHUNK_SIZE,
        )
        self._motion_config = _load_stream_config(
            driver_id=self._device_id,
            stream_id=self._motion_stream_id,
            default_nominal_sample_rate_hz=MOCK_MOTION_NOMINAL_SAMPLE_RATE_HZ,
            default_chunk_size=DEFAULT_CHUNK_SIZE,
        )
        self._rebuild_descriptors()

    @property
    def device_id(self) -> str:
        return self._device_id

    @property
    def display_name(self) -> str:
        return self._display_name

    def streams(self) -> list[tuple[StreamDescriptor, pyqtBoundSignal]]:
        return [
            (self._eeg_descriptor, self.sig_eeg_frame),
            (self._motion_descriptor, self.sig_motion_frame),
        ]

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
        if config is not None:
            raise ValueError(
                "MockDriver configuration must be provided via settings domains"
            )
        if self._connected:
            return
        self._connected = True
        self.sig_event.emit(
            {
                "kind": "connected",
                "device_id": self._device_id,
                "settings_domain": _driver_settings_domain(self._device_id),
                "streams": {
                    self._eeg_stream_id: dict(self._eeg_config),
                    self._motion_stream_id: dict(self._motion_config),
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

        if self._eeg_timer is None:
            self._eeg_timer = QTimer(self)
            self._eeg_timer.timeout.connect(self._emit_eeg_frame)
        if self._motion_timer is None:
            self._motion_timer = QTimer(self)
            self._motion_timer.timeout.connect(self._emit_motion_frame)

        self._eeg_next_chunk_start_ns = None
        self._motion_next_chunk_start_ns = None
        self._eeg_timer.start(
            timer_interval_ms(
                self._eeg_config["nominal_sample_rate_hz"],
                self._eeg_config["chunk_size"],
            )
        )
        self._motion_timer.start(
            timer_interval_ms(
                self._motion_config["nominal_sample_rate_hz"],
                self._motion_config["chunk_size"],
            )
        )
        self._streaming = True
        self.sig_event.emit(
            {
                "kind": "streaming_started",
                "device_id": self._device_id,
                "ts": time.time(),
            }
        )

    def stop_streaming(self) -> None:
        if self._eeg_timer is not None:
            self._eeg_timer.stop()
        if self._motion_timer is not None:
            self._motion_timer.stop()
        self._eeg_next_chunk_start_ns = None
        self._motion_next_chunk_start_ns = None
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

    def _emit_eeg_frame(self) -> None:
        chunk_size = int(self._eeg_config["chunk_size"])
        sample_rate_hz = float(self._eeg_config["nominal_sample_rate_hz"])
        chunk_start_ns = self._next_chunk_start_ns(self._eeg_next_chunk_start_ns)
        eeg_samples: list[list[float]] = []
        for offset in range(chunk_size):
            sample_index = self._eeg_sample_index + offset
            phase = sample_index / sample_rate_hz
            eeg_samples.append(
                [
                    45.0 * math.sin(2.0 * math.pi * 8.0 * phase),
                    35.0 * math.sin(2.0 * math.pi * 10.0 * phase + 0.4),
                    30.0 * math.sin(2.0 * math.pi * 12.0 * phase + 0.8),
                    25.0 * math.sin(2.0 * math.pi * 15.0 * phase + 1.2),
                ]
            )

        self.sig_eeg_frame.emit(
            FrameEnvelope(
                stream_id=self._eeg_stream_id,
                timestamp_ns=chunk_start_ns,
                data=np.asarray(eeg_samples, dtype=np.float64).T,
                seq=self._eeg_seq,
                extra={"sample_index0": self._eeg_sample_index},
            )
        )
        self._eeg_seq += 1
        self._eeg_sample_index += chunk_size
        self._eeg_next_chunk_start_ns = chunk_start_ns + chunk_duration_ns(
            sample_rate_hz,
            chunk_size,
        )

    def _emit_motion_frame(self) -> None:
        chunk_size = int(self._motion_config["chunk_size"])
        sample_rate_hz = float(self._motion_config["nominal_sample_rate_hz"])
        chunk_start_ns = self._next_chunk_start_ns(self._motion_next_chunk_start_ns)
        motion_samples: list[list[float]] = []
        for offset in range(chunk_size):
            sample_index = self._motion_sample_index + offset
            phase = sample_index / sample_rate_hz
            motion_samples.append(
                [
                    0.2 * math.sin(2.0 * math.pi * 0.7 * phase),
                    0.15 * math.sin(2.0 * math.pi * 1.2 * phase + 0.6),
                    1.0 + 0.1 * math.sin(2.0 * math.pi * 0.3 * phase + 1.1),
                ]
            )

        self.sig_motion_frame.emit(
            FrameEnvelope(
                stream_id=self._motion_stream_id,
                timestamp_ns=chunk_start_ns,
                data=np.asarray(motion_samples, dtype=np.float64).T,
                seq=self._motion_seq,
                extra={"sample_index0": self._motion_sample_index},
            )
        )
        self._motion_seq += 1
        self._motion_sample_index += chunk_size
        self._motion_next_chunk_start_ns = chunk_start_ns + chunk_duration_ns(
            sample_rate_hz,
            chunk_size,
        )

    def _rebuild_descriptors(self) -> None:
        self._eeg_descriptor = StreamDescriptor(
            stream_id=self._eeg_stream_id,
            modality="eeg",
            payload_type="line",
            nominal_sample_rate_hz=self._eeg_config["nominal_sample_rate_hz"],
            chunk_size=self._eeg_config["chunk_size"],
            display_name="Mock EEG",
            metadata={
                "channel_names": ["C3", "C4", "P3", "P4"],
                "unit": "uV",
            },
        )
        self._motion_descriptor = StreamDescriptor(
            stream_id=self._motion_stream_id,
            modality="motion",
            payload_type="line",
            nominal_sample_rate_hz=self._motion_config["nominal_sample_rate_hz"],
            chunk_size=self._motion_config["chunk_size"],
            display_name="Mock Motion",
            metadata={
                "channel_names": ["ax", "ay", "az"],
                "unit": "g",
            },
        )

    @staticmethod
    def _next_chunk_start_ns(next_chunk_start_ns: int | None) -> int:
        if next_chunk_start_ns is None:
            return time.time_ns()
        return next_chunk_start_ns


def create_mock_driver() -> MockDriver:
    return MockDriver()


def _load_stream_config(
    *,
    driver_id: str,
    stream_id: str,
    default_nominal_sample_rate_hz: float,
    default_chunk_size: int,
) -> dict[str, float | int]:
    settings = SettingsService.instance()
    sample_rate_key = _stream_setting_key(
        driver_id,
        stream_id,
        "nominal_sample_rate_hz",
    )
    chunk_size_key = _stream_setting_key(driver_id, stream_id, "chunk_size")

    nominal_sample_rate_hz = settings.get(sample_rate_key)
    if nominal_sample_rate_hz is None:
        nominal_sample_rate_hz = default_nominal_sample_rate_hz
        settings.set(sample_rate_key, nominal_sample_rate_hz, persist=False)
    nominal_sample_rate_hz = normalize_nominal_sample_rate_hz(nominal_sample_rate_hz)

    chunk_size = settings.get(chunk_size_key)
    if chunk_size is None:
        chunk_size = default_chunk_size
        settings.set(chunk_size_key, chunk_size, persist=False)
    chunk_size = normalize_chunk_size(chunk_size)

    return {
        "nominal_sample_rate_hz": nominal_sample_rate_hz,
        "chunk_size": chunk_size,
    }


def _driver_settings_domain(driver_id: str) -> str:
    return f"drivers.{_settings_scope_component(driver_id)}"


def _stream_setting_key(driver_id: str, stream_id: str, leaf: str) -> str:
    return (
        f"{_driver_settings_domain(driver_id)}."
        f"streams.{_settings_scope_component(stream_id)}.{leaf}"
    )


def _settings_scope_component(value: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError("settings scope component must not be empty")
    return normalized.replace(".", "__")
