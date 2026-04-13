from __future__ import annotations

import os
import shutil
import sys
import unittest
from pathlib import Path
from uuid import uuid4

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PACKAGE_ROOT.parents[1]
for path in (
    PACKAGE_ROOT,
    WORKSPACE_ROOT / "packages" / "modlink_sdk",
    WORKSPACE_ROOT / "packages" / "modlink_core",
    WORKSPACE_ROOT / "packages" / "modlink_qt_bridge",
):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication

from modlink_core.settings.service import SettingsService
from modlink_qt_bridge import QtSettingsBridge
from modlink_ui_qt_widgets.widgets.main.acquisition.view_model import AcquisitionViewModel


class _AcquisitionStub(QObject):
    sig_state_changed = pyqtSignal(str)
    sig_error = pyqtSignal(str)
    sig_recording_failed = pyqtSignal(object)

    def __init__(self, root_dir: Path) -> None:
        super().__init__()
        self._root_dir = root_dir
        self._is_recording = False

    @property
    def root_dir(self) -> Path:
        return self._root_dir

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    def start_recording(self, _session_name: str, _recording_label: str | None = None) -> None:
        self._is_recording = True

    def stop_recording(self) -> None:
        self._is_recording = False

    def add_marker(self, _label: str | None = None) -> None:
        return None

    def add_segment(self, *, start_ns: int, end_ns: int, label: str | None = None) -> None:
        return None

    def emit_state(self, state: str) -> None:
        self._is_recording = str(state or "").strip().lower() == "recording"
        self.sig_state_changed.emit(state)


class _EngineStub:
    def __init__(self, settings: QtSettingsBridge, recording: _AcquisitionStub) -> None:
        self.settings = settings
        self.recording = recording


class AcquisitionViewModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        test_tmp_root = WORKSPACE_ROOT / ".tmp-tests"
        test_tmp_root.mkdir(exist_ok=True)
        self._temp_dir = test_tmp_root / f"acquisition-vm-{uuid4().hex}"
        self._temp_dir.mkdir()
        settings = SettingsService(self._temp_dir / "acquisition-settings.json")
        self._settings_bridge = QtSettingsBridge(settings)
        self._acquisition = _AcquisitionStub(self._temp_dir)
        self._view_model = AcquisitionViewModel(
            _EngineStub(self._settings_bridge, self._acquisition)
        )

    def tearDown(self) -> None:
        shutil.rmtree(self._temp_dir, ignore_errors=True)

    def test_idle_state_before_recording_does_not_clear_pending_segment(self) -> None:
        segment_state_changes: list[bool] = []
        self._view_model.sig_segment_active_changed.connect(segment_state_changes.append)

        self._view_model.request_toggle_segment()
        self.assertTrue(self._view_model.is_segment_active)

        self._acquisition.emit_state("idle")

        self.assertTrue(self._view_model.is_segment_active)
        self.assertEqual([True], segment_state_changes)

    def test_recording_exit_clears_pending_segment(self) -> None:
        segment_state_changes: list[bool] = []
        self._view_model.sig_segment_active_changed.connect(segment_state_changes.append)

        self._acquisition.emit_state("recording")
        self._view_model.request_toggle_segment()
        self.assertTrue(self._view_model.is_segment_active)

        self._acquisition.emit_state("idle")

        self.assertFalse(self._view_model.is_segment_active)
        self.assertEqual([True, False], segment_state_changes)


if __name__ == "__main__":
    unittest.main()
