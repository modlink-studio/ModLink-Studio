from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    SimpleCardWidget,
    SingleDirectionScrollArea,
    SmoothMode,
    StrongBodyLabel,
    SubtitleLabel,
)

from ..settings import DEFAULT_RADIUS


class GuidePage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.setObjectName("guide-page")

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(36, 28, 36, 28)
        root_layout.setSpacing(20)

        header_label = SubtitleLabel("说明", self)
        intro_label = BodyLabel(
            "这里说明采集模式、常用设置和数据保存结构。",
            self,
        )
        intro_label.setWordWrap(True)

        self.scroll_area = SingleDirectionScrollArea(self, orient=Qt.Orientation.Vertical)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setSmoothMode(SmoothMode.NO_SMOOTH)
        self.scroll_area.enableTransparentBackground()

        self.scroll_widget = QWidget(self.scroll_area)
        self.scroll_widget.setObjectName("guide-scroll-widget")
        self.scroll_widget.setStyleSheet("QWidget#guide-scroll-widget { background: transparent; }")

        scroll_layout = QVBoxLayout(self.scroll_widget)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(0)

        guide_card = SimpleCardWidget(self.scroll_widget)
        guide_card.setBorderRadius(DEFAULT_RADIUS)

        card_layout = QVBoxLayout(guide_card)
        card_layout.setContentsMargins(24, 22, 24, 22)
        card_layout.setSpacing(10)

        self._add_paragraphs(
            card_layout,
            [
                "这是一个面向 OpenBCI Ganglion 的采集 UI，用于完成设备连接、实时预览、标签标注和数据录制。",
            ],
        )
        self._add_paragraphs(
            card_layout,
            [
                "目前支持两种蓝牙连接方式：",
            ],
        )
        self._add_paragraphs(
            card_layout,
            [
                "Native BLE（本机原生蓝牙）",
                "Ganglion Dongle（OpenBCI 官方蓝牙适配器）",
            ],
            indent=True,
        )
        self._add_paragraphs(
            card_layout,
            [
                "当前仅支持采集通道数据的显示与保存，暂不包含加速度传感器数据。",
            ],
        )
        self._add_paragraphs(
            card_layout,
            [
                "Native BLE 模式下，连接会优先使用设备名（如 Ganglion-9c3b）作为连接参数；MAC 地址主要用于识别设备。",
            ],
        )

        self._add_h1(card_layout, "采集模式")
        self._add_paragraphs(
            card_layout,
            [
                "提供两种录制模式：片段录制和连续录制。",
                "可在设置页面 -> 录制设置 -> 录制模式中切换。",
            ],
        )

        self._add_h2(card_layout, "片段录制")
        self._add_paragraphs(
            card_layout,
            [
                "适用于单次、边界明确的动作采集。",
                "一次开始到结束的录制会保存为一个独立样本。",
                "建议在录制前先选择当前标签。录制的数据会按标签分类保存，便于后续整理和分析。",
                "片段录制过程中还可以插入 marker，用于补充时间点标记。",
                "在采集页中，录制期间按空格可快速插入 marker；若 Marker 输入框为空，则默认使用当前标签。",
            ],
        )

        self._add_h2(card_layout, "连续录制")
        self._add_paragraphs(
            card_layout,
            [
                "适用于长时间、连续进行的采集任务。",
                "一次录制会保存为一个完整 session，期间可在同一段数据中标记多个标签区间。",
                "这种模式更适合需要保留完整时间轴和上下文信息的场景。",
                "在采集页中，录制期间按空格会开始或结束当前标签区间，而不是插入 marker。",
            ],
        )

        self._add_h2(card_layout, "快捷操作")
        self._add_paragraphs(
            card_layout,
            [
                "空格快捷键仅在采集页内生效。",
                "当光标焦点位于文本输入框时，空格会作为普通输入，不会触发快捷操作。",
            ],
        )

        self._add_h1(card_layout, "其他设置")
        self._add_h2(card_layout, "显示设置")
        self._add_paragraphs(
            card_layout,
            [
                "设置页中，实时显示和滤波设置已经分组展示。",
                "实时显示用于调整显示点数、通道显示和纵轴范围；滤波设置用于配置各通道滤波和工频滤波。",
                "这些设置只影响显示效果，不改变原始采集数据。",
            ],
        )

        self._add_h2(card_layout, "标签管理")
        self._add_paragraphs(
            card_layout,
            [
                "标签管理用于维护实验中使用的 label 列表。",
                "建议提前配置常用标签，便于快速选择并保持命名统一。",
            ],
        )

        self._add_h2(card_layout, "数据保存")
        self._add_paragraphs(
            card_layout,
            [
                "文件保存目录表示数据保存的根目录。",
            ],
        )

        self._add_h3(card_layout, "片段录制")
        self._add_code_block(card_layout, "根目录 / subject_id / task_name / session_id")

        self._add_h3(card_layout, "连续录制")
        self._add_code_block(card_layout, "根目录 / subject_id / session_id")
        self._add_h3(card_layout, "说明")
        self._add_paragraphs(
            card_layout,
            [
                "subject_id 表示受试编号。",
                "task_name 在片段录制模式下就是当前标签（也就是 label），用于分类保存。",
                "session_id 用于区分具体的录制结果（默认是时间戳）。",
                "每个 session 目录下会包含 stream.csv，以及 markers.csv（片段录制）或 segments.csv（连续录制），并附带 session_meta.txt。",
            ],
            indent=True,
        )

        scroll_layout.addWidget(guide_card)
        scroll_layout.addStretch(1)
        self.scroll_area.setWidget(self.scroll_widget)

        root_layout.addWidget(header_label)
        root_layout.addWidget(intro_label)
        root_layout.addWidget(self.scroll_area, 1)

    def _add_h1(
        self,
        layout: QVBoxLayout,
        title: str,
    ) -> None:
        parent = layout.parentWidget() or self
        title_label = StrongBodyLabel(title, parent)
        title_label.setStyleSheet("font-size: 20px; font-weight: 600;")
        layout.addWidget(title_label)

    def _add_h2(
        self,
        layout: QVBoxLayout,
        title: str,
    ) -> None:
        parent = layout.parentWidget() or self
        title_label = BodyLabel(title, parent)
        title_label.setStyleSheet("font-weight: 600;")
        layout.addWidget(title_label)

    def _add_h3(
        self,
        layout: QVBoxLayout,
        title: str,
    ) -> None:
        parent = layout.parentWidget() or self
        title_label = CaptionLabel(title, parent)
        title_label.setStyleSheet("font-weight: 600;")
        layout.addWidget(title_label)

    def _add_paragraphs(
        self,
        layout: QVBoxLayout,
        items: list[str],
        indent: bool = False,
    ) -> None:
        parent = layout.parentWidget() or self
        for item in items:
            text = f"• {item}" if indent else item
            item_label = BodyLabel(text, parent)
            item_label.setWordWrap(True)
            layout.addWidget(item_label)

    def _add_code_block(
        self,
        layout: QVBoxLayout,
        text: str,
    ) -> None:
        parent = layout.parentWidget() or self
        code_label = CaptionLabel(text, parent)
        code_label.setStyleSheet(
            """
            padding: 8px 10px;
            background: rgba(0, 0, 0, 0.04);
            border: 1px solid rgba(0, 0, 0, 0.06);
            border-radius: 6px;
            font-family: Consolas;
            """
        )
        layout.addWidget(code_label)
