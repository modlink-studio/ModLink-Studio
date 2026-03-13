from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QStandardPaths


class AppSettingsStore:
    VERSION = 1
    DEFAULT_DISPLAY_SETTINGS = {
        "max_samples": 2000,
        "y_axis_auto": True,
        "y_axis_lower": -100.0,
        "y_axis_upper": 100.0,
        "plot_height": 380,
        "filter_family": "butterworth",
        "filter_order": 4,
        "shared_filter_enabled": False,
        "shared_filter": {
            "mode": "none",
            "low_cut_hz": 1.0,
            "high_cut_hz": 40.0,
            "powerline_mode": "none",
            "notch_width_hz": 4.0,
        },
    }
    DEFAULT_RECORDING_MODE = "clip"

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or self._resolve_path()
        self._payload = self._read_payload()

    def load_display_settings(self) -> dict[str, Any]:
        display = self._section("display")
        return {
            "max_samples": self._as_int(
                display.get("max_samples"),
                self.DEFAULT_DISPLAY_SETTINGS["max_samples"],
                minimum=1,
            ),
            "channel_visibility": self._as_bool_list(display.get("channel_visibility")),
            "y_axis_auto": self._as_bool(
                display.get("y_axis_auto"),
                self.DEFAULT_DISPLAY_SETTINGS["y_axis_auto"],
            ),
            "y_axis_lower": self._as_float(
                display.get("y_axis_lower"),
                self.DEFAULT_DISPLAY_SETTINGS["y_axis_lower"],
            ),
            "y_axis_upper": self._as_float(
                display.get("y_axis_upper"),
                self.DEFAULT_DISPLAY_SETTINGS["y_axis_upper"],
            ),
            "plot_height": self._as_int(
                display.get("plot_height"),
                self.DEFAULT_DISPLAY_SETTINGS["plot_height"],
                minimum=260,
            ),
            "filter_family": str(display.get("filter_family", self.DEFAULT_DISPLAY_SETTINGS["filter_family"])).strip().lower() or self.DEFAULT_DISPLAY_SETTINGS["filter_family"],
            "filter_order": self._as_int(
                display.get("filter_order"),
                self.DEFAULT_DISPLAY_SETTINGS["filter_order"],
                minimum=1,
            ),
            "shared_filter_enabled": self._as_bool(
                display.get("shared_filter_enabled"),
                self.DEFAULT_DISPLAY_SETTINGS["shared_filter_enabled"],
            ),
            "shared_filter": self._as_filter_config(display.get("shared_filter")),
            "channel_filters": self._as_filter_config_list(display.get("channel_filters")),
        }

    def save_display_settings(self, settings) -> None:
        self._save_section(
            "display",
            {
                "max_samples": int(settings.max_samples),
                "channel_visibility": list(settings.channel_visibility),
                "y_axis_auto": bool(settings.y_axis_auto),
                "y_axis_lower": float(settings.y_axis_lower),
                "y_axis_upper": float(settings.y_axis_upper),
                "plot_height": int(settings.plot_height),
                "filter_family": str(settings.filter_family),
                "filter_order": int(settings.filter_order),
                "shared_filter_enabled": bool(settings.shared_filter_enabled),
                "shared_filter": settings.shared_filter_config.to_dict(),
                "channel_filters": [
                    config.to_dict() for config in settings.channel_filter_configs
                ],
            },
        )

    def load_recording_settings(self) -> dict[str, Any]:
        recording = self._section("recording")
        return {
            "recording_mode": (
                str(recording.get("recording_mode", self.DEFAULT_RECORDING_MODE)).strip()
                or self.DEFAULT_RECORDING_MODE
            ),
        }

    def save_recording_settings(self, settings) -> None:
        self._save_section(
            "recording",
            {"recording_mode": str(settings.recording_mode.value)},
        )

    def load_labels(self, default_labels: list[str]) -> list[str]:
        labels_section = self._section("labels")
        labels = self._as_str_list(labels_section.get("items"))
        return labels or list(default_labels)

    def save_labels(self, labels: list[str]) -> None:
        self._save_section("labels", {"items": self._normalize_labels(labels)})

    def load_default_save_dir(self, default_dir: str) -> str:
        storage = self._section("storage")
        save_dir = str(storage.get("default_save_dir", "")).strip()
        return save_dir or default_dir

    def save_default_save_dir(self, save_dir: str) -> None:
        normalized = str(Path(save_dir).expanduser()).strip()
        self._save_section("storage", {"default_save_dir": normalized})

    def _section(self, key: str) -> dict[str, Any]:
        value = self._payload.get(key, {})
        return value if isinstance(value, dict) else {}

    def _read_payload(self) -> dict[str, Any]:
        try:
            if not self._path.exists():
                return {"version": self.VERSION}

            payload = json.loads(self._path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                payload.setdefault("version", self.VERSION)
                return payload
        except (OSError, json.JSONDecodeError):
            pass

        return {"version": self.VERSION}

    def _write_payload(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._payload["version"] = self.VERSION
        self._path.write_text(
            json.dumps(self._payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _save_section(self, key: str, value: dict[str, Any]) -> None:
        self._payload[key] = value
        self._write_payload()

    def _resolve_path(self) -> Path:
        base_dir = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppDataLocation
        )
        if not base_dir:
            return Path.home() / ".openbciganglionui" / "app_settings.json"
        return Path(base_dir) / "app_settings.json"

    def _as_bool(self, value: Any, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "on"}:
                return True
            if normalized in {"false", "0", "no", "off"}:
                return False
        return default

    def _as_int(self, value: Any, default: int, minimum: int | None = None) -> int:
        try:
            normalized = int(value)
        except (TypeError, ValueError):
            normalized = default
        if minimum is not None:
            normalized = max(minimum, normalized)
        return normalized

    def _as_float(self, value: Any, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _as_bool_list(self, value: Any) -> list[bool]:
        if not isinstance(value, list):
            return []
        return [bool(item) for item in value]

    def _as_filter_config(self, value: Any) -> dict[str, Any]:
        default_config = self.DEFAULT_DISPLAY_SETTINGS["shared_filter"]
        payload = value if isinstance(value, dict) else {}
        return {
            "mode": str(payload.get("mode", default_config["mode"])).strip().lower() or default_config["mode"],
            "low_cut_hz": self._as_positive_float(
                payload.get("low_cut_hz"),
                float(default_config["low_cut_hz"]),
            ),
            "high_cut_hz": self._as_positive_float(
                payload.get("high_cut_hz"),
                float(default_config["high_cut_hz"]),
            ),
            "powerline_mode": str(payload.get("powerline_mode", default_config["powerline_mode"])).strip().lower() or default_config["powerline_mode"],
            "notch_width_hz": self._as_positive_float(
                payload.get("notch_width_hz"),
                float(default_config["notch_width_hz"]),
            ),
        }

    def _as_filter_config_list(self, value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        return [self._as_filter_config(item) for item in value]

    def _as_positive_float(self, value: Any, default: float) -> float:
        try:
            normalized = float(value)
        except (TypeError, ValueError):
            normalized = default
        return max(0.1, normalized)

    def _as_str_list(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return self._normalize_labels(value)

    def _normalize_labels(self, labels: list[Any]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for label in labels:
            text = str(label).strip()
            if not text or text in seen:
                continue
            normalized.append(text)
            seen.add(text)
        return normalized
