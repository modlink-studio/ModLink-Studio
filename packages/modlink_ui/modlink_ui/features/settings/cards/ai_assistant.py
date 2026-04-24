from __future__ import annotations

from PyQt6.QtWidgets import QLineEdit, QVBoxLayout, QWidget
from qfluentwidgets import (
    CaptionLabel,
    LineEdit,
    MessageBoxBase,
    PushSettingCard,
    StrongBodyLabel,
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


class _AiAssistantField(QWidget):
    def __init__(
        self,
        title: str,
        input_widget: QWidget,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.title_label = CaptionLabel(title, self)
        self.input = input_widget

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(self.title_label)
        layout.addWidget(self.input)


class _AiAssistantSettingsDialog(MessageBoxBase):
    def __init__(
        self,
        settings: QtSettingsBridge,
        parent: QWidget,
    ) -> None:
        super().__init__(parent=parent)
        self._settings = settings

        self.yesButton.setText("保存")
        self.cancelButton.setText("取消")
        self.widget.setMinimumWidth(540)

        self.title_label = StrongBodyLabel("AI 助手", self.widget)
        self.description_label = CaptionLabel(
            "配置 OpenAI-compatible Chat Completions 接口。API key 会明文保存到本机设置文件。",
            self.widget,
        )
        self.description_label.setWordWrap(True)

        self.base_url_input = LineEdit(self.widget)
        self.base_url_input.setPlaceholderText("例如 https://api.openai.com/v1")
        self.base_url_input.setClearButtonEnabled(True)

        self.api_key_input = LineEdit(self.widget)
        self.api_key_input.setPlaceholderText("API key")
        self.api_key_input.setClearButtonEnabled(True)
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)

        self.model_input = LineEdit(self.widget)
        self.model_input.setPlaceholderText("例如 gpt-4.1-mini 或兼容服务的模型名")
        self.model_input.setClearButtonEnabled(True)

        self.base_url_field = _AiAssistantField("Base URL", self.base_url_input, self.widget)
        self.api_key_field = _AiAssistantField("API key", self.api_key_input, self.widget)
        self.model_field = _AiAssistantField("Model", self.model_input, self.widget)

        self.viewLayout.addWidget(self.title_label)
        self.viewLayout.addWidget(self.description_label)
        self.viewLayout.addWidget(self.base_url_field)
        self.viewLayout.addWidget(self.api_key_field)
        self.viewLayout.addWidget(self.model_field)

        self._sync_from_config(load_ai_assistant_config(self._settings))

    def validate(self) -> bool:
        self._settings.ui.ai.base_url = self.base_url_input.text().strip()
        self._settings.ui.ai.api_key = self.api_key_input.text().strip()
        self._settings.ui.ai.model = self.model_input.text().strip()
        self._settings.save()
        return True

    def _sync_from_config(self, config: AiAssistantConfig) -> None:
        self.base_url_input.setText(config.base_url)
        self.api_key_input.setText(config.api_key)
        self.model_input.setText(config.model)


class AiAssistantSettingsCard(PushSettingCard):
    def __init__(
        self,
        settings: QtSettingsBridge,
        parent: QWidget | None = None,
    ) -> None:
        self._settings = settings
        declare_ai_assistant_settings(self._settings)
        if self._settings.path is not None and self._settings.path.exists():
            self._settings.load(ignore_unknown=True)
        config = load_ai_assistant_config(self._settings)

        super().__init__(
            "配置",
            FIF.ROBOT,
            "AI 助手",
            self._content_text(config),
            parent,
        )

        self.button.setFixedWidth(120)
        self.clicked.connect(self._open_dialog)
        self._settings.sig_setting_changed.connect(self._on_setting_changed)
        self._refresh_content()

    def _open_dialog(self) -> None:
        dialog = _AiAssistantSettingsDialog(self._settings, self.window())
        dialog.finished.connect(lambda _code: self._refresh_content())
        dialog.open()

    def _on_setting_changed(self, event: object) -> None:
        if getattr(event, "key", None) not in {
            UI_AI_BASE_URL_KEY,
            UI_AI_API_KEY_KEY,
            UI_AI_MODEL_KEY,
        }:
            return
        self._refresh_content()

    def _refresh_content(self) -> None:
        config = load_ai_assistant_config(self._settings)
        self.setContent(self._content_text(config))

    @classmethod
    def _content_text(cls, config: AiAssistantConfig) -> str:
        if config.is_configured:
            return f"已配置 {config.model} @ {cls._format_base_url(config.base_url)}"
        return "未配置。需要 base URL、API key 和 model。"

    @staticmethod
    def _format_base_url(base_url: str, max_length: int = 34) -> str:
        if len(base_url) <= max_length:
            return base_url
        return f"{base_url[:16]}...{base_url[-15:]}"


__all__ = ["AiAssistantSettingsCard"]
