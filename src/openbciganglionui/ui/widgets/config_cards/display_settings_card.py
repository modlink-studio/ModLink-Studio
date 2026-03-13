from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CheckBox,
    ComboBox,
    CompactDoubleSpinBox,
    DoubleSpinBox,
    FluentIcon as FIF,
    SpinBox,
    TogglePushButton,
)
from qfluentwidgets.components.settings.setting_card import SettingCard

from ...settings import ChannelFilterConfig, DisplaySettings
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
        self.unit_label = CaptionLabel("pts", self)

        self.spin_box.setRange(100, 10000)
        self.spin_box.setSingleStep(100)
        self.spin_box.setFixedWidth(164)
        self.spin_box.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.spin_box.setValue(self.display_settings.max_samples)
        self.unit_label.setStyleSheet("color: rgba(0, 0, 0, 0.62);")

        self.hBoxLayout.addWidget(self.spin_box, 0, Qt.AlignmentFlag.AlignRight)
        self.hBoxLayout.addSpacing(12)
        self.hBoxLayout.addWidget(self.unit_label, 0, Qt.AlignmentFlag.AlignRight)
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


class BandFilterEditorRow(QWidget):
    MODE_LABELS = {
        "none": "关闭",
        "lowpass": "低通",
        "highpass": "高通",
        "bandpass": "带通",
    }
    MODE_ORDER = ("none", "lowpass", "highpass", "bandpass")
    LABEL_TO_MODE = {label: mode for mode, label in MODE_LABELS.items()}

    def __init__(
        self,
        title: str,
        description: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.title_label = BodyLabel(title, self)
        self.description_label = CaptionLabel(description, self)

        self.mode_label = CaptionLabel("滤波", self)
        self.mode_combo = ComboBox(self)
        self.mode_combo.addItems([self.MODE_LABELS[mode] for mode in self.MODE_ORDER])
        self.mode_combo.setFixedWidth(96)

        self.low_cut_label = CaptionLabel("低频", self)
        self.low_cut_spin = self._create_spin_box()
        self.low_cut_unit_label = CaptionLabel("Hz", self)
        self.high_cut_label = CaptionLabel("高频", self)
        self.high_cut_spin = self._create_spin_box()
        self.high_cut_unit_label = CaptionLabel("Hz", self)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)
        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.description_label)

        control_layout = QHBoxLayout()
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.setSpacing(8)
        control_layout.addWidget(self.mode_label)
        control_layout.addWidget(self.mode_combo)
        control_layout.addWidget(self.low_cut_label)
        control_layout.addWidget(self.low_cut_spin)
        control_layout.addWidget(self.low_cut_unit_label)
        control_layout.addWidget(self.high_cut_label)
        control_layout.addWidget(self.high_cut_spin)
        control_layout.addWidget(self.high_cut_unit_label)
        control_layout.addStretch(1)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(48, 14, 48, 14)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addLayout(text_layout, 1)
        layout.addLayout(control_layout, 0)

        self.description_label.setStyleSheet("color: rgba(0, 0, 0, 0.62);")
        for label in (
            self.mode_label,
            self.low_cut_label,
            self.low_cut_unit_label,
            self.high_cut_label,
            self.high_cut_unit_label,
        ):
            label.setStyleSheet("color: rgba(0, 0, 0, 0.62);")

        self.mode_combo.currentTextChanged.connect(self._on_editor_changed)
        self.low_cut_spin.valueChanged.connect(self._on_editor_changed)
        self.high_cut_spin.valueChanged.connect(self._on_editor_changed)

        self.set_config(ChannelFilterConfig())

    def _create_spin_box(self) -> CompactDoubleSpinBox:
        spin_box = CompactDoubleSpinBox(self)
        spin_box.setDecimals(1)
        spin_box.setRange(0.1, 1000.0)
        spin_box.setSingleStep(1.0)
        spin_box.setFixedWidth(84)
        spin_box.setAlignment(Qt.AlignmentFlag.AlignRight)
        return spin_box

    def set_config(self, config: ChannelFilterConfig) -> None:
        self.mode_combo.blockSignals(True)
        self.low_cut_spin.blockSignals(True)
        self.high_cut_spin.blockSignals(True)

        self.mode_combo.setCurrentText(
            self.MODE_LABELS.get(config.mode, self.MODE_LABELS["none"])
        )
        self.low_cut_spin.setValue(float(config.low_cut_hz))
        self.high_cut_spin.setValue(float(config.high_cut_hz))

        self.mode_combo.blockSignals(False)
        self.low_cut_spin.blockSignals(False)
        self.high_cut_spin.blockSignals(False)
        self._update_parameter_visibility(config.mode)

    def current_patch(self) -> dict[str, float | str]:
        return {
            "mode": self.LABEL_TO_MODE.get(self.mode_combo.currentText(), "none"),
            "low_cut_hz": float(self.low_cut_spin.value()),
            "high_cut_hz": float(self.high_cut_spin.value()),
        }

    def _on_editor_changed(self, *_args) -> None:
        mode = self.LABEL_TO_MODE.get(self.mode_combo.currentText(), "none")
        self._update_parameter_visibility(mode)

    def _update_parameter_visibility(self, mode: str) -> None:
        show_low_cut = mode in {"highpass", "bandpass"}
        show_high_cut = mode in {"lowpass", "bandpass"}

        for widget in (self.low_cut_label, self.low_cut_spin, self.low_cut_unit_label):
            widget.setVisible(show_low_cut)
        for widget in (self.high_cut_label, self.high_cut_spin, self.high_cut_unit_label):
            widget.setVisible(show_high_cut)


