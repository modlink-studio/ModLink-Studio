from __future__ import annotations

from functools import partial

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QAbstractButton,
    QGridLayout,
    QHBoxLayout,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    ComboBox,
    InfoBar,
    InfoBarPosition,
    LineEdit,
    PopupTeachingTip,
    PrimaryPushButton,
    PrimaryToolButton,
    PushButton,
    SimpleCardWidget,
    TeachingTipTailPosition,
    TransparentToolButton,
    isDarkTheme,
)
from qfluentwidgets import (
    FluentIcon as FIF,
)

from modlink_qt_bridge import QtModLinkBridge

from .view_model import AcquisitionFieldState, AcquisitionViewModel


def _field_label_stylesheet() -> str:
    if isDarkTheme():
        return "color: rgba(255, 255, 255, 0.68); font-size: 12px;"
    return "color: rgba(15, 23, 42, 0.62); font-size: 12px;"


class LabeledField(QWidget):
    def __init__(
        self,
        state: AcquisitionFieldState,
        *,
        header_suffix: QWidget | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.label = BodyLabel(state.label, self)
        self.label.setStyleSheet(_field_label_stylesheet())
        self.input = LineEdit(self)

        self.input.setPlaceholderText(state.placeholder)
        self.input.setText(state.value)
        self.input.setReadOnly(state.read_only)
        self.input.setClearButtonEnabled(not state.read_only)
        self.input.setFixedHeight(36)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)
        header_layout.addWidget(self.label)
        if header_suffix is not None:
            header_layout.addWidget(header_suffix)
        header_layout.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addLayout(header_layout)
        layout.addWidget(self.input)


class LabeledComboField(QWidget):
    def __init__(
        self,
        label: str,
        *,
        header_suffix: QWidget | None = None,
        input_widget: ComboBox | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.label = BodyLabel(label, self)
        self.label.setStyleSheet(_field_label_stylesheet())
        self.input = input_widget or ComboBox(self)
        self.input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.input.setFixedHeight(36)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)
        header_layout.addWidget(self.label)
        if header_suffix is not None:
            header_layout.addWidget(header_suffix)
        header_layout.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addLayout(header_layout)
        layout.addWidget(self.input)


