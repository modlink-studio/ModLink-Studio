from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal

from .models import SessionPlan


class SessionControllerBase(QObject):
    """Stable session-facing runtime port for future platform integrations."""

    sig_session = pyqtSignal(object)
    sig_marker = pyqtSignal(object)
    sig_segment = pyqtSignal(object)
    sig_recording = pyqtSignal(object)
    sig_error = pyqtSignal(object)

    def _not_implemented(self, member: str) -> None:
        raise NotImplementedError(
            f"{type(self).__name__} must implement SessionControllerBase.{member}"
        )

    def start_session(self, plan: SessionPlan) -> None:
        self._not_implemented("start_session")

    def stop_session(self) -> None:
        self._not_implemented("stop_session")

    def insert_marker(self, marker) -> None:
        self._not_implemented("insert_marker")

    def start_segment(self, segment) -> None:
        self._not_implemented("start_segment")

    def stop_segment(self) -> None:
        self._not_implemented("stop_segment")

    def get_session_state(self):
        self._not_implemented("get_session_state")
