from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

import httpx

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PACKAGE_ROOT.parents[1]
for path in (
    PACKAGE_ROOT,
    WORKSPACE_ROOT / "packages" / "modlink_core",
):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from modlink_ui.features.live.experiment_ai import (
    ExperimentAiToolRunner,
    ExperimentAiToolState,
    OpenAICompatibleExperimentClient,
)
from modlink_ui.shared.ui_settings.ai import AiAssistantConfig


class _Response:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> object:
        return self._payload


class ExperimentAiClientTests(unittest.TestCase):
    def test_client_runs_tool_calls_and_returns_actions(self) -> None:
        calls: list[dict[str, object]] = []
        responses = [
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [
                                {
                                    "id": "call_1",
                                    "type": "function",
                                    "function": {
                                        "name": "set_experiment_name",
                                        "arguments": json.dumps({"value": "swallow_study"}),
                                    },
                                },
                                {
                                    "id": "call_2",
                                    "type": "function",
                                    "function": {
                                        "name": "set_steps",
                                        "arguments": json.dumps({"steps": ["0ml", "5ml"]}),
                                    },
                                },
                            ],
                        }
                    }
                ]
            },
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "已设置实验名称和步骤。",
                        }
                    }
                ]
            },
        ]

        def post(url: str, **kwargs: object) -> _Response:
            calls.append({"url": url, **kwargs})
            return _Response(responses.pop(0))

        client = OpenAICompatibleExperimentClient(
            AiAssistantConfig(
                base_url="https://api.example.com/v1/",
                api_key="secret-key",
                model="gpt-test",
            ),
            post=post,
        )
        runner = ExperimentAiToolRunner(
            ExperimentAiToolState(
                experiment_name="",
                session_name="",
                recording_label="",
                annotation_label="",
                steps=[],
                current_step_index=-1,
            )
        )
        reply = client.complete(
            [{"role": "user", "content": "生成吞咽实验"}],
            tool_runner=runner,
        )

        self.assertEqual("https://api.example.com/v1/chat/completions", calls[0]["url"])
        self.assertEqual("Bearer secret-key", calls[0]["headers"]["Authorization"])
        self.assertEqual("gpt-test", calls[0]["json"]["model"])
        self.assertEqual(0.2, calls[0]["json"]["temperature"])
        self.assertIn("tools", calls[0]["json"])
        self.assertEqual("auto", calls[0]["json"]["tool_choice"])
        second_messages = calls[1]["json"]["messages"]
        self.assertEqual("tool", second_messages[-2]["role"])
        self.assertEqual("tool", second_messages[-1]["role"])
        self.assertEqual("已设置实验名称和步骤。", reply.message)
        self.assertEqual(
            ["set_experiment_name", "set_steps"],
            [action.name for action in reply.actions],
        )
        self.assertEqual("swallow_study", runner.state.experiment_name)
        self.assertEqual(["0ml", "5ml"], runner.state.steps)

    def test_request_error_is_reported_as_runtime_error(self) -> None:
        def post(url: str, **_kwargs: object) -> object:
            request = httpx.Request("POST", url)
            raise httpx.ConnectError("connection refused", request=request)

        client = OpenAICompatibleExperimentClient(
            AiAssistantConfig(
                base_url="https://api.example.com/v1",
                api_key="secret-key",
                model="gpt-test",
            ),
            post=post,
        )
        runner = ExperimentAiToolRunner(
            ExperimentAiToolState(
                experiment_name="",
                session_name="",
                recording_label="",
                annotation_label="",
                steps=[],
                current_step_index=-1,
            )
        )

        with self.assertRaisesRegex(RuntimeError, "无法连接 AI 服务"):
            client.complete([{"role": "user", "content": "test"}], tool_runner=runner)


if __name__ == "__main__":
    unittest.main()
