from __future__ import annotations

from dataclasses import dataclass

from modlink_plugin_manager import cli


@dataclass
class _FakeDistribution:
    name: str
    version: str


@dataclass
class _FakeEntryPoint:
    name: str
    dist: _FakeDistribution


def _manifest_payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "plugins": [
            {
                "plugin_id": "host-camera",
                "distribution": "modlink-plugin-host-camera",
                "display_name": "Host Camera",
                "summary": "Camera capture driver for local webcam devices.",
                "releases": [
                    {
                        "version": "0.2.0rc2",
                        "host_version_spec": ">=0.2.0rc2,<0.3.0",
                        "wheel_url": "https://example.invalid/host-camera-0.2.0rc2.whl",
                    }
                ],
            },
            {
                "plugin_id": "host-microphone",
                "distribution": "modlink-plugin-host-microphone",
                "display_name": "Host Microphone",
                "summary": "Microphone capture driver for local audio input devices.",
                "releases": [
                    {
                        "version": "0.2.0rc2",
                        "host_version_spec": ">=0.2.0rc2,<0.3.0",
                        "wheel_url": "https://example.invalid/host-microphone-0.2.0rc2.whl",
                    }
                ],
            },
        ],
    }


def test_list_shows_available_plugins(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "_load_manifest", lambda: cli._parse_manifest(_manifest_payload()))

    exit_code = cli.main(["list"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "host-camera" in output
    assert "host-microphone" in output


def test_list_installed_shows_all_detected_plugins(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "entry_points",
        lambda *, group: [
            _FakeEntryPoint("host-camera", _FakeDistribution("modlink-plugin-host-camera", "0.2.0rc2")),
            _FakeEntryPoint("custom-eeg", _FakeDistribution("my-eeg-plugin", "1.2.3")),
        ],
    )

    exit_code = cli.main(["list", "--installed"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "host-camera" in output
    assert "custom-eeg" in output
    assert "my-eeg-plugin" in output


def test_list_installed_reports_none_for_empty_environment(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "entry_points", lambda *, group: [])

    exit_code = cli.main(["list", "--installed"])

    assert exit_code == 0
    assert "- none" in capsys.readouterr().out


def test_status_reports_official_and_third_party_plugins(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "_host_version", lambda: "0.2.0rc2")
    monkeypatch.setattr(cli, "_load_manifest", lambda: cli._parse_manifest(_manifest_payload()))
    monkeypatch.setattr(
        cli,
        "entry_points",
        lambda *, group: [
            _FakeEntryPoint("host-camera", _FakeDistribution("modlink-plugin-host-camera", "0.2.0rc2")),
            _FakeEntryPoint("custom-eeg", _FakeDistribution("my-eeg-plugin", "1.2.3")),
        ],
    )

    exit_code = cli.main(["status"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Installed" in output
    assert "Available" in output
    assert "source=official" in output
    assert "source=third-party" in output
    assert "host-microphone" in output


def test_install_downloads_latest_compatible_release_and_runs_pip(monkeypatch, tmp_path, capsys) -> None:
    pip_calls: list[tuple[str, ...]] = []

    monkeypatch.setattr(cli, "_host_version", lambda: "0.2.1")
    monkeypatch.setattr(
        cli,
        "_load_manifest",
        lambda: cli._parse_manifest(
            {
                "schema_version": 1,
                "plugins": [
                    {
                        "plugin_id": "host-camera",
                        "distribution": "modlink-plugin-host-camera",
                        "display_name": "Host Camera",
                        "summary": "Camera capture driver for local webcam devices.",
                        "releases": [
                            {
                                "version": "0.2.0rc2",
                                "host_version_spec": ">=0.2.0rc2,<0.2.1",
                                "wheel_url": "https://example.invalid/old.whl",
                            },
                            {
                                "version": "0.2.1",
                                "host_version_spec": ">=0.2.1,<0.3.0",
                                "wheel_url": "https://example.invalid/new.whl",
                            },
                        ],
                    }
                ],
            }
        ),
    )
    monkeypatch.setattr(cli, "_download_wheel", lambda _url, _dir: tmp_path / "new.whl")
    monkeypatch.setattr(cli, "_run_pip", lambda *args: pip_calls.append(args))

    exit_code = cli.main(["install", "host-camera"])

    assert exit_code == 0
    assert pip_calls == [("install", str(tmp_path / "new.whl"))]
    assert "Installed Host Camera 0.2.1." in capsys.readouterr().out


def test_uninstall_supports_third_party_plugins(monkeypatch, capsys) -> None:
    pip_calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(
        cli,
        "entry_points",
        lambda *, group: [
            _FakeEntryPoint("custom-eeg", _FakeDistribution("my-eeg-plugin", "1.2.3")),
        ],
    )
    monkeypatch.setattr(cli, "_run_pip", lambda *args: pip_calls.append(args))

    exit_code = cli.main(["uninstall", "custom-eeg"])

    assert exit_code == 0
    assert pip_calls == [("uninstall", "-y", "my-eeg-plugin")]
    assert "Uninstalled my-eeg-plugin 1.2.3." in capsys.readouterr().out


def test_manifest_uses_cache_when_network_fetch_fails(monkeypatch, tmp_path) -> None:
    cache_path = tmp_path / "plugin-index.json"
    cache_path.write_text(
        '{"schema_version": 1, "plugins": [{"plugin_id": "host-camera", "distribution": "modlink-plugin-host-camera", "display_name": "Host Camera", "summary": "Camera", "releases": [{"version": "0.2.0rc2", "host_version_spec": ">=0.2.0rc2,<0.3.0", "wheel_url": "https://example.invalid/host-camera.whl"}]}]}',
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "_cache_path", lambda: cache_path)
    monkeypatch.setattr(cli, "_fetch_json", lambda _url: (_ for _ in ()).throw(RuntimeError("boom")))

    manifest = cli._load_manifest()

    assert manifest[0].plugin_id == "host-camera"


def test_manifest_url_can_be_overridden(monkeypatch) -> None:
    monkeypatch.setenv(cli.PLUGIN_INDEX_URL_ENV, "https://example.invalid/plugins.json")

    assert cli._manifest_url() == "https://example.invalid/plugins.json"
