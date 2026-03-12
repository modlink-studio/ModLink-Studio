from pathlib import Path

from PyQt6.QtGui import QIcon
from qfluentwidgets import FluentIcon as FIF, FluentWindow, NavigationItemPosition

from ...backend import GanglionBackendBase, StateEvent
from ..pages import AcquisitionPage, GuidePage, SettingsPage
from ..settings import AppSettingsStore, SettingsManager


class MainWindow(FluentWindow):
    def __init__(
        self,
        backend: GanglionBackendBase,
        settings_store: AppSettingsStore,
    ) -> None:
        super().__init__()
        self.backend = backend
        self.settings_manager = SettingsManager(settings_store=settings_store, parent=self)

        self.acquisition_page = AcquisitionPage(
            backend=self.backend,
            settings_manager=self.settings_manager,
            parent=self,
        )
        self.settings_page = SettingsPage(
            backend=self.backend,
            settings_manager=self.settings_manager,
            parent=self,
        )
        self.guide_page = GuidePage(parent=self)

        self.addSubInterface(self.acquisition_page, FIF.PLAY, "采集")
        self.navigationInterface.addSeparator()
        self.addSubInterface(
            self.guide_page,
            FIF.INFO,
            "说明",
            NavigationItemPosition.BOTTOM,
        )
        self.addSubInterface(
            self.settings_page,
            FIF.SETTING,
            "设置",
            NavigationItemPosition.BOTTOM,
        )

        self.resize(792, 516)
        self.setMinimumWidth(792)
        self.setWindowIcon(
            QIcon(str(Path(__file__).resolve().parents[2] / "assets" / "app_icon.png"))
        )
        self.setWindowTitle("OpenBCI Ganglion UI")

        self.navigationInterface.setIndicatorAnimationEnabled(False)
        self.stackedWidget.setAnimationEnabled(False)
        self.backend.sig_state.connect(self._on_state_changed)
        self._on_state_changed(
            StateEvent(
                state=self.backend.state,
                ts=0.0,
                message="Frontend attached to backend",
                device_name=self.backend.device_name,
                device_address=self.backend.device_address,
            )
        )

    def _on_state_changed(self, event: StateEvent) -> None:
        self.acquisition_page.update_state(event)
        self.setWindowTitle(f"OpenBCI Ganglion UI [{event.state.value}]")

    def switchTo(self, interface) -> None:
        self.stackedWidget.setAnimationEnabled(False)
        super().switchTo(interface)
