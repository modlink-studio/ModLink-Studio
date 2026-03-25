from __future__ import annotations

import math
import time

import numpy as np

from modlink_sdk import FrameEnvelope, LoopDriver, SearchResult, StreamDescriptor

DEFAULT_DEVICE_ID = "plane_demo.01"
DEFAULT_SAMPLE_RATE_HZ = 10.0
DEFAULT_CHUNK_SIZE = 1
DEFAULT_CHANNEL_NAMES = ("intensity",)
THERMAL_SHAPE = (72, 96)
PRESSURE_SHAPE = (48, 48)
RASTER_LENGTH = 128


class PlaneDemoDriver(LoopDriver):
    supported_providers = ("demo",)
    loop_interval_ms = int(round(1000 / DEFAULT_SAMPLE_RATE_HZ))

    def __init__(self) -> None:
        super().__init__()
        self._connected = False
        self._seq = 0
        self._phase = 0.0

    @property
    def device_id(self) -> str:
        return DEFAULT_DEVICE_ID

    @property
    def display_name(self) -> str:
        return "Field And Raster Demo"

    def descriptors(self) -> list[StreamDescriptor]:
        return [
            StreamDescriptor(
                device_id=self.device_id,
                modality="thermal",
                payload_type="field",
                nominal_sample_rate_hz=DEFAULT_SAMPLE_RATE_HZ,
                chunk_size=DEFAULT_CHUNK_SIZE,
                channel_names=DEFAULT_CHANNEL_NAMES,
                display_name="Thermal Map Demo",
                metadata={
                    "unit": "degC",
                    "height": THERMAL_SHAPE[0],
                    "width": THERMAL_SHAPE[1],
                    "demo_kind": "thermal_map",
                },
            ),
            StreamDescriptor(
                device_id=self.device_id,
                modality="pressure",
                payload_type="field",
                nominal_sample_rate_hz=DEFAULT_SAMPLE_RATE_HZ,
                chunk_size=DEFAULT_CHUNK_SIZE,
                channel_names=DEFAULT_CHANNEL_NAMES,
                display_name="Pressure Map Demo",
                metadata={
                    "unit": "kPa",
                    "height": PRESSURE_SHAPE[0],
                    "width": PRESSURE_SHAPE[1],
                    "demo_kind": "pressure_map",
                },
            ),
            StreamDescriptor(
                device_id=self.device_id,
                modality="spectrogram",
                payload_type="raster",
                nominal_sample_rate_hz=DEFAULT_SAMPLE_RATE_HZ,
                chunk_size=DEFAULT_CHUNK_SIZE,
                channel_names=DEFAULT_CHANNEL_NAMES,
                display_name="Spectrogram Raster Demo",
                metadata={
                    "unit": "a.u.",
                    "length": RASTER_LENGTH,
                    "demo_kind": "spectrogram_raster",
                },
            ),
        ]

    def search(self, provider: str) -> list[SearchResult]:
        if provider != "demo":
            raise ValueError("Plane demo provider must be 'demo'")
        return [
            SearchResult(
                title="Plane Demo Device",
                subtitle="Local synthetic field maps and raster spectrogram",
                device_id=self.device_id,
                extra={"demo": True},
            )
        ]

    def connect_device(self, config: SearchResult) -> None:
        self._connected = True
        self._seq = 0
        self._phase = 0.0

    def disconnect_device(self) -> None:
        self.stop_streaming()
        self._connected = False
        self._seq = 0
        self._phase = 0.0

    def on_loop_started(self) -> None:
        if not self._connected:
            raise RuntimeError("device is not connected")
        self._seq = 0
        self._phase = 0.0

    def on_loop_stopped(self) -> None:
        self._phase = 0.0

    def loop(self) -> None:
        if not self._connected:
            return

        timestamp_ns = time.time_ns()
        thermal_frame = np.ascontiguousarray(
            self._build_thermal_map(self._phase)[np.newaxis, np.newaxis, :, :],
            dtype=np.float32,
        )
        pressure_frame = np.ascontiguousarray(
            self._build_pressure_map(self._phase)[np.newaxis, np.newaxis, :, :],
            dtype=np.float32,
        )
        raster_line = np.ascontiguousarray(
            self._build_raster_line(self._phase)[np.newaxis, np.newaxis, :],
            dtype=np.float32,
        )

        self.sig_frame.emit(
            FrameEnvelope(
                device_id=self.device_id,
                modality="thermal",
                timestamp_ns=timestamp_ns,
                data=thermal_frame,
                seq=self._seq,
            )
        )
        self.sig_frame.emit(
            FrameEnvelope(
                device_id=self.device_id,
                modality="pressure",
                timestamp_ns=timestamp_ns,
                data=pressure_frame,
                seq=self._seq,
            )
        )
        self.sig_frame.emit(
            FrameEnvelope(
                device_id=self.device_id,
                modality="spectrogram",
                timestamp_ns=timestamp_ns,
                data=raster_line,
                seq=self._seq,
            )
        )

        self._seq += 1
        self._phase += 0.12

    def _build_thermal_map(self, phase: float) -> np.ndarray:
        height, width = THERMAL_SHAPE
        y = np.linspace(-1.0, 1.0, height, dtype=np.float32)
        x = np.linspace(-1.0, 1.0, width, dtype=np.float32)
        yy, xx = np.meshgrid(y, x, indexing="ij")

        cx = 0.55 * math.sin(phase * 0.9)
        cy = 0.45 * math.cos(phase * 0.7)
        hotspot = np.exp(-(((xx - cx) ** 2) + ((yy - cy) ** 2)) / 0.12)
        wave = 0.18 * np.sin((xx * 5.5) + phase * 1.4) + 0.14 * np.cos(
            (yy * 4.0) - phase * 1.1
        )
        return np.asarray(24.0 + 9.5 * hotspot + 2.0 * wave, dtype=np.float32)

    def _build_pressure_map(self, phase: float) -> np.ndarray:
        height, width = PRESSURE_SHAPE
        y = np.linspace(-1.0, 1.0, height, dtype=np.float32)
        x = np.linspace(-1.0, 1.0, width, dtype=np.float32)
        yy, xx = np.meshgrid(y, x, indexing="ij")

        left = np.exp(-(((xx + 0.38) ** 2) / 0.11 + ((yy - 0.08) ** 2) / 0.30))
        right = np.exp(-(((xx - 0.38) ** 2) / 0.11 + ((yy + 0.04) ** 2) / 0.28))
        gait = 0.35 + 0.25 * math.sin(phase * 1.6)
        ripple = 0.05 * np.sin((xx + yy) * 10.0 - phase * 2.2)
        return np.asarray(
            22.0 + 26.0 * (left + gait * right) + 4.0 * ripple,
            dtype=np.float32,
        )

    def _build_raster_line(self, phase: float) -> np.ndarray:
        x = np.linspace(0.0, 1.0, RASTER_LENGTH, dtype=np.float32)
        peak_center = 0.25 + 0.45 * (0.5 + 0.5 * math.sin(phase * 0.8))
        peak = np.exp(-((x - peak_center) ** 2) / 0.004)
        harmonics = (
            0.25 * np.sin((x * 22.0) + phase * 1.7)
            + 0.18 * np.cos((x * 34.0) - phase * 2.4)
            + 0.12 * np.sin((x * 48.0) + phase * 0.9)
        )
        return np.asarray(0.45 + 0.95 * peak + harmonics, dtype=np.float32)
