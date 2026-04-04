from __future__ import annotations

from PyQt6.QtWidgets import QWidget
from qfluentwidgets import BodyLabel, StrongBodyLabel

from modlink_qt_bridge import QtModLinkBridge
from modlink_ui.widgets.device import create_device_control_panel
from modlink_ui.widgets.shared import BasePage


class DevicePage(BasePage):
    """Device page that mounts one control panel per installed driver."""

    def __init__(
        self,
        engine: QtModLinkBridge,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            page_key="device-page",
            title="设备",
            description="这里后续承接设备发现、连接管理、流启动和运行状态。",
            parent=parent,
        )
        self.engine = engine

        portals = self.engine.driver_portals()
        if not portals:
            self.placeholder_title = StrongBodyLabel("当前没有可用 driver", self.scroll_widget)
            self.placeholder_body = BodyLabel(
                "设备页骨架已经就位，但当前环境还没有发现已加载的 driver。后续装入 driver 包后，这里会自动生成对应控制 panel。",
                self.scroll_widget,
            )
            self.placeholder_body.setWordWrap(True)

            self.content_layout.addWidget(self.placeholder_title)
            self.content_layout.addWidget(self.placeholder_body)
            self.content_layout.addStretch(1)
            return

        for portal in portals:
            self.content_layout.addWidget(create_device_control_panel(portal, self.scroll_widget))
        self.content_layout.addStretch(1)
