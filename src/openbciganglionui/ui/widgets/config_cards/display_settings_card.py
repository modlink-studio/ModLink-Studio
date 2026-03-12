from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CheckBox,
    DoubleSpinBox,
    FluentIcon as FIF,
    SpinBox,
    TogglePushButton,
)
from qfluentwidgets.components.settings.setting_card import SettingCard

from ...settings import DisplaySettings
from ..common import WheelPassthroughExpandGroupSettingCard


class PointCountSettingCard(SettingCard):
    def __init__(
        self,
        display_settings: DisplaySettings,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            FIF.SETTING,
            "显示点数",
            "控制实时波形窗口最多保留多少个 sample point。",
            parent,
        )
        self.display_settings = display_settings
        self.spin_box = SpinBox(self)

        self.spin_box.setRange(100, 10000)
        self.spin_box.setSingleStep(100)
        self.spin_box.setSuffix(" pts")
        self.spin_box.setFixedWidth(132)
        self.spin_box.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.spin_box.setValue(self.display_settings.max_samples)

        self.hBoxLayout.addWidget(self.spin_box, 0, Qt.AlignmentFlag.AlignRight)
        self.hBoxLayout.addSpacing(16)

        self.spin_box.valueChanged.connect(self.display_settings.set_max_samples)
        self.display_settings.maxSamplesChanged.connect(self._sync_value)

    def _sync_value(self, value: int) -> None:
        if self.spin_box.value() == value:
            return

        self.spin_box.blockSignals(True)
        self.spin_box.setValue(value)
        self.spin_box.blockSignals(False)


class ChannelToggleRow(QWidget):
    def __init__(
        self,
        channel_name: str,
        description: str,
        is_checked: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.title_label = BodyLabel(channel_name, self)
        self.description_label = CaptionLabel(description, self)
        self.state_label = CaptionLabel(self)
        self.check_box = CheckBox(self)
        self.check_box.setText("")

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)
        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.description_label)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(48, 14, 12, 14)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(text_layout, 1)
        layout.addWidget(self.state_label, 0, Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.check_box, 0, Qt.AlignmentFlag.AlignRight)

        self.description_label.setStyleSheet("color: rgba(0, 0, 0, 0.62);")
        self.set_checked(is_checked)

    def set_checked(self, is_checked: bool) -> None:
        self.check_box.setChecked(is_checked)
        self.state_label.setText("ON" if is_checked else "OFF")
        self.state_label.setStyleSheet(
            "color: rgba(0, 0, 0, 0.72);" if is_checked else "color: rgba(0, 0, 0, 0.48);"
        )

    def is_checked(self) -> bool:
        return self.check_box.isChecked()


class ToggleButtonSettingRow(QWidget):
    def __init__(
        self,
        title: str,
        description: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.title_label = BodyLabel(title, self)
        self.description_label = CaptionLabel(description, self)
        self.toggle_button = TogglePushButton(self)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)
        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.description_label)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(48, 14, 48, 14)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(text_layout, 1)
        layout.addWidget(self.toggle_button, 0, Qt.AlignmentFlag.AlignRight)

        self.description_label.setStyleSheet("color: rgba(0, 0, 0, 0.62);")


class YAxisBoundSettingRow(QWidget):
    def __init__(
        self,
        title: str,
        description: str,
        unit_text: str = "uV",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.title_label = BodyLabel(title, self)
        self.description_label = CaptionLabel(description, self)
        self.spin_box = DoubleSpinBox(self)
        self.unit_label = CaptionLabel(unit_text, self)

        self.spin_box.setDecimals(1)
        self.spin_box.setRange(-1000000.0, 1000000.0)
        self.spin_box.setSingleStep(10.0)
        self.spin_box.setFixedWidth(140)
        self.spin_box.setAlignment(Qt.AlignmentFlag.AlignRight)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)
        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.description_label)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(48, 14, 48, 14)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(text_layout, 1)
        layout.addWidget(self.spin_box, 0, Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.unit_label, 0, Qt.AlignmentFlag.AlignRight)

        self.description_label.setStyleSheet("color: rgba(0, 0, 0, 0.62);")
        self.unit_label.setStyleSheet("color: rgba(0, 0, 0, 0.62);")


