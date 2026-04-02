from __future__ import annotations

from dataclasses import dataclass, field

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

from modlink_qt_bridge import QtDriverPortal, QtDriverTask, QtModLinkBridge
from modlink_sdk import SearchResult


@dataclass(slots=True)
class _PortalState:
    portal: QtDriverPortal
    selected_provider: str
    search_results: list[SearchResult] = field(default_factory=list)
    pending_tasks: dict[str, QtDriverTask] = field(default_factory=dict)
    connected_result: SearchResult | None = None
    last_error_text: str = ""

    def busy_action(self) -> str:
        for action, task in self.pending_tasks.items():
            if task.is_running:
                return action
        return ""


class DevicePageController(QObject):
    portalsChanged = pyqtSignal()
    messageRaised = pyqtSignal(str)

    def __init__(self, engine: QtModLinkBridge, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._states: dict[str, _PortalState] = {}

        for portal in engine.driver_portals():
            providers = tuple(portal.supported_providers)
            selected_provider = providers[0] if providers else ""
            state = _PortalState(portal=portal, selected_provider=selected_provider)
            self._states[portal.driver_id] = state
            portal.sig_state_changed.connect(
                lambda _value, driver_id=portal.driver_id: self._on_state_changed(
                    driver_id
                )
            )
            portal.sig_connection_lost.connect(
                lambda detail, driver_id=portal.driver_id: self._on_connection_lost(
                    driver_id, detail
                )
            )
            portal.sig_error.connect(
                lambda message, driver_id=portal.driver_id: self._on_portal_error(
                    driver_id, message
                )
            )

    @pyqtProperty("QVariantList", notify=portalsChanged)
    def portals(self) -> list[dict[str, object]]:
        return [self._serialize_portal_state(state) for state in self._states.values()]

    @pyqtSlot(str, str)
    def setSelectedProvider(self, driver_id: str, provider: str) -> None:
        state = self._states.get(driver_id)
        if state is None:
            return
        normalized = str(provider).strip()
        if not normalized or normalized == state.selected_provider:
            return
        state.selected_provider = normalized
        state.search_results.clear()
        state.last_error_text = ""
        self.portalsChanged.emit()

    @pyqtSlot(str)
    def search(self, driver_id: str) -> None:
        state = self._states.get(driver_id)
        if state is None or not state.selected_provider:
            return
        state.search_results.clear()
        state.last_error_text = ""
        task = state.portal.search(state.selected_provider)
        self._bind_task(state, "search", task, self._on_search_done)
        self.portalsChanged.emit()

    @pyqtSlot(str, int)
    def connectDevice(self, driver_id: str, result_index: int) -> None:
        state = self._states.get(driver_id)
        if state is None:
            return
        if result_index < 0 or result_index >= len(state.search_results):
            return
        state.last_error_text = ""
        task = state.portal.connect_device(state.search_results[result_index])
        self._bind_task(state, "connect", task, self._on_connect_done)
        self.portalsChanged.emit()

    @pyqtSlot(str)
    def disconnectDevice(self, driver_id: str) -> None:
        state = self._states.get(driver_id)
        if state is None:
            return
        state.last_error_text = ""
        task = state.portal.disconnect_device()
        self._bind_task(state, "disconnect", task, self._on_disconnect_done)
        self.portalsChanged.emit()

    @pyqtSlot(str)
    def toggleStreaming(self, driver_id: str) -> None:
        state = self._states.get(driver_id)
        if state is None:
            return
        state.last_error_text = ""
        if state.portal.is_streaming:
            task = state.portal.stop_streaming()
            self._bind_task(
                state, "stop_streaming", task, self._on_stream_toggle_done
            )
        else:
            task = state.portal.start_streaming()
            self._bind_task(
                state, "start_streaming", task, self._on_stream_toggle_done
            )
        self.portalsChanged.emit()

    def _bind_task(
        self,
        state: _PortalState,
        action: str,
        task: QtDriverTask,
        callback,
    ) -> None:
        state.pending_tasks[action] = task

        def _handle_done() -> None:
            if state.pending_tasks.get(action) is task:
                state.pending_tasks.pop(action, None)
            callback(state, task, action)
            task.deleteLater()
            self.portalsChanged.emit()

        task.add_done_callback(lambda _task: _handle_done())

    def _on_search_done(
        self, state: _PortalState, task: QtDriverTask, _action: str
    ) -> None:
        if task.error is not None:
            state.last_error_text = self._format_task_error("search", task.error)
            self.messageRaised.emit(state.last_error_text)
            state.search_results.clear()
            return

        result = task.result if isinstance(task.result, list) else []
        state.search_results = [
            item for item in result if isinstance(item, SearchResult)
        ]

    def _on_connect_done(
        self, state: _PortalState, task: QtDriverTask, _action: str
    ) -> None:
        if task.error is not None:
            state.last_error_text = self._format_task_error("connect", task.error)
            self.messageRaised.emit(state.last_error_text)
            return

        if isinstance(task.request, SearchResult):
            state.connected_result = task.request
        state.search_results.clear()
        self.messageRaised.emit(
            f"{state.portal.display_name or state.portal.driver_id} 已连接。"
        )

    def _on_disconnect_done(
        self, state: _PortalState, task: QtDriverTask, _action: str
    ) -> None:
        if task.error is not None:
            state.last_error_text = self._format_task_error("disconnect", task.error)
            self.messageRaised.emit(state.last_error_text)
            return
        state.connected_result = None
        self.messageRaised.emit(
            f"{state.portal.display_name or state.portal.driver_id} 已断开。"
        )

    def _on_stream_toggle_done(
        self, state: _PortalState, task: QtDriverTask, action: str
    ) -> None:
        if task.error is not None:
            state.last_error_text = self._format_task_error(action, task.error)
            self.messageRaised.emit(state.last_error_text)
            return

        if action == "start_streaming":
            self.messageRaised.emit(
                f"{state.portal.display_name or state.portal.driver_id} 已开始流。"
            )
        else:
            self.messageRaised.emit(
                f"{state.portal.display_name or state.portal.driver_id} 已停止流。"
            )

    def _on_state_changed(self, driver_id: str) -> None:
        state = self._states.get(driver_id)
        if state is None:
            return
        if not state.portal.is_connected:
            state.connected_result = None
        self.portalsChanged.emit()

    def _on_connection_lost(self, driver_id: str, detail: object) -> None:
        state = self._states.get(driver_id)
        if state is None:
            return

        state.connected_result = None
        normalized = str(detail).strip()
        state.last_error_text = (
            f"设备连接已丢失：{normalized}" if normalized else "设备连接已丢失。"
        )
        self.messageRaised.emit(state.last_error_text)
        self.portalsChanged.emit()

    def _on_portal_error(self, driver_id: str, message: str) -> None:
        state = self._states.get(driver_id)
        if state is None or state.busy_action():
            return
        state.last_error_text = self._format_portal_error(message)
        self.messageRaised.emit(state.last_error_text)
        self.portalsChanged.emit()

    def _serialize_portal_state(self, state: _PortalState) -> dict[str, object]:
        busy_action = state.busy_action()
        is_connected = state.portal.is_connected
        is_streaming = state.portal.is_streaming
        providers = list(state.portal.supported_providers)
        descriptor_count = len(state.portal.descriptors())
        subtitle_parts: list[str] = []
        if state.selected_provider:
            subtitle_parts.append(state.selected_provider)
        if (
            state.connected_result is not None
            and state.connected_result.subtitle.strip()
        ):
            subtitle_parts.append(state.connected_result.subtitle.strip())
        if descriptor_count:
            subtitle_parts.append(f"{descriptor_count} 路流")

        return {
            "driverId": state.portal.driver_id,
            "title": state.portal.display_name or state.portal.driver_id,
            "description": "点击展开搜索设备、建立连接并控制实时流。",
            "providers": providers,
            "selectedProvider": state.selected_provider,
            "hasProviders": bool(providers),
            "isConnected": is_connected,
            "isStreaming": is_streaming,
            "busy": bool(busy_action),
            "busyAction": busy_action,
            "statusText": self._status_text(state, busy_action),
            "statusTone": self._status_tone(state, busy_action),
            "connectedSubtitle": " · ".join(subtitle_parts),
            "searchButtonText": "搜索中..." if busy_action == "search" else "搜索设备",
            "streamButtonText": "停止流" if is_streaming else "开始流",
            "searchResults": [
                {"title": item.title, "subtitle": item.subtitle}
                for item in state.search_results
            ],
            "errorText": state.last_error_text,
        }

    @staticmethod
    def _status_text(state: _PortalState, busy_action: str) -> str:
        mapping = {
            "search": "搜索中",
            "connect": "连接中",
            "disconnect": "断开中",
            "start_streaming": "启动中",
            "stop_streaming": "停止中",
        }
        if busy_action:
            return mapping.get(busy_action, "处理中")
        if state.portal.is_streaming:
            return "采集中"
        if state.portal.is_connected:
            return "已连接"
        return "未连接"

    @staticmethod
    def _status_tone(state: _PortalState, busy_action: str) -> str:
        if busy_action in {
            "search",
            "connect",
            "disconnect",
            "start_streaming",
            "stop_streaming",
        }:
            return "warning"
        if state.portal.is_streaming:
            return "success"
        if state.portal.is_connected:
            return "info"
        return "neutral"

    @staticmethod
    def _format_task_error(action: str, error: Exception) -> str:
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
