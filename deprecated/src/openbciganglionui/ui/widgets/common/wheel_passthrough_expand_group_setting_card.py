from __future__ import annotations

from PyQt6.QtGui import QWheelEvent
from qfluentwidgets import ExpandGroupSettingCard


class WheelPassthroughExpandGroupSettingCard(ExpandGroupSettingCard):
    def wheelEvent(self, event: QWheelEvent) -> None:
        # Let the outer settings scroll area consume wheel events.
        event.ignore()
