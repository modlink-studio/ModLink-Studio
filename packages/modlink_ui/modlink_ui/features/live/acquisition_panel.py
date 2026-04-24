from __future__ import annotations

from functools import partial

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    ComboBox,
    InfoBar,
    InfoBarPosition,
    LineEdit,
    PrimaryPushButton,
    PushButton,
    SimpleCardWidget,
    isDarkTheme,
)

from modlink_ui.bridge import QtModLinkBridge

from .acquisition_view_model import AcquisitionViewModel


class LazyRefreshComboBox(ComboBox):
    def __init__(self, on_refresh, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self._on_refresh = on_refresh

    def _showComboMenu(self) -> None:
        self._on_refresh()
        super()._showComboMenu()


class AcquisitionControlsPanel(QWidget):
    def __init__(
        self,
        view_model: AcquisitionViewModel,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.view_model = view_model
        state = self.view_model.state
        (
            recording_label_state,
            annotation_label_state,
        ) = state.fields
        (
            insert_marker_state,
            toggle_segment_state,
            reset_segment_state,
        ) = state.secondary_actions

        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(8)

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
        self.annotation_label_input.setPlaceholderText(annotation_label_state.label)
        self.annotation_label_input.setClearButtonEnabled(True)
        self.annotation_label_input.setFixedHeight(34)
        self.annotation_label_input.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self._bind_line_edit(self.annotation_label_input, annotation_label_state.key)

        self.insert_marker_button = PushButton(insert_marker_state.text, self)
        self.insert_marker_button.setIcon(insert_marker_state.icon)
        self.insert_marker_button.clicked.connect(self.view_model.request_insert_marker)

        self.toggle_segment_button = PushButton(toggle_segment_state.text, self)
        self.toggle_segment_button.setIcon(toggle_segment_state.icon)
        self.toggle_segment_button.clicked.connect(self.view_model.request_toggle_segment)

        self.reset_segment_button = PushButton(reset_segment_state.text, self)
        self.reset_segment_button.setIcon(reset_segment_state.icon)
        self.reset_segment_button.clicked.connect(self.view_model.request_reset_segment)

        self.toggle_recording_button = PrimaryPushButton(state.primary_action.text, self)
        self.toggle_recording_button.setIcon(state.primary_action.icon)
        self.toggle_recording_button.clicked.connect(self.view_model.request_toggle_recording)

        root_layout.addWidget(self.recording_label_combo, 1)
        root_layout.addWidget(self.annotation_label_input, 1)
        root_layout.addWidget(self.insert_marker_button)
        root_layout.addWidget(self.toggle_segment_button)
        root_layout.addWidget(self.reset_segment_button)
        root_layout.addWidget(self.toggle_recording_button)

        self.sync_from_view_model()

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
        labels = self.view_model.get_recording_labels()
        current_text = self.view_model.get_field_value("recording_label").strip()

        was_blocked = self.recording_label_combo.blockSignals(True)
        self.recording_label_combo.clear()
        for label in labels:
            self.recording_label_combo.addItem(label, userData=label)

        if current_text:
            index = self.recording_label_combo.findText(current_text)
            if index >= 0:
                self.recording_label_combo.setCurrentIndex(index)
            else:
                self.recording_label_combo.setPlaceholderText(current_text)
                self.recording_label_combo.setCurrentIndex(-1)
        else:
            self.recording_label_combo.setPlaceholderText(self._recording_label_placeholder)
            self.recording_label_combo.setCurrentIndex(-1)

        self.recording_label_combo.blockSignals(was_blocked)

    def _sync_interaction_state(self) -> None:
        is_recording = self.view_model.is_recording
        is_segment_active = self.view_model.is_segment_active

        self.recording_label_combo.setEnabled(not is_recording)
        self.insert_marker_button.setEnabled(is_recording)
        self.toggle_segment_button.setEnabled(is_recording)
        self.reset_segment_button.setEnabled(is_recording and is_segment_active)

    def sync_from_view_model(self) -> None:
        self._refresh_recording_label_options()
        self._sync_line_edit(self.annotation_label_input, "annotation_label")
        self._sync_interaction_state()

        primary_action = self.view_model.current_primary_action()
        self.toggle_recording_button.setText(primary_action.text)
        self.toggle_recording_button.setIcon(primary_action.icon)

        segment_action = self.view_model.current_toggle_segment_action()
        self.toggle_segment_button.setText(segment_action.text)
        self.toggle_segment_button.setIcon(segment_action.icon)


class AcquisitionControlPanel(SimpleCardWidget):
    def __init__(self, engine: QtModLinkBridge, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.view_model = AcquisitionViewModel(engine, parent=self)

        self.setObjectName("acquisition-control-panel")
        self.setBorderRadius(18)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(0)

        self.controls_panel = AcquisitionControlsPanel(self.view_model, self)

        self.view_model.sig_field_value_changed.connect(self._sync_controls_from_view_model)
        self.view_model.sig_recording_changed.connect(self._sync_controls_from_view_model)
        self.view_model.sig_segment_active_changed.connect(self._sync_controls_from_view_model)
        self.view_model.sig_error.connect(self._show_error_bar)
        self.view_model.sig_info.connect(self._show_success_bar)

        root_layout.addWidget(self.controls_panel)

    def _normalBackgroundColor(self) -> QColor:
        return QColor(43, 43, 43) if isDarkTheme() else QColor(255, 255, 255)

    def _hoverBackgroundColor(self) -> QColor:
        return self._normalBackgroundColor()

    def _pressedBackgroundColor(self) -> QColor:
        return self._normalBackgroundColor()

    def _sync_controls_from_view_model(self, *_args) -> None:
        self.controls_panel.sync_from_view_model()
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

    def _show_success_bar(self, message: str) -> None:
        parent = self.window() if isinstance(self.window(), QWidget) else self
        InfoBar.success(
            title="录制完成",
            content=message,
            duration=5500,
            position=InfoBarPosition.TOP_RIGHT,
            parent=parent,
        )
