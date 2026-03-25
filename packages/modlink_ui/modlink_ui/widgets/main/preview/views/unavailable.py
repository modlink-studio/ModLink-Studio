from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel

from modlink_sdk import FrameEnvelope, StreamDescriptor

from .base import BaseStreamView


class UnavailableStreamView(BaseStreamView):
    def __init__(
        self,
        descriptor: StreamDescriptor,
        *,
        reason: str,
        parent: QWidget | None = None,
    ) -> None:
        self._reason = reason
        super().__init__(descriptor, parent=parent)
        self._body = BodyLabel(reason, self)
        self._body.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.addStretch(1)
        layout.addWidget(self._body, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(1)

        self.setMinimumHeight(220)

    def _ingest_frame(self, frame: FrameEnvelope) -> bool:
        return False

    def _render(self) -> None:
        return
