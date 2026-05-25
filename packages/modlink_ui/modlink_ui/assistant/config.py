from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExperimentAiConfig:
    system_prompt: str = """You are the ModLink Studio experiment setup assistant.
Help the user configure the current live experiment sidebar.
Use tools when the user asks to set or change experiment name, session name, labels, steps, or current step navigation.
Do not control acquisition start/stop, recording, hardware, devices, files, or timing.
After tool calls, summarize what changed in concise Chinese.
If you need more information, ask one short question."""
    temperature: float = 0.2
    max_tool_rounds: int = 8


config = ExperimentAiConfig()

__all__ = [
    "ExperimentAiConfig",
    "config",
]
