from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget
from qfluentwidgets import (
    ComboBox,
    FluentIcon as FIF,
    PrimaryPushButton,
    PushButton,
    StrongBodyLabel,
)

from ...backend import (
    ConnectConfig,
    DeviceSearchResult,
    DeviceState,
    GanglionBackendBase,
    SearchEvent,
    StateEvent,
)
from ..style_constants import DEFAULT_RADIUS
from .wheel_passthrough_expand_group_setting_card import WheelPassthroughExpandGroupSettingCard


class StatusBadge(QLabel):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent=parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumWidth(110)
        self.setContentsMargins(12, 4, 12, 4)
        self._set_disconnected_style()

    def set_state(self, state: DeviceState) -> None:
        if state in {
            DeviceState.CONNECTED,
            DeviceState.PREVIEWING,
            DeviceState.RECORDING,
        }:
            self.setText("Connected")
            self.setStyleSheet(
                f"""
                QLabel {{
                    color: rgb(15, 94, 54);
                    background: rgba(70, 201, 125, 0.18);
                    border: 1px solid rgba(70, 201, 125, 0.35);
                    border-radius: {DEFAULT_RADIUS}px;
                    padding: 4px 12px;
                    font-weight: 600;
                }}
                """
            )
            return

        if state == DeviceState.CONNECTING:
            self.setText("Connecting")
            self.setStyleSheet(
                f"""
                QLabel {{
                    color: rgb(138, 89, 0);
                    background: rgba(255, 197, 61, 0.18);
                    border: 1px solid rgba(255, 197, 61, 0.35);
                    border-radius: {DEFAULT_RADIUS}px;
                    padding: 4px 12px;
                    font-weight: 600;
                }}
                """
            )
            return

        if state == DeviceState.DISCONNECTING:
            self.setText("Disconnecting")
            self.setStyleSheet(
                f"""
                QLabel {{
                    color: rgb(90, 67, 15);
                    background: rgba(255, 214, 102, 0.18);
                    border: 1px solid rgba(255, 214, 102, 0.35);
                    border-radius: {DEFAULT_RADIUS}px;
                    padding: 4px 12px;
                    font-weight: 600;
                }}
                """
            )
            return

        self._set_disconnected_style()

    def _set_disconnected_style(self) -> None:
        self.setText("Disconnected")
        self.setStyleSheet(
            f"""
            QLabel {{
                color: rgb(122, 33, 43);
                background: rgba(255, 99, 99, 0.14);
                border: 1px solid rgba(255, 99, 99, 0.28);
                border-radius: {DEFAULT_RADIUS}px;
                padding: 4px 12px;
                font-weight: 600;
            }}
            """
        )


