from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CheckBox,
    FluentIcon as FIF,
    SpinBox,
)
from qfluentwidgets.components.settings.setting_card import SettingCard

from ..display_settings import DisplaySettings
from .wheel_passthrough_expand_group_setting_card import WheelPassthroughExpandGroupSettingCard


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
        self.check_box = CheckBox(self)
        self.check_box.setText("")

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
        layout.addWidget(self.check_box, 0, Qt.AlignmentFlag.AlignRight)

        self.description_label.setStyleSheet("color: rgba(0, 0, 0, 0.62);")
        self.set_checked(is_checked)

    def set_checked(self, is_checked: bool) -> None:
        self.check_box.setChecked(is_checked)

    def is_checked(self) -> bool:
        return self.check_box.isChecked()


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
                f"绘制 ch{index + 1}",
                f"打开后在实时波形中显示 ch{index + 1}。",
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
