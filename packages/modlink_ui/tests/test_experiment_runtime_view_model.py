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

    def test_experiment_and_session_names_are_trimmed_in_snapshot(self) -> None:
        self._view_model.set_experiment_name("  swallow_study  ")
        self._view_model.set_session_name("  healthy_H03  ")
        snapshot = self._view_model.snapshot()

        self.assertEqual("swallow_study", snapshot.experiment_name)
        self.assertEqual("healthy_H03", snapshot.session_name)


if __name__ == "__main__":
    unittest.main()
