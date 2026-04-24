from __future__ import annotations

from PyQt6.QtCore import QEvent, QObject, QPoint, QTimer
from PyQt6.QtWidgets import QWidget
from qfluentwidgets import PushButton
from qfluentwidgets import FluentIcon as FIF

from modlink_ui.bridge import QtModLinkBridge
from modlink_ui.shared import BasePage
from modlink_ui.shared.preview import StreamPreviewPanel

from .acquisition_panel import AcquisitionControlPanel
from .experiment_panel import LiveExperimentSidebar
from .experiment_runtime import ExperimentRuntimeViewModel


class LivePage(BasePage):
    """Realtime preview page for the ModLink Studio UI."""

    def __init__(self, engine: QtModLinkBridge, parent: QWidget | None = None) -> None:
        super().__init__(
            page_key="live-page",
            title="实时展示",
            description="这里会显示已启动 driver 的实时流预览，底部悬浮控制采集。",
            parent=parent,
        )
        self.engine = engine
        self.acquisition_panel = AcquisitionControlPanel(engine, self)
        self.acquisition_panel.hide()
        self.experiment_runtime = ExperimentRuntimeViewModel(self)
        self.experiment_sidebar = LiveExperimentSidebar(self.experiment_runtime, self)
        self.experiment_sidebar.hide()
        self.preview_panel = StreamPreviewPanel(engine, self.scroll_widget)
        self.preview_panel.hide()
        self._bottom_spacer = QWidget(self.scroll_widget)
        self._bottom_spacer.setFixedHeight(0)
        self.experiment_sidebar_toggle_button = PushButton("实验侧栏", self)
        self.experiment_sidebar_toggle_button.setIcon(FIF.LIBRARY)

        self.content_layout.addWidget(self.preview_panel)
        self.content_layout.addWidget(self._bottom_spacer)
        self.content_layout.addStretch(1)
        self.header_action_layout.addWidget(self.experiment_sidebar_toggle_button)
        self.acquisition_panel.raise_()
        self.experiment_sidebar.raise_()

        self.scroll_area.viewport().installEventFilter(self)
        self.acquisition_panel.installEventFilter(self)
        self.experiment_sidebar.installEventFilter(self)
        self.experiment_sidebar_toggle_button.clicked.connect(self._toggle_experiment_sidebar)
        self.experiment_sidebar.sig_close_requested.connect(self._hide_experiment_sidebar)
        self.experiment_runtime.sig_fill_recording_label_requested.connect(
            self._fill_recording_label_from_experiment_sidebar
        )
        QTimer.singleShot(0, self._sync_floating_widgets)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched in {
            self.scroll_area.viewport(),
            self.acquisition_panel,
            self.experiment_sidebar,
        } and event.type() in {
            QEvent.Type.Resize,
            QEvent.Type.Show,
            QEvent.Type.Hide,
            QEvent.Type.LayoutRequest,
        }:
            QTimer.singleShot(0, self._sync_floating_widgets)
        return super().eventFilter(watched, event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._sync_floating_widgets()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        QTimer.singleShot(0, self._activate_floating_widgets)

    def _activate_floating_widgets(self) -> None:
        if not self.isVisible():
            return
        if not self.preview_panel.isVisible():
            self.preview_panel.show()
        self._sync_floating_widgets()

    def _toggle_experiment_sidebar(self) -> None:
        if self.experiment_sidebar.isVisible():
            self._hide_experiment_sidebar()
            return
        self._show_experiment_sidebar()

    def _show_experiment_sidebar(self) -> None:
        self.experiment_sidebar.show()
        self.experiment_sidebar.raise_()
        self._sync_experiment_sidebar()

    def _hide_experiment_sidebar(self) -> None:
        self.experiment_sidebar.hide()

    def _fill_recording_label_from_experiment_sidebar(self, value: str) -> None:
        self.acquisition_panel.view_model.set_field_value("recording_label", value)

    def _sync_floating_widgets(self) -> None:
        self._sync_floating_acquisition_panel()
        self._sync_experiment_sidebar()

    def _sync_floating_acquisition_panel(self) -> None:
        viewport = self.scroll_area.viewport()
        if not viewport.isVisible():
            return

        panel_height = max(
            self.acquisition_panel.minimumSizeHint().height(),
            self.acquisition_panel.sizeHint().height(),
        )
        reserve_height = panel_height + 24
        if self._bottom_spacer.height() != reserve_height:
            self._bottom_spacer.setFixedHeight(reserve_height)

        viewport_top_left = viewport.mapTo(self, QPoint(0, 0))
        side_margin = 16
        bottom_margin = 12
        max_panel_width = 1160
        panel_width = min(
            max_panel_width,
            max(360, viewport.width() - side_margin * 2),
        )
        panel_x = viewport_top_left.x() + max(0, (viewport.width() - panel_width) // 2)
        panel_y = (
            viewport_top_left.y() + viewport.height() - panel_height - bottom_margin
        )

        self.acquisition_panel.setGeometry(
            panel_x,
            panel_y,
            panel_width,
            panel_height,
        )
        if not self.acquisition_panel.isVisible():
            self.acquisition_panel.show()
        self.acquisition_panel.raise_()

    def _sync_experiment_sidebar(self) -> None:
        viewport = self.scroll_area.viewport()
        if not viewport.isVisible() or not self.experiment_sidebar.isVisible():
            return

        viewport_top_left = viewport.mapTo(self, QPoint(0, 0))
        top_margin = 16
        side_margin = 16
        floating_gap = 16
        preferred_width = 340
        available_width = viewport.width() - side_margin * 2
        if available_width <= 0:
            return
        panel_width = min(preferred_width, available_width)
        panel_x = viewport_top_left.x() + viewport.width() - panel_width - side_margin
        panel_top = viewport_top_left.y() + top_margin
        panel_bottom_limit = viewport_top_left.y() + viewport.height() - top_margin
        acquisition_top = self.acquisition_panel.geometry().top()
        if acquisition_top > 0:
            panel_bottom_limit = min(panel_bottom_limit, acquisition_top - floating_gap)
        panel_height = panel_bottom_limit - panel_top
        if panel_height <= 0:
            return

        self.experiment_sidebar.setGeometry(
            panel_x,
            panel_top,
            panel_width,
            panel_height,
        )
        self.experiment_sidebar.raise_()
