from __future__ import annotations

from pathlib import Path

import pytest
from modlink_studio import app


class _FakeSignal:
    def __init__(self) -> None:
        self._callbacks: list[object] = []

    def connect(self, callback) -> None:
        self._callbacks.append(callback)


class _FakeApplication:
    def __init__(self, argv: list[str]) -> None:
        self.argv = argv
        self.aboutToQuit = _FakeSignal()

    def setApplicationName(self, _name: str) -> None:
        pass

    def setOrganizationName(self, _name: str) -> None:
        pass

    def setWindowIcon(self, _icon: object) -> None:
        pass

    def processEvents(self) -> None:
        pass

    def exec(self) -> int:
        return 0


class _FakeWindow:
    def __init__(self, *, engine) -> None:
        self.engine = engine
        self.window_icon = None
        self.was_shown = False

    def setWindowIcon(self, icon) -> None:
        self.window_icon = icon

    def show(self) -> None:
        self.was_shown = True


class _FakeSplash:
    def __init__(self) -> None:
        self.was_finished = False

    def finish(self) -> None:
        self.was_finished = True


def test_debug_main_passes_debug_logging_and_qt_args(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def _fake_configure_host_logging(**kwargs):
        captured["logging_kwargs"] = kwargs
        return tmp_path / "modlink-studio.log"

    def _fake_qapplication(argv):
        fake_app = _FakeApplication(list(argv))
        captured["app"] = fake_app
        return fake_app

    def _fake_engine(*, parent):
        captured["engine_parent"] = parent
        return "runtime"

    def _fake_bridge(runtime, *, parent):
        captured["bridge_runtime"] = runtime
        captured["bridge_parent"] = parent
        return "bridge"

    def _fake_window(*, engine):
        window = _FakeWindow(engine=engine)
        captured["window"] = window
        return window

    def _fake_load_runtime_deps():
        return _fake_engine, _fake_bridge, _fake_window

    def _fake_show_splash(_icon: object) -> _FakeSplash:
        splash = _FakeSplash()
        captured["splash"] = splash
        return splash

    monkeypatch.setattr(app, "configure_host_logging", _fake_configure_host_logging)
    monkeypatch.setattr(app, "load_runtime_deps", _fake_load_runtime_deps)
    monkeypatch.setattr(app, "show_splash_screen", _fake_show_splash)
    monkeypatch.setattr(app, "load_app_icon", lambda: "icon")
    monkeypatch.setattr(app, "set_windows_app_user_model_id", lambda: None)
    monkeypatch.setattr(app, "QApplication", _fake_qapplication)

    with pytest.raises(SystemExit) as exc_info:
        app.debug_main(["--log-path", str(tmp_path / "custom.log"), "-style", "fusion"])

    assert exc_info.value.code == 0
    assert captured["logging_kwargs"] == {
        "log_path": tmp_path / "custom.log",
        "log_filename": "modlink-studio.log",
        "debug": True,
    }
    fake_app = captured["app"]
    assert fake_app.argv == ["modlink-studio-debug", "-style", "fusion"]
    assert captured["splash"].was_finished is True
    assert captured["engine_parent"] is fake_app
    assert captured["bridge_runtime"] == "runtime"
    assert captured["bridge_parent"] is fake_app
    assert captured["window"].engine == "bridge"
    assert captured["window"].window_icon == "icon"
    assert captured["window"].was_shown is True
