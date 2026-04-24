from __future__ import annotations

from dataclasses import dataclass

from modlink_core.settings import SettingsGroup, SettingsStr
from modlink_ui.bridge import QtSettingsBridge

UI_AI_BASE_URL_KEY = "ui.ai.base_url"
UI_AI_API_KEY_KEY = "ui.ai.api_key"
UI_AI_MODEL_KEY = "ui.ai.model"


@dataclass(frozen=True, slots=True)
class AiAssistantConfig:
    base_url: str
    api_key: str
    model: str

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.model)


def normalize_ai_config(base_url: object, api_key: object, model: object) -> AiAssistantConfig:
    return AiAssistantConfig(
        base_url=str(base_url or "").strip(),
        api_key=str(api_key or "").strip(),
        model=str(model or "").strip(),
    )


def declare_ai_assistant_settings(settings: QtSettingsBridge) -> None:
    settings.add(
        ui=SettingsGroup(
            ai=SettingsGroup(
                base_url=SettingsStr(default=""),
                api_key=SettingsStr(default=""),
                model=SettingsStr(default=""),
            )
        )
    )


def load_ai_assistant_config(settings: QtSettingsBridge) -> AiAssistantConfig:
    declare_ai_assistant_settings(settings)
    if settings.path is not None and settings.path.exists():
        settings.load(ignore_unknown=True)
    return normalize_ai_config(
        settings.ui.ai.base_url.value,
        settings.ui.ai.api_key.value,
        settings.ui.ai.model.value,
    )


__all__ = [
    "AiAssistantConfig",
    "UI_AI_API_KEY_KEY",
    "UI_AI_BASE_URL_KEY",
    "UI_AI_MODEL_KEY",
    "declare_ai_assistant_settings",
    "load_ai_assistant_config",
    "normalize_ai_config",
]
