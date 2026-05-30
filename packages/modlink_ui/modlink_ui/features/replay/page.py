from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

from PyQt6.QtWidgets import QStackedWidget, QVBoxLayout, QWidget
from qfluentwidgets import InfoBar, InfoBarPosition

from modlink_core.models import ReplaySnapshot
from modlink_ui.bridge import QtModLinkBridge

from .export_page import ReplayExportPage
from .player_page import ReplayPlayerPage
from .recordings_page import ReplayRecordingsPage

type ReplayRoute = Literal["recordings", "player", "export"]

logger = logging.getLogger(__name__)


class _CurrentReplayStack(QStackedWidget):
    def sizeHint(self):
        w = self.currentWidget()
        return w.sizeHint() if w else super().sizeHint()

    def minimumSizeHint(self):
        w = self.currentWidget()
        return w.minimumSizeHint() if w else super().minimumSizeHint()


class ReplayPage(QWidget):
    def __init__(self, engine: QtModLinkBridge, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.setObjectName("replay-page")
        self._replay = engine.replay
        self._route: ReplayRoute = "recordings"
        self._pending_open_recording_path: str | None = None

        # --- Pages ---
        self._page_stack = _CurrentReplayStack(self)
        self._recordings_page = ReplayRecordingsPage(self._page_stack)
        self._player_page = ReplayPlayerPage(self._replay, engine.settings, self._page_stack)
        self._export_page = ReplayExportPage(self._replay.export_root_dir, self._page_stack)
        self._page_stack.addWidget(self._recordings_page)
        self._page_stack.addWidget(self._player_page)
        self._page_stack.addWidget(self._export_page)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._page_stack, 1)

        # --- User actions → bridge commands ---
        self._recordings_page.sig_open_recording_requested.connect(self._open_recording)
        self._recordings_page.sig_refresh_requested.connect(self._replay.refresh_recordings)
        self._recordings_page.sig_delete_recording_requested.connect(self._replay.delete_recording)
        self._player_page.sig_show_recordings_requested.connect(self._show_recordings_page)
        self._player_page.sig_show_export_requested.connect(self._show_export_page)
        self._player_page.sig_play_requested.connect(self._replay.play)
        self._player_page.sig_pause_requested.connect(self._replay.pause)
        self._player_page.sig_reset_requested.connect(self._replay.stop)
        self._player_page.sig_reset_requested.connect(self._player_page.preview_panel.clear_plots)
        self._player_page.sig_speed_changed.connect(self._replay.set_speed)
        self._player_page.sig_seek_requested.connect(self._replay.seek)
        self._player_page.sig_delete_recording_requested.connect(self._replay.delete_recording)
        self._export_page.sig_show_recordings_requested.connect(self._show_recordings_page)
        self._export_page.sig_show_player_requested.connect(self._show_player_page)
        self._export_page.sig_export_requested.connect(self._replay.start_export)

        # --- Bridge state → UI updates ---
        self._replay.sig_snapshot_changed.connect(self._on_snapshot_changed)
        self._replay.sig_recordings_changed.connect(self._reload_recordings)
        self._replay.sig_annotations_changed.connect(self._reload_annotations)
        self._replay.sig_export_jobs_changed.connect(self._reload_export_jobs)
        self._replay.sig_bus_reset.connect(self._on_bus_reset)
        self._replay.sig_error.connect(self._on_error)

        # --- Initial sync ---
        self._on_snapshot_changed(self._replay.snapshot())
        self._reload_recordings()
        self._reload_annotations()
        self._reload_export_jobs()
        self._set_route("recordings")
        self._replay.refresh_recordings()

    # --- Routing ---

    def _set_route(self, route: ReplayRoute) -> None:
        if route in {"player", "export"} and self._replay.snapshot().recording_id is None:
            route = "recordings"
        target = {"recordings": self._recordings_page, "player": self._player_page,
                  "export": self._export_page}[route]
        if self._route == route and self._page_stack.currentWidget() is target:
            return
        self._route = route
        self._page_stack.setCurrentWidget(target)
        self._page_stack.updateGeometry()
        self.updateGeometry()

    def _show_recordings_page(self) -> None:
        self._set_route("recordings")

    def _show_player_page(self) -> None:
        self._set_route("player")

    def _show_export_page(self) -> None:
        self._set_route("export")

    # --- Bridge state handlers ---

    def _on_snapshot_changed(self, snapshot: object) -> None:
        if not isinstance(snapshot, ReplaySnapshot):
            snapshot = self._replay.snapshot()
        self._player_page.apply_snapshot(snapshot)
        self._export_page.apply_snapshot(snapshot, export_root_dir=self._replay.export_root_dir)
        self._finish_pending_open_if_ready(snapshot)
        if snapshot.recording_id is None and self._route in {"player", "export"}:
            self._set_route("recordings")

    def _reload_recordings(self) -> None:
        self._recordings_page.reload_recordings(self._replay.recordings())

    def _reload_annotations(self) -> None:
        self._player_page.reload_annotations(
            self._replay.markers(),
            self._replay.segments(),
            self._replay.snapshot(),
        )

    def _reload_export_jobs(self) -> None:
        self._export_page.reload_jobs(self._replay.export_jobs())

    def _on_bus_reset(self) -> None:
        self._finish_pending_open_if_ready(self._replay.snapshot())

    # --- Open recording flow ---

    def _open_recording(self, recording_path: str) -> None:
        self._pending_open_recording_path = recording_path
        self._replay.open_recording(recording_path)

    def _finish_pending_open_if_ready(self, snapshot: ReplaySnapshot) -> None:
        if self._pending_open_recording_path is None:
            return
        if not snapshot.recording_path:
            return
        if Path(snapshot.recording_path) != Path(self._pending_open_recording_path):
            return
        self._pending_open_recording_path = None
        self._set_route("player")

    # --- Error ---

    def _on_error(self, message: str) -> None:
        self._pending_open_recording_path = None
        self._export_page.set_status_hint(message)
        parent = self.window() if isinstance(self.window(), QWidget) else self
        InfoBar.error(
            title="回放错误",
            content=message,
            duration=4500,
            position=InfoBarPosition.TOP_RIGHT,
            parent=parent,
        )