class PowerlineFilterEditorRow(QWidget):
    POWERLINE_LABELS = {
        "none": "关闭",
        "hz50": "50 Hz",
        "hz60": "60 Hz",
        "hz50_60": "50 + 60 Hz",
    }
    POWERLINE_ORDER = ("none", "hz50", "hz60", "hz50_60")
    LABEL_TO_POWERLINE = {label: mode for mode, label in POWERLINE_LABELS.items()}

    def __init__(
        self,
        title: str,
        description: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.title_label = BodyLabel(title, self)
        self.description_label = CaptionLabel(description, self)
        self.mode_label = CaptionLabel("工频", self)
        self.mode_combo = ComboBox(self)
        self.mode_combo.addItems(
            [self.POWERLINE_LABELS[mode] for mode in self.POWERLINE_ORDER]
        )
        self.mode_combo.setFixedWidth(132)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)
        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.description_label)

        control_layout = QHBoxLayout()
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.setSpacing(8)
        control_layout.addWidget(self.mode_label)
        control_layout.addWidget(self.mode_combo)
        control_layout.addStretch(1)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(48, 14, 48, 14)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(text_layout, 1)
        layout.addLayout(control_layout, 0)

        self.description_label.setStyleSheet("color: rgba(0, 0, 0, 0.62);")
        self.mode_label.setStyleSheet("color: rgba(0, 0, 0, 0.62);")

    def set_config(self, config: ChannelFilterConfig) -> None:
        self.mode_combo.blockSignals(True)
        self.mode_combo.setCurrentText(
            self.POWERLINE_LABELS.get(
                config.powerline_mode,
                self.POWERLINE_LABELS["none"],
            )
        )
        self.mode_combo.blockSignals(False)

    def current_patch(self) -> dict[str, str]:
        return {
            "powerline_mode": self.LABEL_TO_POWERLINE.get(
                self.mode_combo.currentText(),
                "none",
            )
        }


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


class FilterScopeSettingCard(SettingCard):
    SHARED_TEXT = "统一配置"
    PER_CHANNEL_TEXT = "分别配置"

    def __init__(
        self,
        display_settings: DisplaySettings,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            FIF.SETTING,
            "配置方式",
            "决定 4 个通道是共用一套滤波配置，还是分别配置。",
            parent,
        )
        self.display_settings = display_settings
        self.toggle_button = TogglePushButton(self)
        self.toggle_button.setFixedWidth(140)
        self.toggle_button.setFixedHeight(32)
        self.hBoxLayout.addWidget(self.toggle_button, 0, Qt.AlignmentFlag.AlignRight)
        self.hBoxLayout.addSpacing(16)

        self.toggle_button.clicked.connect(self._toggle_mode)
        self.display_settings.filterSettingsChanged.connect(self._sync_from_settings)
        self._sync_from_settings()

    def _toggle_mode(self) -> None:
        self.display_settings.set_shared_filter_enabled(
            not self.display_settings.shared_filter_enabled
        )

    def _sync_from_settings(self) -> None:
        is_shared = self.display_settings.shared_filter_enabled
        self.toggle_button.blockSignals(True)
        self.toggle_button.setChecked(is_shared)
        self.toggle_button.setText(
            self.SHARED_TEXT if is_shared else self.PER_CHANNEL_TEXT
        )
        self.toggle_button.setIcon(None)
        self.toggle_button.blockSignals(False)


