from __future__ import annotations

from PyQt6.QtCore import QSignalBlocker, Qt, pyqtSignal
from PyQt6.QtWidgets import QCheckBox, QGridLayout, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    ComboBox,
    CompactDoubleSpinBox,
    SimpleCardWidget,
    SpinBox,
    StrongBodyLabel,
    SwitchButton,
)

from modlink_sdk import StreamDescriptor
from modlink_ui_qt_widgets.widgets.shared.inputs import TokenLineEdit

from ..models import SignalFilterSettings, SignalPreviewSettings

SIGNAL_WINDOW_SECONDS_OPTIONS = (1, 2, 4, 8, 12, 20)


class SignalPayloadSettingsPanel(SimpleCardWidget):
    sig_state_changed = pyqtSignal(object)

    def __init__(
        self,
        descriptor: StreamDescriptor,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.descriptor = descriptor
        self._channel_names = tuple(descriptor.channel_names)
        self._is_multi_channel = len(self._channel_names) > 1
        self._channel_checkboxes: list[QCheckBox] = []
        self.setBorderRadius(12)

        self.title_label = StrongBodyLabel("信号图设置", self)
        self.tip_label = CaptionLabel(
            "设置会立即作用到当前预览，包括滤波、布局、通道显示和 Y 轴范围。",
            self,
        )
        self.tip_label.setWordWrap(True)

        nyquist_hz = max(
            1,
            int(round(float(descriptor.nominal_sample_rate_hz or 1.0) / 2.0)),
        )
        default_high_cutoff_hz = max(2, min(40, nyquist_hz))

        self.settings_grid = QGridLayout()
        self.settings_grid.setContentsMargins(0, 0, 0, 0)
        self.settings_grid.setHorizontalSpacing(12)
        self.settings_grid.setVerticalSpacing(10)
        self.settings_grid.setColumnStretch(1, 1)
        self.settings_grid.setColumnMinimumWidth(1, 240)

        self.duration_label = BodyLabel("时间长度", self)
        self.duration_combo = ComboBox(self)
        self.duration_combo.setFixedWidth(180)
        for seconds in SIGNAL_WINDOW_SECONDS_OPTIONS:
            self.duration_combo.addItem(f"{seconds} 秒", userData=seconds)
        self.settings_grid.addWidget(self.duration_label, 0, 0)
        self.settings_grid.addWidget(
            self.duration_combo,
            0,
            1,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

        self.filter_mode_label = BodyLabel("滤波模式", self)
        self.filter_mode_combo = ComboBox(self)
        self.filter_mode_combo.setFixedWidth(180)
        self.filter_mode_combo.addItem("无", userData="none")
        self.filter_mode_combo.addItem("低通", userData="low_pass")
        self.filter_mode_combo.addItem("高通", userData="high_pass")
        self.filter_mode_combo.addItem("带通", userData="band_pass")
        self.filter_mode_combo.addItem("带阻", userData="band_stop")
        self.settings_grid.addWidget(self.filter_mode_label, 1, 0)
        self.settings_grid.addWidget(
            self.filter_mode_combo,
            1,
            1,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

        self.filter_family_label = BodyLabel("滤波器家族", self)
        self.filter_family_combo = ComboBox(self)
        self.filter_family_combo.setFixedWidth(180)
        self.filter_family_combo.addItem("Butterworth", userData="butterworth")
        self.filter_family_combo.addItem("Chebyshev I", userData="chebyshev1")
        self.filter_family_combo.addItem("Bessel", userData="bessel")
        self.settings_grid.addWidget(self.filter_family_label, 2, 0)
        self.settings_grid.addWidget(
            self.filter_family_combo,
            2,
            1,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

        self.filter_order_label = BodyLabel("滤波阶数", self)
        self.filter_order_spinbox = SpinBox(self)
        self.filter_order_spinbox.setRange(1, 12)
        self.filter_order_spinbox.setValue(4)
        self.filter_order_spinbox.setFixedWidth(180)
        self.settings_grid.addWidget(self.filter_order_label, 3, 0)
        self.settings_grid.addWidget(
            self.filter_order_spinbox,
            3,
            1,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

        self.low_cutoff_label = BodyLabel("截止频率", self)
        self.low_cutoff_spinbox = SpinBox(self)
        self.low_cutoff_spinbox.setRange(1, nyquist_hz)
        self.low_cutoff_spinbox.setValue(1)
        self.low_cutoff_spinbox.setFixedWidth(180)
        self.settings_grid.addWidget(self.low_cutoff_label, 4, 0)
        self.settings_grid.addWidget(
            self.low_cutoff_spinbox,
            4,
            1,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

        self.high_cutoff_label = BodyLabel("高截止频率", self)
        self.high_cutoff_spinbox = SpinBox(self)
        self.high_cutoff_spinbox.setRange(1, nyquist_hz)
        self.high_cutoff_spinbox.setValue(default_high_cutoff_hz)
        self.high_cutoff_spinbox.setFixedWidth(180)
        self.settings_grid.addWidget(self.high_cutoff_label, 5, 0)
        self.settings_grid.addWidget(
            self.high_cutoff_spinbox,
            5,
            1,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

        self.notch_enabled_label = BodyLabel("启用陷波", self)
        self.notch_enabled_switch = SwitchButton(self)
        self.notch_enabled_switch.setOffText("关闭")
        self.notch_enabled_switch.setOnText("启用")
        self.settings_grid.addWidget(self.notch_enabled_label, 6, 0)
        self.settings_grid.addWidget(
            self.notch_enabled_switch,
            6,
            1,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

        self.notch_frequencies_label = BodyLabel("陷波频率", self)
        self.notch_frequencies_edit = TokenLineEdit(
            self,
            placeholder_text="输入频率后按回车或逗号",
            token_normalizer=self._normalize_frequency_token,
        )
        self.notch_frequencies_edit.setMinimumWidth(240)
        self.settings_grid.addWidget(self.notch_frequencies_label, 7, 0)
        self.settings_grid.addWidget(
            self.notch_frequencies_edit,
            7,
            1,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

        self.antialias_label = BodyLabel("折线抗锯齿", self)
        self.antialias_switch = SwitchButton(self)
        self.antialias_switch.setOffText("关闭")
        self.antialias_switch.setOnText("启用")
        self.antialias_switch.setChecked(True)
        self.settings_grid.addWidget(self.antialias_label, 8, 0)
        self.settings_grid.addWidget(
            self.antialias_switch,
            8,
            1,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

        self.y_range_label = BodyLabel("Y 轴范围", self)
        self.y_range_combo = ComboBox(self)
        self.y_range_combo.setFixedWidth(180)
        self.y_range_combo.addItem("自动", userData="auto")
        self.y_range_combo.addItem("手动", userData="manual")
        self.settings_grid.addWidget(self.y_range_label, 9, 0)
        self.settings_grid.addWidget(
            self.y_range_combo,
            9,
            1,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

        self.manual_y_range_label = BodyLabel("手动范围", self)
        self.manual_y_range_widget = QWidget(self)
        manual_y_range_layout = QHBoxLayout(self.manual_y_range_widget)
        manual_y_range_layout.setContentsMargins(0, 0, 0, 0)
        manual_y_range_layout.setSpacing(8)
        self.manual_y_min_spinbox = CompactDoubleSpinBox(self.manual_y_range_widget)
        self.manual_y_min_spinbox.setRange(-1_000_000.0, 1_000_000.0)
        self.manual_y_min_spinbox.setDecimals(3)
        self.manual_y_min_spinbox.setSingleStep(0.1)
        self.manual_y_min_spinbox.setFixedWidth(96)
        self.manual_y_max_spinbox = CompactDoubleSpinBox(self.manual_y_range_widget)
        self.manual_y_max_spinbox.setRange(-1_000_000.0, 1_000_000.0)
        self.manual_y_max_spinbox.setDecimals(3)
        self.manual_y_max_spinbox.setSingleStep(0.1)
        self.manual_y_max_spinbox.setValue(1.0)
        self.manual_y_max_spinbox.setFixedWidth(96)
        self.manual_y_range_separator = CaptionLabel("到", self.manual_y_range_widget)
        manual_y_range_layout.addWidget(self.manual_y_min_spinbox)
        manual_y_range_layout.addWidget(self.manual_y_range_separator)
        manual_y_range_layout.addWidget(self.manual_y_max_spinbox)
        manual_y_range_layout.addStretch(1)
        self.settings_grid.addWidget(self.manual_y_range_label, 10, 0)
        self.settings_grid.addWidget(
            self.manual_y_range_widget,
            10,
            1,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

        self.channel_section_widget = QWidget(self)
        self.channel_section_layout = QVBoxLayout(self.channel_section_widget)
        self.channel_section_layout.setContentsMargins(0, 0, 0, 0)
        self.channel_section_layout.setSpacing(10)

        self.channel_section_title = StrongBodyLabel("Channel 设置", self.channel_section_widget)
        self.channel_section_description = CaptionLabel(
            "控制多通道的布局模式，以及每个 channel 是否参与显示和自动范围计算。",
            self.channel_section_widget,
        )
        self.channel_section_description.setWordWrap(True)

        self.channel_settings_grid = QGridLayout()
        self.channel_settings_grid.setContentsMargins(0, 0, 0, 0)
        self.channel_settings_grid.setHorizontalSpacing(12)
        self.channel_settings_grid.setVerticalSpacing(10)
        self.channel_settings_grid.setColumnStretch(1, 1)

        self.layout_mode_label = BodyLabel("布局模式", self.channel_section_widget)
        self.layout_mode_combo = ComboBox(self.channel_section_widget)
        self.layout_mode_combo.setFixedWidth(180)
        self.layout_mode_combo.addItem("叠加", userData="stacked")
        self.layout_mode_combo.addItem("分图", userData="expanded")
        self.channel_settings_grid.addWidget(self.layout_mode_label, 0, 0)
        self.channel_settings_grid.addWidget(
            self.layout_mode_combo,
            0,
            1,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

        self.channel_visibility_label = BodyLabel("显示通道", self.channel_section_widget)
        self.channel_visibility_widget = QWidget(self.channel_section_widget)
        self.channel_visibility_layout = QVBoxLayout(self.channel_visibility_widget)
        self.channel_visibility_layout.setContentsMargins(0, 0, 0, 0)
        self.channel_visibility_layout.setSpacing(6)
        self.channel_settings_grid.addWidget(self.channel_visibility_label, 1, 0)
        self.channel_settings_grid.addWidget(
            self.channel_visibility_widget,
            1,
            1,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

        self.channel_section_layout.addWidget(self.channel_section_title)
        self.channel_section_layout.addWidget(self.channel_section_description)
        self.channel_section_layout.addLayout(self.channel_settings_grid)
        self._build_channel_checkboxes()
        self.channel_section_widget.setVisible(self._is_multi_channel)

        self.hint_label = CaptionLabel(
            "当前支持时间长度、滤波器、陷波器、多通道布局、通道显隐、Y 轴范围，以及折线抗锯齿选项。",
            self,
        )
        self.hint_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)
        layout.addWidget(self.title_label)
        layout.addWidget(self.tip_label)
        layout.addLayout(self.settings_grid)
        layout.addWidget(self.channel_section_widget)
        layout.addWidget(self.hint_label)

        self.filter_mode_combo.currentIndexChanged.connect(self._sync_filter_mode_ui)
        self.notch_enabled_switch.checkedChanged.connect(self._sync_notch_controls)
        self.duration_combo.currentIndexChanged.connect(self._emit_state_changed)
        self.filter_mode_combo.currentIndexChanged.connect(self._emit_state_changed)
        self.filter_family_combo.currentIndexChanged.connect(self._emit_state_changed)
        self.filter_order_spinbox.valueChanged.connect(self._emit_state_changed)
        self.low_cutoff_spinbox.valueChanged.connect(self._emit_state_changed)
        self.high_cutoff_spinbox.valueChanged.connect(self._emit_state_changed)
        self.notch_enabled_switch.checkedChanged.connect(self._emit_state_changed)
        self.notch_frequencies_edit.sig_tokens_changed.connect(self._emit_state_changed)
        self.antialias_switch.checkedChanged.connect(self._emit_state_changed)
        self.y_range_combo.currentIndexChanged.connect(self._sync_manual_y_range_visibility)
        self.y_range_combo.currentIndexChanged.connect(self._emit_state_changed)
        self.manual_y_min_spinbox.valueChanged.connect(self._emit_state_changed)
        self.manual_y_max_spinbox.valueChanged.connect(self._emit_state_changed)
        self.layout_mode_combo.currentIndexChanged.connect(self._emit_state_changed)

        self._sync_filter_mode_ui()
        self._sync_notch_controls(self.notch_enabled_switch.isChecked())
        self._sync_manual_y_range_visibility()

    def state(self) -> SignalPreviewSettings:
        return SignalPreviewSettings(
            window_seconds=int(self.duration_combo.currentData() or 8),
            antialias_enabled=bool(self.antialias_switch.isChecked()),
            layout_mode=str(self.layout_mode_combo.currentData() or "expanded"),
            visible_channel_indices=self._selected_channel_indices(),
            y_range_mode=str(self.y_range_combo.currentData() or "auto"),
            manual_y_min=float(self.manual_y_min_spinbox.value()),
            manual_y_max=float(self.manual_y_max_spinbox.value()),
            filter=SignalFilterSettings(
                mode=str(self.filter_mode_combo.currentData() or "none"),
                family=str(self.filter_family_combo.currentData() or "butterworth"),
                order=int(self.filter_order_spinbox.value()),
                low_cutoff_hz=float(self.low_cutoff_spinbox.value()),
                high_cutoff_hz=float(self.high_cutoff_spinbox.value()),
                notch_enabled=bool(self.notch_enabled_switch.isChecked()),
                notch_frequencies_hz=tuple(self._parse_notch_tokens()),
                notch_q=30.0,
                chebyshev1_ripple_db=1.0,
            ),
        )

    def set_state(self, settings: SignalPreviewSettings) -> None:
        if not isinstance(settings, SignalPreviewSettings):
            raise TypeError("signal settings panel requires SignalPreviewSettings")
        visible_channel_indices = settings.visible_channel_indices
        if self._is_multi_channel and not visible_channel_indices:
            visible_channel_indices = tuple(range(len(self._channel_checkboxes)))
        elif not self._channel_checkboxes:
            visible_channel_indices = ()
        elif not visible_channel_indices:
            visible_channel_indices = (0,)

        blockers = [
            QSignalBlocker(self.duration_combo),
            QSignalBlocker(self.filter_mode_combo),
            QSignalBlocker(self.filter_family_combo),
            QSignalBlocker(self.filter_order_spinbox),
            QSignalBlocker(self.low_cutoff_spinbox),
            QSignalBlocker(self.high_cutoff_spinbox),
            QSignalBlocker(self.notch_enabled_switch),
            QSignalBlocker(self.notch_frequencies_edit),
            QSignalBlocker(self.antialias_switch),
            QSignalBlocker(self.y_range_combo),
            QSignalBlocker(self.manual_y_min_spinbox),
            QSignalBlocker(self.manual_y_max_spinbox),
            QSignalBlocker(self.layout_mode_combo),
        ]
        blockers.extend(QSignalBlocker(checkbox) for checkbox in self._channel_checkboxes)
        with _SignalBlockerGroup(blockers):
            self._set_combo_to_data(self.duration_combo, settings.window_seconds)
            self._set_combo_to_data(self.filter_mode_combo, settings.filter.mode)
            self._set_combo_to_data(
                self.filter_family_combo,
                settings.filter.family,
            )
            self.filter_order_spinbox.setValue(int(settings.filter.order))
            self.low_cutoff_spinbox.setValue(int(settings.filter.low_cutoff_hz))
            self.high_cutoff_spinbox.setValue(int(settings.filter.high_cutoff_hz))
            self.notch_enabled_switch.setChecked(bool(settings.filter.notch_enabled))
            self.notch_frequencies_edit.set_tokens(
                [f"{value:g}" for value in settings.filter.notch_frequencies_hz]
            )
            self.antialias_switch.setChecked(bool(settings.antialias_enabled))
            self._set_combo_to_data(self.layout_mode_combo, settings.layout_mode)
            self._set_combo_to_data(self.y_range_combo, settings.y_range_mode)
            self.manual_y_min_spinbox.setValue(float(settings.manual_y_min))
            self.manual_y_max_spinbox.setValue(float(settings.manual_y_max))
            self._set_visible_channels(visible_channel_indices)

        self._sync_filter_mode_ui()
        self._sync_notch_controls(self.notch_enabled_switch.isChecked())
        self._sync_manual_y_range_visibility()

    def _build_channel_checkboxes(self) -> None:
        while self.channel_visibility_layout.count():
            item = self.channel_visibility_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self._channel_checkboxes.clear()
        for index, label in enumerate(self._channel_names):
            checkbox = QCheckBox(label or f"ch{index + 1}", self.channel_visibility_widget)
            checkbox.setChecked(True)
            checkbox.toggled.connect(self._on_channel_checkbox_toggled)
            self.channel_visibility_layout.addWidget(checkbox)
            self._channel_checkboxes.append(checkbox)
        self.channel_visibility_layout.addStretch(1)

    def _selected_channel_indices(self) -> tuple[int, ...]:
        if not self._channel_checkboxes:
            return ()
        selected = tuple(
            index for index, checkbox in enumerate(self._channel_checkboxes) if checkbox.isChecked()
        )
        if selected:
            return selected
        return (0,)

    def _set_visible_channels(self, visible_channel_indices: tuple[int, ...]) -> None:
        if not self._channel_checkboxes:
            return
        visible_set = {
            index for index in visible_channel_indices if 0 <= index < len(self._channel_checkboxes)
        }
        if not visible_set:
            visible_set = set(range(len(self._channel_checkboxes)))
        for index, checkbox in enumerate(self._channel_checkboxes):
            checkbox.setChecked(index in visible_set)

    def _on_channel_checkbox_toggled(self, checked: bool) -> None:
        if checked:
            self._emit_state_changed()
            return

        visible_count = sum(1 for checkbox in self._channel_checkboxes if checkbox.isChecked())
        if visible_count <= 0:
            checkbox = self.sender()
            if isinstance(checkbox, QCheckBox):
                with _SignalBlockerGroup([QSignalBlocker(checkbox)]):
                    checkbox.setChecked(True)
            return
        self._emit_state_changed()

    def _sync_filter_mode_ui(self) -> None:
        mode = self.filter_mode_combo.currentData()
        has_main_filter = mode != "none"

        self.filter_family_label.setVisible(has_main_filter)
        self.filter_family_combo.setVisible(has_main_filter)
        self.filter_order_label.setVisible(has_main_filter)
        self.filter_order_spinbox.setVisible(has_main_filter)

        if mode == "none":
            self.low_cutoff_label.hide()
            self.low_cutoff_spinbox.hide()
            self.high_cutoff_label.hide()
            self.high_cutoff_spinbox.hide()
            return

        self.low_cutoff_label.show()
        self.low_cutoff_spinbox.show()

        if mode in {"low_pass", "high_pass"}:
            self.low_cutoff_label.setText("截止频率")
            self.high_cutoff_label.hide()
            self.high_cutoff_spinbox.hide()
            return

        self.low_cutoff_label.setText("低截止频率")
        self.high_cutoff_label.show()
        self.high_cutoff_spinbox.show()

    def _sync_notch_controls(self, enabled: bool) -> None:
        self.notch_frequencies_label.setVisible(enabled)
        self.notch_frequencies_edit.setVisible(enabled)

    def _sync_manual_y_range_visibility(self) -> None:
        is_manual = self.y_range_combo.currentData() == "manual"
        self.manual_y_range_label.setVisible(is_manual)
        self.manual_y_range_widget.setVisible(is_manual)

    def _parse_notch_tokens(self) -> list[float]:
        values: list[float] = []
        for token in self.notch_frequencies_edit.tokens():
            try:
                value = float(token)
            except ValueError:
                continue
            if value > 0:
                values.append(value)
        return values

    def _emit_state_changed(self, *_args: object) -> None:
        self.sig_state_changed.emit(self.state())

    @staticmethod
    def _set_combo_to_data(combo: ComboBox, data: object) -> None:
        for index in range(combo.count()):
            if combo.itemData(index) == data:
                combo.setCurrentIndex(index)
                return

    @staticmethod
    def _normalize_frequency_token(token: str) -> str | None:
        candidate = token.strip().lower().removesuffix("hz").strip()
        if not candidate:
            return None
        try:
            value = float(candidate)
        except ValueError:
            return None
        if value <= 0:
            return None
        if value.is_integer():
            return str(int(value))
        return f"{value:.3f}".rstrip("0").rstrip(".")


class _SignalBlockerGroup:
    def __init__(self, blockers: list[QSignalBlocker]) -> None:
        self._blockers = blockers

    def __enter__(self) -> _SignalBlockerGroup:
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        self._blockers.clear()
        return False
