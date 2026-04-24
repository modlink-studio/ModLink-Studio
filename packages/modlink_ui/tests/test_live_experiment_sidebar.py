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

from modlink_core.settings import SettingsStore, declare_core_settings
from modlink_sdk import StreamDescriptor
from modlink_ui.bridge import QtSettingsBridge
from modlink_ui.features.live import LivePage


class _BusStub(QObject):
    sig_frame = pyqtSignal(object)

    def __init__(self) -> None:
        super().__init__()
        self._descriptors: dict[str, StreamDescriptor] = {}

    def descriptor(self, stream_id: str) -> StreamDescriptor | None:
        return self._descriptors.get(stream_id)

    def descriptors(self) -> dict[str, StreamDescriptor]:
        return dict(self._descriptors)


class _RecordingStub(QObject):
    sig_state_changed = pyqtSignal(str)
    sig_error = pyqtSignal(str)
    sig_recording_failed = pyqtSignal(object)
    sig_recording_completed = pyqtSignal(object)

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

    def start_recording(self, _recording_label: str | None = None) -> None:
        self._is_recording = True

    def stop_recording(self) -> None:
        self._is_recording = False

    def add_marker(self, _label: str | None = None) -> None:
        return None

    def add_segment(self, *, start_ns: int, end_ns: int, label: str | None = None) -> None:
        _ = (start_ns, end_ns, label)
        return None


class _EngineStub:
    def __init__(self, bus: _BusStub, settings: QtSettingsBridge, recording: _RecordingStub) -> None:
        self.bus = bus
        self.settings = settings
        self.recording = recording


class LiveExperimentSidebarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        test_tmp_root = WORKSPACE_ROOT / ".tmp-tests"
        test_tmp_root.mkdir(exist_ok=True)
        self._temp_dir = test_tmp_root / f"live-experiment-{uuid4().hex}"
        self._temp_dir.mkdir()
        settings = SettingsStore(path=self._temp_dir / "live-experiment-settings.json")
        declare_core_settings(settings)
        settings.storage.root_dir = str(self._temp_dir)
        self._settings_bridge = QtSettingsBridge(settings)
        self._engine = _EngineStub(_BusStub(), self._settings_bridge, _RecordingStub(self._temp_dir))

    def tearDown(self) -> None:
        shutil.rmtree(self._temp_dir, ignore_errors=True)

    def _pump_events(self) -> None:
        for _ in range(5):
            self._app.processEvents()

    def _create_page(self) -> LivePage:
        page = LivePage(self._engine)
        page.resize(1200, 900)
        page.show()
        self._pump_events()
        return page

    def test_header_action_toggles_sidebar_visibility(self) -> None:
        page = self._create_page()
        self.assertFalse(page.experiment_sidebar.isVisible())

        page.experiment_sidebar_toggle_button.click()
        self._pump_events()
        self.assertTrue(page.experiment_sidebar.isVisible())

        page.experiment_sidebar_toggle_button.click()
        self._pump_events()
        self.assertFalse(page.experiment_sidebar.isVisible())
        page.close()

    def test_sidebar_updates_suggested_label_when_current_step_changes(self) -> None:
        page = self._create_page()
        page.experiment_sidebar_toggle_button.click()
        self._pump_events()

        page.experiment_sidebar.session_name_input.setText("healthy_H03")
        page.experiment_sidebar.steps_editor.setPlainText("0ml\n5ml")
        self._pump_events()

        self.assertEqual(
            "healthy_H03__0ml__step01",
            page.experiment_sidebar.suggested_label_label.text(),
        )
        self.assertEqual("第 1 / 2 步", page.experiment_sidebar.current_step_position_label.text())

        page.experiment_sidebar.next_button.click()
        self._pump_events()

        self.assertEqual(
            "healthy_H03__5ml__step02",
            page.experiment_sidebar.suggested_label_label.text(),
        )
        self.assertEqual("第 2 / 2 步", page.experiment_sidebar.current_step_position_label.text())
        page.close()

    def test_fill_button_writes_suggested_label_into_recording_label_field(self) -> None:
        page = self._create_page()
        page.experiment_sidebar_toggle_button.click()
        self._pump_events()

        page.experiment_sidebar.session_name_input.setText("patient_P07")
        page.experiment_sidebar.steps_editor.setPlainText("15ml")
        self._pump_events()
        page.experiment_sidebar.fill_button.click()
        self._pump_events()

        self.assertEqual(
            "patient_P07__15ml__step01",
            page.acquisition_panel.view_model.get_field_value("recording_label"),
        )
        page.close()

    def test_sidebar_can_float_without_covering_acquisition_panel(self) -> None:
        page = self._create_page()
        page.experiment_sidebar_toggle_button.click()
        self._pump_events()

        self.assertTrue(page.acquisition_panel.isVisible())
        self.assertTrue(page.experiment_sidebar.isVisible())
        self.assertLess(page.experiment_sidebar.geometry().bottom(), page.acquisition_panel.geometry().top())
        page.close()


if __name__ == "__main__":
    unittest.main()
