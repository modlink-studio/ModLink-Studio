from __future__ import annotations

import time

import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtMultimedia import (
    QAudioDevice,
    QAudioFormat,
    QAudioSource,
    QMediaDevices,
)

from packages.modlink_shared import FrameEnvelope, StreamDescriptor

from .chunking import chunk_duration_ns

DEFAULT_AUDIO_SAMPLE_RATE_HZ = 16_000
DEFAULT_AUDIO_CHUNK_DURATION_MS = 20
DEFAULT_AUDIO_CHANNEL_COUNT = 1


class FrameSource(QObject):
    """Owns data acquisition while the Driver stays focused on ModLink lifecycle."""

    sig_event = pyqtSignal(object)
    sig_frame = pyqtSignal(FrameEnvelope)

    @property
    def descriptor(self) -> StreamDescriptor:
        raise NotImplementedError(f"{type(self).__name__} must implement descriptor")

    @property
    def source_name(self) -> str:
        raise NotImplementedError(f"{type(self).__name__} must implement source_name")

    @property
    def transport(self) -> str:
        raise NotImplementedError(f"{type(self).__name__} must implement transport")

    def connect_source(self, config: object | None = None) -> None:
        raise NotImplementedError(
            f"{type(self).__name__} must implement connect_source"
        )

    def disconnect_source(self) -> None:
        raise NotImplementedError(
            f"{type(self).__name__} must implement disconnect_source"
        )

    def start(self) -> None:
        raise NotImplementedError(f"{type(self).__name__} must implement start")

    def stop(self) -> None:
        raise NotImplementedError(f"{type(self).__name__} must implement stop")


