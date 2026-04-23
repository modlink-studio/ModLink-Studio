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
        current_widget = self.currentWidget()
        if current_widget is None:
            return super().sizeHint()
        return current_widget.sizeHint()

    def minimumSizeHint(self):
        current_widget = self.currentWidget()
        if current_widget is None:
            return super().minimumSizeHint()
        return current_widget.minimumSizeHint()


class ReplayPage(QWidget):
    def __init__(self, engine: QtModLinkBridge, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.setObjectName("replay-page")
        self.engine = engine
        self._replay = engine.replay
        self._route: ReplayRoute = "recordings"
        self._pending_open_recording_path: str | None = None

        self._page_stack = _CurrentReplayStack(self)
        self._recordings_page = ReplayRecordingsPage(self._page_stack)
        self._player_page = ReplayPlayerPage(
            self._replay,
            self.engine.settings,
            self._page_stack,
        )
        self._export_page = ReplayExportPage(self._replay.export_root_dir, self._page_stack)
        self._page_stack.addWidget(self._recordings_page)
        self._page_stack.addWidget(self._player_page)
        self._page_stack.addWidget(self._export_page)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._page_stack, 1)

        self._recordings_page.sig_open_recording_requested.connect(self._open_recording)
        self._recordings_page.sig_refresh_requested.connect(self._replay.refresh_recordings)
        self._player_page.sig_show_recordings_requested.connect(self._show_recordings_page)
        self._player_page.sig_show_export_requested.connect(self._show_export_page)
        self._player_page.sig_play_requested.connect(self._replay.play)
        self._player_page.sig_pause_requested.connect(self._replay.pause)
        self._player_page.sig_reset_requested.connect(self._replay.stop)
        self._player_page.sig_speed_changed.connect(self._replay.set_speed)
        self._export_page.sig_show_recordings_requested.connect(self._show_recordings_page)
        self._export_page.sig_show_player_requested.connect(self._show_player_page)
        self._export_page.sig_export_requested.connect(self._replay.start_export)
        self._replay.sig_bus_reset.connect(self._on_bus_reset)
        self._replay.sig_recordings_changed.connect(self._reload_recordings)
        self._replay.sig_snapshot_changed.connect(self._on_snapshot_changed)
        self._replay.sig_annotations_changed.connect(self._reload_annotations)
        self._replay.sig_export_jobs_changed.connect(self._reload_export_jobs)
        self._replay.sig_error.connect(self._on_error)

        self._reload_recordings()
        self._on_snapshot_changed(self._replay.snapshot())
        self._reload_annotations()
        self._reload_export_jobs()
        self._set_route("recordings")
        self._replay.refresh_recordings()

    def _current_snapshot(self) -> ReplaySnapshot:
        snapshot = self._replay.snapshot()
        if isinstance(snapshot, ReplaySnapshot):
            return snapshot
        return ReplaySnapshot(
            state="idle",
            is_started=False,
            recording_id=None,
            recording_path=None,
            position_ns=0,
            duration_ns=0,
            speed_multiplier=1.0,
        )

    def _set_route(self, route: ReplayRoute) -> None:
        snapshot = self._current_snapshot()
        if route in {"player", "export"} and snapshot.recording_id is None:
            route = "recordings"

        if route == "recordings":
            target_widget = self._recordings_page
        elif route == "player":
            target_widget = self._player_page
        else:
            target_widget = self._export_page

        if self._route == route and self._page_stack.currentWidget() is target_widget:
            logger.debug("Replay route already active: %s", route)
            return

        logger.debug(
            "Switching replay route from %s to %s (recording_id=%s)",
            self._route,
            route,
            snapshot.recording_id,
        )
        self._route = route
        self._page_stack.setCurrentWidget(target_widget)
        self._page_stack.updateGeometry()
        self.updateGeometry()

    def _show_recordings_page(self) -> None:
        self._set_route("recordings")

    def _show_player_page(self) -> None:
        self._set_route("player")

    def _show_export_page(self) -> None:
        self._set_route("export")

    def _reload_recordings(self) -> None:
        self._recordings_page.reload_recordings(self._replay.recordings())

    def _reload_annotations(self) -> None:
        self._player_page.reload_annotations(
            self._replay.markers(),
            self._replay.segments(),
            self._current_snapshot(),
        )

    def _reload_export_jobs(self) -> None:
        self._export_page.reload_jobs(self._replay.export_jobs())

    def _open_recording(self, recording_path: str) -> None:
        logger.debug("Requesting replay open for recording_path=%s", recording_path)
        self._pending_open_recording_path = recording_path
        self._replay.open_recording(recording_path)

    def _on_bus_reset(self) -> None:
        logger.debug("Replay bus reset received")
        self._finish_pending_open_if_ready(self._current_snapshot())

    def _on_snapshot_changed(self, snapshot: object) -> None:
        if not isinstance(snapshot, ReplaySnapshot):
            snapshot = self._current_snapshot()

        logger.debug(
            "Replay snapshot changed: state=%s recording_id=%s position_ns=%s duration_ns=%s",
            snapshot.state,
            snapshot.recording_id,
            snapshot.position_ns,
            snapshot.duration_ns,
        )
        self._player_page.apply_snapshot(snapshot)
        self._export_page.apply_snapshot(
            snapshot,
            export_root_dir=self._replay.export_root_dir,
        )
        self._finish_pending_open_if_ready(snapshot)

    def _finish_pending_open_if_ready(self, snapshot: ReplaySnapshot) -> None:
        if self._pending_open_recording_path is None:
            return

        recording_path = str(snapshot.recording_path or "").strip()
        if not recording_path:
            return

        if Path(recording_path) != Path(self._pending_open_recording_path):
            return

        logger.debug("Replay open completed for recording_path=%s", recording_path)
        self._pending_open_recording_path = None
        self._set_route("player")

    def _on_error(self, message: str) -> None:
        if self._pending_open_recording_path is not None:
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
