from __future__ import annotations

import time

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    LineEdit,
    PrimaryPushButton,
    PushButton,
    SubtitleLabel,
)

from packages.modlink_core.runtime.engine import ModLinkEngine


class AcquisitionControlPanel(QFrame):
    """Acquisition entry panel backed by ``ModLinkEngine``."""

    def __init__(self, engine: ModLinkEngine, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.engine = engine
        self._last_event_text = "等待采集状态更新"

        self.setObjectName("acquisition-control-panel")
        self.setStyleSheet("""
            QFrame#acquisition-control-panel {
                background: rgba(255, 255, 255, 0.84);
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: 16px;
            }
            QLabel#acquisition-error-label {
                color: #b42318;
            }
            """)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 18, 20, 18)
        root_layout.setSpacing(14)

        title_label = SubtitleLabel("采集入口", self)
        description_label = BodyLabel(
            "这一层只负责把用户意图转成 engine.acquisition 的公开操作。",
            self,
        )
        description_label.setWordWrap(True)

        header_row = QHBoxLayout()
        header_row.setSpacing(12)
        header_row.addWidget(title_label)
        header_row.addStretch(1)

        self.status_chip = QLabel("IDLE", self)
        self.status_chip.setObjectName("acquisition-status-chip")
        self.status_chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._set_status_chip_style("rgba(0, 0, 0, 0.06)")

        self.status_summary = CaptionLabel(self._last_event_text, self)
        self.status_summary.setWordWrap(True)

        self.error_label = QLabel("", self)
        self.error_label.setObjectName("acquisition-error-label")
        self.error_label.setWordWrap(True)
        self.error_label.hide()

        self.session_name_input = LineEdit(self)
        self.session_name_input.setPlaceholderText("session 名称，留空则自动生成")
        self.session_name_input.setClearButtonEnabled(True)
        self.session_name_input.setFixedHeight(36)

        self.recording_label_input = LineEdit(self)
        self.recording_label_input.setPlaceholderText("recording label，可选")
        self.recording_label_input.setClearButtonEnabled(True)
        self.recording_label_input.setFixedHeight(36)

        self.marker_input = LineEdit(self)
        self.marker_input.setPlaceholderText("Marker 文本，留空则使用当前 session 名称")
        self.marker_input.setClearButtonEnabled(True)
        self.marker_input.setFixedHeight(36)

        form = QGridLayout()
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)
        form.addWidget(CaptionLabel("Session", self), 0, 0)
        form.addWidget(self.session_name_input, 1, 0)
        form.addWidget(CaptionLabel("Label", self), 0, 1)
        form.addWidget(self.recording_label_input, 1, 1)
        form.addWidget(CaptionLabel("Marker", self), 2, 0)
        form.addWidget(self.marker_input, 3, 0, 1, 2)

        self.start_button = PrimaryPushButton("开始采集", self)
        self.start_button.setMinimumWidth(148)
        self.start_button.setFixedHeight(36)
        self.start_button.clicked.connect(self._toggle_recording)

        self.marker_button = PushButton("插入 Marker", self)
        self.marker_button.setMinimumWidth(124)
        self.marker_button.setFixedHeight(36)
        self.marker_button.clicked.connect(self._insert_marker)

        self.stop_button = PushButton("停止采集", self)
        self.stop_button.setMinimumWidth(124)
        self.stop_button.setFixedHeight(36)
        self.stop_button.clicked.connect(self._stop_recording)

        action_row = QHBoxLayout()
        action_row.setSpacing(10)
        action_row.addWidget(self.marker_button)
        action_row.addWidget(self.stop_button)
        action_row.addStretch(1)
        action_row.addWidget(self.start_button)

        root_layout.addLayout(header_row)
        root_layout.addWidget(description_label)
        root_layout.addWidget(self.status_chip, alignment=Qt.AlignmentFlag.AlignLeft)
        root_layout.addWidget(self.status_summary)
        root_layout.addWidget(self.error_label)
        root_layout.addLayout(form)
        root_layout.addLayout(action_row)

        self.engine.acquisition.sig_state_changed.connect(self._on_state_changed)
        self.engine.acquisition.sig_event.connect(self._on_event)
        self.engine.acquisition.sig_error.connect(self._on_error)

        self._sync_ui_state(self.engine.acquisition.state)

    def _toggle_recording(self) -> None:
        if self.engine.acquisition.is_recording:
            self.engine.acquisition.stop_recording()
            return

        session_name = self._normalized_session_name()
        recording_label = self._normalized_recording_label()
        self.engine.acquisition.start_recording(session_name, recording_label)

    def _stop_recording(self) -> None:
        self.engine.acquisition.stop_recording()

    def _insert_marker(self) -> None:
        marker_label = (
            self.marker_input.text().strip() or self._normalized_session_name()
        )
        self.engine.acquisition.add_marker(marker_label)

    def _normalized_session_name(self) -> str:
        text = self.session_name_input.text().strip()
        if text:
            return text
        generated = time.strftime("session_%Y%m%d_%H%M%S")
        self.session_name_input.setText(generated)
        return generated

    def _normalized_recording_label(self) -> str | None:
        text = self.recording_label_input.text().strip()
        return text or None

    def _on_state_changed(self, state: str) -> None:
        self._sync_ui_state(state)

    def _on_event(self, event: object) -> None:
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
            self._last_event_text = self._format_event_text(
                "采集已开始",
                session_name=session_name,
                recording_label=recording_label,
            )
        elif event_kind == "recording_stopped":
            self._last_event_text = self._format_event_text("采集已停止")
        elif event_kind == "marker_added":
            marker_label = event.get("label", "") if isinstance(event, dict) else ""
            self._last_event_text = self._format_event_text(
                "Marker 已写入",
                detail=marker_label or "未命名",
            )
        elif event_kind == "segment_added":
            segment_label = event.get("label", "") if isinstance(event, dict) else ""
            self._last_event_text = self._format_event_text(
                "Segment 已写入",
                detail=segment_label or "未命名",
            )
        else:
            self._last_event_text = self._format_event_text("采集事件已更新")

        self.status_summary.setText(self._last_event_text)

    def _on_error(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.show()

    def _sync_ui_state(self, state: str) -> None:
        normalized_state = str(state or "idle").strip().lower()
        self.status_chip.setText(normalized_state.upper())

        is_recording = self.engine.acquisition.is_recording
        self.start_button.setText("停止采集" if is_recording else "开始采集")
        self.marker_button.setEnabled(is_recording)
        self.stop_button.setEnabled(is_recording)
        self.session_name_input.setEnabled(not is_recording)
        self.recording_label_input.setEnabled(not is_recording)
        self.error_label.hide()

        if normalized_state == "recording":
            self._set_status_chip_style("rgba(21, 128, 61, 0.12)")
        elif normalized_state == "connecting":
            self._set_status_chip_style("rgba(180, 83, 9, 0.12)")
        elif normalized_state == "error":
            self._set_status_chip_style("rgba(185, 28, 28, 0.12)")
        else:
            self._set_status_chip_style("rgba(0, 0, 0, 0.06)")

        self.status_summary.setText(self._last_event_text)

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
            fragments.append(f"Session: {session_name}")
        if recording_label:
            fragments.append(f"Label: {recording_label}")
        if detail:
            fragments.append(f"Detail: {detail}")
        return " | ".join(fragments)

    def _set_status_chip_style(self, background_color: str) -> None:
        self.status_chip.setStyleSheet(f"""
            QLabel#acquisition-status-chip {{
                padding: 4px 10px;
                border-radius: 10px;
                background: {background_color};
            }}
            """)
