from __future__ import annotations

from collections.abc import Iterable
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from PyQt6.QtCore import QObject, pyqtSignal
from qfluentwidgets import FluentIcon as FIF

from modlink_core.runtime.engine import ModLinkEngine
from modlink_core.settings.service import SettingsService

ActionKind = Literal["primary", "secondary"]
LayoutMode = Literal["detailed", "compact"]

UI_ACQUISITION_LAYOUT_MODE_KEY = "ui.acquisition.layout_mode"
DEFAULT_ACQUISITION_LAYOUT_MODE: LayoutMode = "detailed"
UI_LABELS_KEY = "ui.labels.items"
DEFAULT_LABELS = ("default",)


def normalize_acquisition_layout_mode(value: object) -> LayoutMode:
    normalized = str(value or "").strip().lower()
    if normalized in {"detailed", "compact"}:
        return normalized  # type: ignore[return-value]
    return DEFAULT_ACQUISITION_LAYOUT_MODE


def normalize_labels(values: object) -> tuple[str, ...]:
    if not isinstance(values, Iterable) or isinstance(values, (str, bytes)):
        return DEFAULT_LABELS

    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        normalized.append(text)
        seen.add(text)

    return tuple(normalized) or DEFAULT_LABELS


@dataclass(frozen=True, slots=True)
class AcquisitionFieldState:
    key: str
    label: str
    placeholder: str
    value: str = ""
    read_only: bool = False


@dataclass(frozen=True, slots=True)
class AcquisitionActionState:
    key: str
    text: str
    icon: object
    kind: ActionKind = "secondary"


@dataclass(frozen=True, slots=True)
class AcquisitionPanelState:
    fields: tuple[AcquisitionFieldState, ...]
    primary_action: AcquisitionActionState
    secondary_actions: tuple[AcquisitionActionState, ...]


@dataclass(slots=True)
class AcquisitionFormValues:
    session_name: str = ""
    recording_label: str = ""
    marker_label: str = ""
    segment_label: str = ""


