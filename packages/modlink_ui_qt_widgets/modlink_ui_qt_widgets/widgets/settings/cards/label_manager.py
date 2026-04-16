from __future__ import annotations

from collections.abc import Iterable

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    FlowLayout,
    LineEdit,
    PushButton,
    PushSettingCard,
    StrongBodyLabel,
    TransparentToolButton,
    isDarkTheme,
)
from qfluentwidgets import (
    FluentIcon as FIF,
)

from modlink_core.settings import settings_group, value_setting
from modlink_qt_bridge import QtSettingsBridge

UI_LABELS_KEY = "ui.labels.items"
DEFAULT_LABELS = ("default",)


def normalize_labels(values: object) -> tuple[str, ...]:
    if not isinstance(values, Iterable) or isinstance(values, (str, bytes)):
        return DEFAULT_LABELS

    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        normalized.append(text)
        seen.add(text)

    return tuple(normalized) or DEFAULT_LABELS


def serialize_labels(values: tuple[str, ...]) -> list[str]:
    return list(values)


def declare_label_settings(settings: QtSettingsBridge) -> None:
    settings.add(
        ui=settings_group(
            labels=settings_group(
                items=value_setting(default=DEFAULT_LABELS),
            )
        )
    )


def _dialog_background_stylesheet() -> str:
    if isDarkTheme():
        return "background: rgba(15, 23, 42, 0.96);"
    return "background: rgba(255, 255, 255, 0.98);"


class LabelChip(QFrame):
    def __init__(
        self,
        text: str,
        on_remove,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self._text = text
        self._on_remove = on_remove

        self.setObjectName("label-chip")
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(
            """
            QFrame#label-chip {
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: 14px;
            }
            """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 6, 6)
        layout.setSpacing(4)

        self.text_label = BodyLabel(text, self)
        self.remove_button = TransparentToolButton(FIF.CLOSE, self)
        self.remove_button.setFixedSize(20, 20)
        self.remove_button.setIconSize(QSize(8, 8))
        self.remove_button.clicked.connect(self._remove)

        layout.addWidget(self.text_label)
        layout.addWidget(self.remove_button)

    def _remove(self) -> None:
        self._on_remove(self._text)


class LabelCloud(QWidget):
    def __init__(self, on_remove, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self._on_remove = on_remove
        self.empty_label = CaptionLabel("还没有标签，先添加一个。", self)
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.flow_layout = FlowLayout(self)
        self.flow_layout.setContentsMargins(0, 0, 0, 0)
        self.flow_layout.setHorizontalSpacing(8)
        self.flow_layout.setVerticalSpacing(8)

    def set_labels(self, labels: tuple[str, ...]) -> None:
        self.flow_layout.takeAllWidgets()
        for label in labels:
            self.flow_layout.addWidget(LabelChip(label, self._on_remove, self))

        self.empty_label.setVisible(not labels)
        self.empty_label.setGeometry(self.rect())

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.empty_label.setGeometry(self.rect())


class LabelManagerDialog(QDialog):
    def __init__(
        self,
        settings: QtSettingsBridge,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self._settings = settings
        declare_label_settings(self._settings)
        self._labels = normalize_labels(self._settings.ui.labels.items)

        self.setWindowTitle("标签管理")
        self.resize(600, 420)
        self.setMinimumSize(500, 360)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setStyleSheet(_dialog_background_stylesheet())
        self.finished.connect(self.deleteLater)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 20, 20, 20)
        root_layout.setSpacing(14)

        self.title_label = StrongBodyLabel("标签管理", self)
        self.tip_label = CaptionLabel(
            "设置标签，后续录制和标注时直接从这里取用。",
            self,
        )
        self.tip_label.setWordWrap(True)

        input_row = QHBoxLayout()
        input_row.setContentsMargins(0, 0, 0, 0)
        input_row.setSpacing(8)

        self.input = LineEdit(self)
        self.input.setPlaceholderText("输入一个标签，按 Enter 添加")
        self.input.setClearButtonEnabled(True)
        self.input.returnPressed.connect(self._add_current_label)

        self.add_button = PushButton("添加", self)
        self.add_button.clicked.connect(self._add_current_label)

        input_row.addWidget(self.input, 1)
        input_row.addWidget(self.add_button)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.label_cloud = LabelCloud(self._remove_label, self)
        self.label_cloud.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.MinimumExpanding,
        )
        self.scroll_area.setWidget(self.label_cloud)

        footer_row = QHBoxLayout()
        footer_row.setContentsMargins(0, 0, 0, 0)
        footer_row.addStretch(1)

        self.close_button = PushButton("关闭", self)
        self.close_button.clicked.connect(self.accept)
        footer_row.addWidget(self.close_button)

        root_layout.addWidget(self.title_label)
        root_layout.addWidget(self.tip_label)
        root_layout.addLayout(input_row)
        root_layout.addWidget(self.scroll_area, 1)
        root_layout.addLayout(footer_row)

        self._settings.sig_setting_changed.connect(self._on_setting_changed)
        self.label_cloud.set_labels(self._labels)

    def _add_current_label(self) -> None:
        text = self.input.text().strip()
        if not text:
            return
        self._labels = normalize_labels([*self._labels, text])
        self._settings.ui.labels.items = serialize_labels(self._labels)
        self._settings.save()
        self.input.clear()

    def _remove_label(self, text: str) -> None:
        filtered = [label for label in self._labels if label != text]
        self._labels = normalize_labels(filtered)
        self._settings.ui.labels.items = serialize_labels(self._labels)
        self._settings.save()

    def _on_setting_changed(self, event: object) -> None:
        if getattr(event, "key", None) != UI_LABELS_KEY:
            return
        self._labels = normalize_labels(self._settings.ui.labels.items)
        self.label_cloud.set_labels(self._labels)


class LabelManagerCard(PushSettingCard):
    def __init__(
        self,
        settings: QtSettingsBridge,
        parent: QWidget | None = None,
    ) -> None:
        self._settings = settings
        declare_label_settings(self._settings)
        labels = self._load_labels()

        super().__init__(
            "打开",
            FIF.TAG,
            "标签管理器",
            self._summary_text(labels),
            parent,
        )
        self._labels = labels
        self._dialog: LabelManagerDialog | None = None

        self.clicked.connect(self._open_dialog)
        self._settings.sig_setting_changed.connect(self._on_setting_changed)
        self._refresh_summary()

    def _open_dialog(self) -> None:
        if self._dialog is None:
            dialog = LabelManagerDialog(self._settings, self.window())
            dialog.destroyed.connect(self._on_dialog_destroyed)
            self._dialog = dialog

        self._dialog.show()
        self._dialog.raise_()
        self._dialog.activateWindow()

    def _on_dialog_destroyed(self, _object: object | None = None) -> None:
        self._dialog = None

    def _on_setting_changed(self, event: object) -> None:
        if getattr(event, "key", None) != UI_LABELS_KEY:
            return
        self._labels = self._load_labels()
        self._refresh_summary()

    def _load_labels(self) -> tuple[str, ...]:
        return normalize_labels(self._settings.ui.labels.items)

    def _refresh_summary(self) -> None:
        self.setContent(self._summary_text(self._labels))

    @staticmethod
    def _summary_text(labels: tuple[str, ...]) -> str:
        count = len(labels)
        preview = ", ".join(labels[:3])
        if count > 3:
            preview += " ..."
        return f"当前 {count} 个标签：{preview}"