class FilterFamilySettingCard(SettingCard):
    FILTER_LABELS = {
        "butterworth": "Butterworth",
        "chebyshev1": "Chebyshev I",
        "bessel": "Bessel",
        "butterworth_zero_phase": "Butterworth Zero Phase",
        "chebyshev1_zero_phase": "Chebyshev I Zero Phase",
        "bessel_zero_phase": "Bessel Zero Phase",
    }
    FILTER_ORDER = (
        "butterworth",
        "chebyshev1",
        "bessel",
        "butterworth_zero_phase",
        "chebyshev1_zero_phase",
        "bessel_zero_phase",
    )
    LABEL_TO_FILTER = {label: value for value, label in FILTER_LABELS.items()}

    def __init__(
        self,
        display_settings: DisplaySettings,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            FIF.SETTING,
            "滤波器类别",
            "统一设置显示滤波和工频滤波使用的 BrainFlow 滤波器类别。",
            parent,
        )
        self.display_settings = display_settings
        self.combo_box = ComboBox(self)
        self.combo_box.addItems([self.FILTER_LABELS[item] for item in self.FILTER_ORDER])
        self.combo_box.setFixedWidth(220)

        self.hBoxLayout.addWidget(self.combo_box, 0, Qt.AlignmentFlag.AlignRight)
        self.hBoxLayout.addSpacing(16)

        self.combo_box.currentTextChanged.connect(self._on_value_changed)
        self.display_settings.filterSettingsChanged.connect(self._sync_value)
        self._sync_value()

    def _on_value_changed(self, text: str) -> None:
        self.display_settings.set_filter_family(
            self.LABEL_TO_FILTER.get(text, "butterworth")
        )

    def _sync_value(self) -> None:
        target = self.FILTER_LABELS.get(
            self.display_settings.filter_family,
            self.FILTER_LABELS["butterworth"],
        )
        if self.combo_box.currentText() == target:
            return

        self.combo_box.blockSignals(True)
        self.combo_box.setCurrentText(target)
        self.combo_box.blockSignals(False)


class FilterOrderSettingCard(SettingCard):
    def __init__(
        self,
        display_settings: DisplaySettings,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            FIF.SETTING,
            "滤波阶次",
            "统一设置显示滤波和工频滤波的阶次。",
            parent,
        )
        self.display_settings = display_settings
        self.spin_box = SpinBox(self)
        self.unit_label = CaptionLabel("阶", self)

        self.spin_box.setRange(1, 8)
        self.spin_box.setFixedWidth(168)
        self.spin_box.setValue(self.display_settings.filter_order)
        self.unit_label.setStyleSheet("color: rgba(0, 0, 0, 0.62);")

        self.hBoxLayout.addWidget(self.spin_box, 0, Qt.AlignmentFlag.AlignRight)
        self.hBoxLayout.addSpacing(12)
        self.hBoxLayout.addWidget(self.unit_label, 0, Qt.AlignmentFlag.AlignRight)
        self.hBoxLayout.addSpacing(16)

        self.spin_box.valueChanged.connect(self.display_settings.set_filter_order)
        self.display_settings.filterSettingsChanged.connect(self._sync_value)

    def _sync_value(self) -> None:
        if self.spin_box.value() == self.display_settings.filter_order:
            return

        self.spin_box.blockSignals(True)
        self.spin_box.setValue(self.display_settings.filter_order)
        self.spin_box.blockSignals(False)


class ChannelBandFilterSettingCard(WheelPassthroughExpandGroupSettingCard):
    def __init__(
        self,
        display_settings: DisplaySettings,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            FIF.SETTING,
            "通道滤波",
            "配置低通、高通、带通等显示滤波，不影响原始数据保存。",
            parent,
        )
        self.display_settings = display_settings
        self.active_rows: list[QWidget] = []

        self.shared_editor_row = BandFilterEditorRow(
            "全部通道",
            "统一配置 4 个通道的显示滤波。",
        )
        self.shared_editor_row.mode_combo.currentTextChanged.connect(
            self._on_shared_filter_changed
        )
        self.shared_editor_row.low_cut_spin.valueChanged.connect(
            self._on_shared_filter_changed
        )
        self.shared_editor_row.high_cut_spin.valueChanged.connect(
            self._on_shared_filter_changed
        )

        self.channel_editor_rows: list[BandFilterEditorRow] = []
        for index in range(self.display_settings.n_channels):
            row = BandFilterEditorRow(
                f"通道 {index + 1}",
                f"仅影响通道 {index + 1} 的显示滤波。",
            )
            row.mode_combo.currentTextChanged.connect(
                lambda _text, channel_index=index: self._on_channel_filter_changed(
                    channel_index
                )
            )
            row.low_cut_spin.valueChanged.connect(
                lambda _value, channel_index=index: self._on_channel_filter_changed(
                    channel_index
                )
            )
            row.high_cut_spin.valueChanged.connect(
                lambda _value, channel_index=index: self._on_channel_filter_changed(
                    channel_index
                )
            )
            self.channel_editor_rows.append(row)

        self.display_settings.filterSettingsChanged.connect(self._sync_from_settings)
        self._sync_from_settings()

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
        if self.display_settings.shared_filter_enabled:
            self._mount_group_widget(self.shared_editor_row)
            return

        for row in self.channel_editor_rows:
            self._mount_group_widget(row)

    def _sync_from_settings(self) -> None:
        self.shared_editor_row.set_config(self.display_settings.shared_filter_config)
        for index, row in enumerate(self.channel_editor_rows):
            row.set_config(self.display_settings.channel_filter_config(index))
        self._refresh_groups()

    def _on_shared_filter_changed(self, *_args) -> None:
        self.display_settings.set_shared_filter_config(
            self._merge_band_patch(
                self.display_settings.shared_filter_config,
                self.shared_editor_row.current_patch(),
            )
        )

    def _on_channel_filter_changed(self, index: int) -> None:
        if not 0 <= index < len(self.channel_editor_rows):
            return
        self.display_settings.set_channel_filter_config(
            index,
            self._merge_band_patch(
                self.display_settings.channel_filter_config(index),
                self.channel_editor_rows[index].current_patch(),
            ),
        )

    def _merge_band_patch(
        self,
        base_config: ChannelFilterConfig,
        patch: dict[str, float | str],
    ) -> ChannelFilterConfig:
        return ChannelFilterConfig(
            mode=str(patch["mode"]),
            low_cut_hz=float(patch["low_cut_hz"]),
            high_cut_hz=float(patch["high_cut_hz"]),
            powerline_mode=base_config.powerline_mode,
            notch_width_hz=base_config.notch_width_hz,
        )