class MicrophoneFrameSource(FrameSource):
    """Reads PCM samples from the system default microphone and emits line chunks."""

    def __init__(
        self,
        *,
        stream_id: str,
        display_name: str,
        modality: str = "audio",
        chunk_duration_ms: int = DEFAULT_AUDIO_CHUNK_DURATION_MS,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent=parent)
        if chunk_duration_ms <= 0:
            raise ValueError("chunk_duration_ms must be positive")

        self._stream_id = stream_id
        self._display_name = display_name
        self._modality = modality
        self._chunk_duration_ms = int(chunk_duration_ms)

        self._audio_device = self._default_audio_input()
        self._format = self._select_capture_format(self._audio_device)
        self._chunk_size = max(
            1,
            int(round(self._format.sampleRate() * self._chunk_duration_ms / 1000.0)),
        )
        self._descriptor = StreamDescriptor(
            stream_id=self._stream_id,
            modality=self._modality,
            payload_type="line",
            nominal_sample_rate_hz=float(self._format.sampleRate()),
            chunk_size=self._chunk_size,
            display_name=self._display_name,
            metadata={
                "channel_names": self._channel_names(self._format.channelCount()),
                "unit": "amplitude",
                "sample_format": self._format.sampleFormat().name.lower(),
                "source_kind": "microphone",
            },
        )

        self._audio_source: QAudioSource | None = None
        self._io_device = None
        self._buffer = bytearray()
        self._chunk_bytes = int(self._format.bytesPerFrame()) * self._chunk_size
        self._chunk_duration_ns = chunk_duration_ns(
            self._descriptor.nominal_sample_rate_hz,
            self._descriptor.chunk_size,
        )
        self._sequence = 0
        self._next_timestamp_ns: int | None = None
        self._connected = False
        self._streaming = False

    @property
    def descriptor(self) -> StreamDescriptor:
        return self._descriptor

    @property
    def source_name(self) -> str:
        if self._audio_device.isNull():
            return "Default Microphone"
        return self._audio_device.description() or "Default Microphone"

    @property
    def transport(self) -> str:
        return "microphone"

    def connect_source(self, config: object | None = None) -> None:
        if config is not None:
            raise ValueError(
                "MicrophoneFrameSource does not accept connection config; it always uses the default microphone"
            )
        if self._connected:
            return
        if self._audio_device.isNull():
            raise RuntimeError("No audio input device is available")

        self._audio_source = QAudioSource(self._audio_device, self._format, self)
        self._audio_source.stateChanged.connect(self._on_state_changed)
        self._buffer.clear()
        self._next_timestamp_ns = None
        self._connected = True

    def disconnect_source(self) -> None:
        self.stop()
        if not self._connected:
            return

        audio_source = self._audio_source
        self._audio_source = None
        if audio_source is not None:
            try:
                audio_source.stateChanged.disconnect(self._on_state_changed)
            except TypeError:
                pass
            audio_source.deleteLater()

        self._io_device = None
        self._buffer.clear()
        self._next_timestamp_ns = None
        self._connected = False

    def start(self) -> None:
        if not self._connected:
            self.connect_source()
        if self._streaming:
            return
        if self._audio_source is None:
            raise RuntimeError("Microphone audio source is not initialized")

        io_device = self._audio_source.start()
        if io_device is None:
            raise RuntimeError("Failed to start microphone capture")

        self._io_device = io_device
        self._io_device.readyRead.connect(self._on_ready_read)
        self._buffer.clear()
        self._next_timestamp_ns = None
        self._streaming = True

    def stop(self) -> None:
        if self._io_device is not None:
            try:
                self._io_device.readyRead.disconnect(self._on_ready_read)
            except TypeError:
                pass
            self._io_device = None

        if self._audio_source is not None:
            self._audio_source.stop()

        self._buffer.clear()
        self._next_timestamp_ns = None
        self._streaming = False

    def _on_ready_read(self) -> None:
        if self._io_device is None:
            return

        self._buffer.extend(bytes(self._io_device.readAll()))

        while len(self._buffer) >= self._chunk_bytes:
            raw_chunk = bytes(self._buffer[: self._chunk_bytes])
            del self._buffer[: self._chunk_bytes]
            self.sig_frame.emit(
                FrameEnvelope(
                    stream_id=self._descriptor.stream_id,
                    timestamp_ns=self._consume_timestamp_ns(),
                    data=self._decode_chunk(raw_chunk),
                    seq=self._sequence,
                )
            )
            self._sequence += 1

    def _consume_timestamp_ns(self) -> int:
        if self._next_timestamp_ns is None:
            timestamp_ns = time.time_ns()
            self._next_timestamp_ns = timestamp_ns + self._chunk_duration_ns
            return timestamp_ns

        timestamp_ns = self._next_timestamp_ns
        self._next_timestamp_ns += self._chunk_duration_ns
        return timestamp_ns

    def _decode_chunk(self, raw_chunk: bytes) -> np.ndarray:
        sample_format = self._format.sampleFormat()
        if sample_format == QAudioFormat.SampleFormat.UInt8:
            data = np.frombuffer(raw_chunk, dtype=np.uint8).astype(np.float64)
            data = (data - 128.0) / 128.0
        elif sample_format == QAudioFormat.SampleFormat.Int16:
            data = np.frombuffer(raw_chunk, dtype=np.int16).astype(np.float64)
            data /= 32768.0
        elif sample_format == QAudioFormat.SampleFormat.Int32:
            data = np.frombuffer(raw_chunk, dtype=np.int32).astype(np.float64)
            data /= 2147483648.0
        elif sample_format == QAudioFormat.SampleFormat.Float:
            data = np.frombuffer(raw_chunk, dtype=np.float32).astype(np.float64)
        else:
            raise RuntimeError(
                f"Unsupported microphone sample format: {sample_format}"
            )

        channel_count = self._format.channelCount()
        frame_count = len(raw_chunk) // int(self._format.bytesPerFrame())
        interleaved = data.reshape(frame_count, channel_count)
        return np.ascontiguousarray(interleaved.T)

    def _on_state_changed(self, state) -> None:
        audio_source = self._audio_source
        if audio_source is None:
            return
        error = audio_source.error()
        error_name = getattr(error, "name", str(error))
        if error_name == "NoError":
            return
        state_name = getattr(state, "name", str(state))

        self.sig_event.emit(
            {
                "kind": "source_error",
                "source": "microphone",
                "state": state_name.lower(),
                "error": error_name.lower(),
                "message": (
                    "microphone capture entered "
                    f"{state_name.lower()} with error {error_name.lower()}"
                ),
                "ts": time.time(),
            }
        )

    @staticmethod
    def _default_audio_input() -> QAudioDevice:
        default_device = QMediaDevices.defaultAudioInput()
        if not default_device.isNull():
            return default_device

        inputs = list(QMediaDevices.audioInputs())
        if inputs:
            return inputs[0]

        return QAudioDevice()

    @staticmethod
    def _select_capture_format(audio_device: QAudioDevice) -> QAudioFormat:
        if audio_device.isNull():
            return MicrophoneFrameSource._fallback_format()

        preferred = audio_device.preferredFormat()
        sample_rate_hz = preferred.sampleRate() or DEFAULT_AUDIO_SAMPLE_RATE_HZ
        sample_formats = [
            QAudioFormat.SampleFormat.Float,
            QAudioFormat.SampleFormat.Int16,
            preferred.sampleFormat(),
        ]

        for sample_format in sample_formats:
            candidate = QAudioFormat()
            candidate.setSampleRate(sample_rate_hz)
            candidate.setChannelCount(DEFAULT_AUDIO_CHANNEL_COUNT)
            candidate.setSampleFormat(sample_format)
            if audio_device.isFormatSupported(candidate):
                return candidate

        return preferred

    @staticmethod
    def _fallback_format() -> QAudioFormat:
        fallback = QAudioFormat()
        fallback.setSampleRate(DEFAULT_AUDIO_SAMPLE_RATE_HZ)
        fallback.setChannelCount(DEFAULT_AUDIO_CHANNEL_COUNT)
        fallback.setSampleFormat(QAudioFormat.SampleFormat.Float)
        return fallback

    @staticmethod
    def _channel_names(channel_count: int) -> list[str]:
        if channel_count <= 1:
            return ["mic"]
        return [f"mic_{index}" for index in range(channel_count)]