class AcquisitionViewModel(QObject):
    sig_field_value_changed = pyqtSignal(str, str)
    sig_recording_changed = pyqtSignal(bool)
    sig_segment_active_changed = pyqtSignal(bool)
    sig_error = pyqtSignal(str)

    def __init__(
        self,
        engine: ModLinkEngine,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.engine = engine
        self._state = self._build_default_state()
        self._values = AcquisitionFormValues(
            session_name=self._state.fields[0].value,
            recording_label=self._state.fields[1].value,
            marker_label=self._state.fields[2].value,
            segment_label=self._state.fields[3].value,
        )
        self._pending_segment_start_ns: int | None = None
        self._settings = SettingsService.instance()
        self._layout_mode: LayoutMode = normalize_acquisition_layout_mode(
            self._settings.get(
                UI_ACQUISITION_LAYOUT_MODE_KEY,
                DEFAULT_ACQUISITION_LAYOUT_MODE,
            )
        )

        self.engine.acquisition.sig_state_changed.connect(self._on_state_changed)
        self.engine.acquisition.sig_error.connect(self._on_error)

    @property
    def state(self) -> AcquisitionPanelState:
        return self._state

    @property
    def layout_mode(self) -> LayoutMode:
        return self._layout_mode

    @property
    def is_recording(self) -> bool:
        return self.engine.acquisition.is_recording

    @property
    def is_segment_active(self) -> bool:
        return self._pending_segment_start_ns is not None

    @staticmethod
    def _build_default_state() -> AcquisitionPanelState:
        return AcquisitionPanelState(
            fields=(
                AcquisitionFieldState(
                    key="session_name",
                    label="Session 名称",
                    placeholder="例如 session_20260324_001",
                ),
                AcquisitionFieldState(
                    key="recording_label",
                    label="录制标签",
                    placeholder="例如 resting_state",
                ),
                AcquisitionFieldState(
                    key="marker_label",
                    label="Marker 标签",
                    placeholder="例如 blink、event_a、cue",
                ),
                AcquisitionFieldState(
                    key="segment_label",
                    label="区间标签",
                    placeholder="例如 trial_a、focus、rest",
                ),
            ),
            primary_action=AcquisitionActionState(
                key="toggle_recording",
                text="开始采集",
                icon=FIF.PLAY_SOLID,
                kind="primary",
            ),
            secondary_actions=(
                AcquisitionActionState(
                    key="insert_marker",
                    text="插入 Marker",
                    icon=FIF.TAG,
                ),
                AcquisitionActionState(
                    key="toggle_segment",
                    text="开始区间",
                    icon=FIF.STOP_WATCH,
                ),
                AcquisitionActionState(
                    key="reset_segment",
                    text="清空区间",
                    icon=FIF.BROOM,
                ),
            ),
        )

    def get_field_value(self, key: str) -> str:
        if not hasattr(self._values, key):
            raise KeyError(f"Unknown acquisition field: {key}")
        return str(getattr(self._values, key))

    def update_field_value_from_ui(self, key: str, value: str) -> None:
        self._update_field_value(key, value, notify=False)

    def set_field_value(self, key: str, value: str) -> None:
        self._update_field_value(key, value, notify=True)

    def _update_field_value(self, key: str, value: str, *, notify: bool) -> None:
        if not hasattr(self._values, key):
            raise KeyError(f"Unknown acquisition field: {key}")

        normalized_value = str(value)
        if getattr(self._values, key) == normalized_value:
            return

        setattr(self._values, key, normalized_value)
        if notify:
            self.sig_field_value_changed.emit(key, normalized_value)

    def toggle_layout_mode(self) -> LayoutMode:
        next_mode: LayoutMode = (
            "compact" if self._layout_mode == "detailed" else "detailed"
        )
        return self.set_layout_mode(next_mode)

    def set_layout_mode(self, mode: LayoutMode) -> LayoutMode:
        self._layout_mode = normalize_acquisition_layout_mode(mode)
        self._settings.set(UI_ACQUISITION_LAYOUT_MODE_KEY, self._layout_mode)
        return self._layout_mode

    def get_recording_labels(self) -> tuple[str, ...]:
        return normalize_labels(self._settings.get(UI_LABELS_KEY, DEFAULT_LABELS))

    def build_output_directory(self, session_name: str | None = None) -> str:
        root_dir = Path(self.engine.acquisition.root_dir)
        preview_session_name = session_name or self._values.session_name or "<session_name>"
        return str(root_dir / f"session_{preview_session_name}")

    def current_primary_action(self) -> AcquisitionActionState:
        if self.is_recording:
            return AcquisitionActionState(
                key="toggle_recording",
                text="停止采集",
                icon=FIF.PAUSE_BOLD,
                kind="primary",
            )
        return self._state.primary_action

    def current_toggle_segment_action(self) -> AcquisitionActionState:
        if self.is_segment_active:
            return AcquisitionActionState(
                key="toggle_segment",
                text="结束区间",
                icon=FIF.STOP_WATCH,
            )
        return self._state.secondary_actions[1]

    def request_toggle_recording(self) -> None:
        if self.is_recording:
            self._clear_pending_segment(notify=True)
            self.engine.acquisition.stop_recording()
            return

        session_name = self.get_field_value("session_name").strip()
        if not session_name:
            session_name = time.strftime("session_%Y%m%d_%H%M%S")
            self.set_field_value("session_name", session_name)

        recording_label = self.get_field_value("recording_label").strip() or None
        self.engine.acquisition.start_recording(session_name, recording_label)

    def request_insert_marker(self) -> None:
        session_name = self.get_field_value("session_name").strip()
        if not session_name:
            session_name = time.strftime("session_%Y%m%d_%H%M%S")
            self.set_field_value("session_name", session_name)

        marker_label = self.get_field_value("marker_label").strip() or session_name
        self.engine.acquisition.add_marker(marker_label)

    def request_toggle_segment(self) -> None:
        if self._pending_segment_start_ns is None:
            self._pending_segment_start_ns = time.time_ns()
            self.sig_segment_active_changed.emit(True)
            return

        start_ns = self._pending_segment_start_ns
        end_ns = time.time_ns()
        segment_label = self.get_field_value("segment_label").strip() or None
        self._clear_pending_segment(notify=True)
        self.engine.acquisition.add_segment(
            start_ns=start_ns,
            end_ns=end_ns,
            label=segment_label,
        )

    def request_reset_segment(self) -> None:
        self._clear_pending_segment(notify=True)

    def _clear_pending_segment(self, *, notify: bool) -> None:
        if self._pending_segment_start_ns is None:
            return
        self._pending_segment_start_ns = None
        if notify:
            self.sig_segment_active_changed.emit(False)

    def _on_state_changed(self, state: str) -> None:
        if str(state or "").strip().lower() != "recording":
            self._clear_pending_segment(notify=True)
        self.sig_recording_changed.emit(self.is_recording)

    def _on_error(self, message: str) -> None:
        self.sig_error.emit(self._format_error_message(message))

    def _format_error_message(self, message: str) -> str:
        normalized = str(message or "").strip()
        if not normalized:
            return "发生了未知采集错误。"

        prefix, separator, detail = normalized.partition(":")
        friendly = {
            "ACQ_NOT_STARTED": "采集后端还没有启动。",
            "ACQ_ALREADY_RECORDING": "采集已经在进行中。",
            "ACQ_INVALID_SESSION_NAME": "Session 名称不能为空。",
            "ACQ_MARKER_REJECTED": "请先开始采集，再写入 Marker。",
            "ACQ_SEGMENT_REJECTED": "请先开始采集，再记录区间。",
            "ACQ_SEGMENT_START_REQUIRED": "请先点击“开始区间”。",
            "ACQ_INVALID_SEGMENT_RANGE": "区间时间范围无效。",
            "ACQ_STOP_IGNORED": "当前没有进行中的采集。",
            "ACQ_START_FAILED": "开始采集失败。",
            "ACQ_STOP_FAILED": "停止采集失败。",
            "ACQ_WRITE_FAILED": "写入采集数据失败。",
            "ACQ_MARKER_FAILED": "写入 Marker 失败。",
            "ACQ_SEGMENT_FAILED": "写入区间失败。",
            "ACQ_STOP_TIMEOUT": "停止采集超时。",
        }.get(prefix.strip())
        if friendly is None:
            cleaned = normalized.strip()
            if len(cleaned) <= 140:
                return cleaned
            head = max(12, 140 - 18)
            return f"{cleaned[:head]} ..."

        cleaned_detail = detail.strip() if separator else ""
        if not cleaned_detail or cleaned_detail == "not recording":
            return friendly

        if len(cleaned_detail) > 96:
            head = max(12, 96 - 18)
            cleaned_detail = f"{cleaned_detail[:head]} ..."
        return f"{friendly} 详情：{cleaned_detail}"


__all__ = [
    "AcquisitionActionState",
    "AcquisitionFieldState",
    "AcquisitionFormValues",
    "AcquisitionPanelState",
    "AcquisitionViewModel",
]
