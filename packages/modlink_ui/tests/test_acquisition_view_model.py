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
):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication

from modlink_core.models import RecordingStopSummary
from modlink_core.settings import SettingsStore, declare_core_settings
from modlink_ui.bridge import QtSettingsBridge
from modlink_ui.features.live.acquisition_view_model import AcquisitionViewModel


class _AcquisitionStub(QObject):
    sig_state_changed = pyqtSignal(str)
    sig_error = pyqtSignal(str)
    sig_recording_failed = pyqtSignal(object)
    sig_recording_completed = pyqtSignal(object)

    def __init__(self, root_dir: Path) -> None:
        super().__init__()
        self._root_dir = root_dir
        self._is_recording = False
        self.started_recording_label: str | None = None
        self.last_marker_label: str | None = None
        self.last_segment: tuple[int, int, str | None] | None = None

    @property
    def root_dir(self) -> Path:
        return self._root_dir

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    def start_recording(self, _recording_label: str | None = None) -> None:
        self.started_recording_label = _recording_label
        self._is_recording = True

    def stop_recording(self) -> None:
        self._is_recording = False

    def add_marker(self, _label: str | None = None) -> None:
        self.last_marker_label = _label
        return None

    def add_segment(self, *, start_ns: int, end_ns: int, label: str | None = None) -> None:
        self.last_segment = (start_ns, end_ns, label)
        return None

    def emit_state(self, state: str) -> None:
        self._is_recording = str(state or "").strip().lower() == "recording"
        self.sig_state_changed.emit(state)

    def emit_completed(self, summary: RecordingStopSummary) -> None:
        self.sig_recording_completed.emit(summary)


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
        settings = SettingsStore(path=self._temp_dir / "acquisition-settings.json")
        declare_core_settings(settings)
        settings.storage.root_dir = str(self._temp_dir)
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

    def test_start_recording_uses_recording_label(self) -> None:
        self._view_model.set_field_value("recording_label", "resting_state")

        self._view_model.request_toggle_recording()

        self.assertEqual("resting_state", self._acquisition.started_recording_label)

    def test_insert_marker_uses_none_when_label_is_empty(self) -> None:
        self._view_model.request_insert_marker()

        self.assertIsNone(self._acquisition.last_marker_label)

    def test_marker_and_segment_use_shared_annotation_label(self) -> None:
        self._view_model.set_field_value("annotation_label", "trial_a")

        self._view_model.request_insert_marker()
        self._view_model.request_toggle_segment()
        self._view_model.request_toggle_segment()

        self.assertEqual("trial_a", self._acquisition.last_marker_label)
        self.assertIsNotNone(self._acquisition.last_segment)
        self.assertEqual("trial_a", self._acquisition.last_segment[2])

    def test_stop_completion_message_uses_stop_summary(self) -> None:
        info_messages: list[str] = []
        self._view_model.sig_info.connect(info_messages.append)

        self._acquisition.emit_state("recording")
        self._view_model.request_toggle_recording()
        self._acquisition.emit_completed(
            RecordingStopSummary(
                recording_id="rec_demo",
                recording_path=str(self._temp_dir / "recordings" / "rec_demo"),
                started_at_ns=1,
                stopped_at_ns=2,
                status="completed",
                frame_counts_by_stream={"demo.video": 12},
            )
        )

        self.assertEqual(
            [
                f"录制已完成。 recording_id=rec_demo，路径：{self._temp_dir / 'recordings' / 'rec_demo'}"
            ],
            info_messages,
        )


if __name__ == "__main__":
    unittest.main()
