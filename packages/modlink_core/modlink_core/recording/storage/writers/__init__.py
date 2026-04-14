from __future__ import annotations

from pathlib import Path

from modlink_sdk import StreamDescriptor

from .base import BaseStreamRecordingWriter
from .field_writer import FieldStreamRecordingWriter
from .raster_writer import RasterStreamRecordingWriter
from .signal_writer import SignalStreamRecordingWriter
from .video_writer import VideoStreamRecordingWriter


def create_stream_writer(
    stream_dir: Path,
    descriptor: StreamDescriptor,
) -> BaseStreamRecordingWriter:
    if descriptor.payload_type == "signal":
        return SignalStreamRecordingWriter(stream_dir, descriptor)
    if descriptor.payload_type == "raster":
        return RasterStreamRecordingWriter(stream_dir, descriptor)
    if descriptor.payload_type == "field":
        return FieldStreamRecordingWriter(stream_dir, descriptor)
    if descriptor.payload_type == "video":
        return VideoStreamRecordingWriter(stream_dir, descriptor)
    raise ValueError(
        f"unsupported payload_type '{descriptor.payload_type}' for stream_id={descriptor.stream_id}"
    )


__all__ = [
    "BaseStreamRecordingWriter",
    "SignalStreamRecordingWriter",
    "RasterStreamRecordingWriter",
    "FieldStreamRecordingWriter",
    "VideoStreamRecordingWriter",
    "create_stream_writer",
]
