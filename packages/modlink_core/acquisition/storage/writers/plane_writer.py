from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from packages.modlink_shared import FrameEnvelope, StreamDescriptor

from ..utils import (
    normalize_data_array,
    to_json_text,
    to_json_value,
    write_npz,
)
from .base import BaseStreamRecordingWriter


class PlaneStreamRecordingWriter(BaseStreamRecordingWriter):
    def __init__(self, stream_dir: Path, descriptor: StreamDescriptor) -> None:
        super().__init__(stream_dir, descriptor)
        self.chunks_dir = self.stream_dir / "chunks"
        self.chunks_dir.mkdir(parents=True, exist_ok=True)
        self._chunks_file = (self.stream_dir / "chunks.csv").open(
            "w",
            encoding="utf-8",
            newline="",
        )
        self._chunks_writer = csv.writer(self._chunks_file)
        self._chunks_writer.writerow(
            [
                "chunk_index",
                "chunk_seq",
                "chunk_start_timestamp_ns",
                "time_count",
                "file_name",
                "shape_json",
                "dtype",
                "extra_json",
            ]
        )
        self._chunks_file.flush()
        self._chunk_index = 0
        self._channel_count: int | None = None
        self._spatial_shape: tuple[int, int] | None = None
        self._dtype_str: str | None = None
        self._write_index(
            writer_kind="plane_npz_chunks",
            dtype=None,
            channel_count=None,
            spatial_shape=None,
            chunk_count=0,
        )

    def append_frame(self, frame: FrameEnvelope) -> None:
        data = normalize_data_array(frame, expected_ndim=4)
        channel_count, chunk_size, height, width = (
            int(data.shape[0]),
            int(data.shape[1]),
            int(data.shape[2]),
            int(data.shape[3]),
        )
        self._validate_chunk_size(frame, chunk_size)

        if self._channel_count is None:
            self._channel_count = channel_count
            self._spatial_shape = (height, width)
            self._dtype_str = data.dtype.str
        else:
            if channel_count != self._channel_count:
                raise ValueError(
                    f"stream_id={frame.stream_id}: channel count changed from {self._channel_count} to {channel_count}"
                )
            if (height, width) != self._spatial_shape:
                raise ValueError(
                    f"stream_id={frame.stream_id}: spatial shape changed from {self._spatial_shape} to {(height, width)}"
                )
            if data.dtype.str != self._dtype_str:
                raise ValueError(
                    f"stream_id={frame.stream_id}: dtype changed from {self._dtype_str} to {data.dtype.str}"
                )

        self._chunk_index += 1
        file_name = f"chunk-{self._chunk_index:06d}.npz"
        timestamps_ns = np.asarray(int(frame.timestamp_ns), dtype=np.int64) + (
            np.arange(chunk_size, dtype=np.int64) * int(self._sample_period_ns)
        )
        manifest = {
            "chunk_index": self._chunk_index,
            "chunk_seq": None if frame.seq is None else int(frame.seq),
            "chunk_start_timestamp_ns": int(frame.timestamp_ns),
            "time_count": chunk_size,
            "shape": [channel_count, chunk_size, height, width],
            "dtype": data.dtype.str,
            "extra": to_json_value(frame.extra),
        }
        write_npz(
            self.chunks_dir / file_name,
            data=np.ascontiguousarray(data),
            timestamps_ns=timestamps_ns,
            manifest_json=np.asarray(to_json_text(manifest)),
        )
        self._chunks_writer.writerow(
            [
                self._chunk_index,
                "" if frame.seq is None else int(frame.seq),
                int(frame.timestamp_ns),
                chunk_size,
                file_name,
                to_json_text([channel_count, chunk_size, height, width]),
                data.dtype.str,
                to_json_text(frame.extra),
            ]
        )
        self._chunks_file.flush()

        self._frame_count += 1
        self._sample_count += chunk_size
        self._write_index(
            writer_kind="plane_npz_chunks",
            dtype=self._dtype_str,
            channel_count=self._channel_count,
            spatial_shape=list(self._spatial_shape or ()),
            chunk_count=self._chunk_index,
        )

    def close(self) -> None:
        self._chunks_file.close()
        self._write_index(
            writer_kind="plane_npz_chunks",
            dtype=self._dtype_str,
            channel_count=self._channel_count,
            spatial_shape=list(self._spatial_shape or ()),
            chunk_count=self._chunk_index,
        )
