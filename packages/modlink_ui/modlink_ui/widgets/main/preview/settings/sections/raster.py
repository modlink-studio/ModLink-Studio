from __future__ import annotations

from PyQt6.QtCore import QSignalBlocker, Qt, pyqtSignal
from PyQt6.QtWidgets import QGridLayout, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    ComboBox,
    CompactSpinBox,
    SimpleCardWidget,
    StrongBodyLabel,
)

from modlink_sdk import StreamDescriptor

from ..models import RasterPreviewSettings

RASTER_WINDOW_SECONDS_OPTIONS = (1, 2, 4, 8, 12, 20)


class RasterPayloadSettingsPanel(SimpleCardWidget):
    sig_state_changed = pyqtSignal(object)

    def __init__(
        self,
        descriptor: StreamDescriptor,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.descriptor = descriptor
        self.setBorderRadius(12)

        self.title_label = StrongBodyLabel("栅格图设置", self)
        self.tip_label = CaptionLabel(
            "这里先只搭 raster 预览的 UI，暂时不接实际渲染逻辑。",
            self,
        )
        self.tip_label.setWordWrap(True)

        self.settings_grid = QGridLayout()
        self.settings_grid.setContentsMargins(0, 0, 0, 0)
        self.settings_grid.setHorizontalSpacing(12)
        self.settings_grid.setVerticalSpacing(10)
        self.settings_grid.setColumnStretch(1, 1)
        self.settings_grid.setColumnMinimumWidth(1, 240)

        self.duration_label = BodyLabel("时间长度", self)
        self.duration_combo = ComboBox(self)
        self.duration_combo.setFixedWidth(180)
        for seconds in RASTER_WINDOW_SECONDS_OPTIONS:
            self.duration_combo.addItem(f"{seconds} 秒", userData=seconds)
        self.settings_grid.addWidget(self.duration_label, 0, 0)
        self.settings_grid.addWidget(
            self.duration_combo,
            0,
            1,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

        self.colormap_label = BodyLabel("染色方式", self)
        self.colormap_combo = ComboBox(self)
        self.colormap_combo.setFixedWidth(180)
        self.colormap_combo.addItem("灰度", userData="gray")
        self.colormap_combo.addItem("Viridis", userData="viridis")
        self.colormap_combo.addItem("Plasma", userData="plasma")
        self.colormap_combo.addItem("Inferno", userData="inferno")
        self.colormap_combo.addItem("Magma", userData="magma")
        self.colormap_combo.addItem("Turbo", userData="turbo")
        self.settings_grid.addWidget(self.colormap_label, 1, 0)
        self.settings_grid.addWidget(
            self.colormap_combo,
            1,
            1,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

        self.value_range_label = BodyLabel("数值范围", self)
        self.value_range_combo = ComboBox(self)
        self.value_range_combo.setFixedWidth(180)
        self.value_range_combo.addItem("自动", userData="auto")
        self.value_range_combo.addItem("0 到 1", userData="zero_to_one")
        self.value_range_combo.addItem("0 到 255", userData="zero_to_255")
        self.value_range_combo.addItem("手动", userData="manual")
        self.settings_grid.addWidget(self.value_range_label, 2, 0)
        self.settings_grid.addWidget(
            self.value_range_combo,
            2,
            1,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

        self.manual_range_label = BodyLabel("手动范围", self)
        self.manual_range_widget = QWidget(self)
        manual_range_layout = QHBoxLayout(self.manual_range_widget)
        manual_range_layout.setContentsMargins(0, 0, 0, 0)
        manual_range_layout.setSpacing(8)
        self.manual_min_spinbox = CompactSpinBox(self.manual_range_widget)
        self.manual_min_spinbox.setRange(-1_000_000, 1_000_000)
        self.manual_min_spinbox.setFixedWidth(96)
        self.manual_max_spinbox = CompactSpinBox(self.manual_range_widget)
        self.manual_max_spinbox.setRange(-1_000_000, 1_000_000)
        self.manual_max_spinbox.setValue(1)
        self.manual_max_spinbox.setFixedWidth(96)
        self.manual_range_separator = CaptionLabel("到", self.manual_range_widget)
        manual_range_layout.addWidget(self.manual_min_spinbox)
        manual_range_layout.addWidget(self.manual_range_separator)
        manual_range_layout.addWidget(self.manual_max_spinbox)
        manual_range_layout.addStretch(1)
        self.settings_grid.addWidget(self.manual_range_label, 3, 0)
        self.settings_grid.addWidget(
            self.manual_range_widget,
            3,
            1,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

        self.interpolation_label = BodyLabel("插值方式", self)
        self.interpolation_combo = ComboBox(self)
        self.interpolation_combo.setFixedWidth(180)
        self.interpolation_combo.addItem("最近邻", userData="nearest")
        self.interpolation_combo.addItem("双线性", userData="bilinear")
        self.interpolation_combo.addItem("双三次", userData="bicubic")
        self.settings_grid.addWidget(self.interpolation_label, 4, 0)
        self.settings_grid.addWidget(
            self.interpolation_combo,
            4,
            1,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

        self.transform_label = BodyLabel("几何方向", self)
        self.transform_combo = ComboBox(self)
        self.transform_combo.setFixedWidth(180)
        self.transform_combo.addItem("无", userData="none")
        self.transform_combo.addItem("水平翻转", userData="flip_horizontal")
        self.transform_combo.addItem("垂直翻转", userData="flip_vertical")
        self.transform_combo.addItem("旋转 90°", userData="rotate_90")
        self.transform_combo.addItem("旋转 180°", userData="rotate_180")
        self.transform_combo.addItem("旋转 270°", userData="rotate_270")
        self.settings_grid.addWidget(self.transform_label, 5, 0)
        self.settings_grid.addWidget(
            self.transform_combo,
            5,
            1,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

        self.hint_label = CaptionLabel(
            "当前先只搭 UI：时间长度、染色方式、数值范围、插值方式和几何方向。",
            self,
        )
        self.hint_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)
        layout.addWidget(self.title_label)
        layout.addWidget(self.tip_label)
        layout.addLayout(self.settings_grid)
        layout.addWidget(self.hint_label)

        self.value_range_combo.currentIndexChanged.connect(self._sync_manual_range_visibility)
        self.duration_combo.currentIndexChanged.connect(self._emit_state_changed)
        self.colormap_combo.currentIndexChanged.connect(self._emit_state_changed)
        self.value_range_combo.currentIndexChanged.connect(self._emit_state_changed)
        self.manual_min_spinbox.valueChanged.connect(self._emit_state_changed)
        self.manual_max_spinbox.valueChanged.connect(self._emit_state_changed)
        self.interpolation_combo.currentIndexChanged.connect(self._emit_state_changed)
        self.transform_combo.currentIndexChanged.connect(self._emit_state_changed)
        self._sync_manual_range_visibility()

    def state(self) -> RasterPreviewSettings:
        return RasterPreviewSettings(
            window_seconds=int(self.duration_combo.currentData() or 8),
            colormap=str(self.colormap_combo.currentData() or "gray"),
            value_range_mode=str(self.value_range_combo.currentData() or "auto"),
            manual_min=float(self.manual_min_spinbox.value()),
            manual_max=float(self.manual_max_spinbox.value()),
            interpolation=str(self.interpolation_combo.currentData() or "nearest"),
            transform=str(self.transform_combo.currentData() or "none"),
        )

    def set_state(self, state: object) -> None:
        settings = state if isinstance(state, RasterPreviewSettings) else RasterPreviewSettings()
        with (
            QSignalBlocker(self.duration_combo),
            QSignalBlocker(self.colormap_combo),
            QSignalBlocker(self.value_range_combo),
            QSignalBlocker(self.manual_min_spinbox),
            QSignalBlocker(self.manual_max_spinbox),
            QSignalBlocker(self.interpolation_combo),
            QSignalBlocker(self.transform_combo),
        ):
            self._set_combo_to_data(
                self.duration_combo,
                settings.window_seconds,
            )
            self._set_combo_to_data(self.colormap_combo, settings.colormap)
            self._set_combo_to_data(
                self.value_range_combo,
                settings.value_range_mode,
            )
            self.manual_min_spinbox.setValue(int(settings.manual_min))
            self.manual_max_spinbox.setValue(int(settings.manual_max))
            self._set_combo_to_data(
                self.interpolation_combo,
                settings.interpolation,
            )
            self._set_combo_to_data(self.transform_combo, settings.transform)
        self._sync_manual_range_visibility()

    def _sync_manual_range_visibility(self) -> None:
        is_manual = self.value_range_combo.currentData() == "manual"
        self.manual_range_label.setVisible(is_manual)
        self.manual_range_widget.setVisible(is_manual)

    def _emit_state_changed(self, *_args: object) -> None:
        self.sig_state_changed.emit(self.state())

    @staticmethod
    def _set_combo_to_data(combo: ComboBox, data: object) -> None:
        for index in range(combo.count()):
            if combo.itemData(index) == data:
                combo.setCurrentIndex(index)
                return
