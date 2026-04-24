from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    LineEdit,
    MessageBoxBase,
    PlainTextEdit,
    SimpleCardWidget,
    SingleDirectionScrollArea,
    SmoothMode,
    StrongBodyLabel,
    SubtitleLabel,
    TextBrowser,
    ToolButton,
    TransparentToolButton,
)
from qfluentwidgets import FluentIcon as FIF

from modlink_ui.bridge import QtSettingsBridge
from modlink_ui.shared.ui_settings.ai import (
    UI_AI_API_KEY_KEY,
    UI_AI_BASE_URL_KEY,
    UI_AI_MODEL_KEY,
    AiAssistantConfig,
    declare_ai_assistant_settings,
    load_ai_assistant_config,
)

from .acquisition_view_model import AcquisitionViewModel
from .experiment_ai import (
    ChatMessage,
    ExperimentAiAction,
    ExperimentAiReply,
    ExperimentAiRequestWorker,
    ExperimentAiToolRunner,
    ExperimentAiToolState,
    OpenAICompatibleExperimentClient,
    build_experiment_ai_messages,
)
from .experiment_runtime import ExperimentRuntimeSnapshot, ExperimentRuntimeViewModel

type ExperimentAiClientFactory = Callable[
    [AiAssistantConfig],
    OpenAICompatibleExperimentClient,
]


def _section_label(text: str, parent: QWidget) -> BodyLabel:
    label = BodyLabel(text, parent)
    label.setStyleSheet("font-size: 12px;")
    return label


