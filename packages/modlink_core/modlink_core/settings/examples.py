from __future__ import annotations

from pathlib import Path

from modlink_core.storage import StorageSettings
from modlink_core.storage.settings import default_storage_root_dir
from modlink_core.settings import (
    SettingsSpec,
    SettingsStore,
    bool_setting,
    enum_setting,
    int_setting,
    path_setting,
    string_setting,
)


# Example 1: 用接近 JSON 的嵌套结构声明一个独立的 settings 域
DEMO_SETTINGS_SPEC = SettingsSpec(
    namespace="demo",
    schema={
        "enabled": bool_setting(default=False),
        "sample_rate_hz": int_setting(default=30, min_value=1, max_value=1000),
        "label": string_setting(default="experiment-01"),
        "storage": {
            "root_dir": path_setting(),
        },
    },
)


def demo_bind_and_read(tmp_path: Path) -> None:
    settings = SettingsStore(path=tmp_path / "settings.json")
    demo = settings.bind(DEMO_SETTINGS_SPEC)

    # 使用默认值（没有写入 settings 文件时）
    assert demo.enabled is False
    assert demo.sample_rate_hz == 30
    assert demo.label == "experiment-01"
    assert demo.storage.root_dir is None

    # 读写是先改内存
    demo.enabled = True
    demo.sample_rate_hz = 60
    demo.storage.root_dir = tmp_path / "records"
    assert demo.enabled is True
    assert demo.storage.root_dir == (tmp_path / "records").resolve()

    # 显式持久化
    settings.save()


def demo_storage_domain(tmp_path: Path) -> None:
    settings = SettingsStore(path=tmp_path / "settings.json")
    storage_settings = StorageSettings(settings)

    # 读取默认 fallback
    assert storage_settings.storage_root_dir is None
    assert storage_settings.resolved_storage_root_dir() == default_storage_root_dir()

    # 只改内存
    storage_settings.set_storage_root_dir(tmp_path / "custom-data", persist=False)
    assert storage_settings.storage_root_dir == (tmp_path / "custom-data").resolve()

    # 显式落盘
    settings.save()


def demo_raw_key_api(tmp_path: Path) -> None:
    settings = SettingsStore(path=tmp_path / "settings.json")

    # 直接操作底层 key
    settings.set("demo.sample_rate_hz", 120, persist=False)
    settings.set("demo.enabled", True, persist=False)
    settings.set("demo.storage.root_dir", str(tmp_path / "raw"), persist=False)

    # 读值
    assert settings.get("demo.sample_rate_hz") == 120
    assert settings.get("demo.enabled") is True

    # 与 bind 后访问同一份数据
    demo = settings.bind(DEMO_SETTINGS_SPEC)
    assert demo.sample_rate_hz == 120
    assert demo.storage.root_dir == (tmp_path / "raw").resolve()
    settings.save()


def demo_nested_binding() -> SettingsStore:
    # Example of a more structured schema
    spec = SettingsSpec(
        namespace="preview",
        schema={
            "mode": enum_setting(
                values=("off", "simple", "advanced"),
                default="simple",
            ),
            "quality": {
                "width": int_setting(default=1920, min_value=320, max_value=7680),
                "height": int_setting(default=1080, min_value=240, max_value=4320),
            },
        },
    )
    settings = SettingsStore()
    preview = settings.bind(spec)
    assert preview.quality.width == 1920
    assert preview.quality.height == 1080
    assert preview.mode == "simple"
    preview.quality.width = 1280
    preview.mode = "advanced"
    settings.save()
    return settings


def example_defaults() -> None:
    # 也可以用 StorageSettings 的接口读取/写入核心目录设置
    settings = SettingsStore()
    storage = StorageSettings(settings)
    print(storage.resolved_storage_root_dir())  # default location
    print(default_storage_root_dir())  # same as above
    print(storage.recordings_dir())  # <storage_root>/recordings


__all__ = [
    "DEMO_SETTINGS_SPEC",
    "demo_bind_and_read",
    "demo_nested_binding",
    "demo_raw_key_api",
    "demo_storage_domain",
    "example_defaults",
]
