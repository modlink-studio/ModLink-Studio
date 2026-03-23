from __future__ import annotations

from pathlib import Path
import time

from PyQt6.QtCore import QSize, QStringListModel, QTimer, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QAbstractButton,
    QCompleter,
    QHBoxLayout,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    CaptionLabel,
    FluentIcon as FIF,
    InfoBar,
    InfoBarPosition,
    LineEdit,
    PrimaryPushButton,
    PrimaryToolButton,
    SimpleCardWidget,
    StrongBodyLabel,
    TransparentToolButton,
    isDarkTheme,
)

from modlink_core.runtime.engine import ModLinkEngine

from .view_model import AcquisitionViewModel


class ChevronStripButton(QAbstractButton):
    """Full-width transparent handle used to toggle panel modes."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(10)
        self.setToolTip("")
        self.setStatusTip("")
        self.setWhatsThis("")

    def sizeHint(self) -> QSize:
        return QSize(240, 10)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        stroke_color = QColor(176, 176, 176) if isDarkTheme() else QColor(150, 150, 150)
        painter.setPen(
            QPen(
                stroke_color,
                1.35,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin,
            )
        )
        painter.setBrush(Qt.BrushStyle.NoBrush)

        center_x = self.width() / 2
        center_y = self.height() / 2
        half_width = 4.0
        half_height = 2.2

        if self.isChecked():
            painter.drawLine(
                int(round(center_x - half_width)),
                int(round(center_y - half_height)),
                int(round(center_x)),
                int(round(center_y + half_height)),
            )
            painter.drawLine(
                int(round(center_x)),
                int(round(center_y + half_height)),
                int(round(center_x + half_width)),
                int(round(center_y - half_height)),
            )
            return

        painter.drawLine(
            int(round(center_x - half_width)),
            int(round(center_y + half_height)),
            int(round(center_x)),
            int(round(center_y - half_height)),
        )
        painter.drawLine(
            int(round(center_x)),
            int(round(center_y - half_height)),
            int(round(center_x + half_width)),
            int(round(center_y + half_height)),
        )


class AcquisitionControlPanel(SimpleCardWidget):
    """Floating acquisition panel with compact and detailed modes."""

    def __init__(self, engine: ModLinkEngine, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.view_model = AcquisitionViewModel(engine, parent=self)
        self._is_detailed = True

        self.setObjectName("acquisition-control-panel")
        self.setBorderRadius(16)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum,
        )

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.toggle_strip = QWidget(self)
        self.toggle_strip.setFixedHeight(10)
        toggle_layout = QVBoxLayout(self.toggle_strip)
        toggle_layout.setContentsMargins(0, 0, 0, 0)
        toggle_layout.setSpacing(0)

        self.mode_toggle_button = ChevronStripButton(self.toggle_strip)
        toggle_layout.addWidget(self.mode_toggle_button)
        root_layout.addWidget(self.toggle_strip)

        self.content_widget = QWidget(self)
        self.content_layout = QVBoxLayout(self.content_widget)
        root_layout.addWidget(self.content_widget)

        self.title_label = StrongBodyLabel("采集")

        self.status_summary = CaptionLabel()
        self.status_summary.setWordWrap(False)
        self.status_summary.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Fixed,
        )
        self.status_summary.setMinimumWidth(0)

        self.session_name_input = LineEdit(self.content_widget)
        self.recording_label_input = LineEdit(self.content_widget)
        self.annotation_label_input = LineEdit(self.content_widget)

        for widget, placeholder in (
            (self.session_name_input, "Session"),
            (self.recording_label_input, "Label"),
            (self.annotation_label_input, "Marker / 区间标签"),
        ):
            widget.setPlaceholderText(placeholder)
            widget.setClearButtonEnabled(True)
            widget.setFixedHeight(34)

        self._label_model = QStringListModel(self.view_model.labels, self)
        self._label_completer = QCompleter(self._label_model, self)
        self._label_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.recording_label_input.setCompleter(self._label_completer)
        self.annotation_label_input.setCompleter(self._label_completer)

        self.start_button = PrimaryPushButton("开始采集")
        self.start_button.setIcon(FIF.PLAY_SOLID)
        self.start_button.setMinimumWidth(136)
        self.start_button.setFixedHeight(34)
        self.start_button.clicked.connect(self._toggle_recording)

        self.marker_button = TransparentToolButton(FIF.TAG)
        self.marker_button.setFixedSize(34, 34)
        self.marker_button.setToolTip("插入 Marker")
        self.marker_button.clicked.connect(self._insert_marker)

        self.segment_toggle_button = TransparentToolButton(FIF.STOP_WATCH)
        self.segment_toggle_button.setFixedSize(34, 34)
        self.segment_toggle_button.clicked.connect(self._toggle_segment)

        self.segment_reset_button = TransparentToolButton(FIF.BROOM)
        self.segment_reset_button.setFixedSize(34, 34)
        self.segment_reset_button.setToolTip("清空区间起点")
        self.segment_reset_button.clicked.connect(self._reset_segment)

        self.compact_start_button = PrimaryToolButton(FIF.PLAY_SOLID)
        self.compact_start_button.setFixedSize(36, 36)
        self.compact_start_button.clicked.connect(self._toggle_recording)

        for widget in (
            self.title_label,
            self.status_summary,
            self.session_name_input,
            self.recording_label_input,
            self.annotation_label_input,
            self.start_button,
            self.marker_button,
            self.segment_toggle_button,
            self.segment_reset_button,
            self.compact_start_button,
        ):
            widget.hide()

        self.mode_toggle_button.setChecked(self._is_detailed)
        self.mode_toggle_button.toggled.connect(self._set_detailed_mode)

        self.view_model.sig_recording_changed.connect(self._sync_recording_state)
        self.view_model.sig_segment_active_changed.connect(self._sync_segment_state)
        self.view_model.sig_feedback_changed.connect(self._on_feedback_changed)
        self.view_model.sig_error.connect(self._show_error_bar)
        self.view_model.sig_labels_changed.connect(self._label_model.setStringList)
        self.view_model.sig_session_name_generated.connect(
            self.session_name_input.setText
        )

        self._sync_recording_state(self.view_model.is_recording)
        self._sync_segment_state(self.view_model.is_segment_active)
        self._rebuild_content_layout()
        self.view_model.request_reset_segment()  # trigger initial feedback text

    def _normalBackgroundColor(self) -> QColor:
        return QColor(43, 43, 43) if isDarkTheme() else QColor(255, 255, 255)

    def _hoverBackgroundColor(self) -> QColor:
        return self._normalBackgroundColor()

    def _pressedBackgroundColor(self) -> QColor:
        return self._normalBackgroundColor()

    def _toggle_recording(self) -> None:
        self.view_model.request_toggle_recording(
            self.session_name_input.text(),
            self.recording_label_input.text(),
        )

    def _insert_marker(self) -> None:
        self.view_model.request_insert_marker(
            self.session_name_input.text(),
            self.annotation_label_input.text(),
        )

    def _toggle_segment(self) -> None:
        self.view_model.request_toggle_segment(self.annotation_label_input.text())

    def _reset_segment(self) -> None:
        self.view_model.request_reset_segment()

    def _sync_recording_state(self, is_recording: bool) -> None:
        start_text = "停止采集" if is_recording else "开始采集"
        start_icon = FIF.PAUSE_BOLD if is_recording else FIF.PLAY_SOLID

        self.start_button.setText(start_text)
        self.start_button.setIcon(start_icon)
        self.compact_start_button.setIcon(start_icon)
        self.compact_start_button.setToolTip(start_text)

        self.marker_button.setEnabled(is_recording)
        self.segment_toggle_button.setEnabled(is_recording)

        self.session_name_input.setEnabled(not is_recording)
        self.recording_label_input.setEnabled(not is_recording)

    def _sync_segment_state(self, is_segment_active: bool) -> None:
        segment_text = "结束区间" if is_segment_active else "开始区间"
        self.segment_toggle_button.setToolTip(segment_text)
        self.segment_reset_button.setEnabled(is_segment_active)

    def _on_feedback_changed(self, text: str) -> None:
        self._current_feedback_text = text
        self._update_feedback_display()

    def _update_feedback_display(self) -> None:
        if not hasattr(self, "_current_feedback_text"):
            return
        compact_limit = 56 if self._is_detailed else 28
        self.status_summary.setText(
            self._shorten(self._current_feedback_text, compact_limit)
        )
        self.status_summary.setToolTip(self._current_feedback_text)

    def _rebuild_content_layout(self) -> None:
        self._clear_layout(self.content_layout)

        if self._is_detailed:
            self.content_layout.setContentsMargins(18, 4, 18, 14)
            self.content_layout.setSpacing(10)
            self.status_summary.setMaximumWidth(280)

            self.compact_start_button.hide()

            header = QHBoxLayout()
            header.setContentsMargins(0, 0, 0, 0)
            header.setSpacing(8)

            self._mount_widget(header, self.title_label)

            self._mount_widget(header, self.status_summary)

            header.addStretch(1)

            self._mount_widget(header, self.marker_button)

            self._mount_widget(header, self.segment_toggle_button)

            self._mount_widget(header, self.segment_reset_button)

            self._mount_widget(header, self.start_button)

            self.content_layout.addLayout(header)

            controls = QHBoxLayout()
            controls.setContentsMargins(0, 0, 0, 0)
            controls.setSpacing(10)

            self._mount_widget(controls, self.session_name_input, 3)

            self._mount_widget(controls, self.recording_label_input, 2)

            self._mount_widget(controls, self.annotation_label_input, 2)

            self.content_layout.addLayout(controls)
        else:
            self.content_layout.setContentsMargins(14, 2, 14, 12)
            self.content_layout.setSpacing(0)

            self.title_label.hide()
            self.status_summary.hide()
            self.start_button.hide()

            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(6)

            self._mount_widget(row, self.session_name_input, 3)

            self._mount_widget(row, self.recording_label_input, 2)

            self._mount_widget(row, self.annotation_label_input, 2)

            self._mount_widget(row, self.marker_button)

            self._mount_widget(row, self.segment_toggle_button)

            self._mount_widget(row, self.segment_reset_button)

            self._mount_widget(row, self.compact_start_button)

            self.content_layout.addLayout(row)

        self.content_widget.adjustSize()
        self.adjustSize()

    def _clear_layout(self, layout: QVBoxLayout | QHBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            child_layout = item.layout()
            child_widget = item.widget()

            if child_layout is not None:
                self._clear_layout(child_layout)
            elif child_widget is not None:
                child_widget.hide()

    def _mount_widget(
        self,
        layout: QHBoxLayout | QVBoxLayout,
        widget: QWidget,
        *args: int,
    ) -> None:
        if widget.parentWidget() is not self.content_widget:
            widget.setParent(self.content_widget)
        layout.addWidget(widget, *args)
        widget.show()

    def _set_detailed_mode(self, is_detailed: bool) -> None:
        is_detailed = bool(is_detailed)
        if self._is_detailed == is_detailed:
            return

        self._is_detailed = is_detailed
        self._update_feedback_display()
        self._rebuild_content_layout()
        self.updateGeometry()

    def _show_error_bar(self, message: str) -> None:
        parent = self.window() if isinstance(self.window(), QWidget) else self
        InfoBar.error(
            title="采集错误",
            content=message,
            duration=4500,
            position=InfoBarPosition.TOP_RIGHT,
            parent=parent,
        )

    def _shorten(self, text: str, limit: int) -> str:
        cleaned = str(text or "").strip()
        if len(cleaned) <= limit:
            return cleaned
        head = max(12, limit - 18)
        return f"{cleaned[:head]} ..."
