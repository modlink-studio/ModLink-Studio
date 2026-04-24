from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import QObject, pyqtSignal


@dataclass(frozen=True, slots=True)
class ExperimentStep:
    label: str
    prompt: str | None = None


@dataclass(frozen=True, slots=True)
class ExperimentRuntimeSnapshot:
    experiment_name: str
    session_name: str
    steps: tuple[ExperimentStep, ...]
    current_step_index: int
    current_step: ExperimentStep | None
    suggested_recording_label: str
    can_fill_recording_label: bool
    can_go_previous: bool
    can_go_next: bool
    can_retry: bool


class ExperimentRuntimeViewModel(QObject):
    sig_snapshot_changed = pyqtSignal(object)
    sig_fill_recording_label_requested = pyqtSignal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent=parent)
        self._experiment_name = ""
        self._session_name = ""
        self._steps: tuple[ExperimentStep, ...] = ()
        self._current_step_index = -1
        self._snapshot = self._build_snapshot()

    def snapshot(self) -> ExperimentRuntimeSnapshot:
        return self._snapshot

    def set_experiment_name(self, value: str) -> None:
        normalized = str(value or "").strip()
        if normalized == self._experiment_name:
            return
        self._experiment_name = normalized
        self._publish_snapshot()

    def set_session_name(self, value: str) -> None:
        normalized = str(value or "").strip()
        if normalized == self._session_name:
            return
        self._session_name = normalized
        self._publish_snapshot()

    def set_steps_text(self, value: str) -> None:
        steps = self._parse_steps_text(value)
        next_index = self._resolve_current_index(len(steps))
        if steps == self._steps and next_index == self._current_step_index:
            return
        self._steps = steps
        self._current_step_index = next_index
        self._publish_snapshot()

    def suggested_recording_label(self) -> str:
        return self._snapshot.suggested_recording_label

    def request_fill_suggested_label(self) -> None:
        suggested_label = self.suggested_recording_label()
        if not suggested_label:
            return
        self.sig_fill_recording_label_requested.emit(suggested_label)

    def next_step(self) -> None:
        if self._current_step_index < 0:
            return
        next_index = min(self._current_step_index + 1, len(self._steps) - 1)
        if next_index == self._current_step_index:
            return
        self._current_step_index = next_index
        self._publish_snapshot()

    def prev_step(self) -> None:
        if self._current_step_index <= 0:
            return
        self._current_step_index -= 1
        self._publish_snapshot()

    def retry_step(self) -> None:
        self.request_fill_suggested_label()

    def _resolve_current_index(self, step_count: int) -> int:
        if step_count <= 0:
            return -1
        if self._current_step_index < 0:
            return 0
        return min(self._current_step_index, step_count - 1)

    def _publish_snapshot(self) -> None:
        snapshot = self._build_snapshot()
        if snapshot == self._snapshot:
            return
        self._snapshot = snapshot
        self.sig_snapshot_changed.emit(snapshot)

    def _build_snapshot(self) -> ExperimentRuntimeSnapshot:
        current_step: ExperimentStep | None = None
        if 0 <= self._current_step_index < len(self._steps):
            current_step = self._steps[self._current_step_index]

        suggested_recording_label = ""
        if current_step is not None and self._session_name:
            suggested_recording_label = (
                f"{self._session_name}__{current_step.label}"
                f"__step{self._current_step_index + 1:02d}"
            )

        can_retry = bool(suggested_recording_label)
        return ExperimentRuntimeSnapshot(
            experiment_name=self._experiment_name,
            session_name=self._session_name,
            steps=self._steps,
            current_step_index=self._current_step_index,
            current_step=current_step,
            suggested_recording_label=suggested_recording_label,
            can_fill_recording_label=bool(suggested_recording_label),
            can_go_previous=self._current_step_index > 0,
            can_go_next=0 <= self._current_step_index < len(self._steps) - 1,
            can_retry=can_retry,
        )

    @staticmethod
    def _parse_steps_text(value: str) -> tuple[ExperimentStep, ...]:
        labels = [line.strip() for line in str(value or "").splitlines()]
        return tuple(ExperimentStep(label=label) for label in labels if label)


__all__ = [
    "ExperimentRuntimeSnapshot",
    "ExperimentRuntimeViewModel",
    "ExperimentStep",
]
