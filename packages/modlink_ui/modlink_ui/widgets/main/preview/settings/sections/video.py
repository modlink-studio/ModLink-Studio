from __future__ import annotations

from PyQt6.QtCore import QSignalBlocker, pyqtSignal
from PyQt6.QtWidgets import QGridLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    ComboBox,
    SimpleCardWidget,
    StrongBodyLabel,
)

from modlink_sdk import StreamDescriptor


class VideoPayloadSettingsPanel(SimpleCardWidget):
    sig_state_changed = pyqtSignal(object)

    def __init__(
        self,
        descriptor: StreamDescriptor,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.descriptor = descriptor
        self.setBorderRadius(12)

        self.title_label = StrongBodyLabel("视频设置", self)
        self.tip_label = CaptionLabel(
            "这里先只搭视频预览的 UI，暂时不接实际渲染逻辑。",
            self,
        )
        self.tip_label.setWordWrap(True)

        self.settings_grid = QGridLayout()
        self.settings_grid.setContentsMargins(0, 0, 0, 0)
        self.settings_grid.setHorizontalSpacing(12)
        self.settings_grid.setVerticalSpacing(10)
        self.settings_grid.setColumnStretch(1, 1)

        self.color_format_label = BodyLabel("颜色格式", self)
        self.color_format_combo = ComboBox(self)
        self.color_format_combo.setFixedWidth(180)
        self.color_format_combo.addItem("RGB", userData="rgb")
        self.color_format_combo.addItem("BGR", userData="bgr")
        self.color_format_combo.addItem("Gray", userData="gray")
        self.color_format_combo.addItem("YUV", userData="yuv")
        self.settings_grid.addWidget(self.color_format_label, 0, 0)
        self.settings_grid.addWidget(self.color_format_combo, 0, 1)

        self.scale_mode_label = BodyLabel("缩放模式", self)
        self.scale_mode_combo = ComboBox(self)
        self.scale_mode_combo.setFixedWidth(180)
        self.scale_mode_combo.addItem("适应窗口", userData="fit")
        self.scale_mode_combo.addItem("填满窗口", userData="fill")
        self.scale_mode_combo.addItem("1:1 原始大小", userData="original")
        self.settings_grid.addWidget(self.scale_mode_label, 1, 0)
        self.settings_grid.addWidget(self.scale_mode_combo, 1, 1)

        self.aspect_ratio_label = BodyLabel("宽高比", self)
        self.aspect_ratio_combo = ComboBox(self)
        self.aspect_ratio_combo.setFixedWidth(180)
        self.aspect_ratio_combo.addItem("保持比例", userData="keep")
        self.aspect_ratio_combo.addItem("允许拉伸", userData="stretch")
        self.settings_grid.addWidget(self.aspect_ratio_label, 2, 0)
        self.settings_grid.addWidget(self.aspect_ratio_combo, 2, 1)

        self.transform_label = BodyLabel("几何变换", self)
        self.transform_combo = ComboBox(self)
        self.transform_combo.setFixedWidth(180)
        self.transform_combo.addItem("无", userData="none")
        self.transform_combo.addItem("水平翻转", userData="flip_horizontal")
        self.transform_combo.addItem("垂直翻转", userData="flip_vertical")
        self.transform_combo.addItem("旋转 90°", userData="rotate_90")
        self.transform_combo.addItem("旋转 180°", userData="rotate_180")
        self.transform_combo.addItem("旋转 270°", userData="rotate_270")
        self.settings_grid.addWidget(self.transform_label, 3, 0)
        self.settings_grid.addWidget(self.transform_combo, 3, 1)

        self.format_hint_label = CaptionLabel(
            "当前先只搭 UI：颜色格式、缩放模式、宽高比和几何变换，后续再接实际渲染逻辑。",
            self,
        )
        self.format_hint_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)
        layout.addWidget(self.title_label)
        layout.addWidget(self.tip_label)
        layout.addLayout(self.settings_grid)
        layout.addWidget(self.format_hint_label)

        self.color_format_combo.currentIndexChanged.connect(self._emit_state_changed)
        self.scale_mode_combo.currentIndexChanged.connect(self._emit_state_changed)
        self.aspect_ratio_combo.currentIndexChanged.connect(self._emit_state_changed)
        self.transform_combo.currentIndexChanged.connect(self._emit_state_changed)

    def state(self) -> dict[str, object]:
        return {
            "color_format": self.color_format_combo.currentData(),
            "scale_mode": self.scale_mode_combo.currentData(),
            "aspect_mode": self.aspect_ratio_combo.currentData(),
            "transform": self.transform_combo.currentData(),
        }

    def set_state(self, state: object) -> None:
        data = state if isinstance(state, dict) else {}
        with (
            QSignalBlocker(self.color_format_combo),
            QSignalBlocker(self.scale_mode_combo),
            QSignalBlocker(self.aspect_ratio_combo),
            QSignalBlocker(self.transform_combo),
        ):
            self._set_combo_to_data(
                self.color_format_combo,
                data.get("color_format", "rgb"),
            )
            self._set_combo_to_data(self.scale_mode_combo, data.get("scale_mode", "fit"))
            self._set_combo_to_data(
                self.aspect_ratio_combo,
                data.get("aspect_mode", "keep"),
            )
            self._set_combo_to_data(self.transform_combo, data.get("transform", "none"))

    def _emit_state_changed(self, *_args: object) -> None:
        self.sig_state_changed.emit(self.state())

    @staticmethod
    def _set_combo_to_data(combo: ComboBox, data: object) -> None:
        for index in range(combo.count()):
            if combo.itemData(index) == data:
                combo.setCurrentIndex(index)
                return