class _MarkdownMessageBrowser(TextBrowser):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("experiment-ai-markdown-message")
        self.setReadOnly(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.viewport().setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.document().setDocumentMargin(0)
        self.viewport().setAutoFillBackground(False)
        self.setStyleSheet(
            "QTextBrowser#experiment-ai-markdown-message {"
            "background: transparent; border: none;"
            "}"
        )
        self.setMarkdown(text)
        self._fit_to_content()
        QTimer.singleShot(0, self._fit_to_content)

    def resizeEvent(self, event: object) -> None:
        super().resizeEvent(event)
        self._fit_to_content()

    def wheelEvent(self, event: object) -> None:
        event.ignore()

    def _fit_to_content(self) -> None:
        width = self.viewport().width() or self.width()
        if width <= 0:
            return
        self.document().setTextWidth(width)
        self.setFixedHeight(max(24, int(self.document().size().height()) + 2))


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


class _ExperimentSettingsDialog(MessageBoxBase):
    def __init__(
        self,
        view_model: ExperimentRuntimeViewModel,
        parent: QWidget,
    ) -> None:
        super().__init__(parent=parent)
        self.view_model = view_model

        self.yesButton.setText("保存")
        self.cancelButton.setText("取消")
        self.widget.setMinimumWidth(540)

        self.title_label = StrongBodyLabel("实验设置", self.widget)
        self.description_label = CaptionLabel(
            "设置 experiment、session 和步骤队列。",
            self.widget,
        )
        self.description_label.setWordWrap(True)

        self.experiment_name_input = LineEdit(self.widget)
        self.experiment_name_input.setPlaceholderText("例如 吞咽障碍采集_2025_04_21")
        self.experiment_name_input.setClearButtonEnabled(True)

        self.session_name_input = LineEdit(self.widget)
        self.session_name_input.setPlaceholderText("例如 healthy_H03")
        self.session_name_input.setClearButtonEnabled(True)

        self.steps_editor = PlainTextEdit(self.widget)
        self.steps_editor.setPlaceholderText("一行一个步骤，例如：\n0ml\n5ml\n15ml")
        self.steps_editor.setMinimumHeight(190)

        self.experiment_field = _SidebarField(
            "Experiment Name",
            self.experiment_name_input,
            self.widget,
        )
        self.session_field = _SidebarField(
            "Session Name",
            self.session_name_input,
            self.widget,
        )
        self.steps_field = _SidebarField("Step Queue", self.steps_editor, self.widget)

        self.viewLayout.addWidget(self.title_label)
        self.viewLayout.addWidget(self.description_label)
        self.viewLayout.addWidget(self.experiment_field)
        self.viewLayout.addWidget(self.session_field)
        self.viewLayout.addWidget(self.steps_field)

        self._sync_from_snapshot(self.view_model.snapshot())

    def validate(self) -> bool:
        self.view_model.set_experiment_name(self.experiment_name_input.text())
        self.view_model.set_session_name(self.session_name_input.text())
        self.view_model.set_steps_text(self.steps_editor.toPlainText())
        return True

    def _sync_from_snapshot(self, snapshot: ExperimentRuntimeSnapshot) -> None:
        self.experiment_name_input.setText(snapshot.experiment_name)
        self.session_name_input.setText(snapshot.session_name)
        self.steps_editor.setPlainText("\n".join(step.label for step in snapshot.steps))


class ExperimentAiChatPanel(QWidget):
    def __init__(
        self,
        view_model: ExperimentRuntimeViewModel,
        settings: QtSettingsBridge,
        acquisition_view_model: AcquisitionViewModel | None = None,
        parent: QWidget | None = None,
        *,
        client_factory: ExperimentAiClientFactory | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.view_model = view_model
        self._settings = settings
        self._acquisition_view_model = acquisition_view_model
        self._client_factory = client_factory or OpenAICompatibleExperimentClient
        self._config = load_ai_assistant_config(self._settings)
        self._conversation: list[ChatMessage] = []
        self._request_thread: QThread | None = None
        self._request_worker: ExperimentAiRequestWorker | None = None

        self.setObjectName("experiment-ai-chat-panel")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(10)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)

        self.title_label = StrongBodyLabel("AI 助手", self)

        header_row.addWidget(self.title_label, 1)

        self.messages_area = SingleDirectionScrollArea(self, orient=Qt.Orientation.Vertical)
        self.messages_area.setObjectName("experiment-ai-chat-messages")
        self.messages_area.setWidgetResizable(True)
        self.messages_area.setMinimumHeight(160)
        self.messages_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.messages_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.messages_area.setSmoothMode(SmoothMode.LINEAR)
        self.messages_area.smoothScroll.setDynamicEngineEnabled(True)
        self.messages_area.smoothScroll.widthThreshold = 0
        self.messages_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.messages_widget = QWidget(self.messages_area)
        self.messages_widget.setObjectName("experiment-ai-chat-messages-widget")
        self.messages_widget.setStyleSheet(
            "QWidget#experiment-ai-chat-messages-widget { background: transparent; }"
        )
        self.messages_layout = QVBoxLayout(self.messages_widget)
        self.messages_layout.setContentsMargins(0, 0, 0, 0)
        self.messages_layout.setSpacing(8)
        self.messages_layout.addStretch(1)
        self.messages_area.setWidget(self.messages_widget)

        input_row = QHBoxLayout()
        input_row.setContentsMargins(0, 0, 0, 0)
        input_row.setSpacing(8)

        self.input = LineEdit(self)
        self.input.setPlaceholderText("输入指令...")
        self.input.setClearButtonEnabled(True)
        self.input.returnPressed.connect(self._send_current_message)
        self.input.textChanged.connect(self._refresh_send_state)

        self.send_button = ToolButton(FIF.SEND, self)
        self.send_button.setFixedSize(36, 36)
        self.send_button.setToolTip("发送")
        self.send_button.clicked.connect(self._send_current_message)

        input_row.addWidget(self.input, 1)
        input_row.addWidget(self.send_button)

        root_layout.addLayout(header_row)
        root_layout.addWidget(self.messages_area, 1)
        root_layout.addLayout(input_row)

        self._settings.sig_setting_changed.connect(self._on_setting_changed)
        self._append_message(
            "assistant",
            "我可以帮你设置 experiment、session、标签和步骤，也可以切换上一步/下一步。",
        )
        self._refresh_config()

    def _send_current_message(self) -> None:
        text = self.input.text().strip()
        if not text or self._request_thread is not None or not self._config.is_configured:
            return

        self.input.clear()
        self._append_message("user", text)
        self._conversation.append({"role": "user", "content": text})

        try:
            client = self._client_factory(self._config)
        except Exception as exc:
            self._append_message("error", f"AI 配置不可用：{exc}")
            self._refresh_send_state()
            return

        snapshot = self.view_model.snapshot()
        recording_label = self._acquisition_field_value("recording_label")
        annotation_label = self._acquisition_field_value("annotation_label")
        messages = build_experiment_ai_messages(
            snapshot,
            self._conversation,
            recording_label=recording_label,
            annotation_label=annotation_label,
        )
        tool_runner = ExperimentAiToolRunner(
            ExperimentAiToolState.from_snapshot(
                snapshot,
                recording_label=recording_label,
                annotation_label=annotation_label,
            )
        )
        worker = ExperimentAiRequestWorker(client, messages, tool_runner)
        thread = QThread(self)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.sig_finished.connect(self._on_ai_reply)
        worker.sig_failed.connect(self._on_ai_failed)
        worker.sig_finished.connect(thread.quit)
        worker.sig_failed.connect(thread.quit)
        worker.sig_finished.connect(worker.deleteLater)
        worker.sig_failed.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_request_worker)

        self._request_thread = thread
        self._request_worker = worker
        self._refresh_send_state()
        thread.start()

    def _on_ai_reply(self, reply: object) -> None:
        if not isinstance(reply, ExperimentAiReply):
            self._on_ai_failed("AI 响应格式不正确")
            return
        self._apply_actions(reply.actions)
        self._append_message("assistant", reply.message)
        self._conversation.append({"role": "assistant", "content": reply.message})

    def _on_ai_failed(self, message: str) -> None:
        self._append_message("error", f"请求失败：{message}")

    def _clear_request_worker(self) -> None:
        self._request_thread = None
        self._request_worker = None
        self._refresh_send_state()

    def _on_setting_changed(self, event: object) -> None:
        if getattr(event, "key", None) not in {
            UI_AI_BASE_URL_KEY,
            UI_AI_API_KEY_KEY,
            UI_AI_MODEL_KEY,
        }:
            return
        self._refresh_config()

    def _refresh_config(self) -> None:
        self._config = load_ai_assistant_config(self._settings)
        self._refresh_send_state()

    def _refresh_send_state(self) -> None:
        can_send = (
            self._config.is_configured
            and self._request_thread is None
            and bool(self.input.text().strip())
        )
        self.input.setEnabled(self._config.is_configured and self._request_thread is None)
        self.send_button.setEnabled(can_send)

    def _acquisition_field_value(self, key: str) -> str:
        if self._acquisition_view_model is None:
            return ""
        try:
            return self._acquisition_view_model.get_field_value(key)
        except KeyError:
            return ""

    def _apply_actions(self, actions: tuple[ExperimentAiAction, ...]) -> None:
        for action in actions:
            self._apply_action(action)

    def _apply_action(self, action: ExperimentAiAction) -> None:
        arguments = action.arguments
        if action.name == "set_experiment_name":
            self.view_model.set_experiment_name(str(arguments.get("value", "")))
            return
        if action.name == "set_session_name":
            self.view_model.set_session_name(str(arguments.get("value", "")))
            return
        if action.name == "set_steps":
            raw_steps = arguments.get("steps", [])
            if isinstance(raw_steps, list):
                self.view_model.set_steps_text("\n".join(str(step) for step in raw_steps))
            return
        if action.name == "set_label":
            if self._acquisition_view_model is None:
                return
            target = str(arguments.get("target", "recording_label"))
            if target not in {"recording_label", "annotation_label"}:
                return
            value = str(arguments.get("value", ""))
            self._acquisition_view_model.set_field_value(target, value)
            return
        if action.name == "previous_step":
            self.view_model.prev_step()
            return
        if action.name == "next_step":
            self.view_model.next_step()

    def _append_message(self, role: str, text: str) -> None:
        row = QFrame(self.messages_widget)
        row.setObjectName(f"experiment-ai-message-{role}")
        row.setProperty("role", role)
        row_layout = QVBoxLayout(row)
        row_layout.setContentsMargins(10, 8, 10, 8)
        row_layout.setSpacing(4)

        role_label = CaptionLabel(self._role_title(role), row)
        if role == "assistant":
            body_widget = _MarkdownMessageBrowser(text, row)
        else:
            body_widget = BodyLabel(text, row)
            body_widget.setWordWrap(True)

        row_layout.addWidget(role_label)
        row_layout.addWidget(body_widget)
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, row)
        self._scroll_messages_to_bottom()

    def _scroll_messages_to_bottom(self) -> None:
        def scroll() -> None:
            bar = self.messages_area.verticalScrollBar()
            bar.setValue(bar.maximum())

        QTimer.singleShot(0, scroll)

    @staticmethod
    def _role_title(role: str) -> str:
        if role == "user":
            return "你"
        if role == "error":
            return "错误"
        return "AI"


