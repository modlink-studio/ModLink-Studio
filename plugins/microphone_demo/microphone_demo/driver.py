from __future__ import annotations

import time

import numpy as np
import sounddevice as sd

from modlink_sdk import Driver, FrameEnvelope, SearchResult, StreamDescriptor

DEFAULT_DEVICE_ID = "microphone_demo.01"
DEFAULT_SAMPLE_RATE_HZ = 16_000.0
DEFAULT_CHUNK_SIZE = 1024


class MicrophoneDemoDriver(Driver):
    supported_providers = ("audio",)

    def __init__(self) -> None:
        super().__init__()
        self._device_index: int | None = None
        self._stream: sd.InputStream | None = None
        self._seq = 0

    @property
    def device_id(self) -> str:
        return DEFAULT_DEVICE_ID

    @property
    def display_name(self) -> str:
        return "Microphone Demo"

    def descriptors(self) -> list[StreamDescriptor]:
        return [
            StreamDescriptor(
                device_id=self.device_id,
                modality="audio",
                payload_type="line",
                nominal_sample_rate_hz=DEFAULT_SAMPLE_RATE_HZ,
                chunk_size=DEFAULT_CHUNK_SIZE,
                channel_names=("mic",),
                unit=None,
                display_name="Microphone Waveform",
            )
        ]

    def search(self, provider: str) -> list[SearchResult]:
        if provider != "audio":
            raise ValueError("Microphone demo provider must be 'audio'")

        return [
            SearchResult(
                title=device["name"],
                subtitle=f"index={index}",
                extra={"device_index": index},
            )
            for index, device in enumerate(sd.query_devices())
            if device["max_input_channels"] > 0
        ]

    def connect_device(self, config: SearchResult) -> None:
        self._device_index = int(config.extra["device_index"])
        self._seq = 0

    def disconnect_device(self) -> None:
        self.stop_streaming()
        self._device_index = None
        self._seq = 0

    def start_streaming(self) -> None:
        if self._device_index is None:
            raise RuntimeError("device is not connected")
        if self._stream is not None:
            return

        self._stream = sd.InputStream(
            device=self._device_index,
            channels=1,
            samplerate=DEFAULT_SAMPLE_RATE_HZ,
            blocksize=DEFAULT_CHUNK_SIZE,
            callback=self._on_audio,
        )
        self._stream.start()

    def stop_streaming(self) -> None:
        if self._stream is None:
            return
        try:
            self._stream.stop()
        finally:
            self._stream.close()
            self._stream = None

    def _on_audio(
        self,
        indata: np.ndarray,
        frames: int,
        timestamp: object,
        status: sd.CallbackFlags,
    ) -> None:
        if status:
            print(status)

        self.sig_frame.emit(
            FrameEnvelope(
                device_id=self.device_id,
                modality="audio",
                timestamp_ns=time.time_ns(),
                data=np.ascontiguousarray(indata[:, 0], dtype=np.float32)[
                    np.newaxis, :
                ],
                seq=self._seq,
            )
        )
        self._seq += 1
