from __future__ import annotations

from PyQt6.QtWidgets import QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, SubtitleLabel

from packages.modlink_core.runtime.engine import ModLinkEngine

from ..widgets import AcquisitionControlPanel


class MainPage(QWidget):
    """Main landing page for the ModLink Studio UI."""

    def __init__(self, engine: ModLinkEngine, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.engine = engine

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(36, 28, 36, 28)
        root_layout.setSpacing(18)

        title_label = SubtitleLabel("ModLink Studio", self)
        intro_label = BodyLabel(
            "主页面先承接采集入口，后续再向这里逐步挂接设备、设置和预览区域。",
            self,
        )
        intro_label.setWordWrap(True)

        self.acquisition_panel = AcquisitionControlPanel(engine, self)

        root_layout.addWidget(title_label)
        root_layout.addWidget(intro_label)
        root_layout.addWidget(self.acquisition_panel)
        root_layout.addStretch(1)