class LiveExperimentSidebar(SimpleCardWidget):
    sig_close_requested = pyqtSignal()

    def __init__(
        self,
        view_model: ExperimentRuntimeViewModel,
        settings: QtSettingsBridge,
        acquisition_view_model: AcquisitionViewModel | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.view_model = view_model
        self.settings = settings

        self.setObjectName("live-experiment-sidebar")
        self.setBorderRadius(18)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.settings_dialog: _ExperimentSettingsDialog | None = None
        declare_ai_assistant_settings(self.settings)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 16, 18, 16)
        root_layout.setSpacing(12)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)

        self.title_label = StrongBodyLabel("实验侧栏", self)
        self.subtitle_label = CaptionLabel(
            "管理 experiment、session 和当前步骤。",
            self,
        )
        self.subtitle_label.setWordWrap(True)

        self.settings_button = TransparentToolButton(FIF.SETTING, self)
        self.settings_button.clicked.connect(self._show_settings_dialog)

        self.close_button = TransparentToolButton(FIF.CLOSE, self)
        self.close_button.clicked.connect(self.sig_close_requested.emit)

        title_block = QVBoxLayout()
        title_block.setContentsMargins(0, 0, 0, 0)
        title_block.setSpacing(4)
        title_block.addWidget(self.title_label)
        title_block.addWidget(self.subtitle_label)

        header_row.addLayout(title_block, 1)
        header_row.addWidget(self.settings_button, 0, Qt.AlignmentFlag.AlignTop)
        header_row.addWidget(self.close_button, 0, Qt.AlignmentFlag.AlignTop)

        self.current_step_card = SimpleCardWidget(self)
        self.current_step_card.setBorderRadius(14)
        current_step_layout = QHBoxLayout(self.current_step_card)
        current_step_layout.setContentsMargins(10, 12, 10, 12)
        current_step_layout.setSpacing(8)

        self.prev_button = TransparentToolButton(FIF.LEFT_ARROW, self.current_step_card)
        self.prev_button.setFixedSize(32, 32)
        self.prev_button.setToolTip("上一步")
        self.prev_button.clicked.connect(self.view_model.prev_step)

        self.next_button = TransparentToolButton(FIF.RIGHT_ARROW, self.current_step_card)
        self.next_button.setFixedSize(32, 32)
        self.next_button.setToolTip("下一步")
        self.next_button.clicked.connect(self.view_model.next_step)

        step_text_layout = QVBoxLayout()
        step_text_layout.setContentsMargins(0, 0, 0, 0)
        step_text_layout.setSpacing(4)

        self.current_step_label = SubtitleLabel("未设置步骤", self.current_step_card)
        self.current_step_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.current_step_label.setWordWrap(True)
        self.current_step_position_label = CaptionLabel("0/0", self.current_step_card)
        self.current_step_position_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        step_text_layout.addWidget(self.current_step_label)
        step_text_layout.addWidget(self.current_step_position_label)

        current_step_layout.addWidget(self.prev_button)
        current_step_layout.addLayout(step_text_layout, 1)
        current_step_layout.addWidget(self.next_button)

        self.ai_chat_panel = ExperimentAiChatPanel(
            self.view_model,
            self.settings,
            acquisition_view_model,
            self,
        )

        root_layout.addLayout(header_row)
        root_layout.addWidget(self.current_step_card)
        root_layout.addWidget(self.ai_chat_panel, 1)

        self.view_model.sig_snapshot_changed.connect(self._sync_from_snapshot)

        self._sync_from_snapshot(self.view_model.snapshot())

    def _show_settings_dialog(self) -> None:
        if self.settings_dialog is not None and self.settings_dialog.isVisible():
            self.settings_dialog.raise_()
            return

        parent = self.window() if isinstance(self.window(), QWidget) else self
        self.settings_dialog = _ExperimentSettingsDialog(self.view_model, parent)
        self.settings_dialog.finished.connect(self._clear_settings_dialog)
        self.settings_dialog.open()

    def _clear_settings_dialog(self) -> None:
        self.settings_dialog = None

    def _sync_from_snapshot(self, snapshot: object) -> None:
        if not isinstance(snapshot, ExperimentRuntimeSnapshot):
            snapshot = self.view_model.snapshot()

        current_step = snapshot.current_step
        self.current_step_label.setText(
            "未设置步骤" if current_step is None else current_step.label
        )
        current_position = (
            0 if current_step is None or snapshot.current_step_index < 0 else snapshot.current_step_index + 1
        )
        self.current_step_position_label.setText(f"{current_position}/{len(snapshot.steps)}")

        self.prev_button.setEnabled(snapshot.can_go_previous)
        self.next_button.setEnabled(snapshot.can_go_next)


__all__ = ["ExperimentAiChatPanel", "LiveExperimentSidebar"]
