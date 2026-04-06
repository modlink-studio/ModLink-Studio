from __future__ import annotations

from PyQt6.QtWidgets import QWidget

from modlink_qt_bridge import QtSettingsBridge
from modlink_sdk import StreamDescriptor

from .base import BaseStreamView
from .field import FieldStreamView
from .raster import RasterStreamView
from .signal import SignalStreamView
from .video import VideoStreamView


def create_stream_view(
    descriptor: StreamDescriptor,
    settings: QtSettingsBridge,
    parent: QWidget | None = None,
) -> BaseStreamView:
    if descriptor.payload_type == "signal":
        return SignalStreamView(descriptor, settings, parent=parent)
    if descriptor.payload_type == "raster":
        return RasterStreamView(descriptor, settings, parent=parent)
    if descriptor.payload_type == "field":
        return FieldStreamView(descriptor, settings, parent=parent)
    if descriptor.payload_type == "video":
        return VideoStreamView(descriptor, settings, parent=parent)
    raise ValueError(f"unsupported payload_type: {descriptor.payload_type}")
