from __future__ import annotations

from pathlib import Path

from modlink_sdk import StreamDescriptor

from .base import BaseStreamRecordingWriter
from .line_writer import LineStreamRecordingWriter
from .plane_writer import PlaneStreamRecordingWriter
from .video_writer import VideoStreamRecordingWriter


def create_stream_writer(
    stream_dir: Path,
    descriptor: StreamDescriptor,
) -> BaseStreamRecordingWriter:
    if descriptor.payload_type == "line":
        return LineStreamRecordingWriter(stream_dir, descriptor)
    if descriptor.payload_type == "plane":
        return PlaneStreamRecordingWriter(stream_dir, descriptor)
    if descriptor.payload_type == "video":
        return VideoStreamRecordingWriter(stream_dir, descriptor)
    raise ValueError(
        f"unsupported payload_type '{descriptor.payload_type}' for stream_id={descriptor.stream_id}"
    )


__all__ = [
    "BaseStreamRecordingWriter",
    "LineStreamRecordingWriter",
    "PlaneStreamRecordingWriter",
    "VideoStreamRecordingWriter",
    "create_stream_writer",
]
