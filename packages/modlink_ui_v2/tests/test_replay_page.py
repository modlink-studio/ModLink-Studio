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
from PyQt6.QtWidgets import QApplication

from modlink_core.models import ReplaySnapshot
from modlink_core.replay import ReplayBackend
from modlink_core.settings import SettingsStore, declare_core_settings
from modlink_core.storage import (
    add_recording_marker,
    add_recording_segment,
    append_recording_frame,
    create_recording,
)
from modlink_sdk import FrameEnvelope, StreamDescriptor
from modlink_ui_v2.bridge import QtReplayBridge, QtSettingsBridge
from modlink_ui_v2.features.replay import ReplayPage


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
            self.assertEqual("recordings", page._route)
            self._pump_events_until(lambda: page._recording_list.count() == 1)
            page._recording_list.setCurrentRow(0)
            page._open_button.click()
            self._pump_events_until(
                lambda: replay_bridge.snapshot().recording_id == recording_id
                and page._route == "player"
            )

            self.assertEqual(recording_id, replay_bridge.snapshot().recording_id)
            self.assertEqual("player", page._route)
            self.assertTrue(page._preview_panel._cards)

            page._play_button.click()
            self._pump_events_until(
                lambda: replay_bridge.snapshot().state in {"playing", "finished"},
                timeout=2.0,
            )

            page._show_export_page()
            self.assertEqual("export", page._route)
            page._export_button.click()
            self._pump_events_until(lambda: page._jobs_list.count() == 1, timeout=2.0)
            self._pump_events_until(
                lambda: replay_bridge.export_jobs() and replay_bridge.export_jobs()[-1].state == "completed",
                timeout=2.0,
            )
            self.assertEqual(1, page._jobs_list.count())
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
            self._pump_events_until(lambda: page._recording_list.count() == 2)
            self._select_recording(page, second_recording_id)

            self._create_recording(descriptor, recording_label="third", with_two_frames=False)
            replay_bridge.refresh_recordings()
            self._pump_events_until(lambda: page._recording_list.count() == 3)

            current_item = page._recording_list.currentItem()
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
            self._pump_events_until(lambda: page._recording_list.count() == 1)
            page._recording_list.setCurrentRow(0)
            page._open_button.click()
            self._pump_events_until(
                lambda: replay_bridge.snapshot().recording_id == recording_id
                and page._route == "player"
            )
            self._pump_events_until(
                lambda: page._markers_list.count() == 2 and page._segments_list.count() == 1
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

            self.assertEqual(1, page._markers_list.currentRow())
            self.assertTrue(page._markers_list.item(1).isSelected())
            self.assertEqual(0, page._segments_list.currentRow())
            self.assertTrue(page._segments_list.item(0).isSelected())
        finally:
            page.close()
            replay_bridge.shutdown()
            backend.shutdown()

    def _select_recording(self, page: ReplayPage, recording_id: str) -> None:
        for index in range(page._recording_list.count()):
            item = page._recording_list.item(index)
            if item.data(Qt.ItemDataRole.UserRole) == recording_id:
                page._recording_list.setCurrentItem(item)
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
