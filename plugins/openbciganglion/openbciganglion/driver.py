from __future__ import annotations

import asyncio
import time

import numpy as np
from brainflow.board_shim import BoardIds, BoardShim, BrainFlowInputParams
from bleak import BleakScanner
from serial.tools import list_ports

from modlink_sdk import FrameEnvelope, LoopDriver, SearchResult, StreamDescriptor


DEFAULT_GANGLION_DEVICE_ID = "eeg:openbci:ganglion"
DEFAULT_GANGLION_DISPLAY_NAME = "OpenBCI Ganglion"
DEFAULT_STREAM_ID = f"{DEFAULT_GANGLION_DEVICE_ID}:eeg"
DEFAULT_SAMPLE_RATE_HZ = 200.0
DEFAULT_CHUNK_SIZE = 10
DEFAULT_CHANNEL_NAMES = ("ch1", "ch2", "ch3", "ch4")


class OpenBCIGanglionDriver(LoopDriver):
    supported_providers = ("ble", "serial")
    loop_interval_ms = int(round(1000 * DEFAULT_CHUNK_SIZE / DEFAULT_SAMPLE_RATE_HZ))

    def __init__(self) -> None:
        super().__init__()
        self._board = None
        self._transport = ""
        self._eeg_channels: tuple[int, ...] = ()
        self._buffer = np.empty((len(DEFAULT_CHANNEL_NAMES), 0), dtype=np.float32)
        self._seq = 0

    @property
    def device_id(self) -> str:
        return DEFAULT_GANGLION_DEVICE_ID

    @property
    def display_name(self) -> str:
        return DEFAULT_GANGLION_DISPLAY_NAME

    def descriptors(self) -> list[StreamDescriptor]:
        return [
            StreamDescriptor(
                stream_id=DEFAULT_STREAM_ID,
                modality="eeg",
                payload_type="line",
                nominal_sample_rate_hz=DEFAULT_SAMPLE_RATE_HZ,
                chunk_size=DEFAULT_CHUNK_SIZE,
                channel_names=DEFAULT_CHANNEL_NAMES,
                unit="uV",
                display_name="Ganglion EEG",
            )
        ]

    def search(self, provider: str) -> list[SearchResult]:
        if provider == "ble":
            devices = asyncio.run(BleakScanner.discover(timeout=5.0))
            return [
                SearchResult(
                    title=(device.name or "OpenBCI Ganglion").strip()
                    or "OpenBCI Ganglion",
                    subtitle=f"Native BLE | {device.address}",
                    extra={
                        "transport": "native_ble",
                        "serial_number": (device.name or "").strip(),
                    },
                )
                for device in devices
                if device.address
            ]

        if provider == "serial":
            return [
                SearchResult(
                    title=port.description or port.device,
                    subtitle=(
                        f"Dongle | {port.device} | {port.serial_number}"
                        if port.serial_number
                        else f"Dongle | {port.device}"
                    ),
                    extra={
                        "transport": "dongle",
                        "serial_port": port.device,
                    },
                )
                for port in list_ports.comports()
                if port.device
            ]

        raise ValueError("OpenBCI Ganglion search provider must be 'ble' or 'serial'")

    def connect_device(self, config: SearchResult) -> None:
        extra = config.extra
        params = BrainFlowInputParams()
        params.timeout = 15
        params.other_info = "fw:auto"

        if extra["transport"] == "dongle":
            params.serial_port = extra["serial_port"]
            board_id = int(BoardIds.GANGLION_BOARD.value)
        else:
            params.serial_number = extra["serial_number"]
            board_id = int(BoardIds.GANGLION_NATIVE_BOARD.value)

        board = BoardShim(board_id, params)
        board.prepare_session()

        self._board = board
        self._transport = extra["transport"]
        self._eeg_channels = tuple(BoardShim.get_eeg_channels(board_id))
        self._buffer = np.empty((len(DEFAULT_CHANNEL_NAMES), 0), dtype=np.float32)
        self._seq = 0

    def disconnect_device(self) -> None:
        self.stop_streaming()
        if self._board is None:
            return

        if self._transport == "dongle":
            try:
                self._board.config_board("v")
            except Exception:
                pass

        try:
            self._board.release_session()
        finally:
            self._board = None
            self._transport = ""
            self._eeg_channels = ()
            self._buffer = np.empty((len(DEFAULT_CHANNEL_NAMES), 0), dtype=np.float32)
            self._seq = 0

    def on_loop_started(self) -> None:
        if self._board is None:
            raise RuntimeError("device is not connected")

        self._board.start_stream(45_000, "")
        self._buffer = np.empty((len(DEFAULT_CHANNEL_NAMES), 0), dtype=np.float32)
        self._seq = 0

    def on_loop_stopped(self) -> None:
        try:
            if self._board is not None:
                self._board.stop_stream()
        finally:
            self._buffer = np.empty((len(DEFAULT_CHANNEL_NAMES), 0), dtype=np.float32)
            self._seq = 0

    def loop(self) -> None:
        if self._board is None:
            return
        if self._board.get_board_data_count() <= 0:
            return

        try:
            board_data = self._board.get_board_data()
            eeg_data = np.ascontiguousarray(
                board_data[list(self._eeg_channels), :],
                dtype=np.float32,
            )
        except Exception as exc:
            self.disconnect_device()
            self.sig_connection_lost.emit(
                {
                    "code": "GANGLION_STREAM_FAILED",
                    "message": "OpenBCI Ganglion stream polling failed",
                    "detail": str(exc),
                }
            )
            return

        if eeg_data.size == 0:
            return

        self._buffer = np.ascontiguousarray(
            np.concatenate((self._buffer, eeg_data), axis=1),
            dtype=np.float32,
        )
        while self._buffer.shape[1] >= DEFAULT_CHUNK_SIZE:
            chunk = np.ascontiguousarray(
                self._buffer[:, :DEFAULT_CHUNK_SIZE],
                dtype=np.float32,
            )
            self._buffer = np.ascontiguousarray(
                self._buffer[:, DEFAULT_CHUNK_SIZE:],
                dtype=np.float32,
            )
            self.sig_frame.emit(
                FrameEnvelope(
                    stream_id=DEFAULT_STREAM_ID,
                    timestamp_ns=time.time_ns(),
                    data=chunk,
                    seq=self._seq,
                )
            )
            self._seq += 1