class ChannelPowerlineFilterSettingCard(WheelPassthroughExpandGroupSettingCard):
    def __init__(
        self,
        display_settings: DisplaySettings,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            FIF.SETTING,
            "工频滤波",
            "配置 50 Hz、60 Hz 或 50 + 60 Hz 工频抑制。",
            parent,
        )
        self.display_settings = display_settings
        self.active_rows: list[QWidget] = []

        self.shared_editor_row = PowerlineFilterEditorRow(
            "全部通道",
            "统一配置 4 个通道的工频滤波。",
        )
        self.shared_editor_row.mode_combo.currentTextChanged.connect(
            self._on_shared_filter_changed
        )

        self.channel_editor_rows: list[PowerlineFilterEditorRow] = []
        for index in range(self.display_settings.n_channels):
            row = PowerlineFilterEditorRow(
                f"通道 {index + 1}",
                f"仅影响通道 {index + 1} 的工频滤波。",
            )
            row.mode_combo.currentTextChanged.connect(
                lambda _text, channel_index=index: self._on_channel_filter_changed(
                    channel_index
                )
            )
            self.channel_editor_rows.append(row)

        self.display_settings.filterSettingsChanged.connect(self._sync_from_settings)
        self._sync_from_settings()

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
        if self.display_settings.shared_filter_enabled:
            self._mount_group_widget(self.shared_editor_row)
            return

        for row in self.channel_editor_rows:
            self._mount_group_widget(row)

    def _sync_from_settings(self) -> None:
        self.shared_editor_row.set_config(self.display_settings.shared_filter_config)
        for index, row in enumerate(self.channel_editor_rows):
            row.set_config(self.display_settings.channel_filter_config(index))
        self._refresh_groups()

    def _on_shared_filter_changed(self, *_args) -> None:
        self.display_settings.set_shared_filter_config(
            self._merge_powerline_patch(
                self.display_settings.shared_filter_config,
                self.shared_editor_row.current_patch(),
            )
        )

    def _on_channel_filter_changed(self, index: int) -> None:
        if not 0 <= index < len(self.channel_editor_rows):
            return
        self.display_settings.set_channel_filter_config(
            index,
            self._merge_powerline_patch(
                self.display_settings.channel_filter_config(index),
                self.channel_editor_rows[index].current_patch(),
            ),
        )

    def _merge_powerline_patch(
        self,
        base_config: ChannelFilterConfig,
        patch: dict[str, str],
    ) -> ChannelFilterConfig:
        return ChannelFilterConfig(
            mode=base_config.mode,
            low_cut_hz=base_config.low_cut_hz,
            high_cut_hz=base_config.high_cut_hz,
            powerline_mode=str(patch["powerline_mode"]),
            notch_width_hz=base_config.notch_width_hz,
        )


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
        )
        self.mode_row.toggle_button.setFixedWidth(140)
        self.mode_row.toggle_button.setFixedHeight(32)
        self.mode_row.toggle_button.clicked.connect(self._toggle_mode)

        self.lower_bound_row = YAxisBoundSettingRow(
            "下界",
            "固定模式下显示的最小值。",
        )
        self.lower_bound_row.spin_box.valueChanged.connect(self._on_lower_bound_changed)

        self.upper_bound_row = YAxisBoundSettingRow(
            "上界",
            "固定模式下显示的最大值。",
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
