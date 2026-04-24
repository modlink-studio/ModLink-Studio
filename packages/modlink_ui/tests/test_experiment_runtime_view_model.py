from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

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

from PyQt6.QtWidgets import QApplication

from modlink_ui.features.live.experiment_runtime import ExperimentRuntimeViewModel


class ExperimentRuntimeViewModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self._view_model = ExperimentRuntimeViewModel()

    def test_steps_text_ignores_blank_lines_and_preserves_duplicates(self) -> None:
        self._view_model.set_steps_text(" 0ml \n\n5ml\n0ml \n")

        snapshot = self._view_model.snapshot()

        self.assertEqual(["0ml", "5ml", "0ml"], [step.label for step in snapshot.steps])
        self.assertEqual(0, snapshot.current_step_index)
        self.assertEqual("0ml", snapshot.current_step.label if snapshot.current_step else None)

    def test_next_and_previous_are_clamped_to_queue_bounds(self) -> None:
        self._view_model.set_steps_text("0ml\n5ml")

        self._view_model.prev_step()
        self.assertEqual(0, self._view_model.snapshot().current_step_index)

        self._view_model.next_step()
        self.assertEqual(1, self._view_model.snapshot().current_step_index)

        self._view_model.next_step()
        self.assertEqual(1, self._view_model.snapshot().current_step_index)

        self._view_model.prev_step()
        self.assertEqual(0, self._view_model.snapshot().current_step_index)

    def test_editing_step_queue_clamps_current_index_by_position(self) -> None:
        self._view_model.set_steps_text("0ml\n5ml\n15ml")
        self._view_model.next_step()
        self._view_model.next_step()

        self._view_model.set_steps_text("alpha\nbeta")

        snapshot = self._view_model.snapshot()
        self.assertEqual(1, snapshot.current_step_index)
        self.assertEqual("beta", snapshot.current_step.label if snapshot.current_step else None)

    def test_suggested_recording_label_requires_session_and_current_step(self) -> None:
        self._view_model.set_session_name("healthy_H03")
        self.assertFalse(self._view_model.snapshot().can_fill_recording_label)

        self._view_model.set_steps_text("5ml")
        snapshot = self._view_model.snapshot()

        self.assertTrue(snapshot.can_fill_recording_label)
        self.assertEqual("healthy_H03__5ml__step01", snapshot.suggested_recording_label)

    def test_request_fill_does_not_emit_when_suggestion_is_missing(self) -> None:
        requested_labels: list[str] = []
        self._view_model.sig_fill_recording_label_requested.connect(requested_labels.append)

        self._view_model.set_steps_text("5ml")
        self._view_model.request_fill_suggested_label()

        self.assertEqual([], requested_labels)

    def test_retry_republishes_current_suggestion_without_moving_index(self) -> None:
        requested_labels: list[str] = []
        self._view_model.sig_fill_recording_label_requested.connect(requested_labels.append)
        self._view_model.set_session_name("patient_P07")
        self._view_model.set_steps_text("0ml\n15ml")
        self._view_model.next_step()

        self._view_model.retry_step()

        snapshot = self._view_model.snapshot()
        self.assertEqual(1, snapshot.current_step_index)
        self.assertEqual(["patient_P07__15ml__step02"], requested_labels)


if __name__ == "__main__":
    unittest.main()
