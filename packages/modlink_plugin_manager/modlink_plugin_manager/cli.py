from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, entry_points, version
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from packaging.specifiers import SpecifierSet
from packaging.version import InvalidVersion, Version
from platformdirs import user_cache_path

PLUGIN_ENTRY_POINT_GROUP = "modlink.drivers"
DEFAULT_PLUGIN_INDEX_URL = "https://modlink-studio.github.io/plugins/index.json"
PLUGIN_INDEX_URL_ENV = "MODLINK_PLUGIN_INDEX_URL"
USER_AGENT = "modlink-plugin"


@dataclass(frozen=True)
class PluginRelease:
    version: str
    host_version_spec: str
    wheel_url: str


@dataclass(frozen=True)
class IndexedPlugin:
    plugin_id: str
    distribution: str
    display_name: str
    summary: str
    releases: tuple[PluginRelease, ...]


@dataclass(frozen=True)
class InstalledPlugin:
    plugin_id: str
    distribution: str
    version: str | None


def _host_version() -> str:
    try:
        return version("modlink-studio")
    except PackageNotFoundError:
        return "0.0.0"


def _manifest_url() -> str:
    return os.environ.get(PLUGIN_INDEX_URL_ENV, DEFAULT_PLUGIN_INDEX_URL)


def _cache_path() -> Path:
    return user_cache_path("modlink-studio") / "plugin-index.json"


def _fetch_json(url: str) -> dict[str, Any]:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    with urlopen(request, timeout=10) as response:
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise RuntimeError("Plugin index must be a JSON object.")
    return payload


def _load_manifest() -> list[IndexedPlugin]:
    cache_path = _cache_path()
    payload: dict[str, Any] | None = None
    fetch_error: str | None = None
    try:
        payload = _fetch_json(_manifest_url())
    except (HTTPError, URLError, TimeoutError, RuntimeError, OSError) as exc:
        fetch_error = str(exc)

    if payload is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
        return _parse_manifest(payload)

    if cache_path.exists():
        cached_payload = json.loads(cache_path.read_text(encoding="utf-8"))
        if not isinstance(cached_payload, dict):
            raise RuntimeError("Cached plugin index is invalid.")
        return _parse_manifest(cached_payload)

    raise RuntimeError(
        "Failed to load plugin index and no cached copy is available."
        if fetch_error is None
        else f"Failed to load plugin index ({fetch_error}) and no cached copy is available."
    )


def _parse_manifest(payload: dict[str, Any]) -> list[IndexedPlugin]:
    schema_version = payload.get("schema_version")
    if schema_version != 1:
        raise RuntimeError(f"Unsupported plugin index schema version: {schema_version!r}")

    plugins = payload.get("plugins")
    if not isinstance(plugins, list):
        raise RuntimeError("Plugin index is missing a valid 'plugins' array.")

    parsed: list[IndexedPlugin] = []
    for item in plugins:
        if not isinstance(item, dict):
            raise RuntimeError("Each plugin entry must be an object.")
        releases_payload = item.get("releases")
        if not isinstance(releases_payload, list):
            raise RuntimeError("Each plugin entry must include a 'releases' array.")

        releases: list[PluginRelease] = []
        for release in releases_payload:
            if not isinstance(release, dict):
                raise RuntimeError("Each plugin release entry must be an object.")
            version_text = release.get("version")
            host_version_spec = release.get("host_version_spec")
            wheel_url = release.get("wheel_url")
            if (
                not isinstance(version_text, str)
                or not isinstance(host_version_spec, str)
                or not isinstance(wheel_url, str)
            ):
                raise RuntimeError("Plugin release entries must include version, host_version_spec, and wheel_url.")
            releases.append(
                PluginRelease(
                    version=version_text,
                    host_version_spec=host_version_spec,
                    wheel_url=wheel_url,
                )
            )

        plugin_id = item.get("plugin_id")
        distribution_name = item.get("distribution")
        display_name = item.get("display_name")
        summary = item.get("summary")
        if (
            not isinstance(plugin_id, str)
            or not isinstance(distribution_name, str)
            or not isinstance(display_name, str)
            or not isinstance(summary, str)
        ):
            raise RuntimeError(
                "Plugin entries must include plugin_id, distribution, display_name, and summary."
            )
        parsed.append(
            IndexedPlugin(
                plugin_id=plugin_id,
                distribution=distribution_name,
                display_name=display_name,
                summary=summary,
                releases=tuple(releases),
            )
        )

    return sorted(parsed, key=lambda item: item.plugin_id)


def _installed_plugins() -> list[InstalledPlugin]:
    installed: list[InstalledPlugin] = []
    for entry_point in sorted(entry_points(group=PLUGIN_ENTRY_POINT_GROUP), key=lambda item: item.name):
        dist = getattr(entry_point, "dist", None)
        distribution_name = getattr(dist, "name", None) or getattr(dist, "metadata", {}).get("Name", "unknown")
        plugin_version = getattr(dist, "version", None)
        installed.append(
            InstalledPlugin(
                plugin_id=entry_point.name,
                distribution=distribution_name,
                version=plugin_version,
            )
        )
    return installed


def _indexed_plugins_by_id(indexed_plugins: list[IndexedPlugin]) -> dict[str, IndexedPlugin]:
    return {plugin.plugin_id: plugin for plugin in indexed_plugins}


def _installed_plugins_by_id(installed_plugins: list[InstalledPlugin]) -> dict[str, InstalledPlugin]:
    return {plugin.plugin_id: plugin for plugin in installed_plugins}


