from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from modlink_studio_qml.app import _shutdown_bridge, main


def test_shutdown_bridge_shows_error_dialog_on_failure() -> None:
    bridge = Mock()
    bridge.shutdown.side_effect = RuntimeError("boom")

    with patch("modlink_studio_qml.app.traceback.print_exc") as print_exc:
        with patch("modlink_studio_qml.app._show_shutdown_error") as critical:
            _shutdown_bridge(bridge)

    print_exc.assert_called_once()
    critical.assert_called_once()


def test_main_wires_qml_app_entry() -> None:
    class _Signal:
        def __init__(self) -> None:
            self.callback = None

        def connect(self, callback) -> None:
            self.callback = callback

    app = Mock()
    app.aboutToQuit = _Signal()
    app.exec.return_value = 17

    qml_engine = Mock()
    controller = Mock()

    with patch("modlink_studio_qml.app.create_application", return_value=app):
        with patch(
            "modlink_studio_qml.app.discover_driver_factories",
            return_value=["driver_factory"],
        ) as discover:
            with patch("modlink_studio_qml.app.SettingsService") as settings_cls:
                with patch("modlink_studio_qml.app.ModLinkEngine") as engine_cls:
                    with patch("modlink_studio_qml.app.QtModLinkBridge") as bridge_cls:
                        with patch(
                            "modlink_studio_qml.app.load_window",
                            return_value=(qml_engine, controller),
                        ) as load_window:
                            with pytest.raises(SystemExit) as exc_info:
                                main()

    assert exc_info.value.code == 17
    discover.assert_called_once()
    settings_cls.assert_called_once_with(parent=app)
    engine_cls.assert_called_once()
    bridge_cls.assert_called_once()
    load_window.assert_called_once()
    assert app.aboutToQuit.callback is not None
    qml_engine.setObjectName.assert_called_once_with("modlink-qml-engine")
    controller.setObjectName.assert_called_once_with("modlink-qml-controller")
