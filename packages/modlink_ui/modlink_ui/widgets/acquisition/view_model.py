import time
from pathlib import Path

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from modlink_core.runtime.engine import ModLinkEngine
from modlink_core.settings.service import SettingsService
from ...ui_settings import UI_LABELS_KEY, load_labels


class AcquisitionViewModel(QObject):
    """View model for the acquisition control panel, separating state and business logic from UI."""

    sig_recording_changed = pyqtSignal(bool)
    sig_segment_active_changed = pyqtSignal(bool)
    sig_feedback_changed = pyqtSignal(str)
    sig_error = pyqtSignal(str)
    sig_labels_changed = pyqtSignal(list)
    sig_session_name_generated = pyqtSignal(str)

    def __init__(self, engine: ModLinkEngine, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.engine = engine
        self._settings = SettingsService.instance()
        self._labels = load_labels(self._settings)

        self._pending_segment_start_ns: int | None = None
        self._last_event_text = "空闲中。"
        self._last_error_text: str | None = None

        self._segment_timer = QTimer(self)
        self._segment_timer.setInterval(250)
        self._segment_timer.timeout.connect(self._refresh_feedback)

        self.engine.acquisition.sig_state_changed.connect(self._on_state_changed)
        self.engine.acquisition.sig_event.connect(self._on_event)
        self.engine.acquisition.sig_error.connect(self._on_error)
        self._settings.sig_setting_changed.connect(self._on_setting_changed)

    @property
    def is_recording(self) -> bool:
        return self.engine.acquisition.is_recording

    @property
    def is_segment_active(self) -> bool:
        return self._pending_segment_start_ns is not None

    @property
    def labels(self) -> list[str]:
        return list(self._labels)

    def request_toggle_recording(
        self, current_session: str, current_label: str
    ) -> None:
        if self.is_recording:
            self._pending_segment_start_ns = None
            self._segment_timer.stop()
            self.engine.acquisition.stop_recording()
            return

        session_name = current_session.strip()
        if not session_name:
            session_name = time.strftime("session_%Y%m%d_%H%M%S")
            self.sig_session_name_generated.emit(session_name)

        self.engine.acquisition.start_recording(
            session_name,
            current_label.strip() or None,
        )

    def request_insert_marker(self, current_session: str, annot_label: str) -> None:
        session_name = current_session.strip()
        if not session_name:
            session_name = time.strftime("session_%Y%m%d_%H%M%S")
            self.sig_session_name_generated.emit(session_name)

        marker_label = annot_label.strip() or session_name
        self.engine.acquisition.add_marker(marker_label)

    def request_toggle_segment(self, annot_label: str) -> None:
        if self._pending_segment_start_ns is None:
            self._pending_segment_start_ns = time.time_ns()
            self._last_event_text = "区间起点已记录。"
            self._segment_timer.start()
            self._refresh_feedback()
            self.sig_segment_active_changed.emit(True)
            return

        end_ns = time.time_ns()
        segment_label = annot_label.strip() or None
        self.engine.acquisition.add_segment(
            start_ns=self._pending_segment_start_ns,
            end_ns=end_ns,
            label=segment_label,
        )
        self._pending_segment_start_ns = None
        self._segment_timer.stop()
        self.sig_segment_active_changed.emit(False)

    def request_reset_segment(self) -> None:
        self._pending_segment_start_ns = None
        self._segment_timer.stop()
        self._last_event_text = "区间起点已清空。"
        self._refresh_feedback()
        self.sig_segment_active_changed.emit(False)

    def _on_state_changed(self, state: str) -> None:
        if str(state or "").strip().lower() != "recording":
            self._pending_segment_start_ns = None
            self._segment_timer.stop()
            self.sig_segment_active_changed.emit(False)
        self.sig_recording_changed.emit(self.is_recording)

    def _on_event(self, event: object) -> None:
        self._last_error_text = None

        event_kind = getattr(event, "kind", None)
        if isinstance(event, dict):
            event_kind = event.get("kind")

        if event_kind == "recording_started":
            session_name = (
                event.get("session_name", "") if isinstance(event, dict) else ""
            )
            recording_label = (
                event.get("recording_label") if isinstance(event, dict) else None
            )
            recording_path = (
                event.get("recording_path") if isinstance(event, dict) else None
            )
            self._last_event_text = self._format_event_text(
                "采集已开始",
                session_name=session_name,
                recording_label=recording_label,
                detail=(
                    Path(recording_path).name
                    if isinstance(recording_path, str) and recording_path.strip()
                    else None
                ),
            )
        elif event_kind == "recording_stopped":
            self._last_event_text = "采集已停止。"
        elif event_kind == "marker_added":
            marker_label = event.get("label", "") if isinstance(event, dict) else ""
            self._last_event_text = self._format_event_text(
                "Marker 已写入",
                detail=marker_label or "未命名",
            )
        elif event_kind == "segment_added":
            segment_label = event.get("label", "") if isinstance(event, dict) else ""
            start_ns = event.get("start_ns") if isinstance(event, dict) else None
            end_ns = event.get("end_ns") if isinstance(event, dict) else None
            detail = segment_label or "未命名"
            if isinstance(start_ns, int) and isinstance(end_ns, int):
                duration_ms = max(0, (end_ns - start_ns) / 1_000_000)
                detail = f"{detail} · {self._format_duration(duration_ms)}"
            self._last_event_text = self._format_event_text("区间已写入", detail=detail)
        else:
            self._last_event_text = "采集状态已更新。"

        self._refresh_feedback()

    def _on_error(self, message: str) -> None:
        self._last_error_text = self._format_error_message(message)
        self._last_event_text = "操作失败，请查看右上角提示。"
        self.sig_error.emit(self._last_error_text)
        self._refresh_feedback()

    def _on_setting_changed(self, event: object) -> None:
        if getattr(event, "key", None) != UI_LABELS_KEY:
            return
        self._labels = load_labels(self._settings)
        self.sig_labels_changed.emit(list(self._labels))

    def _refresh_feedback(self) -> None:
        summary_text = self._last_event_text
        segment_hint = self._segment_hint_text()
        if segment_hint and not self._last_error_text:
            summary_text = f"{summary_text} · {segment_hint}"

        self.sig_feedback_changed.emit(summary_text)

    def _segment_hint_text(self) -> str | None:
        if self._pending_segment_start_ns is None:
            return None
        elapsed_ms = max(
            0, (time.time_ns() - self._pending_segment_start_ns) / 1_000_000
        )
        return f"区间进行中 {self._format_duration(elapsed_ms)}"

    def _format_event_text(
        self,
        headline: str,
        *,
        session_name: str | None = None,
        recording_label: str | None = None,
        detail: str | None = None,
    ) -> str:
        fragments = [headline]
        if session_name:
            fragments.append(session_name)
        if recording_label:
            fragments.append(f"Label {recording_label}")
        if detail:
            fragments.append(detail)
        return " · ".join(fragments)

    def _format_duration(self, duration_ms: float) -> str:
        if duration_ms < 1_000:
            return f"{duration_ms:.0f} ms"
        if duration_ms < 60_000:
            return f"{duration_ms / 1_000:.1f} s"
        return f"{duration_ms / 60_000:.1f} min"

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
            cleaned = str(normalized).strip()
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
