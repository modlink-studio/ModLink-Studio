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
    PushButton,
    SimpleCardWidget,
    SingleDirectionScrollArea,
    SmoothMode,
    StrongBodyLabel,
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

from .experiment_ai import (
    ChatMessage,
    ExperimentAiProposal,
    ExperimentAiReply,
    ExperimentAiRequestWorker,
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


class ExperimentAiChatPanel(SimpleCardWidget):
    def __init__(
        self,
        view_model: ExperimentRuntimeViewModel,
        settings: QtSettingsBridge,
        parent: QWidget | None = None,
        *,
        client_factory: ExperimentAiClientFactory | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.view_model = view_model
        self._settings = settings
        self._client_factory = client_factory or OpenAICompatibleExperimentClient
        self._config = load_ai_assistant_config(self._settings)
        self._conversation: list[ChatMessage] = []
        self._request_thread: QThread | None = None
        self._request_worker: ExperimentAiRequestWorker | None = None
        self.latest_proposal_button: PushButton | None = None

        self.setObjectName("experiment-ai-chat-panel")
        self.setBorderRadius(14)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(14, 12, 14, 12)
        root_layout.setSpacing(10)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)

        self.title_label = StrongBodyLabel("AI 助手", self)
        self.status_label = CaptionLabel("", self)
        self.status_label.setWordWrap(True)

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
        self.input.setPlaceholderText("让 AI 帮你生成或修改实验设置")
        self.input.setClearButtonEnabled(True)
        self.input.returnPressed.connect(self._send_current_message)
        self.input.textChanged.connect(self._refresh_send_state)

        self.send_button = PushButton("发送", self)
        self.send_button.setIcon(FIF.SEND)
        self.send_button.clicked.connect(self._send_current_message)

        input_row.addWidget(self.input, 1)
        input_row.addWidget(self.send_button)

        root_layout.addLayout(header_row)
        root_layout.addWidget(self.status_label)
        root_layout.addWidget(self.messages_area, 1)
        root_layout.addLayout(input_row)

        self._settings.sig_setting_changed.connect(self._on_setting_changed)
        self._append_message(
            "assistant",
            "我可以根据当前实验设置生成 experiment、session 和步骤队列草案。",
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

        messages = build_experiment_ai_messages(
            self.view_model.snapshot(),
            self._conversation,
        )
        worker = ExperimentAiRequestWorker(client, messages)
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
        self.status_label.setText("正在生成...")
        self._refresh_send_state()
        thread.start()

    def _on_ai_reply(self, reply: object) -> None:
        if not isinstance(reply, ExperimentAiReply):
            self._on_ai_failed("AI 响应格式不正确")
            return
        self._append_message("assistant", reply.message)
        self._conversation.append({"role": "assistant", "content": reply.message})
        if reply.proposal is not None:
            self._append_proposal(reply.proposal)
        self.status_label.setText("已生成建议。")

    def _on_ai_failed(self, message: str) -> None:
        self._append_message("error", f"请求失败：{message}")
        self.status_label.setText("生成失败。")

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
        if self._config.is_configured:
            self.status_label.setText(f"已配置 {self._config.model}。")
        else:
            self.status_label.setText("未配置 AI 助手。请在设置页填写 base URL、API key 和 model。")
        self._refresh_send_state()

    def _refresh_send_state(self) -> None:
        can_send = (
            self._config.is_configured
            and self._request_thread is None
            and bool(self.input.text().strip())
        )
        self.input.setEnabled(self._config.is_configured and self._request_thread is None)
        self.send_button.setEnabled(can_send)

    def _append_message(self, role: str, text: str) -> None:
        row = QFrame(self.messages_widget)
        row.setObjectName(f"experiment-ai-message-{role}")
        row.setProperty("role", role)
        row_layout = QVBoxLayout(row)
        row_layout.setContentsMargins(10, 8, 10, 8)
        row_layout.setSpacing(4)

        role_label = CaptionLabel(self._role_title(role), row)
        body_label = BodyLabel(text, row)
        body_label.setWordWrap(True)

        row_layout.addWidget(role_label)
        row_layout.addWidget(body_label)
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, row)
        self._scroll_messages_to_bottom()

    def _append_proposal(self, proposal: ExperimentAiProposal) -> None:
        proposal_card = QFrame(self.messages_widget)
        proposal_card.setObjectName("experiment-ai-proposal")
        proposal_card.setProperty("role", "proposal")
        layout = QVBoxLayout(proposal_card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        title = CaptionLabel("待应用草案", proposal_card)
        summary = BodyLabel(self._proposal_summary(proposal), proposal_card)
        summary.setWordWrap(True)

        apply_button = PushButton("应用到实验设置", proposal_card)
        apply_button.setIcon(FIF.ACCEPT)
        apply_button.clicked.connect(lambda: self._apply_proposal(proposal))
        self.latest_proposal_button = apply_button

        layout.addWidget(title)
        layout.addWidget(summary)
        layout.addWidget(apply_button)
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, proposal_card)
        self._scroll_messages_to_bottom()

    def _apply_proposal(self, proposal: ExperimentAiProposal) -> None:
        if proposal.experiment_name is not None:
            self.view_model.set_experiment_name(proposal.experiment_name)
        if proposal.session_name is not None:
            self.view_model.set_session_name(proposal.session_name)
        if proposal.steps is not None:
            self.view_model.set_steps_text("\n".join(proposal.steps))
        self.status_label.setText("草案已应用到实验设置。")

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

    @staticmethod
    def _proposal_summary(proposal: ExperimentAiProposal) -> str:
        lines: list[str] = []
        if proposal.experiment_name is not None:
            lines.append(f"Experiment: {proposal.experiment_name}")
        if proposal.session_name is not None:
            lines.append(f"Session: {proposal.session_name}")
        if proposal.steps is not None:
            preview = ", ".join(proposal.steps[:6])
            if len(proposal.steps) > 6:
                preview += " ..."
            lines.append(f"Steps: {preview if preview else '空'}")
        return "\n".join(lines) if lines else "没有可应用字段。"


class LiveExperimentSidebar(SimpleCardWidget):
    sig_close_requested = pyqtSignal()

    def __init__(
        self,
        view_model: ExperimentRuntimeViewModel,
        settings: QtSettingsBridge,
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

        self.scroll_area = SingleDirectionScrollArea(self, orient=Qt.Orientation.Vertical)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setSmoothMode(SmoothMode.LINEAR)
        self.scroll_area.smoothScroll.setDynamicEngineEnabled(True)
        self.scroll_area.smoothScroll.widthThreshold = 0
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

        controls_row = QHBoxLayout()
        controls_row.setContentsMargins(0, 0, 0, 0)
        controls_row.setSpacing(8)

        self.prev_button = PushButton("Prev", self.scroll_widget)
        self.prev_button.clicked.connect(self.view_model.prev_step)

        self.next_button = PushButton("Next", self.scroll_widget)
        self.next_button.clicked.connect(self.view_model.next_step)

        controls_row.addStretch(1)
        controls_row.addWidget(self.prev_button)
        controls_row.addWidget(self.next_button)

        self.ai_chat_panel = ExperimentAiChatPanel(
            self.view_model,
            self.settings,
            self.scroll_widget,
        )

        content_layout.addWidget(self.current_step_card)
        content_layout.addLayout(controls_row)
        content_layout.addWidget(self.ai_chat_panel, 1)
        content_layout.addStretch(1)

        root_layout.addLayout(header_row)
        root_layout.addWidget(self.scroll_area, 1)

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
        self.current_step_position_label.setText(
            f"第 {current_position} / {len(snapshot.steps)} 步"
        )

        self.prev_button.setEnabled(snapshot.can_go_previous)
        self.next_button.setEnabled(snapshot.can_go_next)


__all__ = ["ExperimentAiChatPanel", "LiveExperimentSidebar"]
