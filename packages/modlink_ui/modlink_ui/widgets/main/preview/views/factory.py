from __future__ import annotations

from PyQt6.QtWidgets import QWidget

from modlink_sdk import StreamDescriptor

from .base import BaseStreamView
from .field import FieldStreamView
from .raster import RasterStreamView
from .signal import SignalStreamView
from .unavailable import UnavailableStreamView
from .video import VideoStreamView


def create_stream_view(
    descriptor: StreamDescriptor,
    parent: QWidget | None = None,
) -> BaseStreamView:
    if descriptor.payload_type == "signal":
        return SignalStreamView(descriptor, parent=parent)
    if descriptor.payload_type == "raster":
        return RasterStreamView(descriptor, parent=parent)
    if descriptor.payload_type == "field":
        return FieldStreamView(descriptor, parent=parent)
    if descriptor.payload_type == "video":
        return VideoStreamView(descriptor, parent=parent)

    return UnavailableStreamView(
        descriptor,
        reason=f"当前不支持 payload_type={descriptor.payload_type} 的预览。",
        parent=parent,
    )
