from __future__ import annotations

import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from modlink_plugin_agent.agent import PluginAgent, PluginAgentConfig
from modlink_plugin_agent.cli import app
from modlink_plugin_agent.client import AiConfig, OpenAICompatibleJsonClient
from modlink_plugin_agent.scaffold import generate_scaffold_project
from modlink_plugin_agent.verifier import VerificationResult
from modlink_plugin_agent.workspace import FileEdit, apply_file_edits


class _Response:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> object:
        return self._payload


class _FakeClient:
    def __init__(self, responses: list[dict[str, object]]) -> None:
        self.responses = responses
        self.messages: list[object] = []

    def complete_json(self, messages):
        self.messages.append(messages)
        return self.responses.pop(0)


def test_openai_client_returns_json_object() -> None:
    calls: list[dict[str, object]] = []

    def post(url: str, **kwargs: object) -> _Response:
        calls.append({"url": url, **kwargs})
        return _Response(
            {
                "choices": [
                    {
                        "message": {
                            "content": '{"pluginName":"demo-device","providers":["serial"],"streams":[]}'
                        }
                    }
                ]
            }
        )

    client = OpenAICompatibleJsonClient(
        AiConfig(base_url="https://api.example.test/v1", api_key="secret", model="demo"),
        post=post,
    )

    result = client.complete_json([{"role": "user", "content": "test"}])

    assert calls[0]["url"] == "https://api.example.test/v1/chat/completions"
    assert calls[0]["headers"]["Authorization"] == "Bearer secret"
    assert result["pluginName"] == "demo-device"


def test_python_scaffold_writes_project_tree(tmp_path) -> None:
    result = generate_scaffold_project(_demo_spec(), tmp_path)

    assert result.project_dir == tmp_path / "demo_device"
    assert (result.project_dir / "pyproject.toml").read_text(encoding="utf-8").find(
        'demo-device = "demo_device.factory:create_driver"'
    ) != -1
    assert (result.project_dir / "demo_device" / "driver.py").exists()
    assert result.spec.as_json()["pluginName"] == "demo_device"


def test_agent_scaffolds_generates_repairs_and_verifies(tmp_path) -> None:
    project_dir = tmp_path / "demo_device"

    verify_calls = 0

    def fake_verify(_project_dir: Path) -> VerificationResult:
        nonlocal verify_calls
        verify_calls += 1
        if verify_calls == 1:
            return VerificationResult(False, "SyntaxError: bad driver")
        return VerificationResult(True, "pytest passed")

    client = _FakeClient(
        [
            _demo_spec(),
            {
                "files": [
                    {
                        "path": "demo_device/driver.py",
                        "content": "BROKEN",
                    }
                ]
            },
            {
                "files": [
                    {
                        "path": "demo_device/driver.py",
                        "content": "FIXED",
                    }
                ]
            },
        ]
    )
    agent = PluginAgent(
        client=client,
        config=PluginAgentConfig(out_dir=tmp_path, max_repairs=2),
        verify=fake_verify,
    )

    result = agent.generate("serial two-channel pressure sensor")

    assert result.ok is True
    assert result.repairs == 1
    assert verify_calls == 2
    assert (project_dir / "demo_device" / "driver.py").read_text() == "FIXED"


def test_workspace_rejects_edits_outside_project(tmp_path) -> None:
    project_dir = tmp_path / "demo_device"
    project_dir.mkdir()

    with pytest.raises(ValueError):
        apply_file_edits(project_dir, "demo_device", [FileEdit("../escape.py", "")])
    with pytest.raises(ValueError):
        apply_file_edits(project_dir, "demo_device", [FileEdit("setup.py", "")])


def test_cli_reports_missing_ai_config() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["generate", "demo device", "--out", "."])

    assert result.exit_code != 0
    assert "Missing AI configuration" in result.output


def _demo_spec() -> dict[str, object]:
    return {
        "pluginName": "demo-device",
        "displayName": "Demo Device",
        "deviceId": "demo_device.01",
        "providers": ["serial"],
        "dataArrival": "poll",
        "driverKind": "loop",
        "dependencies": [],
        "streams": [
            {
                "streamKey": "pressure",
                "displayName": "Pressure",
                "payloadType": "signal",
                "sampleRateHz": 100,
                "chunkSize": 10,
                "channelNames": ["left", "right"],
                "unit": "kPa",
            }
        ],
    }
