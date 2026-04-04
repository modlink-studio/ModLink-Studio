from __future__ import annotations

from typing import cast

from PyQt6.QtCore import QObject

from modlink_sdk import StreamDescriptor

from .image_controller import ImageStreamController
from .models import PreviewPayloadType, PreviewSettings
from .raster_controller import RasterStreamController, VideoStreamController
from .signal_controller import SignalStreamController

StreamController = SignalStreamController | ImageStreamController | RasterStreamController | VideoStreamController


def create_stream_controller(
    descriptor: StreamDescriptor,
    parent: QObject | None = None,
) -> StreamController:
    pt = str(descriptor.payload_type)
    if pt == "signal":
        return SignalStreamController(descriptor, parent)
    if pt == "raster":
        return RasterStreamController(descriptor, parent)
    if pt == "field":
        return ImageStreamController(descriptor, parent)
    if pt == "video":
        return VideoStreamController(descriptor, parent)
    raise ValueError(f"unsupported payload_type: {pt}")


def apply_settings_to_controller(
    controller: StreamController,
    settings: PreviewSettings,
) -> None:
    controller.apply_settings(settings)  # type: ignore[arg-type]
