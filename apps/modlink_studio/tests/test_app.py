from __future__ import annotations

from pathlib import Path

import pytest
from modlink_studio import app
from modlink_studio.startup import RuntimeDeps


class _FakeSignal:
    def __init__(self) -> None:
        self._callbacks: list[object] = []

    def connect(self, callback) -> None:
        self._callbacks.append(callback)


class _FakeApplication:
    def __init__(self) -> None:
        self.aboutToQuit = _FakeSignal()

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


class _FakePyqtgraph:
    def __init__(self, captured: dict[str, object]) -> None:
        self._captured = captured

    def setConfigOptions(self, **kwargs: object) -> None:
        self._captured["pg"] = kwargs


def test_parse_launch_options_keeps_unknown_qt_args() -> None:
    options = app._parse_launch_options(
        ["--log-path", "C:/logs/modlink.log", "-style", "fusion"],
        prog="modlink-studio",
    )

    assert options.log_path == Path("C:/logs/modlink.log")
    assert options.qt_args == ("-style", "fusion")


def test_debug_main_passes_debug_logging_and_qt_args(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}
    fake_app = _FakeApplication()

    def _fake_configure_host_logging(**kwargs):
        captured["logging_kwargs"] = kwargs
        return tmp_path / "modlink-studio.log"

    def _fake_create_application(argv):
        captured["qt_argv"] = list(argv)
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

    def _fake_install_debug_bootstrap() -> None:
        captured["bootstrap"] = 1

    def _fake_set_theme(theme: object) -> None:
        captured["theme"] = theme

    def _fake_load_runtime_deps() -> RuntimeDeps:
        return RuntimeDeps(
            pg=_FakePyqtgraph(captured),
            set_theme=_fake_set_theme,
            theme_auto="auto",
            ModLinkEngine=_fake_engine,
            QtModLinkBridge=_fake_bridge,
            MainWindow=_fake_window,
        )

    def _fake_show_splash(_icon: object) -> None:
        captured["splash_shown"] = True
        return None

    monkeypatch.setattr(app, "configure_host_logging", _fake_configure_host_logging)
    monkeypatch.setattr(app, "_create_application", _fake_create_application)
    monkeypatch.setattr(app, "install_debug_bootstrap", _fake_install_debug_bootstrap)
    monkeypatch.setattr(app, "load_runtime_deps", _fake_load_runtime_deps)
    monkeypatch.setattr(app, "show_splash_screen", _fake_show_splash)
    monkeypatch.setattr(app, "load_app_icon", lambda: "icon")

    with pytest.raises(SystemExit) as exc_info:
        app.debug_main(["--log-path", str(tmp_path / "custom.log"), "-style", "fusion"])

    assert exc_info.value.code == 0
    assert captured["logging_kwargs"] == {
        "log_path": tmp_path / "custom.log",
        "log_filename": "modlink-studio.log",
        "debug": True,
    }
    assert captured["qt_argv"] == ["modlink-studio-debug", "-style", "fusion"]
    assert captured["splash_shown"] is True
    assert captured["engine_parent"] is fake_app
    assert captured["bridge_runtime"] == "runtime"
    assert captured["bridge_parent"] is fake_app
    assert captured["bootstrap"] == 1
    assert captured["pg"] == {"useOpenGL": True}
    assert captured["theme"] == "auto"
    assert captured["window"].engine == "bridge"
    assert captured["window"].window_icon == "icon"
    assert captured["window"].was_shown is True
