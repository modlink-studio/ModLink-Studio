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

from modlink_core.models import (
    ExportJobSnapshot,
    ReplayMarker,
    ReplaySegment,
    ReplaySnapshot,
)
from modlink_ui.pages.replay_state import (
    build_export_job_item_text,
    build_export_progress_view_state,
    build_replay_status_view_state,
    find_annotation_selection,
    format_time_ns,
)


class ReplayStateTests(unittest.TestCase):
    def test_status_view_state_clamps_progress_but_keeps_raw_status_text(self) -> None:
        snapshot = ReplaySnapshot(
            state="playing",
            is_started=True,
            recording_id="rec_01",
            recording_path="/tmp/rec_01",
            position_ns=7_500_000_000,
            duration_ns=5_000_000_000,
            speed_multiplier=2.0,
        )

        view_state = build_replay_status_view_state(
            snapshot,
            export_root_dir=Path("/tmp/exports"),
        )

        self.assertEqual(
            "状态：playing · recording：rec_01 · 位置：00:07.500 / 00:05.000",
            view_state.status_text,
        )
        self.assertEqual(f"导出根目录：{Path('/tmp/exports')}", view_state.hint_text)
        self.assertEqual(1000, view_state.playback_progress_value)
        self.assertEqual("00:05.000 / 00:05.000", view_state.playback_progress_text)
        self.assertFalse(view_state.can_play)
        self.assertTrue(view_state.can_pause)
        self.assertTrue(view_state.can_stop)
        self.assertTrue(view_state.can_export)

    def test_find_annotation_selection_uses_last_past_marker_and_first_matching_segment(self) -> None:
        snapshot = ReplaySnapshot(
            state="paused",
            is_started=True,
            recording_id="rec_01",
            recording_path="/tmp/rec_01",
            position_ns=3_500_000_000,
            duration_ns=8_000_000_000,
            speed_multiplier=1.0,
        )
        markers = (
            ReplayMarker(timestamp_ns=1_000_000_000, label="start"),
            ReplayMarker(timestamp_ns=3_000_000_000, label="cue"),
            ReplayMarker(timestamp_ns=4_000_000_000, label="late"),
        )
        segments = (
            ReplaySegment(start_ns=0, end_ns=2_000_000_000, label="warmup"),
            ReplaySegment(start_ns=3_000_000_000, end_ns=4_000_000_000, label="task"),
            ReplaySegment(start_ns=3_200_000_000, end_ns=5_000_000_000, label="overlap"),
        )

        selection = find_annotation_selection(
            snapshot,
            markers=markers,
            segments=segments,
        )

        self.assertEqual(1, selection.marker_index)
        self.assertEqual(1, selection.segment_index)

    def test_export_progress_and_job_text_follow_latest_job(self) -> None:
        jobs = (
            ExportJobSnapshot(
                job_id="job_01",
                recording_id="rec_01",
                format_id="signal_csv",
                state="running",
                progress=0.25,
                output_path=None,
                error=None,
            ),
            ExportJobSnapshot(
                job_id="job_02",
                recording_id="rec_01",
                format_id="recording_bundle_zip",
                state="failed",
                progress=0.875,
                output_path="/tmp/out.zip",
                error="disk full",
            ),
        )

        latest_text = build_export_job_item_text(jobs[-1])
        progress_state = build_export_progress_view_state(jobs)

        self.assertEqual(
            "Recording Bundle ZIP · failed · 87% · /tmp/out.zip · disk full",
            latest_text,
        )
        self.assertEqual(875, progress_state.value)
        self.assertEqual("Recording Bundle ZIP · failed · 87%", progress_state.text)

    def test_format_time_ns_formats_hours_and_negative_values(self) -> None:
        self.assertEqual("00:00.000", format_time_ns(-1))
        self.assertEqual("01:02.003", format_time_ns(62_003_000_000))
        self.assertEqual("01:01:02.003", format_time_ns(3_662_003_000_000))


if __name__ == "__main__":
    unittest.main()
