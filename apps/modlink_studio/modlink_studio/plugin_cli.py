from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from . import __version__
from .official_plugins import OFFICIAL_PLUGINS, OfficialPlugin, get_official_plugin

GITHUB_OWNER = "modlink-studio"
GITHUB_REPO = "ModLink-Studio"
GITHUB_API_BASE = "https://api.github.com"


def _parse_version(raw: str) -> tuple[int, ...]:
    parts: list[int] = []
    for chunk in raw.split("."):
        digits = "".join(char for char in chunk if char.isdigit())
        parts.append(int(digits or "0"))
    return tuple(parts)


def _is_version_in_range(version_str: str, plugin: OfficialPlugin) -> bool:
    current = _parse_version(version_str)
    lower = _parse_version(plugin.min_host_version)
    upper = _parse_version(plugin.max_host_version_exclusive)
    return lower <= current < upper


def _installed_version(distribution_name: str) -> str | None:
    try:
        return version(distribution_name)
    except PackageNotFoundError:
        return None


def _normalized_dist_name(distribution_name: str) -> str:
    return distribution_name.replace("-", "_")


def _release_tag_for_host(host_version: str) -> str:
    return f"v{host_version}"


def _fetch_release_payload(tag: str) -> dict[str, object]:
    request = Request(
        f"{GITHUB_API_BASE}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/tags/{tag}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "modlink-studio-plugin",
        },
    )
    with urlopen(request) as response:
        return json.load(response)


def _find_release_asset(plugin: OfficialPlugin, host_version: str, payload: dict[str, object]) -> dict[str, object]:
    expected_prefix = f"{_normalized_dist_name(plugin.distribution)}-{host_version}-"
    for asset in payload.get("assets", []):
        if not isinstance(asset, dict):
            continue
        name = asset.get("name")
        if isinstance(name, str) and name.startswith(expected_prefix) and name.endswith(".whl"):
            return asset
    raise RuntimeError(
        f"Release {_release_tag_for_host(host_version)} does not contain a wheel for {plugin.plugin_id}."
    )


def _download_asset(asset: dict[str, object], target_dir: Path) -> Path:
    url = asset.get("browser_download_url")
    name = asset.get("name")
    if not isinstance(url, str) or not isinstance(name, str):
        raise RuntimeError("Release asset is missing download metadata.")

    target_path = target_dir / name
    request = Request(url, headers={"User-Agent": "modlink-studio-plugin"})
    with urlopen(request) as response:
        target_path.write_bytes(response.read())
    return target_path


def _run_pip(*args: str) -> None:
    subprocess.run([sys.executable, "-m", "pip", *args], check=True)


def _format_plugin_line(plugin: OfficialPlugin, host_version: str) -> str:
    installed = _installed_version(plugin.distribution)
    compatible = "yes" if _is_version_in_range(host_version, plugin) else "no"
    installed_label = installed if installed is not None else "not-installed"
    return (
        f"{plugin.plugin_id:<18} "
        f"installed={installed_label:<14} "
        f"compatible={compatible:<3} "
        f"{plugin.display_name}"
    )


def _cmd_list() -> int:
    for plugin in OFFICIAL_PLUGINS:
        print(f"{plugin.plugin_id:<18} {plugin.display_name} - {plugin.description}")
    return 0


def _cmd_status(host_version: str) -> int:
    print(f"modlink-studio {host_version}")
    for plugin in OFFICIAL_PLUGINS:
        print(_format_plugin_line(plugin, host_version))
    return 0


def _cmd_install(plugin_id: str, host_version: str) -> int:
    plugin = get_official_plugin(plugin_id)
    if not _is_version_in_range(host_version, plugin):
        raise RuntimeError(
            f"{plugin.plugin_id} is not compatible with modlink-studio {host_version}."
        )

    installed = _installed_version(plugin.distribution)
    if installed == host_version:
        print(f"{plugin.display_name} {installed} is already installed.")
        return 0

    tag = _release_tag_for_host(host_version)
    try:
        payload = _fetch_release_payload(tag)
    except HTTPError as exc:
        raise RuntimeError(f"Failed to resolve GitHub release {tag}: HTTP {exc.code}.") from exc
    except URLError as exc:
        raise RuntimeError(f"Failed to resolve GitHub release {tag}: {exc.reason}.") from exc

    asset = _find_release_asset(plugin, host_version, payload)
    with tempfile.TemporaryDirectory(prefix="modlink-plugin-") as temp_dir:
        wheel_path = _download_asset(asset, Path(temp_dir))
        _run_pip("install", str(wheel_path))
    print(f"Installed {plugin.display_name} for modlink-studio {host_version}.")
    return 0


def _cmd_uninstall(plugin_id: str) -> int:
    plugin = get_official_plugin(plugin_id)
    installed = _installed_version(plugin.distribution)
    if installed is None:
        print(f"{plugin.display_name} is not installed.")
        return 0

    _run_pip("uninstall", "-y", plugin.distribution)
    print(f"Uninstalled {plugin.display_name} {installed}.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="modlink-studio-plugin",
        description="Manage official ModLink Studio driver plugins.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="List official driver plugins.")
    subparsers.add_parser("status", help="Show install status for official driver plugins.")

    install_parser = subparsers.add_parser("install", help="Install one official driver plugin.")
    install_parser.add_argument("plugin_id", choices=[plugin.plugin_id for plugin in OFFICIAL_PLUGINS])

    uninstall_parser = subparsers.add_parser(
        "uninstall",
        help="Uninstall one official driver plugin.",
    )
    uninstall_parser.add_argument("plugin_id", choices=[plugin.plugin_id for plugin in OFFICIAL_PLUGINS])
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    host_version = __version__

    if args.command == "list":
        return _cmd_list()
    if args.command == "status":
        return _cmd_status(host_version)
    if args.command == "install":
        return _cmd_install(args.plugin_id, host_version)
    if args.command == "uninstall":
        return _cmd_uninstall(args.plugin_id)
    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