def _distribution_aliases(installed_plugins: list[InstalledPlugin]) -> dict[str, InstalledPlugin]:
    aliases: dict[str, InstalledPlugin] = {}
    for plugin in installed_plugins:
        aliases[plugin.distribution] = plugin
        aliases[plugin.distribution.replace("-", "_")] = plugin
    return aliases


def _select_release(plugin: IndexedPlugin, host_version: str) -> PluginRelease:
    try:
        current = Version(host_version)
    except InvalidVersion as exc:
        raise RuntimeError(f"Invalid modlink-studio version: {host_version!r}") from exc

    compatible: list[PluginRelease] = []
    for release in plugin.releases:
        if current in SpecifierSet(release.host_version_spec):
            compatible.append(release)
    if not compatible:
        raise RuntimeError(f"No compatible release found for {plugin.plugin_id}.")
    return max(compatible, key=lambda item: Version(item.version))


def _download_wheel(url: str, target_dir: Path) -> Path:
    wheel_name = url.rsplit("/", 1)[-1]
    target_path = target_dir / wheel_name
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=30) as response:
        target_path.write_bytes(response.read())
    return target_path


def _run_pip(*args: str) -> None:
    subprocess.run([sys.executable, "-m", "pip", *args], check=True)


def _format_available(plugin: IndexedPlugin, installed: InstalledPlugin | None, host_version: str) -> str:
    try:
        release = _select_release(plugin, host_version)
        availability = f"available={release.version}"
    except RuntimeError:
        availability = "available=none"
    installed_label = installed.version if installed and installed.version else "not-installed"
    return f"{plugin.plugin_id:<18} installed={installed_label:<14} {availability:<18} {plugin.display_name}"


def _format_installed(plugin: InstalledPlugin, indexed_plugin: IndexedPlugin | None, host_version: str) -> str:
    if indexed_plugin is None:
        compatibility = "unknown"
        source = "third-party"
    else:
        try:
            _select_release(indexed_plugin, host_version)
            compatibility = "compatible"
        except RuntimeError:
            compatibility = "unsupported"
        source = "official"
    version_label = plugin.version if plugin.version is not None else "unknown"
    return (
        f"{plugin.plugin_id:<18} version={version_label:<12} "
        f"source={source:<11} compatible={compatibility:<10} dist={plugin.distribution}"
    )


def _cmd_list(show_installed: bool) -> int:
    if show_installed:
        installed_plugins = _installed_plugins()
        if not installed_plugins:
            print("- none")
            return 0
        for plugin in installed_plugins:
            print(f"{plugin.plugin_id:<18} {plugin.distribution} {plugin.version or 'unknown'}")
        return 0

    indexed_plugins = _load_manifest()
    for plugin in indexed_plugins:
        print(f"{plugin.plugin_id:<18} {plugin.display_name} - {plugin.summary}")
    return 0


def _cmd_status() -> int:
    host_version = _host_version()
    indexed_plugins = _load_manifest()
    installed_plugins = _installed_plugins()
    indexed_by_id = _indexed_plugins_by_id(indexed_plugins)
    installed_by_id = _installed_plugins_by_id(installed_plugins)

    print(f"modlink-studio {host_version}")
    print()
    print("Installed")
    if not installed_plugins:
        print("- none")
    else:
        for plugin in installed_plugins:
            print(f"- {_format_installed(plugin, indexed_by_id.get(plugin.plugin_id), host_version)}")

    print()
    print("Available")
    for plugin in indexed_plugins:
        print(f"- {_format_available(plugin, installed_by_id.get(plugin.plugin_id), host_version)}")
    return 0


def _cmd_install(plugin_id: str) -> int:
    host_version = _host_version()
    indexed_plugins = _load_manifest()
    indexed_by_id = _indexed_plugins_by_id(indexed_plugins)
    plugin = indexed_by_id.get(plugin_id)
    if plugin is None:
        raise RuntimeError(f"Plugin '{plugin_id}' is not present in the current plugin index.")

    release = _select_release(plugin, host_version)
    with tempfile.TemporaryDirectory(prefix="modlink-plugin-") as temp_dir:
        wheel_path = _download_wheel(release.wheel_url, Path(temp_dir))
        _run_pip("install", str(wheel_path))
    print(f"Installed {plugin.display_name} {release.version}.")
    return 0


def _cmd_uninstall(plugin_id: str) -> int:
    installed_plugins = _installed_plugins()
    installed_by_id = _installed_plugins_by_id(installed_plugins)
    aliases = _distribution_aliases(installed_plugins)
    plugin = installed_by_id.get(plugin_id) or aliases.get(plugin_id)
    if plugin is None:
        print(f"Plugin '{plugin_id}' is not installed.")
        return 0

    _run_pip("uninstall", "-y", plugin.distribution)
    version_label = plugin.version or "unknown"
    print(f"Uninstalled {plugin.distribution} {version_label}.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="modlink-plugin",
        description="Manage ModLink Studio plugins.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List available plugins or installed plugins.")
    list_parser.add_argument(
        "--installed",
        action="store_true",
        help="List plugins currently installed in this environment.",
    )

    subparsers.add_parser("status", help="Show plugin environment overview.")

    install_parser = subparsers.add_parser("install", help="Install one plugin from the plugin index.")
    install_parser.add_argument("plugin_id")

    uninstall_parser = subparsers.add_parser("uninstall", help="Uninstall one installed plugin.")
    uninstall_parser.add_argument("plugin_id")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "list":
        return _cmd_list(args.installed)
    if args.command == "status":
        return _cmd_status()
    if args.command == "install":
        return _cmd_install(args.plugin_id)
    if args.command == "uninstall":
        return _cmd_uninstall(args.plugin_id)
    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
