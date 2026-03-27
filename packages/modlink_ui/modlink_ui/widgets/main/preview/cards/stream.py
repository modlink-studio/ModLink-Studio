from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    CaptionLabel,
    FluentIcon as FIF,
    SimpleCardWidget,
    StrongBodyLabel,
    TransparentToolButton,
)

from modlink_sdk import FrameEnvelope, StreamDescriptor

from ..settings import PreviewSettingsRuntime
from ..views import create_stream_view


class StreamPreviewCard(SimpleCardWidget):
    def __init__(
        self,
        descriptor: StreamDescriptor,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.descriptor = descriptor
        self.setBorderRadius(12)
        self.setToolTip(descriptor.stream_id)

        title = descriptor.display_name or descriptor.stream_id

        self.title_label = StrongBodyLabel(title, self)
        self.stream_view = create_stream_view(descriptor, self)
        self.settings_runtime = PreviewSettingsRuntime(
            descriptor=descriptor,
            stream_view=self.stream_view,
            parent=self,
        )
        self.summary_label = CaptionLabel(self._summary_text(), self)
        self.settings_button = TransparentToolButton(FIF.SETTING, self)
        self.settings_button.setToolTip("预览设置")
        self.settings_button.clicked.connect(self.open_settings_dialog)
        self.header_action_layout = QHBoxLayout()
        self.header_action_layout.setContentsMargins(0, 0, 0, 0)
        self.header_action_layout.setSpacing(4)
        self.header_action_layout.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight
        )

        title_block_layout = QVBoxLayout()
        title_block_layout.setContentsMargins(0, 0, 0, 0)
        title_block_layout.setSpacing(2)
        title_block_layout.addWidget(self.title_label)
        title_block_layout.addWidget(self.summary_label)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        header_layout.addLayout(title_block_layout, 1)
        header_layout.addLayout(self.header_action_layout)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(8)
        layout.addLayout(header_layout)
        layout.addWidget(self.stream_view, 1)

        self.add_header_action(self.settings_button)

    def open_settings_dialog(self) -> None:
        self.settings_runtime.open_dialog(self.window())

    def push_frame(self, frame: FrameEnvelope) -> None:
        self.stream_view.push_frame(frame)
        self.summary_label.setText(self._summary_text())

    def _summary_text(self) -> str:
        descriptor = self.descriptor
        sample_rate = float(descriptor.nominal_sample_rate_hz or 0.0)
        channel_count = len(descriptor.channel_names)
        parts = [
            descriptor.payload_type,
            descriptor.modality,
            f"{channel_count} ch",
            f"{sample_rate:.1f} Hz",
        ]
        unit = descriptor.metadata.get("unit")
        if unit:
            parts.append(str(unit))
        parts.append("正在更新" if self.stream_view.has_frame else "等待首帧")
        return " · ".join(parts)

    @property
    def has_frame(self) -> bool:
        return self.stream_view.has_frame

    def add_header_action(self, widget: QWidget) -> None:
        widget.setParent(self)
        self.header_action_layout.addWidget(widget)
