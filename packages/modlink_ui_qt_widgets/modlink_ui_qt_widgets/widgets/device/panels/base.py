from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QWheelEvent
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    CaptionLabel,
    ComboBox,
    ExpandGroupSettingCard,
    PrimaryPushButton,
    PushButton,
    StrongBodyLabel,
    isDarkTheme,
    qconfig,
)
from qfluentwidgets import (
    FluentIcon as FIF,
)

from modlink_qt_bridge import QtDriverPortal, QtDriverTask
from modlink_sdk import SearchResult


class WheelPassthroughExpandGroupSettingCard(ExpandGroupSettingCard):
    def wheelEvent(self, event: QWheelEvent) -> None:
        event.ignore()


class StatusBadge(QLabel):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self._status = "disconnected"
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumWidth(112)
        self.setContentsMargins(12, 4, 12, 4)
        qconfig.themeChangedFinished.connect(self._refresh_style)
        self.set_status("disconnected")

    def set_status(self, status: str) -> None:
        self._status = status
        self._refresh_style()

    def _refresh_style(self) -> None:
        palette = self._palette()
        text, color, background, border = palette.get(self._status, palette["disconnected"])
        self.setText(text)
        self.setStyleSheet(
            f"""
            QLabel {{
                color: {color};
                background: {background};
                border: 1px solid {border};
                border-radius: 12px;
                padding: 4px 12px;
                font-weight: 600;
            }}
            """
        )

    @staticmethod
    def _palette() -> dict[str, tuple[str, str, str, str]]:
        if isDarkTheme():
            return {
                "streaming": (
                    "采集中",
                    "rgb(132, 230, 170)",
                    "rgba(70, 201, 125, 0.18)",
                    "rgba(70, 201, 125, 0.32)",
                ),
                "connected": (
                    "已连接",
                    "rgb(145, 205, 255)",
                    "rgba(76, 156, 255, 0.18)",
                    "rgba(76, 156, 255, 0.32)",
                ),
                "searching": (
                    "搜索中",
                    "rgb(255, 214, 122)",
                    "rgba(255, 197, 61, 0.18)",
                    "rgba(255, 197, 61, 0.30)",
                ),
                "connecting": (
                    "连接中",
                    "rgb(255, 214, 122)",
                    "rgba(255, 197, 61, 0.18)",
                    "rgba(255, 197, 61, 0.30)",
                ),
                "disconnecting": (
                    "断开中",
                    "rgb(255, 220, 138)",
                    "rgba(255, 214, 102, 0.18)",
                    "rgba(255, 214, 102, 0.28)",
                ),
                "starting": (
                    "启动中",
                    "rgb(255, 214, 122)",
                    "rgba(255, 197, 61, 0.18)",
                    "rgba(255, 197, 61, 0.30)",
                ),
                "stopping": (
                    "停止中",
                    "rgb(255, 220, 138)",
                    "rgba(255, 214, 102, 0.18)",
                    "rgba(255, 214, 102, 0.28)",
                ),
                "disconnected": (
                    "未连接",
                    "rgba(255, 255, 255, 0.82)",
                    "rgba(255, 255, 255, 0.06)",
                    "rgba(255, 255, 255, 0.10)",
                ),
            }

        return {
            "streaming": (
                "采集中",
                "rgb(15, 94, 54)",
                "rgba(70, 201, 125, 0.18)",
                "rgba(0, 0, 0, 0.08)",
            ),
            "connected": (
                "已连接",
                "rgb(9, 71, 140)",
                "rgba(76, 156, 255, 0.16)",
                "rgba(0, 0, 0, 0.08)",
            ),
            "searching": (
                "搜索中",
                "rgb(138, 89, 0)",
                "rgba(255, 197, 61, 0.18)",
                "rgba(0, 0, 0, 0.08)",
            ),
            "connecting": (
                "连接中",
                "rgb(138, 89, 0)",
                "rgba(255, 197, 61, 0.18)",
                "rgba(0, 0, 0, 0.08)",
            ),
            "disconnecting": (
                "断开中",
                "rgb(90, 67, 15)",
                "rgba(255, 214, 102, 0.18)",
                "rgba(0, 0, 0, 0.08)",
            ),
            "starting": (
                "启动中",
                "rgb(138, 89, 0)",
                "rgba(255, 197, 61, 0.18)",
                "rgba(0, 0, 0, 0.08)",
            ),
            "stopping": (
                "停止中",
                "rgb(90, 67, 15)",
                "rgba(255, 214, 102, 0.18)",
                "rgba(0, 0, 0, 0.08)",
            ),
            "disconnected": (
                "未连接",
                "rgb(92, 92, 92)",
                "rgba(0, 0, 0, 0.06)",
                "rgba(0, 0, 0, 0.08)",
            ),
        }


