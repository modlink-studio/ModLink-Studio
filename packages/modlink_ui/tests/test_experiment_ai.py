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
    OpenAICompatibleExperimentClient,
    parse_experiment_ai_content,
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
    def test_client_posts_openai_compatible_payload_and_parses_proposal(self) -> None:
        calls: list[dict[str, object]] = []

        def post(url: str, **kwargs: object) -> _Response:
            calls.append({"url": url, **kwargs})
            content = json.dumps(
                {
                    "message": "已生成实验设置草案。",
                    "proposal": {
                        "experiment_name": "swallow_study",
                        "session_name": "healthy_H03",
                        "steps": ["0ml", "5ml"],
                    },
                },
                ensure_ascii=False,
            )
            return _Response({"choices": [{"message": {"content": content}}]})

        client = OpenAICompatibleExperimentClient(
            AiAssistantConfig(
                base_url="https://api.example.com/v1/",
                api_key="secret-key",
                model="gpt-test",
            ),
            post=post,
        )
        reply = client.complete([{"role": "user", "content": "生成吞咽实验"}])

        self.assertEqual("https://api.example.com/v1/chat/completions", calls[0]["url"])
        self.assertEqual("Bearer secret-key", calls[0]["headers"]["Authorization"])
        self.assertEqual("gpt-test", calls[0]["json"]["model"])
        self.assertEqual(0.2, calls[0]["json"]["temperature"])
        self.assertEqual("已生成实验设置草案。", reply.message)
        self.assertIsNotNone(reply.proposal)
        assert reply.proposal is not None
        self.assertEqual("swallow_study", reply.proposal.experiment_name)
        self.assertEqual("healthy_H03", reply.proposal.session_name)
        self.assertEqual(("0ml", "5ml"), reply.proposal.steps)

    def test_non_json_model_content_falls_back_to_plain_message(self) -> None:
        reply = parse_experiment_ai_content("先设置 session，再填写步骤。")

        self.assertEqual("先设置 session，再填写步骤。", reply.message)
        self.assertIsNone(reply.proposal)

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

        with self.assertRaisesRegex(RuntimeError, "无法连接 AI 服务"):
            client.complete([{"role": "user", "content": "test"}])


if __name__ == "__main__":
    unittest.main()