class LazyRefreshComboBox(ComboBox):
    def __init__(self, on_refresh, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self._on_refresh = on_refresh

    def _showComboMenu(self) -> None:
        self._on_refresh()
        super()._showComboMenu()


class CurrentWidgetStackedWidget(QStackedWidget):
    def sizeHint(self) -> QSize:
        current_widget = self.currentWidget()
        if current_widget is None:
            return super().sizeHint()
        return current_widget.sizeHint()

    def minimumSizeHint(self) -> QSize:
        current_widget = self.currentWidget()
        if current_widget is None:
            return super().minimumSizeHint()
        return current_widget.minimumSizeHint()

    def refreshGeometry(self) -> None:
        self.updateGeometry()
        parent = self.parentWidget()
        while parent is not None:
            layout = parent.layout()
            if layout is not None:
                layout.invalidate()
            parent.updateGeometry()
            parent = parent.parentWidget()


class ChevronStripButton(QAbstractButton):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(8)

    def sizeHint(self) -> QSize:
        return QSize(240, 8)

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


class SharedAcquisitionPanel(QWidget):
    def __init__(
        self,
        view_model: AcquisitionViewModel,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.view_model = view_model
        self.output_directory_tip: PopupTeachingTip | None = None
        self.recording_label_combo: LazyRefreshComboBox | None = None
        self._recording_label_placeholder = ""

    def _create_output_directory_hint(
        self,
        parent: QWidget | None = None,
    ) -> TransparentToolButton:
        hint = TransparentToolButton(FIF.INFO, parent or self)
        hint.setFixedSize(16, 16)
        hint.setIconSize(QSize(12, 12))
        hint.clicked.connect(partial(self._show_output_directory_tip, hint))
        return hint

    def _bind_line_edit(self, input_widget: LineEdit, key: str) -> None:
        input_widget.textChanged.connect(partial(self.view_model.update_field_value_from_ui, key))

    def _bind_combo_box(self, combo_box: ComboBox, key: str) -> None:
        combo_box.currentTextChanged.connect(
            partial(self.view_model.update_field_value_from_ui, key)
        )

    def _sync_line_edit(self, input_widget: LineEdit, key: str) -> None:
        value = self.view_model.get_field_value(key)
        if input_widget.text() == value:
            return

        was_blocked = input_widget.blockSignals(True)
        input_widget.setText(value)
        input_widget.blockSignals(was_blocked)

    def _refresh_recording_label_options(self) -> None:
        combo = self.recording_label_combo
        if combo is None:
            return

        labels = self.view_model.get_recording_labels()
        current_text = self.view_model.get_field_value("recording_label").strip()

        was_blocked = combo.blockSignals(True)
        combo.clear()
        for label in labels:
            combo.addItem(label, userData=label)

        if current_text:
            index = combo.findText(current_text)
            if index >= 0:
                combo.setCurrentIndex(index)
            else:
                combo.setPlaceholderText(current_text)
                combo.setCurrentIndex(-1)
        else:
            combo.setPlaceholderText(self._recording_label_placeholder)
            combo.setCurrentIndex(-1)

        combo.blockSignals(was_blocked)

    def _show_output_directory_tip(self, target: QWidget) -> None:
        self.close_output_directory_tip()

        output_directory = self.view_model.build_output_directory()
        parent = self.window() if isinstance(self.window(), QWidget) else self
        self.output_directory_tip = PopupTeachingTip.create(
            target=target,
            title="输出目录",
            content=f"录制文件将会保存在 {output_directory}",
            icon=FIF.FOLDER,
            isClosable=False,
            duration=-1,
            tailPosition=TeachingTipTailPosition.BOTTOM_RIGHT,
            parent=parent,
        )
        self.output_directory_tip.destroyed.connect(self._clear_output_directory_tip)

    def close_output_directory_tip(self) -> None:
        if self.output_directory_tip is None:
            return
        self.output_directory_tip.close()
        self.output_directory_tip = None

    def _clear_output_directory_tip(self) -> None:
        self.output_directory_tip = None

    def _sync_interaction_state(self) -> None:
        is_recording = self.view_model.is_recording
        is_segment_active = self.view_model.is_segment_active

        self.session_name_input.setEnabled(not is_recording)
        if self.recording_label_combo is not None:
            self.recording_label_combo.setEnabled(not is_recording)

        self.insert_marker_button.setEnabled(is_recording)
        self.toggle_segment_button.setEnabled(is_recording)
        self.reset_segment_button.setEnabled(is_recording and is_segment_active)

    def sync_from_view_model(self) -> None:
        raise NotImplementedError


class DetailedAcquisitionPanel(SharedAcquisitionPanel):
    def __init__(
        self,
        view_model: AcquisitionViewModel,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(view_model, parent=parent)

        state = self.view_model.state
        (
            session_name_state,
            recording_label_state,
            marker_label_state,
            segment_label_state,
        ) = state.fields
        (
            insert_marker_state,
            toggle_segment_state,
            reset_segment_state,
        ) = state.secondary_actions

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(12)

        form_grid = QGridLayout()
        form_grid.setContentsMargins(0, 0, 0, 0)
        form_grid.setHorizontalSpacing(12)
        form_grid.setVerticalSpacing(10)

        self.output_directory_hint = self._create_output_directory_hint(self)

        session_name_field = LabeledField(
            session_name_state,
            header_suffix=self.output_directory_hint,
            parent=self,
        )
        self.session_name_input = session_name_field.input
        self._bind_line_edit(self.session_name_input, session_name_state.key)

        self.recording_label_combo = LazyRefreshComboBox(
            self._refresh_recording_label_options,
            self,
        )
        self._recording_label_placeholder = recording_label_state.placeholder
        self.recording_label_combo.setPlaceholderText(recording_label_state.placeholder)
        recording_label_field = LabeledComboField(
            recording_label_state.label,
            input_widget=self.recording_label_combo,
            parent=self,
        )
        self._bind_combo_box(self.recording_label_combo, recording_label_state.key)

        marker_label_field = LabeledField(marker_label_state, parent=self)
        self.marker_label_input = marker_label_field.input
        self._bind_line_edit(self.marker_label_input, marker_label_state.key)

        segment_label_field = LabeledField(segment_label_state, parent=self)
        self.segment_label_input = segment_label_field.input
        self._bind_line_edit(self.segment_label_input, segment_label_state.key)

        form_grid.addWidget(session_name_field, 0, 0)
        form_grid.addWidget(recording_label_field, 0, 1)
        form_grid.addWidget(marker_label_field, 1, 0)
        form_grid.addWidget(segment_label_field, 1, 1)

        action_grid = QGridLayout()
        action_grid.setContentsMargins(0, 0, 0, 0)
        action_grid.setHorizontalSpacing(10)
        action_grid.setVerticalSpacing(0)

        self.toggle_recording_button = PrimaryPushButton(state.primary_action.text, self)
        self.toggle_recording_button.setIcon(state.primary_action.icon)
        self.toggle_recording_button.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self.toggle_recording_button.setFixedHeight(38)
        self.toggle_recording_button.clicked.connect(self.view_model.request_toggle_recording)

        self.insert_marker_button = PushButton(insert_marker_state.text, self)
        self.insert_marker_button.setIcon(insert_marker_state.icon)
        self.insert_marker_button.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self.insert_marker_button.setFixedHeight(38)
        self.insert_marker_button.clicked.connect(self.view_model.request_insert_marker)

        self.toggle_segment_button = PushButton(toggle_segment_state.text, self)
        self.toggle_segment_button.setIcon(toggle_segment_state.icon)
        self.toggle_segment_button.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self.toggle_segment_button.setFixedHeight(38)
        self.toggle_segment_button.clicked.connect(self.view_model.request_toggle_segment)

        self.reset_segment_button = PushButton(reset_segment_state.text, self)
        self.reset_segment_button.setIcon(reset_segment_state.icon)
        self.reset_segment_button.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self.reset_segment_button.setFixedHeight(38)
        self.reset_segment_button.clicked.connect(self.view_model.request_reset_segment)

        action_grid.addWidget(self.toggle_recording_button, 0, 0)
        action_grid.addWidget(self.insert_marker_button, 0, 1)
        action_grid.addWidget(self.toggle_segment_button, 0, 2)
        action_grid.addWidget(self.reset_segment_button, 0, 3)
        action_grid.setColumnStretch(0, 1)
        action_grid.setColumnStretch(1, 1)
        action_grid.setColumnStretch(2, 1)
        action_grid.setColumnStretch(3, 1)

        root_layout.addLayout(form_grid)
        root_layout.addLayout(action_grid)

        self.sync_from_view_model()

    def sync_from_view_model(self) -> None:
        self._sync_line_edit(self.session_name_input, "session_name")
        self._refresh_recording_label_options()
        self._sync_line_edit(self.marker_label_input, "marker_label")
        self._sync_line_edit(self.segment_label_input, "segment_label")
        self._sync_interaction_state()

        primary_action = self.view_model.current_primary_action()
        self.toggle_recording_button.setText(primary_action.text)
        self.toggle_recording_button.setIcon(primary_action.icon)

        segment_action = self.view_model.current_toggle_segment_action()
        self.toggle_segment_button.setText(segment_action.text)
        self.toggle_segment_button.setIcon(segment_action.icon)


class CompactAcquisitionPanel(SharedAcquisitionPanel):
    def __init__(
        self,
        view_model: AcquisitionViewModel,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(view_model, parent=parent)

        state = self.view_model.state
        (
            session_name_state,
            recording_label_state,
            marker_label_state,
            segment_label_state,
        ) = state.fields
        (
            insert_marker_state,
            toggle_segment_state,
            reset_segment_state,
        ) = state.secondary_actions

        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(8)

        self.session_name_input = LineEdit(self)
        self.session_name_input.setPlaceholderText(session_name_state.label)
        self.session_name_input.setClearButtonEnabled(True)
        self.session_name_input.setFixedHeight(34)
        self.session_name_input.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self._bind_line_edit(self.session_name_input, session_name_state.key)

        self.recording_label_combo = LazyRefreshComboBox(
            self._refresh_recording_label_options,
            self,
        )
        self._recording_label_placeholder = recording_label_state.label
        self.recording_label_combo.setPlaceholderText(recording_label_state.label)
        self.recording_label_combo.setFixedHeight(34)
        self.recording_label_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self._bind_combo_box(self.recording_label_combo, recording_label_state.key)

        self.annotation_label_input = LineEdit(self)
        self.annotation_label_input.setPlaceholderText(
            f"{marker_label_state.label} / {segment_label_state.label}"
        )
        self.annotation_label_input.setClearButtonEnabled(True)
        self.annotation_label_input.setFixedHeight(34)
        self.annotation_label_input.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self.annotation_label_input.textChanged.connect(self._set_compact_annotation_value)

        self.insert_marker_button = TransparentToolButton(insert_marker_state.icon, self)
        self.insert_marker_button.setFixedSize(34, 34)
        self.insert_marker_button.clicked.connect(self.view_model.request_insert_marker)

        self.toggle_segment_button = TransparentToolButton(
            toggle_segment_state.icon,
            self,
        )
        self.toggle_segment_button.setFixedSize(34, 34)
        self.toggle_segment_button.clicked.connect(self.view_model.request_toggle_segment)

        self.reset_segment_button = TransparentToolButton(reset_segment_state.icon, self)
        self.reset_segment_button.setFixedSize(34, 34)
        self.reset_segment_button.clicked.connect(self.view_model.request_reset_segment)

        self.toggle_recording_button = PrimaryToolButton(state.primary_action.icon, self)
        self.toggle_recording_button.setFixedSize(34, 34)
        self.toggle_recording_button.clicked.connect(self.view_model.request_toggle_recording)

        root_layout.addWidget(self.session_name_input, 1)
        root_layout.addWidget(self.recording_label_combo, 1)
        root_layout.addWidget(self.annotation_label_input, 1)
        root_layout.addWidget(self.insert_marker_button)
        root_layout.addWidget(self.toggle_segment_button)
        root_layout.addWidget(self.reset_segment_button)
        root_layout.addWidget(self.toggle_recording_button)

        self.sync_from_view_model()

    def _set_compact_annotation_value(self, value: str) -> None:
        self.view_model.update_field_value_from_ui("marker_label", value)
        self.view_model.update_field_value_from_ui("segment_label", value)

    def _sync_compact_annotation_value(self) -> None:
        marker_label = self.view_model.get_field_value("marker_label").strip()
        segment_label = self.view_model.get_field_value("segment_label").strip()
        value = marker_label or segment_label
        if self.annotation_label_input.text() == value:
            return

        was_blocked = self.annotation_label_input.blockSignals(True)
        self.annotation_label_input.setText(value)
        self.annotation_label_input.blockSignals(was_blocked)

    def sync_from_view_model(self) -> None:
        self._sync_line_edit(self.session_name_input, "session_name")
        self._refresh_recording_label_options()
        self._sync_compact_annotation_value()
        self._sync_interaction_state()

        primary_action = self.view_model.current_primary_action()
        self.toggle_recording_button.setIcon(primary_action.icon)

        segment_action = self.view_model.current_toggle_segment_action()
        self.toggle_segment_button.setIcon(segment_action.icon)


class AcquisitionControlPanel(SimpleCardWidget):
    def __init__(self, engine: QtModLinkBridge, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.view_model = AcquisitionViewModel(engine, parent=self)

        self.setObjectName("acquisition-control-panel")
        self.setBorderRadius(18)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 5, 18, 18)
        root_layout.setSpacing(5)

        self.toggle_strip = QWidget(self)
        self.toggle_strip.setFixedHeight(8)
        toggle_layout = QVBoxLayout(self.toggle_strip)
        toggle_layout.setContentsMargins(0, 0, 0, 0)
        toggle_layout.setSpacing(0)

        self.layout_toggle_button = ChevronStripButton(self.toggle_strip)
        self.layout_toggle_button.clicked.connect(self._toggle_layout_mode)
        toggle_layout.addWidget(self.layout_toggle_button)

        self.panel_stack = CurrentWidgetStackedWidget(self)
        self.panel_stack.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum,
        )

        self.detailed_panel = DetailedAcquisitionPanel(self.view_model, self.panel_stack)
        self.compact_panel = CompactAcquisitionPanel(self.view_model, self.panel_stack)
        self.panel_stack.addWidget(self.detailed_panel)
        self.panel_stack.addWidget(self.compact_panel)

        self.view_model.sig_field_value_changed.connect(self._sync_panels_from_view_model)
        self.view_model.sig_recording_changed.connect(self._sync_panels_from_view_model)
        self.view_model.sig_segment_active_changed.connect(self._sync_panels_from_view_model)
        self.view_model.sig_error.connect(self._show_error_bar)

        root_layout.addWidget(self.toggle_strip)
        root_layout.addWidget(self.panel_stack)

        self._sync_layout_mode()

    def _normalBackgroundColor(self) -> QColor:
        return QColor(43, 43, 43) if isDarkTheme() else QColor(255, 255, 255)

    def _hoverBackgroundColor(self) -> QColor:
        return self._normalBackgroundColor()

    def _pressedBackgroundColor(self) -> QColor:
        return self._normalBackgroundColor()

    def _toggle_layout_mode(self) -> None:
        self.detailed_panel.close_output_directory_tip()
        self.compact_panel.close_output_directory_tip()
        self.view_model.toggle_layout_mode()
        self._sync_layout_mode()

    def _sync_panels_from_view_model(self, *_args) -> None:
        self.detailed_panel.sync_from_view_model()
        self.compact_panel.sync_from_view_model()
        self.panel_stack.refreshGeometry()
        self.updateGeometry()

    def _sync_layout_mode(self) -> None:
        is_compact_mode = self.view_model.layout_mode == "compact"
        current_panel = self.compact_panel if is_compact_mode else self.detailed_panel
        self.panel_stack.setCurrentWidget(current_panel)
        self._sync_panels_from_view_model()
        was_blocked = self.layout_toggle_button.blockSignals(True)
        self.layout_toggle_button.setChecked(not is_compact_mode)
        self.layout_toggle_button.blockSignals(was_blocked)

    def _show_error_bar(self, message: str) -> None:
        parent = self.window() if isinstance(self.window(), QWidget) else self
        InfoBar.error(
            title="采集错误",
            content=message,
            duration=4500,
            position=InfoBarPosition.TOP_RIGHT,
            parent=parent,
        )


__all__ = ["AcquisitionControlPanel"]
