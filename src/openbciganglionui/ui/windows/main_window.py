from qfluentwidgets import FluentIcon as FIF, FluentWindow, NavigationItemPosition

from ...backend import GanglionBackendBase, StateEvent
from ..pages import AcquisitionPage, SettingsPage


class MainWindow(FluentWindow):
    def __init__(self, backend: GanglionBackendBase) -> None:
        super().__init__()
        self.backend = backend

        self.acquisition_page = AcquisitionPage(backend=self.backend, parent=self)
        self.settings_page = SettingsPage(backend=self.backend, parent=self)

        self.addSubInterface(self.acquisition_page, FIF.PLAY, "采集")
        self.navigationInterface.addSeparator()
        self.addSubInterface(
            self.settings_page,
            FIF.SETTING,
            "设置",
            NavigationItemPosition.BOTTOM,
        )

        self.resize(1320, 860)
        self.setMinimumWidth(1040)
        self.setWindowTitle("OpenBCI Ganglion UI")

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
