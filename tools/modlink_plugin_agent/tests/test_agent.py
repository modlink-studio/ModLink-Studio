from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

import modlink_plugin_agent.cli as cli_module
from modlink_plugin_agent.agent import PluginAgent, PluginAgentConfig, _code_system_message
from modlink_plugin_agent.client import AiConfig, OpenAICompatibleJsonClient
from modlink_plugin_agent.env import load_agent_env
from modlink_plugin_agent.scaffold import generate_scaffold_project
from modlink_plugin_agent.verifier import VerificationResult, verify_plugin_project
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


def test_openai_client_reports_auth_hint() -> None:
    def post(url: str, **_kwargs: object) -> httpx.Response:
        return httpx.Response(401, request=httpx.Request("POST", url))

    client = OpenAICompatibleJsonClient(
        AiConfig(base_url="https://api.example.test/v1", api_key="bad", model="demo"),
        post=post,
    )

    with pytest.raises(RuntimeError, match="API key"):
        client.complete_json([{"role": "user", "content": "test"}])


def test_dotenv_loader_reads_current_directory(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("MODLINK_TEST_DOTENV_VALUE", raising=False)
    (tmp_path / ".env").write_text(
        'MODLINK_TEST_DOTENV_VALUE="loaded from file"\n', encoding="utf-8"
    )

    load_agent_env(cwd=tmp_path)

    assert os.environ["MODLINK_TEST_DOTENV_VALUE"] == "loaded from file"


def test_dotenv_loader_keeps_existing_environment(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MODLINK_TEST_DOTENV_VALUE", "from real environment")
    (tmp_path / ".env").write_text("MODLINK_TEST_DOTENV_VALUE=from dotenv\n", encoding="utf-8")

    load_agent_env(cwd=tmp_path)

    assert os.environ["MODLINK_TEST_DOTENV_VALUE"] == "from real environment"


def test_python_scaffold_writes_project_tree(tmp_path) -> None:
    result = generate_scaffold_project(_demo_spec(), tmp_path)

    assert result.project_dir == tmp_path / "demo_device"
    pyproject = (result.project_dir / "pyproject.toml").read_text(encoding="utf-8")
    assert 'demo-device = "demo_device.factory:create_driver"' in pyproject
    assert '"modlink-studio>=0.3.0rc1"' in pyproject
    assert '"modlink-sdk"' not in pyproject
    assert (result.project_dir / "demo_device" / "driver.py").exists()
    assert result.spec.as_json()["pluginName"] == "demo_device"


def test_python_scaffold_normalizes_ai_device_id(tmp_path) -> None:
    spec = _demo_spec()
    spec["pluginName"] = "pressure-sensor"
    spec["deviceId"] = "pressure-sensor"

    result = generate_scaffold_project(spec, tmp_path)

    assert result.spec.device_id == "pressure_sensor.01"


def test_python_scaffold_replaces_ai_sdk_dependency(tmp_path) -> None:
    spec = _demo_spec()
    spec["dependencies"] = ["modlink-sdk", "modlink_studio", "pyserial"]

    result = generate_scaffold_project(spec, tmp_path)

    assert result.spec.dependencies == (
        "modlink-studio>=0.3.0rc1",
        "numpy>=2.3.3",
        "pyserial",
    )


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


def test_code_prompt_includes_sdk_dataclass_contracts() -> None:
    prompt = str(_code_system_message()["content"])

    assert "SearchResult requires title" in prompt
    assert "FrameEnvelope requires" in prompt


def test_verifier_uses_quiet_compileall_outside_venv(tmp_path) -> None:
    commands: list[list[str]] = []

    def runner(command, **_kwargs):
        commands.append(command)
        return __import__("subprocess").CompletedProcess(command, 0, "", "")

    result = verify_plugin_project(tmp_path, runner=runner)

    assert result.ok is True
    compile_commands = [command for command in commands if "compileall" in command]
    assert compile_commands
    assert "-q" in compile_commands[0]
    assert "-x" in compile_commands[0]
    pytest_commands = [command for command in commands if command[1:3] == ["-m", "pytest"]]
    assert pytest_commands
    assert "error::pytest.PytestUnhandledThreadExceptionWarning" in pytest_commands[0]


def test_workspace_rejects_edits_outside_project(tmp_path) -> None:
    project_dir = tmp_path / "demo_device"
    project_dir.mkdir()

    with pytest.raises(ValueError):
        apply_file_edits(project_dir, "demo_device", [FileEdit("../escape.py", "")])
    with pytest.raises(ValueError):
        apply_file_edits(project_dir, "demo_device", [FileEdit("setup.py", "")])


def test_cli_reports_missing_ai_config(monkeypatch) -> None:
    monkeypatch.setattr(cli_module, "load_agent_env", lambda: None)
    for key in ("MODLINK_AI_BASE_URL", "MODLINK_AI_MODEL", "MODLINK_AI_API_KEY"):
        monkeypatch.delenv(key, raising=False)

    runner = CliRunner()
    result = runner.invoke(cli_module.app, ["generate", "demo device", "--out", "."])

    assert result.exit_code != 0
    assert "Missing AI configuration" in result.output


def test_cli_reports_agent_error_without_traceback(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(cli_module, "load_agent_env", lambda: None)
    monkeypatch.setenv("MODLINK_AI_BASE_URL", "https://api.example.test/v1")
    monkeypatch.setenv("MODLINK_AI_MODEL", "demo")
    monkeypatch.setenv("MODLINK_AI_API_KEY", "secret")

    def fail_generate(self, _description: str) -> object:
        raise RuntimeError("AI service returned HTTP 401. Check the API key value.")

    monkeypatch.setattr(cli_module.PluginAgent, "generate", fail_generate)

    runner = CliRunner()
    result = runner.invoke(
        cli_module.app,
        ["generate", "demo device", "--out", str(tmp_path), "--json"],
    )

    assert result.exit_code != 0
    assert '"ok": false' in result.output
    assert "AI service returned HTTP 401" in result.output
    assert "Traceback" not in result.output


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
