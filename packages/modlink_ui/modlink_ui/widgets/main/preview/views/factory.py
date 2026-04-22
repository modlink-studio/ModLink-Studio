from __future__ import annotations

from PyQt6.QtWidgets import QWidget

from modlink_sdk import StreamDescriptor
from modlink_ui.bridge import QtSettingsBridge

from .base import BaseStreamView


def create_stream_view(
    descriptor: StreamDescriptor,
    settings: QtSettingsBridge,
    parent: QWidget | None = None,
) -> BaseStreamView:
    if descriptor.payload_type == "signal":
        from .signal import SignalStreamView

        return SignalStreamView(descriptor, settings, parent=parent)
    if descriptor.payload_type == "raster":
        from .raster import RasterStreamView

        return RasterStreamView(descriptor, settings, parent=parent)
    if descriptor.payload_type == "field":
        from .field import FieldStreamView

        return FieldStreamView(descriptor, settings, parent=parent)
    if descriptor.payload_type == "video":
        from .video import VideoStreamView

        return VideoStreamView(descriptor, settings, parent=parent)
    raise ValueError(f"unsupported payload_type: {descriptor.payload_type}")
