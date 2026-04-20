from __future__ import annotations

from pathlib import Path

import pytest
from PyQt6.QtCore import QCoreApplication, QObject, pyqtSignal

from modlink_core.events import SettingChangedEvent
from modlink_core.settings import SettingsStore, declare_core_settings
from modlink_qt_bridge import QtSettingsBridge
from modlink_ui_qt_qml.acquisition import AcquisitionController
from modlink_ui_qt_qml.settings_page import SettingsPageController


class _RecordingStub(QObject):
    sig_state_changed = pyqtSignal(str)
    sig_error = pyqtSignal(str)
    sig_recording_failed = pyqtSignal(object)
    sig_recording_completed = pyqtSignal(object)

    def __init__(self) -> None:
        super().__init__()
        self._is_recording = False
        self.started_label: str | None = None

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    def start_recording(self, recording_label: str | None = None) -> None:
        self.started_label = recording_label
        self._is_recording = True

    def stop_recording(self) -> None:
        self._is_recording = False

    def add_marker(self, label: str | None = None) -> None:
        _ = label

    def add_segment(self, *, start_ns: int, end_ns: int, label: str | None = None) -> None:
        _ = (start_ns, end_ns, label)


class _EngineStub:
    def __init__(self, settings: QtSettingsBridge, recording: _RecordingStub | None = None) -> None:
        self.settings = settings
        self.recording = recording or _RecordingStub()


@pytest.fixture(scope="module")
def qapp() -> QCoreApplication:
    app = QCoreApplication.instance()
    if app is not None:
        return app
    return QCoreApplication([])


def test_settings_page_controller_uses_storage_settings_root(qapp: QCoreApplication, tmp_path: Path) -> None:
    _ = qapp
    settings = SettingsStore(path=tmp_path / "settings.json")
    declare_core_settings(settings)
    settings.storage.root_dir = str(tmp_path / "data")
    bridge = QtSettingsBridge(settings)
    controller = SettingsPageController(_EngineStub(bridge))
    changes: list[str] = []
    controller.saveDirectoryChanged.connect(lambda: changes.append(controller.saveDirectory))

    assert controller.saveDirectory == str(tmp_path / "data")

    settings.storage.root_dir = str(tmp_path / "next-data")
    bridge._emit_setting_changed(
        SettingChangedEvent(key="storage.root_dir", value=str(tmp_path / "next-data"), ts=0.0)
    )

    assert controller.saveDirectory == str(tmp_path / "next-data")
    assert changes == [str(tmp_path / "next-data")]


def test_acquisition_controller_builds_recordings_output_dir(
    qapp: QCoreApplication, tmp_path: Path
) -> None:
    _ = qapp
    settings = SettingsStore(path=tmp_path / "settings.json")
    declare_core_settings(settings)
    settings.storage.root_dir = str(tmp_path / "data")
    bridge = QtSettingsBridge(settings)
    recording = _RecordingStub()
    controller = AcquisitionController(_EngineStub(bridge, recording))
    changes: list[str] = []
    controller.outputDirectoryChanged.connect(lambda: changes.append(controller.outputDirectory))

    assert controller.outputDirectory == str(tmp_path / "data" / "recordings")

    settings.storage.root_dir = str(tmp_path / "alt-data")
    bridge._emit_setting_changed(
        SettingChangedEvent(key="storage.root_dir", value=str(tmp_path / "alt-data"), ts=0.0)
    )

    assert controller.outputDirectory == str(tmp_path / "alt-data" / "recordings")
    assert changes == [str(tmp_path / "alt-data" / "recordings")]
