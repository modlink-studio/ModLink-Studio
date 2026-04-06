from __future__ import annotations

import logging

from modlink_core.settings.service import SettingsService


def test_settings_service_backs_up_invalid_json_and_logs_warning(tmp_path, caplog) -> None:
    path = tmp_path / "settings.json"
    path.write_text('{"ui": invalid}', encoding="utf-8")

    with caplog.at_level(logging.WARNING):
        settings = SettingsService(path=path)

    assert settings.snapshot() == {}
    assert path.read_text(encoding="utf-8") == '{"ui": invalid}'

    backups = list(tmp_path.glob("settings.json.corrupt-*.json"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == '{"ui": invalid}'
    assert "invalid JSON" in caplog.text
    assert str(path) in caplog.text
