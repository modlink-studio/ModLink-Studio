from __future__ import annotations

from modlink_studio import plugin_cli


def test_list_shows_official_plugins(capsys) -> None:
    exit_code = plugin_cli.main(["list"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "host-camera" in output
    assert "host-microphone" in output
    assert "openbci-ganglion" in output


def test_status_reports_install_state(monkeypatch, capsys) -> None:
    installed_versions = {
        "modlink-plugin-host-camera": "0.2.0rc1",
        "modlink-plugin-host-microphone": None,
        "modlink-plugin-openbci-ganglion": None,
    }

    monkeypatch.setattr(
        plugin_cli,
        "_installed_version",
        lambda distribution_name: installed_versions[distribution_name],
    )
    monkeypatch.setattr(plugin_cli, "__version__", "0.2.0rc1")

    exit_code = plugin_cli.main(["status"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "modlink-studio 0.2.0rc1" in output
    assert "host-camera" in output
    assert "installed=0.2.0rc1" in output
    assert "host-microphone" in output
    assert "not-installed" in output


def test_install_downloads_release_asset_and_runs_pip(monkeypatch, tmp_path, capsys) -> None:
    pip_calls: list[tuple[str, ...]] = []

    monkeypatch.setattr(plugin_cli, "_installed_version", lambda _distribution_name: None)
    monkeypatch.setattr(plugin_cli, "__version__", "0.2.0rc1")
    monkeypatch.setattr(
        plugin_cli,
        "_fetch_release_payload",
        lambda _tag: {
            "assets": [
                {
                    "name": "modlink_plugin_host_camera-0.2.0rc1-py3-none-any.whl",
                    "browser_download_url": "https://example.invalid/modlink_plugin_host_camera.whl",
                }
            ]
        },
    )
    monkeypatch.setattr(
        plugin_cli,
        "_download_asset",
        lambda _asset, _target_dir: tmp_path / "modlink_plugin_host_camera-0.2.0rc1-py3-none-any.whl",
    )
    monkeypatch.setattr(plugin_cli, "_run_pip", lambda *args: pip_calls.append(args))

    exit_code = plugin_cli.main(["install", "host-camera"])

    assert exit_code == 0
    assert pip_calls == [
        (
            "install",
            str(tmp_path / "modlink_plugin_host_camera-0.2.0rc1-py3-none-any.whl"),
        )
    ]
    assert "Installed Host Camera" in capsys.readouterr().out


def test_uninstall_runs_pip_for_installed_plugin(monkeypatch, capsys) -> None:
    pip_calls: list[tuple[str, ...]] = []

    monkeypatch.setattr(
        plugin_cli,
        "_installed_version",
        lambda distribution_name: "0.2.0rc1"
        if distribution_name == "modlink-plugin-host-microphone"
        else None,
    )
    monkeypatch.setattr(plugin_cli, "_run_pip", lambda *args: pip_calls.append(args))

    exit_code = plugin_cli.main(["uninstall", "host-microphone"])

    assert exit_code == 0
    assert pip_calls == [("uninstall", "-y", "modlink-plugin-host-microphone")]
    assert "Uninstalled Host Microphone 0.2.0rc1." in capsys.readouterr().out
