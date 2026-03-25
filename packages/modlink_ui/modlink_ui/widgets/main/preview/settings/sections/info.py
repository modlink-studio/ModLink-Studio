from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGridLayout, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, CaptionLabel, SimpleCardWidget, StrongBodyLabel

from modlink_sdk import StreamDescriptor


class StreamPreviewInfoPanel(SimpleCardWidget):
    def __init__(
        self,
        descriptor: StreamDescriptor,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.descriptor = descriptor
        self.setBorderRadius(12)

        self.title_label = StrongBodyLabel("流信息", self)

        self.info_grid = QGridLayout()
        self.info_grid.setContentsMargins(0, 0, 0, 0)
        self.info_grid.setHorizontalSpacing(12)
        self.info_grid.setVerticalSpacing(10)
        self.info_grid.setColumnStretch(1, 1)

        self._add_info_row(
            0,
            "流名称",
            descriptor.display_name or descriptor.stream_id,
        )
        self._add_info_row(1, "Stream ID", descriptor.stream_id)
        self._add_info_row(
            2,
            "类型",
            f"{descriptor.payload_type} · {descriptor.modality}",
        )
        self._add_info_row(
            3,
            "采样率",
            f"{float(descriptor.nominal_sample_rate_hz or 0.0):.1f} Hz",
        )
        self._add_info_row(4, "Chunk 大小", str(descriptor.chunk_size))
        self._add_info_row(
            5,
            "通道数",
            str(len(descriptor.channel_names)) if descriptor.channel_names else "-",
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(self.title_label)
        layout.addLayout(self.info_grid)

    def _add_info_row(self, row: int, label: str, value: str) -> None:
        label_widget = CaptionLabel(label, self)
        label_widget.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        value_widget = BodyLabel(value, self)
        value_widget.setWordWrap(True)
        value_widget.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.info_grid.addWidget(label_widget, row, 0)
        self.info_grid.addWidget(value_widget, row, 1)
