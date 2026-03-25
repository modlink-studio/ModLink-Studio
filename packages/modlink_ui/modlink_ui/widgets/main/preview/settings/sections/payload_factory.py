from __future__ import annotations

from PyQt6.QtWidgets import QVBoxLayout, QWidget
from qfluentwidgets import CaptionLabel, SimpleCardWidget, StrongBodyLabel

from modlink_sdk import StreamDescriptor

from .field import FieldPayloadSettingsPanel
from .raster import RasterPayloadSettingsPanel
from .signal import SignalPayloadSettingsPanel
from .video import VideoPayloadSettingsPanel


def create_payload_settings_section(
    descriptor: StreamDescriptor,
    parent: QWidget | None = None,
) -> QWidget:
    if descriptor.payload_type == "video":
        return VideoPayloadSettingsPanel(descriptor, parent)
    if descriptor.payload_type == "signal":
        return SignalPayloadSettingsPanel(descriptor, parent)
    if descriptor.payload_type == "raster":
        return RasterPayloadSettingsPanel(descriptor, parent)
    if descriptor.payload_type == "field":
        return FieldPayloadSettingsPanel(descriptor, parent)

    panel = SimpleCardWidget(parent)
    panel.setBorderRadius(12)
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(18, 18, 18, 18)
    layout.setSpacing(8)

    title_label = StrongBodyLabel("设置项", panel)
    body_label = CaptionLabel(
        f"{descriptor.payload_type} 的专属设置面板还没有开始实现。",
        panel,
    )
    body_label.setWordWrap(True)

    layout.addWidget(title_label)
    layout.addWidget(body_label)
    return panel
