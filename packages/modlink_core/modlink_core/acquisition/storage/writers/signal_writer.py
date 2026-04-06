from __future__ import annotations

import csv
from pathlib import Path

from modlink_sdk import FrameEnvelope, StreamDescriptor

from ..utils import (
    normalize_data_array,
    to_json_text,
    to_json_value,
)
from .base import BaseStreamRecordingWriter


class SignalStreamRecordingWriter(BaseStreamRecordingWriter):
    def __init__(self, stream_dir: Path, descriptor: StreamDescriptor) -> None:
        super().__init__(stream_dir, descriptor)
        self._csv_file = (self.stream_dir / "data.csv").open(
            "w",
            encoding="utf-8",
            newline="",
        )
        self._csv_writer = csv.writer(self._csv_file)
        self._channel_headers: list[str] | None = None
        self._channel_count: int | None = None
        self._write_index(writer_kind="signal_csv", channel_columns=None)

    def append_frame(self, frame: FrameEnvelope) -> None:
        data = normalize_data_array(frame, expected_ndim=2)
        channel_count, chunk_size = int(data.shape[0]), int(data.shape[1])
        self._validate_chunk_size(frame, chunk_size)

        if self._channel_count is None:
            self._channel_count = channel_count
            channel_names = self.descriptor.channel_names
            if (
                isinstance(channel_names, tuple)
                and all(isinstance(name, str) and name for name in channel_names)
                and len(channel_names) == channel_count
            ):
                self._channel_headers = list(channel_names)
            else:
                self._channel_headers = [f"channel_{index}" for index in range(channel_count)]
            self._csv_writer.writerow(
                [
                    "timestamp_ns",
                    "chunk_seq",
                    "sample_index_in_chunk",
                    *self._channel_headers,
                    "extra_json",
                ]
            )
        elif channel_count != self._channel_count:
            raise ValueError(
                f"stream_id={frame.stream_id}: channel count changed from {self._channel_count} to {channel_count}"
            )

        extra_json = to_json_text(frame.extra)
        for sample_index in range(chunk_size):
            self._csv_writer.writerow(
                [
                    int(frame.timestamp_ns) + (sample_index * self._sample_period_ns),
                    "" if frame.seq is None else int(frame.seq),
                    sample_index,
                    *[
                        to_json_value(data[channel_index, sample_index])
                        for channel_index in range(channel_count)
                    ],
                    extra_json,
                ]
            )

        self._csv_file.flush()
        self._frame_count += 1
        self._sample_count += chunk_size
        self._write_index(
            writer_kind="signal_csv",
            channel_columns=self._channel_headers,
        )

    def close(self) -> None:
        self._csv_file.close()
        self._write_index(
            writer_kind="signal_csv",
            channel_columns=self._channel_headers,
        )