class DeviceInfoWidget(QWidget):
    def __init__(
        self,
        title: str,
        subtitle: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.title_label = StrongBodyLabel(title, self)
        self.subtitle_label = QLabel(subtitle, self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)

        self.subtitle_label.setVisible(bool(subtitle))
        self.subtitle_label.setStyleSheet("color: rgba(0, 0, 0, 0.62);")

    def set_text(self, title: str, subtitle: str = "") -> None:
        self.title_label.setText(title)
        self.subtitle_label.setText(subtitle)
        self.subtitle_label.setVisible(bool(subtitle))


class RowContainer(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.row_layout = QHBoxLayout(self)
        self.row_layout.setContentsMargins(48, 14, 48, 14)
        self.row_layout.setSpacing(12)
        self.row_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)


class GanglionConnectionCard(WheelPassthroughExpandGroupSettingCard):
    def __init__(self, backend: GanglionBackendBase, parent: QWidget | None = None) -> None:
        super().__init__(
            FIF.BLUETOOTH,
            "Ganglion 连接",
            "点击展开蓝牙连接设置",
            parent,
        )
        self.backend = backend
        self.current_state = backend.state
        self.current_device_name = backend.device_name
        self.current_device_address = backend.device_address
        self.selected_method = "Native BLE"
        self.search_results: list[DeviceSearchResult] = []
        self.result_rows: list[QWidget] = []
        self.active_rows: list[QWidget] = []
        self.is_searching = False

        self.status_badge = StatusBadge("Disconnected", self.card)
        self.addWidget(self.status_badge)

        self.connection_method_combo = ComboBox(self.view)
        self.connection_method_combo.addItems(
            [
                "Native BLE",
                "Ganglion Dongle",
            ]
        )
        self.connection_method_combo.setCurrentText(self.selected_method)
        self.connection_method_combo.currentTextChanged.connect(self._on_method_changed)

        self.search_button = PrimaryPushButton("Search", self.view)
        self.search_button.setIcon(FIF.SEARCH)
        self.search_button.clicked.connect(self._search_devices)

        self.disconnect_button = PushButton("Disconnect", self.view)
        self.disconnect_button.setIcon(FIF.CLOSE)
        self.disconnect_button.clicked.connect(self.backend.disconnect_device)

        self.search_row = self._create_search_row()
        self.connected_row = self._create_connected_row()

        self.backend.sig_state.connect(self._on_state_changed)
        self.backend.sig_search.connect(self._on_search_event)
        self._sync_action_state()
        self._refresh_groups()
        self.status_badge.set_state(self.current_state)

    def _create_search_row(self) -> QWidget:
        row = RowContainer(self.view)
        self.connection_method_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self.search_button.setFixedWidth(120)

        row.row_layout.addWidget(self.connection_method_combo, 1)
        row.row_layout.addWidget(self.search_button, 0, Qt.AlignmentFlag.AlignRight)
        return row

    def _create_connected_row(self) -> QWidget:
        row = RowContainer(self.view)
        self.connected_info = DeviceInfoWidget(
            self.current_device_name,
            self._connection_subtitle(),
            row,
        )
        self.disconnect_button.setFixedWidth(132)

        row.row_layout.addWidget(self.connected_info, 1)
        row.row_layout.addWidget(self.disconnect_button, 0, Qt.AlignmentFlag.AlignRight)
        return row

    def _clear_group_widgets(self) -> None:
        for widget in self.active_rows:
            self.removeGroupWidget(widget)
            widget.hide()

        for widget in self.result_rows:
            widget.deleteLater()

        self.active_rows.clear()
        self.result_rows.clear()

    def _mount_group_widget(self, widget: QWidget) -> None:
        widget.setParent(self.view)
        widget.show()
        self.addGroupWidget(widget)
        self.active_rows.append(widget)

    def _refresh_groups(self) -> None:
        self._clear_group_widgets()

        if self._shows_connection_panel():
            self.connected_info.set_text(
                self.current_device_name,
                self._connection_subtitle(),
            )
            self._mount_group_widget(self.connected_row)
            return

        self._mount_group_widget(self.search_row)
        if self.is_searching:
            return

        for result in self.search_results:
            row = self._create_result_row(result)
            self.result_rows.append(row)
            self._mount_group_widget(row)

    def _create_result_row(self, result: DeviceSearchResult) -> QWidget:
        row = RowContainer(self.view)
        info = DeviceInfoWidget(result.name, result.address, row)

        connect_button = PrimaryPushButton("Connect", row)
        connect_button.setIcon(FIF.CONNECT)
        connect_button.setFixedWidth(120)
        connect_button.clicked.connect(
            lambda _checked=False, device=result: self._connect_device(device)
        )

        row.row_layout.addWidget(info, 1)
        row.row_layout.addWidget(connect_button, 0, Qt.AlignmentFlag.AlignRight)
        return row

    def _search_devices(self) -> None:
        self.backend.search_devices(self.connection_method_combo.currentText())

    def _connect_device(self, result: DeviceSearchResult) -> None:
        self.backend.connect_device(
            ConnectConfig(
                device_name=result.name,
                connection_method=result.method,
                device_address=result.address,
            )
        )

    def _on_method_changed(self, method: str) -> None:
        self.selected_method = method
        if self.search_results:
            self.search_results.clear()
            self._refresh_groups()

    def _on_state_changed(self, event: StateEvent) -> None:
        self.current_state = event.state
        self.current_device_name = event.device_name or self.current_device_name
        self.current_device_address = event.device_address or self.current_device_address
        self.status_badge.set_state(event.state)
        if not self._shows_connection_panel():
            self.current_device_address = ""

        if self._shows_connection_panel():
            self.search_results.clear()
        elif event.state in {DeviceState.DISCONNECTED, DeviceState.ERROR}:
            self.search_results.clear()

        self._sync_action_state()
        self._refresh_groups()

    def _on_search_event(self, event: SearchEvent) -> None:
        self.is_searching = event.is_searching
        self.search_results = list(event.results)
        self._sync_action_state()
        self._refresh_groups()

    def _is_connected(self) -> bool:
        return self.current_state in {
            DeviceState.CONNECTED,
            DeviceState.PREVIEWING,
            DeviceState.RECORDING,
        }

    def _shows_connection_panel(self) -> bool:
        return self.current_state in {
            DeviceState.CONNECTING,
            DeviceState.DISCONNECTING,
            DeviceState.CONNECTED,
            DeviceState.PREVIEWING,
            DeviceState.RECORDING,
        }

    def _connection_subtitle(self) -> str:
        if self.current_state == DeviceState.CONNECTING:
            return self._build_connection_subtitle("Connecting...")
        if self.current_state == DeviceState.DISCONNECTING:
            return self._build_connection_subtitle("Disconnecting...")
        return self._build_connection_subtitle()

    def _build_connection_subtitle(self, suffix: str = "") -> str:
        parts = [f"Method: {self.selected_method}"]
        if self.current_device_address:
            parts.append(self.current_device_address)
        if suffix:
            parts.append(suffix)
        return " · ".join(parts)

    def _sync_action_state(self) -> None:
        is_busy = self.current_state in {DeviceState.CONNECTING, DeviceState.DISCONNECTING}
        is_connected = self._is_connected()
        self.connection_method_combo.setEnabled(
            not is_busy and not is_connected and not self.is_searching
        )
        self.search_button.setEnabled(not is_busy and not is_connected and not self.is_searching)
        self.disconnect_button.setEnabled(not is_busy and is_connected)
        self.search_button.setText("Searching..." if self.is_searching else "Search")
