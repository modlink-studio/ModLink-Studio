from __future__ import annotations

from PyQt6.QtWidgets import QWidget

from modlink_ui_v2.bridge import QtModLinkBridge
from modlink_ui_v2.shared import BasePage, EmptyStateMessage

from .control_panel import DeviceControlPanel


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
            self.empty_state = EmptyStateMessage(
                "当前没有可用 driver",
                "安装或加载 driver 包后，这里会自动生成对应控制 panel。",
                self.scroll_widget,
            )
            self.content_layout.addWidget(self.empty_state)
            self.content_layout.addStretch(1)
            return

        for portal in portals:
            self.content_layout.addWidget(DeviceControlPanel(portal, self.scroll_widget))
        self.content_layout.addStretch(1)