class DeviceInfoWidget(QWidget):
    def __init__(
        self,
        title: str,
        subtitle: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.title_label = StrongBodyLabel(title, self)
        self.subtitle_label = CaptionLabel(subtitle, self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)

        self.subtitle_label.setVisible(bool(subtitle))

    def set_text(self, title: str, subtitle: str = "") -> None:
        self.title_label.setText(title)
        self.subtitle_label.setText(subtitle)
        self.subtitle_label.setVisible(bool(subtitle))


class DeviceRow(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.row_layout = QHBoxLayout(self)
        self.row_layout.setContentsMargins(28, 14, 28, 14)
        self.row_layout.setSpacing(10)
        self.row_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)


class BaseDeviceControlPanel(WheelPassthroughExpandGroupSettingCard):
    panel_icon = FIF.IOT

    def __init__(
        self,
        portal: QtDriverPortal,
        parent: QWidget | None = None,
    ) -> None:
        self.portal = portal
        self._providers = tuple(portal.supported_providers)
        self._selected_provider = self._providers[0] if self._providers else ""
        self._search_results: list[SearchResult] = []
        self._pending_tasks: dict[str, QtDriverTask] = {}
        self._connected_result: SearchResult | None = None
        self._has_searched = False
        self._last_error_text = ""

        super().__init__(
            self.panel_icon,
            self.panel_title(),
            self.panel_description(),
            parent,
        )

        self.status_badge = StatusBadge(self.card)
        self.addWidget(self.status_badge)

        self.search_row = self._create_search_row()
        self.connected_row = self._create_connected_row()
        self._active_widgets: list[QWidget] = []
        self._dynamic_widgets: list[QWidget] = []

        self.portal.sig_state_changed.connect(self._on_state_changed)
        self.portal.sig_connection_lost.connect(self._on_connection_lost)
        self.portal.sig_error.connect(self._on_portal_error)
        qconfig.themeChangedFinished.connect(self._on_theme_changed)

        self._refresh_groups()
        self._sync_ui()

    def panel_title(self) -> str:
        return self.portal.display_name or self.portal.driver_id

    def panel_description(self) -> str:
        return "点击展开搜索设备、建立连接并控制实时流。"

    def _create_search_row(self) -> QWidget:
        row = DeviceRow()

        self.provider_combo = ComboBox(row)
        if self._providers:
            self.provider_combo.addItems(list(self._providers))
            self.provider_combo.setCurrentText(self._selected_provider)
        else:
            self.provider_combo.addItem("当前 driver 未声明 provider")
        self.provider_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)

        self.search_button = PrimaryPushButton("搜索设备", row)
        self.search_button.setIcon(FIF.SEARCH)
        self.search_button.setFixedWidth(128)
        self.search_button.clicked.connect(self._search_devices)

        row.row_layout.addWidget(self.provider_combo, 1)
        row.row_layout.addWidget(self.search_button, 0, Qt.AlignmentFlag.AlignRight)
        return row

    def _create_connected_row(self) -> QWidget:
        row = DeviceRow()

        self.connected_info = DeviceInfoWidget(
            self._connected_title(),
            self._connected_subtitle(),
            row,
        )

        self.stream_button = PrimaryPushButton("开始流", row)
        self.stream_button.setFixedWidth(112)
        self.stream_button.clicked.connect(self._toggle_streaming)

        self.disconnect_button = PushButton("断开连接", row)
        self.disconnect_button.setFixedWidth(112)
        self.disconnect_button.clicked.connect(self._disconnect_device)

        row.row_layout.addWidget(self.connected_info, 1)
        row.row_layout.addWidget(self.stream_button, 0, Qt.AlignmentFlag.AlignRight)
        row.row_layout.addWidget(self.disconnect_button, 0, Qt.AlignmentFlag.AlignRight)
        return row

    def _clear_group_widgets(self) -> None:
        for widget in self._active_widgets:
            self.removeGroupWidget(widget)
            widget.hide()

        for widget in self._dynamic_widgets:
            widget.deleteLater()

        self._active_widgets.clear()
        self._dynamic_widgets.clear()

    def _mount_group_widget(self, widget: QWidget, *, dynamic: bool = False) -> None:
        widget.setParent(self.view)
        self.addGroupWidget(widget)
        widget.show()
        self._active_widgets.append(widget)
        if dynamic:
            self._dynamic_widgets.append(widget)

    def _refresh_groups(self) -> None:
        self._clear_group_widgets()

        if self.portal.is_connected:
            self.connected_info.set_text(
                self._connected_title(),
                self._connected_subtitle(),
            )
            self._mount_group_widget(self.connected_row)
        else:
            self._mount_group_widget(self.search_row)

            if self._search_results:
                for result in self._search_results:
                    self._mount_group_widget(
                        self._create_result_row(result),
                        dynamic=True,
                    )

        if self._last_error_text:
            self._mount_group_widget(
                self._create_message_row(self._last_error_text, is_error=True),
                dynamic=True,
            )

    def _create_result_row(self, result: SearchResult) -> QWidget:
        row = DeviceRow()
        info = DeviceInfoWidget(result.title, result.subtitle, row)

        connect_button = PrimaryPushButton("连接", row)
        connect_button.setFixedWidth(96)
        connect_button.setEnabled(not self._has_pending_task())
        connect_button.clicked.connect(
            lambda _checked=False, item=result: self._connect_device(item)
        )

        row.row_layout.addWidget(info, 1)
        row.row_layout.addWidget(connect_button, 0, Qt.AlignmentFlag.AlignRight)
        return row

    def _create_message_row(self, text: str, *, is_error: bool = False) -> QWidget:
        row = DeviceRow()
        label = CaptionLabel(text, row)
        label.setWordWrap(True)
        if is_error:
            error_color = "#f97066" if isDarkTheme() else "#b42318"
            label.setStyleSheet(f"color: {error_color};")
        row.row_layout.addWidget(label, 1)
        return row

    def _connected_title(self) -> str:
        if self._connected_result is not None and self._connected_result.title.strip():
            return self._connected_result.title.strip()
        return self.portal.display_name or self.portal.driver_id

    def _connected_subtitle(self) -> str:
        fragments: list[str] = []
        if self._selected_provider:
            fragments.append(self._selected_provider)
        if self._connected_result is not None and self._connected_result.subtitle.strip():
            fragments.append(self._connected_result.subtitle.strip())
        descriptor_count = len(self.portal.descriptors())
        if descriptor_count:
            fragments.append(f"{descriptor_count} 路流")
        return " · ".join(fragments)

    def _search_devices(self) -> None:
        provider = self.provider_combo.currentText().strip()
        if not provider or provider not in self._providers:
            return

        self._selected_provider = provider
        self._has_searched = True
        self._search_results.clear()
        self._last_error_text = ""
        task = self.portal.search(provider)
        self._bind_task("search", task, self._on_search_task_done)
        self._sync_ui()
        self._refresh_groups()

    def _connect_device(self, result: SearchResult) -> None:
        self._last_error_text = ""
        task = self.portal.connect_device(result)
        self._bind_task("connect", task, self._on_connect_task_done)
        self._sync_ui()
        self._refresh_groups()

    def _disconnect_device(self) -> None:
        self._last_error_text = ""
        task = self.portal.disconnect_device()
        self._bind_task("disconnect", task, self._on_disconnect_task_done)
        self._sync_ui()

    def _toggle_streaming(self) -> None:
        self._last_error_text = ""
        if self.portal.is_streaming:
            task = self.portal.stop_streaming()
            self._bind_task("stop_streaming", task, self._on_stop_streaming_task_done)
        else:
            task = self.portal.start_streaming()
            self._bind_task(
                "start_streaming",
                task,
                self._on_start_streaming_task_done,
            )
        self._sync_ui()

    def _bind_task(
        self,
        action: str,
        task: QtDriverTask,
        callback: Callable[[QtDriverTask], None],
    ) -> None:
        self._pending_tasks[action] = task

        def _handle_done() -> None:
            if self._pending_tasks.get(action) is task:
                self._pending_tasks.pop(action, None)
            callback(task)
            task.deleteLater()
            self._sync_ui()
            self._refresh_groups()

        task.add_done_callback(lambda _task: _handle_done())

    def _on_search_task_done(self, task: QtDriverTask) -> None:
        if task.error is not None:
            self._last_error_text = self._format_task_error("search", task.error)
            self._search_results.clear()
            return
        self._search_results = self._coerce_search_results(task.result)

    def _on_connect_task_done(self, task: QtDriverTask) -> None:
        if task.error is not None:
            self._last_error_text = self._format_task_error("connect", task.error)
            return
        if isinstance(task.request, SearchResult):
            self._connected_result = task.request
        self._search_results.clear()

    def _on_disconnect_task_done(self, task: QtDriverTask) -> None:
        if task.error is not None:
            self._last_error_text = self._format_task_error("disconnect", task.error)
            return
        self._connected_result = None

    def _on_start_streaming_task_done(self, task: QtDriverTask) -> None:
        if task.error is not None:
            self._last_error_text = self._format_task_error("start_streaming", task.error)

    def _on_stop_streaming_task_done(self, task: QtDriverTask) -> None:
        if task.error is not None:
            self._last_error_text = self._format_task_error("stop_streaming", task.error)

    def _on_provider_changed(self, provider: str) -> None:
        provider = provider.strip()
        if not provider or provider not in self._providers:
            return
        if provider == self._selected_provider:
            return
        self._selected_provider = provider
        self._search_results.clear()
        self._has_searched = False
        self._last_error_text = ""
        self._refresh_groups()

    def _on_state_changed(self, _state: object) -> None:
        if not self.portal.is_connected:
            self._connected_result = None
        self._sync_ui()
        self._refresh_groups()

    def _on_connection_lost(self, detail: object) -> None:
        self._connected_result = None
        message = str(detail).strip()
        self._last_error_text = f"设备连接已丢失：{message}" if message else "设备连接已丢失。"
        self._sync_ui()
        self._refresh_groups()

    def _on_portal_error(self, message: str) -> None:
        if not self._has_pending_task():
            self._last_error_text = self._format_portal_error(message)
            self._refresh_groups()

    def _on_theme_changed(self) -> None:
        self._sync_ui()
        self._refresh_groups()

    def _sync_ui(self) -> None:
        has_providers = bool(self._providers)
        is_busy = self._has_pending_task()
        is_connected = self.portal.is_connected
        is_streaming = self.portal.is_streaming

        self.provider_combo.setEnabled(has_providers and not is_busy and not is_connected)
        self.search_button.setEnabled(has_providers and not is_busy and not is_connected)
        self.search_button.setText("搜索中..." if self._is_task_running("search") else "搜索设备")

        self.stream_button.setEnabled(is_connected and not is_busy)
        self.stream_button.setText("停止流" if is_streaming else "开始流")
        self.stream_button.setIcon(FIF.PAUSE_BOLD if is_streaming else FIF.PLAY_SOLID)
        self.disconnect_button.setEnabled(is_connected and not is_busy)

        self.connected_info.set_text(
            self._connected_title(),
            self._connected_subtitle(),
        )
        self.status_badge.set_status(self._current_badge_status())

    def _current_badge_status(self) -> str:
        if self._is_task_running("search"):
            return "searching"
        if self._is_task_running("connect"):
            return "connecting"
        if self._is_task_running("disconnect"):
            return "disconnecting"
        if self._is_task_running("start_streaming"):
            return "starting"
        if self._is_task_running("stop_streaming"):
            return "stopping"
        if self.portal.is_streaming:
            return "streaming"
        if self.portal.is_connected:
            return "connected"
        return "disconnected"

    def _has_pending_task(self) -> bool:
        return any(task.is_running for task in self._pending_tasks.values())

    def _is_task_running(self, action: str) -> bool:
        task = self._pending_tasks.get(action)
        return task is not None and task.is_running

    def _coerce_search_results(self, result: object) -> list[SearchResult]:
        if not isinstance(result, list):
            return []
        return [item for item in result if isinstance(item, SearchResult)]

    def _format_task_error(self, action: str, error: Exception) -> str:
        action_label = {
            "search": "搜索设备",
            "connect": "连接设备",
            "disconnect": "断开连接",
            "start_streaming": "启动实时流",
            "stop_streaming": "停止实时流",
        }.get(action, action)
        detail = str(error).strip()
        return f"{action_label}失败：{detail or type(error).__name__}"

    def _format_portal_error(self, message: str) -> str:
        normalized = str(message or "").strip()
        if not normalized:
            return "设备操作失败。"
        return normalized
