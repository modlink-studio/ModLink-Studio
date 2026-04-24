from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QPlainTextEdit,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    PrimaryPushButton,
    PushButton,
    SimpleCardWidget,
    StrongBodyLabel,
    TransparentToolButton,
)
from qfluentwidgets import FluentIcon as FIF

from .experiment_runtime import ExperimentRuntimeSnapshot, ExperimentRuntimeViewModel


def _section_label(text: str, parent: QWidget) -> BodyLabel:
    label = BodyLabel(text, parent)
    label.setStyleSheet("font-size: 12px;")
    return label


class _SidebarField(QWidget):
    def __init__(
        self,
        label_text: str,
        input_widget: QWidget,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.label = _section_label(label_text, self)
        self.input = input_widget

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self.label)
        layout.addWidget(self.input)


class LiveExperimentSidebar(SimpleCardWidget):
    sig_close_requested = pyqtSignal()

    def __init__(
        self,
        view_model: ExperimentRuntimeViewModel,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.view_model = view_model

        self.setObjectName("live-experiment-sidebar")
        self.setBorderRadius(18)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 16, 18, 16)
        root_layout.setSpacing(12)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)

        self.title_label = StrongBodyLabel("实验侧栏", self)
        self.subtitle_label = CaptionLabel(
            "管理 experiment、session 和当前步骤，推荐录制标签由这里生成。",
            self,
        )
        self.subtitle_label.setWordWrap(True)

        self.close_button = TransparentToolButton(FIF.CLOSE, self)
        self.close_button.clicked.connect(self.sig_close_requested.emit)

        title_block = QVBoxLayout()
        title_block.setContentsMargins(0, 0, 0, 0)
        title_block.setSpacing(4)
        title_block.addWidget(self.title_label)
        title_block.addWidget(self.subtitle_label)

        header_row.addLayout(title_block, 1)
        header_row.addWidget(self.close_button, 0, Qt.AlignmentFlag.AlignTop)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.scroll_widget = QWidget(self.scroll_area)
        self.scroll_widget.setObjectName("live-experiment-sidebar-scroll-widget")
        self.scroll_widget.setStyleSheet(
            "QWidget#live-experiment-sidebar-scroll-widget { background: transparent; }"
        )
        self.scroll_area.setWidget(self.scroll_widget)

        content_layout = QVBoxLayout(self.scroll_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(14)

        from qfluentwidgets import LineEdit  # local import to keep qfluent imports grouped above

        self.experiment_name_input = LineEdit(self.scroll_widget)
        self.experiment_name_input.setPlaceholderText("例如 吞咽障碍采集_2025_04_21")
        self.experiment_name_input.setClearButtonEnabled(True)

        self.session_name_input = LineEdit(self.scroll_widget)
        self.session_name_input.setPlaceholderText("例如 healthy_H03")
        self.session_name_input.setClearButtonEnabled(True)

        self.steps_editor = QPlainTextEdit(self.scroll_widget)
        self.steps_editor.setPlaceholderText("一行一个步骤，例如：\n0ml\n5ml\n15ml")
        self.steps_editor.setMinimumHeight(140)

        self.experiment_field = _SidebarField("Experiment Name", self.experiment_name_input, self)
        self.session_field = _SidebarField("Session Name", self.session_name_input, self)
        self.steps_field = _SidebarField("Step Queue", self.steps_editor, self)

        self.current_step_card = SimpleCardWidget(self.scroll_widget)
        self.current_step_card.setBorderRadius(14)
        current_step_layout = QVBoxLayout(self.current_step_card)
        current_step_layout.setContentsMargins(14, 12, 14, 12)
        current_step_layout.setSpacing(6)
        current_step_layout.addWidget(StrongBodyLabel("当前步骤", self.current_step_card))
        self.current_step_label = BodyLabel("未设置步骤", self.current_step_card)
        self.current_step_label.setWordWrap(True)
        self.current_step_position_label = CaptionLabel("第 0 / 0 步", self.current_step_card)
        current_step_layout.addWidget(self.current_step_label)
        current_step_layout.addWidget(self.current_step_position_label)

        self.suggested_label_card = SimpleCardWidget(self.scroll_widget)
        self.suggested_label_card.setBorderRadius(14)
        suggested_layout = QVBoxLayout(self.suggested_label_card)
        suggested_layout.setContentsMargins(14, 12, 14, 12)
        suggested_layout.setSpacing(6)
        suggested_layout.addWidget(StrongBodyLabel("推荐录制标签", self.suggested_label_card))
        self.suggested_label_label = BodyLabel(
            "先填写 session name 并设置当前步骤。",
            self.suggested_label_card,
        )
        self.suggested_label_label.setWordWrap(True)
        suggested_layout.addWidget(self.suggested_label_label)

        controls_row = QHBoxLayout()
        controls_row.setContentsMargins(0, 0, 0, 0)
        controls_row.setSpacing(8)

        self.fill_button = PrimaryPushButton("填入当前建议", self.scroll_widget)
        self.fill_button.clicked.connect(self.view_model.request_fill_suggested_label)

        self.prev_button = PushButton("Prev", self.scroll_widget)
        self.prev_button.clicked.connect(self.view_model.prev_step)

        self.next_button = PushButton("Next", self.scroll_widget)
        self.next_button.clicked.connect(self.view_model.next_step)

        self.retry_button = PushButton("Retry", self.scroll_widget)
        self.retry_button.clicked.connect(self.view_model.retry_step)

        controls_row.addWidget(self.fill_button, 1)
        controls_row.addWidget(self.prev_button)
        controls_row.addWidget(self.next_button)
        controls_row.addWidget(self.retry_button)

        content_layout.addWidget(self.experiment_field)
        content_layout.addWidget(self.session_field)
        content_layout.addWidget(self.steps_field)
        content_layout.addWidget(self.current_step_card)
        content_layout.addWidget(self.suggested_label_card)
        content_layout.addLayout(controls_row)
        content_layout.addStretch(1)

        root_layout.addLayout(header_row)
        root_layout.addWidget(self.scroll_area, 1)

        self.experiment_name_input.textChanged.connect(self.view_model.set_experiment_name)
        self.session_name_input.textChanged.connect(self.view_model.set_session_name)
        self.steps_editor.textChanged.connect(self._on_steps_text_changed)
        self.view_model.sig_snapshot_changed.connect(self._sync_from_snapshot)

        self._sync_from_snapshot(self.view_model.snapshot())

    def _on_steps_text_changed(self) -> None:
        self.view_model.set_steps_text(self.steps_editor.toPlainText())

    def _sync_from_snapshot(self, snapshot: object) -> None:
        if not isinstance(snapshot, ExperimentRuntimeSnapshot):
            snapshot = self.view_model.snapshot()

        if self.experiment_name_input.text() != snapshot.experiment_name:
            was_blocked = self.experiment_name_input.blockSignals(True)
            self.experiment_name_input.setText(snapshot.experiment_name)
            self.experiment_name_input.blockSignals(was_blocked)

        if self.session_name_input.text() != snapshot.session_name:
            was_blocked = self.session_name_input.blockSignals(True)
            self.session_name_input.setText(snapshot.session_name)
            self.session_name_input.blockSignals(was_blocked)

        steps_text = "\n".join(step.label for step in snapshot.steps)
        if self.steps_editor.toPlainText() != steps_text:
            was_blocked = self.steps_editor.blockSignals(True)
            self.steps_editor.setPlainText(steps_text)
            self.steps_editor.blockSignals(was_blocked)

        current_step = snapshot.current_step
        self.current_step_label.setText(
            "未设置步骤" if current_step is None else current_step.label
        )
        current_position = (
            0 if current_step is None or snapshot.current_step_index < 0 else snapshot.current_step_index + 1
        )
        self.current_step_position_label.setText(
            f"第 {current_position} / {len(snapshot.steps)} 步"
        )

        self.suggested_label_label.setText(
            snapshot.suggested_recording_label or "先填写 session name 并设置当前步骤。"
        )
        self.fill_button.setEnabled(snapshot.can_fill_recording_label)
        self.prev_button.setEnabled(snapshot.can_go_previous)
        self.next_button.setEnabled(snapshot.can_go_next)
        self.retry_button.setEnabled(snapshot.can_retry)


__all__ = ["LiveExperimentSidebar"]
