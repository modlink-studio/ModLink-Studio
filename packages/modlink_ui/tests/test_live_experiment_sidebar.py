from __future__ import annotations

import os
import shutil
import sys
import time
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
from modlink_ui.features.live.experiment_ai import ExperimentAiProposal, ExperimentAiReply
from modlink_ui.features.live.experiment_panel import ExperimentAiChatPanel
from modlink_ui.features.live.experiment_runtime import ExperimentRuntimeViewModel
from modlink_ui.shared.ui_settings.ai import declare_ai_assistant_settings


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

    def _pump_until(self, predicate) -> None:
        for _ in range(100):
            self._app.processEvents()
            if predicate():
                return
            time.sleep(0.01)
        self.fail("condition was not reached while pumping Qt events")

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

    def test_sidebar_updates_current_step_when_current_step_changes(self) -> None:
        page = self._create_page()
        page.experiment_sidebar_toggle_button.click()
        self._pump_events()

        page.experiment_runtime.set_session_name("healthy_H03")
        page.experiment_runtime.set_steps_text("0ml\n5ml")
        self._pump_events()

        self.assertEqual("0ml", page.experiment_sidebar.current_step_label.text())
        self.assertEqual("第 1 / 2 步", page.experiment_sidebar.current_step_position_label.text())

        page.experiment_sidebar.next_button.click()
        self._pump_events()

        self.assertEqual("5ml", page.experiment_sidebar.current_step_label.text())
        self.assertEqual("第 2 / 2 步", page.experiment_sidebar.current_step_position_label.text())
        page.close()

    def test_settings_button_opens_dialog_and_saves_inputs(self) -> None:
        page = self._create_page()
        page.experiment_sidebar_toggle_button.click()
        self._pump_events()

        page.experiment_sidebar.settings_button.click()
        self._pump_events()

        dialog = page.experiment_sidebar.settings_dialog
        self.assertIsNotNone(dialog)
        assert dialog is not None

        dialog.experiment_name_input.setText("swallow_study")
        dialog.session_name_input.setText("healthy_H03")
        dialog.steps_editor.setPlainText("0ml\n5ml")
        dialog.yesButton.click()
        self._pump_events()

        snapshot = page.experiment_runtime.snapshot()
        self.assertEqual("swallow_study", snapshot.experiment_name)
        self.assertEqual("healthy_H03", snapshot.session_name)
        self.assertEqual(["0ml", "5ml"], [step.label for step in snapshot.steps])
        self.assertEqual("0ml", page.experiment_sidebar.current_step_label.text())
        page.close()

    def test_sidebar_does_not_expose_recording_label_generation_controls(self) -> None:
        page = self._create_page()
        page.experiment_sidebar_toggle_button.click()
        self._pump_events()

        self.assertNotIn("推荐录制标签", page.experiment_sidebar.subtitle_label.text())
        self.assertTrue(hasattr(page.experiment_sidebar, "settings_button"))
        self.assertFalse(hasattr(page.experiment_sidebar, "fill_button"))
        self.assertFalse(hasattr(page.experiment_sidebar, "retry_button"))
        page.close()

    def test_sidebar_can_float_without_covering_acquisition_panel(self) -> None:
        page = self._create_page()
        page.experiment_sidebar_toggle_button.click()
        self._pump_events()

        self.assertTrue(page.acquisition_panel.isVisible())
        self.assertTrue(page.experiment_sidebar.isVisible())
        self.assertLess(page.experiment_sidebar.geometry().bottom(), page.acquisition_panel.geometry().top())
        page.close()

    def test_ai_chat_panel_is_below_step_navigation_and_disabled_when_unconfigured(self) -> None:
        page = self._create_page()
        page.experiment_sidebar_toggle_button.click()
        self._pump_events()

        root_layout = page.experiment_sidebar.layout()
        self.assertIs(root_layout.itemAt(3).widget(), page.experiment_sidebar.ai_chat_panel)
        self.assertFalse(page.experiment_sidebar.ai_chat_panel.send_button.isEnabled())
        self.assertFalse(page.experiment_sidebar.ai_chat_panel.input.isEnabled())
        page.close()

    def test_ai_chat_appends_messages_and_applies_proposal(self) -> None:
        declare_ai_assistant_settings(self._settings_bridge)
        self._settings_bridge.ui.ai.base_url = "https://api.example.com/v1"
        self._settings_bridge.ui.ai.api_key = "secret-key"
        self._settings_bridge.ui.ai.model = "gpt-test"

        class _FakeClient:
            def complete(self, _messages):
                return ExperimentAiReply(
                    "已生成实验设置草案。",
                    ExperimentAiProposal(
                        experiment_name="swallow_study",
                        session_name="healthy_H03",
                        steps=("0ml", "5ml"),
                    ),
                )

        view_model = ExperimentRuntimeViewModel()
        panel = ExperimentAiChatPanel(
            view_model,
            self._settings_bridge,
            client_factory=lambda _config: _FakeClient(),
        )
        panel.show()
        self._pump_events()

        panel.input.setText("帮我生成吞咽实验设置")
        self.assertTrue(panel.send_button.isEnabled())
        panel.send_button.click()
        self._pump_until(
            lambda: panel.latest_proposal_button is not None and panel._request_thread is None
        )

        self.assertEqual(
            {"role": "assistant", "content": "已生成实验设置草案。"},
            panel._conversation[-1],
        )

        assert panel.latest_proposal_button is not None
        panel.latest_proposal_button.click()
        self._pump_events()

        snapshot = view_model.snapshot()
        self.assertEqual("swallow_study", snapshot.experiment_name)
        self.assertEqual("healthy_H03", snapshot.session_name)
        self.assertEqual(["0ml", "5ml"], [step.label for step in snapshot.steps])
        panel.close()

    def test_ai_chat_failure_does_not_modify_experiment_state(self) -> None:
        declare_ai_assistant_settings(self._settings_bridge)
        self._settings_bridge.ui.ai.base_url = "https://api.example.com/v1"
        self._settings_bridge.ui.ai.api_key = "secret-key"
        self._settings_bridge.ui.ai.model = "gpt-test"

        class _FailingClient:
            def complete(self, _messages):
                raise RuntimeError("network down")

        view_model = ExperimentRuntimeViewModel()
        view_model.set_experiment_name("original")
        panel = ExperimentAiChatPanel(
            view_model,
            self._settings_bridge,
            client_factory=lambda _config: _FailingClient(),
        )
        panel.show()
        self._pump_events()

        panel.input.setText("更新实验设置")
        panel.send_button.click()
        self._pump_until(lambda: panel._request_thread is None)

        self.assertEqual("original", view_model.snapshot().experiment_name)
        self.assertIsNone(panel.latest_proposal_button)
        panel.close()


if __name__ == "__main__":
    unittest.main()
