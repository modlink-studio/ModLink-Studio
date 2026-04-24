from __future__ import annotations

import os
import shutil
import sys
import time
import unittest
from pathlib import Path
from uuid import uuid4

import numpy as np

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

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QAbstractItemView, QApplication

from modlink_core.models import ReplayMarker, ReplaySegment, ReplaySnapshot
from modlink_core.replay import ReplayBackend
from modlink_core.settings import SettingsStore, declare_core_settings
from modlink_core.storage import (
    add_recording_marker,
    add_recording_segment,
    append_recording_frame,
    create_recording,
)
from modlink_sdk import FrameEnvelope, StreamDescriptor
from modlink_ui.bridge import QtReplayBridge, QtSettingsBridge
from modlink_ui.features.replay import ReplayPage
from modlink_ui.features.replay.timeline import ReplayAnnotationTimeline


class _EngineStub:
    def __init__(self, settings: QtSettingsBridge, replay: QtReplayBridge) -> None:
        self.settings = settings
        self.replay = replay


class ReplayPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        test_tmp_root = WORKSPACE_ROOT / ".tmp-tests"
        test_tmp_root.mkdir(exist_ok=True)
        self._temp_dir = test_tmp_root / f"replay-page-{uuid4().hex}"
        self._temp_dir.mkdir()
        self._settings = SettingsStore(path=self._temp_dir / "settings.json")
        declare_core_settings(self._settings)
        self._settings.storage.root_dir = str(self._temp_dir)
        self._settings.storage.export_root_dir = str(self._temp_dir / "exports")
        self._settings_bridge = QtSettingsBridge(self._settings)

    def tearDown(self) -> None:
        shutil.rmtree(self._temp_dir, ignore_errors=True)

    @staticmethod
    def _descriptor() -> StreamDescriptor:
        return StreamDescriptor(
            device_id="demo.01",
            stream_key="signal",
            payload_type="signal",
            nominal_sample_rate_hz=20.0,
            chunk_size=2,
            channel_names=("c3", "c4"),
            display_name="Signal",
        )

    def _create_recording(
        self,
        descriptor: StreamDescriptor,
        *,
        recording_label: str,
        with_two_frames: bool = True,
    ) -> str:
        recording_id = create_recording(
            self._temp_dir,
            {descriptor.stream_id: descriptor},
            recording_label=recording_label,
        )
        append_recording_frame(
            self._temp_dir,
            recording_id,
            FrameEnvelope(
                device_id=descriptor.device_id,
                stream_key=descriptor.stream_key,
                timestamp_ns=1_000_000_000,
                data=np.zeros((2, 2), dtype=np.float32),
                seq=1,
            ),
        )
        if with_two_frames:
            append_recording_frame(
                self._temp_dir,
                recording_id,
                FrameEnvelope(
                    device_id=descriptor.device_id,
                    stream_key=descriptor.stream_key,
                    timestamp_ns=1_050_000_000,
                    data=np.ones((2, 2), dtype=np.float32),
                    seq=2,
                ),
            )
        return recording_id

    def test_page_lists_recordings_opens_selection_and_updates_export_jobs(self) -> None:
        descriptor = self._descriptor()
        recording_id = self._create_recording(
            descriptor,
            recording_label="page_case",
        )

        backend = ReplayBackend(settings=self._settings)
        backend.start()
        replay_bridge = QtReplayBridge(backend, self._settings_bridge)
        page = ReplayPage(_EngineStub(self._settings_bridge, replay_bridge))
        page.show()

        try:
            recordings_page = page._recordings_page
            player_page = page._player_page
            export_page = page._export_page
            self.assertEqual("recordings", page._route)
            self.assertEqual("打开", recordings_page.open_button.text())
            self.assertEqual("刷新", recordings_page.refresh_button.text())
            self.assertEqual(
                recordings_page.open_button.width(),
                recordings_page.refresh_button.width(),
            )
            self.assertEqual(2, recordings_page.header_action_layout.count())
            self.assertEqual(2, recordings_page.content_layout.count())
            self.assertEqual(1, recordings_page.content_layout.stretch(1))
            self._pump_events_until(lambda: recordings_page.recording_list.count() == 1)
            recordings_page.recording_list.setCurrentRow(0)
            recordings_page.open_button.click()
            self._pump_events_until(
                lambda: replay_bridge.snapshot().recording_id == recording_id
                and page._route == "player"
            )

            self.assertEqual(recording_id, replay_bridge.snapshot().recording_id)
            self.assertEqual("player", page._route)
            self.assertTrue(player_page.preview_panel._cards)
            self._pump_events_until(lambda: player_page.transport_bar.isVisible())
            self.assertIs(player_page.transport_bar.parentWidget(), player_page)
            self.assertEqual(2, player_page.header_action_layout.count())
            self.assertGreater(player_page._floating_panel_spacer.height(), 0)
            self.assertTrue(player_page.export_route_button.isEnabled())
            self.assertIs(player_page.preview_panel.parentWidget(), player_page.playback_panel)
            self.assertEqual("列表", player_page.recordings_route_button.text())
            self.assertEqual("导出", player_page.export_route_button.text())
            self.assertEqual(0, player_page.recordings_route_button.minimumHeight())
            self.assertEqual(0, player_page.export_route_button.minimumHeight())
            self.assertEqual("播放", player_page.play_button.text())
            self.assertEqual("复位", player_page.pause_reset_button.text())
            self.assertEqual(0, player_page.play_button.minimumHeight())
            self.assertEqual(0, player_page.pause_reset_button.minimumHeight())
            self.assertFalse(player_page.recordings_route_button.icon().isNull())
            self.assertFalse(player_page.export_route_button.icon().isNull())
            self.assertEqual(
                Qt.AlignmentFlag.AlignCenter,
                player_page.playback_panel.position_badge.alignment(),
            )
            badge_center_y = player_page.playback_panel.position_badge.geometry().center().y()
            play_center_y = player_page.play_button.geometry().center().y()
            self.assertLess(abs(badge_center_y - play_center_y), 8)

            player_page.play_button.click()
            self._pump_events_until(
                lambda: replay_bridge.snapshot().state in {"playing", "finished"},
                timeout=2.0,
            )

            page._show_export_page()
            self.assertEqual("export", page._route)
            self._pump_events_until(lambda: not player_page.transport_bar.isVisible())
            self.assertEqual(2, export_page.header_action_layout.count())
            self.assertTrue(export_page.player_route_button.isVisible())
            self.assertTrue(export_page.recordings_route_button.isVisible())
            self.assertEqual("列表", export_page.recordings_route_button.text())
            self.assertEqual("回放", export_page.player_route_button.text())
            self.assertEqual(0, export_page.recordings_route_button.minimumHeight())
            self.assertEqual(0, export_page.player_route_button.minimumHeight())
            self.assertEqual(0, export_page.export_button.minimumHeight())
            self.assertEqual(
                QAbstractItemView.SelectionMode.SingleSelection,
                export_page.jobs_list.selectionMode(),
            )
            self.assertEqual(2, export_page.content_layout.count())
            self.assertEqual(1, export_page.content_layout.stretch(1))
            self.assertFalse(hasattr(export_page, "summary_card"))
            export_page.export_button.click()
            self._pump_events_until(lambda: export_page.jobs_list.count() == 1, timeout=2.0)
            self._pump_events_until(
                lambda: replay_bridge.export_jobs() and replay_bridge.export_jobs()[-1].state == "completed",
                timeout=2.0,
            )
            self.assertEqual(1, export_page.jobs_list.count())
        finally:
            page.close()
            replay_bridge.shutdown()
            backend.shutdown()

    def test_refresh_recordings_keeps_selected_item(self) -> None:
        descriptor = self._descriptor()
        first_recording_id = self._create_recording(descriptor, recording_label="first")
        second_recording_id = self._create_recording(descriptor, recording_label="second")

        backend = ReplayBackend(settings=self._settings)
        backend.start()
        replay_bridge = QtReplayBridge(backend, self._settings_bridge)
        page = ReplayPage(_EngineStub(self._settings_bridge, replay_bridge))
        page.show()

        try:
            self._pump_events_until(lambda: page._recordings_page.recording_list.count() == 2)
            self._select_recording(page, second_recording_id)

            self._create_recording(descriptor, recording_label="third", with_two_frames=False)
            replay_bridge.refresh_recordings()
            self._pump_events_until(lambda: page._recordings_page.recording_list.count() == 3)

            current_item = page._recordings_page.recording_list.currentItem()
            self.assertIsNotNone(current_item)
            self.assertEqual(
                second_recording_id,
                current_item.data(Qt.ItemDataRole.UserRole),
            )
            self.assertNotEqual(first_recording_id, second_recording_id)
        finally:
            page.close()
            replay_bridge.shutdown()
            backend.shutdown()

    def test_reopen_same_recording_after_returning_to_list_routes_back_to_player(self) -> None:
        descriptor = self._descriptor()
        recording_id = self._create_recording(
            descriptor,
            recording_label="reopen_same_recording",
        )

        backend = ReplayBackend(settings=self._settings)
        backend.start()
        replay_bridge = QtReplayBridge(backend, self._settings_bridge)
        page = ReplayPage(_EngineStub(self._settings_bridge, replay_bridge))
        page.show()

        try:
            recordings_page = page._recordings_page
            self._pump_events_until(lambda: recordings_page.recording_list.count() == 1)
            recordings_page.recording_list.setCurrentRow(0)
            recordings_page.open_button.click()
            self._pump_events_until(
                lambda: replay_bridge.snapshot().recording_id == recording_id
                and page._route == "player"
            )

            page._show_recordings_page()
            self.assertEqual("recordings", page._route)
            recordings_page.open_button.click()
            self._pump_events_until(lambda: page._route == "player")
            self.assertEqual(recording_id, replay_bridge.snapshot().recording_id)
            self.assertIsNone(page._pending_open_recording_path)
        finally:
            page.close()
            replay_bridge.shutdown()
            backend.shutdown()

    def test_recording_list_items_stay_compact_for_long_titles(self) -> None:
        descriptor = self._descriptor()
        short_label = "short"
        long_label = (
            "rec_20260421T153943_302514500Z"
            "_extra_suffix_for_test"
            "_extra_suffix_for_test"
            "_extra_suffix_for_test"
        )
        self._create_recording(descriptor, recording_label=short_label)
        self._create_recording(descriptor, recording_label=long_label)

        backend = ReplayBackend(settings=self._settings)
        backend.start()
        replay_bridge = QtReplayBridge(backend, self._settings_bridge)
        page = ReplayPage(_EngineStub(self._settings_bridge, replay_bridge))
        page.resize(900, 720)
        page.show()

        try:
            recording_list = page._recordings_page.recording_list
            self._pump_events_until(lambda: recording_list.count() == 2)

            items_by_text = {}
            for row in range(recording_list.count()):
                item = recording_list.item(row)
                self.assertIsNone(recording_list.itemWidget(item))
                items_by_text[item.text()] = item

            short_text = f"{short_label} · 1 stream"
            long_text = f"{long_label} · 1 stream"
            self.assertIn(short_text, items_by_text)
            self.assertIn(long_text, items_by_text)
            self.assertEqual(long_text, items_by_text[long_text].text())
        finally:
            page.close()
            replay_bridge.shutdown()
            backend.shutdown()

    def test_recording_list_does_not_repeat_id_when_label_is_missing(self) -> None:
        descriptor = self._descriptor()
        recording_id = self._create_recording(descriptor, recording_label="")

        backend = ReplayBackend(settings=self._settings)
        backend.start()
        replay_bridge = QtReplayBridge(backend, self._settings_bridge)
        page = ReplayPage(_EngineStub(self._settings_bridge, replay_bridge))
        page.show()

        try:
            recording_list = page._recordings_page.recording_list
            self._pump_events_until(lambda: recording_list.count() == 1)
            item = recording_list.item(0)
            self.assertEqual(
                f"{recording_id} · 1 stream",
                item.text(),
            )
            self.assertIsNone(recording_list.itemWidget(item))
        finally:
            page.close()
            replay_bridge.shutdown()
            backend.shutdown()

    def test_snapshot_highlights_latest_marker_and_active_segment(self) -> None:
        descriptor = self._descriptor()
        recording_id = self._create_recording(
            descriptor,
            recording_label="annotated",
        )
        add_recording_marker(self._temp_dir, recording_id, 1_000_000_000, "start")
        add_recording_marker(self._temp_dir, recording_id, 1_500_000_000, "cue")
        add_recording_segment(
            self._temp_dir,
            recording_id,
            1_200_000_000,
            1_800_000_000,
            "trial",
        )

        backend = ReplayBackend(settings=self._settings)
        backend.start()
        replay_bridge = QtReplayBridge(backend, self._settings_bridge)
        page = ReplayPage(_EngineStub(self._settings_bridge, replay_bridge))
        page.show()

        try:
            self._pump_events_until(lambda: page._recordings_page.recording_list.count() == 1)
            page._recordings_page.recording_list.setCurrentRow(0)
            page._recordings_page.open_button.click()
            self._pump_events_until(
                lambda: replay_bridge.snapshot().recording_id == recording_id
                and page._route == "player"
            )
            self._pump_events_until(
                lambda: page._player_page.timeline.marker_count == 2
                and page._player_page.timeline.segment_count == 1
            )

            page._on_snapshot_changed(
                ReplaySnapshot(
                    state="paused",
                    is_started=True,
                    recording_id=recording_id,
                    recording_path=str(self._temp_dir / "recordings" / recording_id),
                    position_ns=600_000_000,
                    duration_ns=1_000_000_000,
                    speed_multiplier=1.0,
                )
            )

            self.assertFalse(hasattr(page._player_page, "annotations_card"))
            self.assertEqual(1, page._player_page.timeline.active_marker_index)
            self.assertEqual(0, page._player_page.timeline.active_segment_index)
        finally:
            page.close()
            replay_bridge.shutdown()
            backend.shutdown()

    def test_transport_button_switches_between_pause_and_reset(self) -> None:
        descriptor = self._descriptor()
        recording_id = self._create_recording(
            descriptor,
            recording_label="transport_button",
        )

        backend = ReplayBackend(settings=self._settings)
        backend.start()
        replay_bridge = QtReplayBridge(backend, self._settings_bridge)
        page = ReplayPage(_EngineStub(self._settings_bridge, replay_bridge))
        page.show()

        try:
            player_page = page._player_page
            self._pump_events_until(lambda: page._recordings_page.recording_list.count() == 1)
            page._recordings_page.recording_list.setCurrentRow(0)
            page._recordings_page.open_button.click()
            self._pump_events_until(
                lambda: replay_bridge.snapshot().recording_id == recording_id
                and page._route == "player"
            )

            self.assertEqual("播放", player_page.play_button.text())
            self.assertEqual("复位", player_page.pause_reset_button.text())
            self.assertEqual("复位", player_page.pause_reset_button.toolTip())
            self.assertFalse(player_page.pause_reset_button.isEnabled())

            calls: list[str] = []
            player_page.sig_pause_requested.connect(lambda: calls.append("pause"))
            player_page.sig_reset_requested.connect(lambda: calls.append("stop"))

            playing_snapshot = ReplaySnapshot(
                state="playing",
                is_started=True,
                recording_id=recording_id,
                recording_path=str(self._temp_dir / "recordings" / recording_id),
                position_ns=600_000_000,
                duration_ns=1_000_000_000,
                speed_multiplier=1.0,
            )
            page._on_snapshot_changed(playing_snapshot)
            self.assertEqual("暂停", player_page.pause_reset_button.text())
            self.assertEqual("暂停", player_page.pause_reset_button.toolTip())
            self.assertTrue(player_page.pause_reset_button.isEnabled())
            player_page.pause_reset_button.click()
            self.assertEqual(["pause"], calls)

            paused_snapshot = ReplaySnapshot(
                state="paused",
                is_started=True,
                recording_id=recording_id,
                recording_path=str(self._temp_dir / "recordings" / recording_id),
                position_ns=600_000_000,
                duration_ns=1_000_000_000,
                speed_multiplier=1.0,
            )
            page._on_snapshot_changed(paused_snapshot)
            self.assertEqual("复位", player_page.pause_reset_button.text())
            self.assertEqual("复位", player_page.pause_reset_button.toolTip())
            self.assertTrue(player_page.pause_reset_button.isEnabled())
            player_page.pause_reset_button.click()
            self.assertEqual(["pause", "stop"], calls)
        finally:
            page.close()
            replay_bridge.shutdown()
            backend.shutdown()

    def test_timeline_handles_empty_state_and_short_segments(self) -> None:
        timeline = ReplayAnnotationTimeline()
        timeline.resize(480, 64)
        timeline.show()

        try:
            timeline.clear()
            timeline._refresh_geometry()
            self.assertEqual(0, timeline.marker_count)
            self.assertEqual(0, timeline.segment_count)
            self.assertEqual(-1, timeline.active_marker_index)
            self.assertEqual(-1, timeline.active_segment_index)

            marker = ReplayMarker(timestamp_ns=220_000_000, label="cue")
            segment = ReplaySegment(
                start_ns=300_000_000,
                end_ns=300_400_000,
                label="blink",
            )
            timeline.set_annotations((marker,), (segment,))
            timeline.set_playback(300_200_000, 1_000_000_000)
            timeline._refresh_geometry()

            self.assertEqual(1, timeline.marker_count)
            self.assertEqual(1, timeline.segment_count)
            self.assertEqual(0, timeline.active_marker_index)
            self.assertEqual(0, timeline.active_segment_index)
            self.assertGreaterEqual(
                timeline._segment_regions[0].width(),
                timeline._minimum_segment_width,
            )
            marker_tooltip = timeline._tooltip_text_at(timeline._marker_regions[0].center())
            segment_tooltip = timeline._tooltip_text_at(timeline._segment_regions[0].center())
            self.assertIn("cue", marker_tooltip or "")
            self.assertIn("blink", segment_tooltip or "")
        finally:
            timeline.close()

    def _select_recording(self, page: ReplayPage, recording_id: str) -> None:
        recording_list = page._recordings_page.recording_list
        for index in range(recording_list.count()):
            item = recording_list.item(index)
            if item.data(Qt.ItemDataRole.UserRole) == recording_id:
                recording_list.setCurrentItem(item)
                return
        raise AssertionError(f"recording_id not found in list: {recording_id}")

    def _pump_events_until(self, predicate, *, timeout: float = 1.0) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            self._app.processEvents()
            if predicate():
                return
            time.sleep(0.01)
        self._app.processEvents()
        if predicate():
            return
        raise AssertionError("condition not reached before timeout")


if __name__ == "__main__":
    unittest.main()
