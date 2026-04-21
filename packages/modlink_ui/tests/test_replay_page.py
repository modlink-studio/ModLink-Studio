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

from PyQt6.QtWidgets import QApplication

from modlink_core.replay import ReplayBackend
from modlink_core.settings import SettingsStore, declare_core_settings
from modlink_core.storage import append_recording_frame, create_recording
from modlink_sdk import FrameEnvelope, StreamDescriptor
from modlink_ui.bridge import QtReplayBridge, QtSettingsBridge
from modlink_ui.pages.replay import ReplayPage


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

    def test_page_lists_recordings_opens_selection_and_updates_export_jobs(self) -> None:
        descriptor = StreamDescriptor(
            device_id="demo.01",
            stream_key="signal",
            payload_type="signal",
            nominal_sample_rate_hz=20.0,
            chunk_size=2,
            channel_names=("c3", "c4"),
            display_name="Signal",
        )
        recording_id = create_recording(
            self._temp_dir,
            {descriptor.stream_id: descriptor},
            recording_label="page_case",
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

        backend = ReplayBackend(settings=self._settings)
        backend.start()
        replay_bridge = QtReplayBridge(backend, self._settings_bridge)
        page = ReplayPage(_EngineStub(self._settings_bridge, replay_bridge))
        page.show()

        try:
            self._pump_events_until(lambda: page._recording_list.count() == 1)
            page._recording_list.setCurrentRow(0)
            page._open_button.click()
            self._pump_events_until(lambda: replay_bridge.snapshot().recording_id == recording_id)

            self.assertEqual(recording_id, replay_bridge.snapshot().recording_id)
            self.assertTrue(page._preview_panel._cards)

            page._play_button.click()
            self._pump_events_until(
                lambda: replay_bridge.snapshot().state in {"playing", "finished"},
                timeout=2.0,
            )

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
