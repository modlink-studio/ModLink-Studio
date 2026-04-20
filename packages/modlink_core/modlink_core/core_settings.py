from __future__ import annotations


def declare_core_settings(settings: object) -> None:
    from .settings.spec import SettingsGroup, SettingsStr

    settings.add(
        storage=SettingsGroup(
            root_dir=SettingsStr(default=""),
            export_root_dir=SettingsStr(default=""),
        )
    )