class ChannelVisibilitySettingCard(WheelPassthroughExpandGroupSettingCard):
    def __init__(
        self,
        display_settings: DisplaySettings,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            FIF.SETTING,
            "Channel 显示",
            "选择要绘制的 Ganglion channel。",
            parent,
        )
        self.display_settings = display_settings
        self.channel_rows: list[ChannelToggleRow] = []

        for index in range(self.display_settings.n_channels):
            row = ChannelToggleRow(
                f"通道 {index + 1}",
                f"打开后在实时波形中显示通道 {index + 1}。",
                self.display_settings.is_channel_visible(index),
                parent=self.view,
            )
            row.check_box.stateChanged.connect(
                lambda is_checked, channel_index=index: self._on_channel_checked(
                    channel_index, bool(is_checked)
                )
            )
            self.addGroupWidget(row)
            self.channel_rows.append(row)

        self.display_settings.channelVisibilityChanged.connect(self._sync_switches)

    def _on_channel_checked(self, index: int, is_checked: bool) -> None:
        self.display_settings.set_channel_visible(index, is_checked)

    def _sync_switches(self, visibility: tuple[bool, ...]) -> None:
        for index, row in enumerate(self.channel_rows):
            if index >= len(visibility):
                break
            if row.is_checked() == visibility[index]:
                continue

            row.check_box.blockSignals(True)
            row.set_checked(visibility[index])
            row.check_box.blockSignals(False)


class YAxisRangeSettingCard(WheelPassthroughExpandGroupSettingCard):
    AUTO_TEXT = "Auto"
    FIXED_TEXT = "固定范围"

    def __init__(
        self,
        display_settings: DisplaySettings,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            FIF.SETTING,
            "纵轴范围",
            "控制实时波形的纵轴缩放方式和固定量程。",
            parent,
        )
        self.display_settings = display_settings
        self.active_rows: list[QWidget] = []

        self.mode_row = ToggleButtonSettingRow(
            "缩放模式",
            "选择自动缩放，或使用固定上下界。",
            parent=self.view,
        )
        self.mode_row.toggle_button.setFixedWidth(140)
        self.mode_row.toggle_button.setFixedHeight(32)
        self.mode_row.toggle_button.clicked.connect(self._toggle_mode)

        self.lower_bound_row = YAxisBoundSettingRow(
            "下界",
            "固定模式下显示的最小值。",
            parent=self.view,
        )
        self.lower_bound_row.spin_box.valueChanged.connect(self._on_lower_bound_changed)

        self.upper_bound_row = YAxisBoundSettingRow(
            "上界",
            "固定模式下显示的最大值。",
            parent=self.view,
        )
        self.upper_bound_row.spin_box.valueChanged.connect(self._on_upper_bound_changed)

        self.display_settings.yAxisAutoChanged.connect(self._sync_auto_mode)
        self.display_settings.yAxisBoundsChanged.connect(self._sync_bounds)

        self._sync_auto_mode(self.display_settings.y_axis_auto)
        self._sync_bounds(
            self.display_settings.y_axis_lower,
            self.display_settings.y_axis_upper,
        )
        self._refresh_groups()

    def _clear_group_widgets(self) -> None:
        for widget in self.active_rows:
            self.removeGroupWidget(widget)
            widget.hide()

        self.active_rows.clear()

    def _mount_group_widget(self, widget: QWidget) -> None:
        widget.setParent(self.view)
        widget.show()
        self.addGroupWidget(widget)
        self.active_rows.append(widget)

    def _refresh_groups(self) -> None:
        self._clear_group_widgets()
        self._mount_group_widget(self.mode_row)

        if self.display_settings.y_axis_auto:
            return

        self._mount_group_widget(self.upper_bound_row)
        self._mount_group_widget(self.lower_bound_row)

    def _sync_auto_mode(self, is_auto: bool) -> None:
        self.mode_row.toggle_button.blockSignals(True)
        self.mode_row.toggle_button.setChecked(not is_auto)
        self.mode_row.toggle_button.blockSignals(False)
        self.mode_row.toggle_button.setText(self.AUTO_TEXT if is_auto else self.FIXED_TEXT)
        self.mode_row.toggle_button.setIcon(None)

        self._refresh_groups()

    def _sync_bounds(self, lower: float, upper: float) -> None:
        self.lower_bound_row.spin_box.blockSignals(True)
        self.lower_bound_row.spin_box.setMaximum(upper - 0.1)
        self.lower_bound_row.spin_box.setValue(lower)
        self.lower_bound_row.spin_box.blockSignals(False)

        self.upper_bound_row.spin_box.blockSignals(True)
        self.upper_bound_row.spin_box.setMinimum(lower + 0.1)
        self.upper_bound_row.spin_box.setValue(upper)
        self.upper_bound_row.spin_box.blockSignals(False)

    def _toggle_mode(self) -> None:
        self.display_settings.set_y_axis_auto(not self.display_settings.y_axis_auto)

    def _on_lower_bound_changed(self, value: float) -> None:
        self.display_settings.set_y_axis_bounds(
            value,
            self.display_settings.y_axis_upper,
        )

    def _on_upper_bound_changed(self, value: float) -> None:
        self.display_settings.set_y_axis_bounds(
            self.display_settings.y_axis_lower,
            value,
        )
