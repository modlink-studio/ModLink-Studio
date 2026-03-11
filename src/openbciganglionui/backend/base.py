from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal

from .models import ConnectConfig, DeviceState, RecordSession


class GanglionBackendBase(QObject):
    sig_state = pyqtSignal(object)
    sig_stream = pyqtSignal(object)
    sig_marker = pyqtSignal(object)
    sig_record = pyqtSignal(object)
    sig_error = pyqtSignal(object)
    sig_search = pyqtSignal(object)
    sig_labels = pyqtSignal(object)

    def _debug_call(self, method: str, **kwargs: object) -> None:
        if kwargs:
            args_text = ", ".join(f"{key}={value!r}" for key, value in kwargs.items())
            print(f"[GanglionBackendBase] {method} called with {args_text}")
            return
        print(f"[GanglionBackendBase] {method} called")

    @property
    def state(self) -> DeviceState:
        self._debug_call("state")
        return DeviceState.DISCONNECTED

    @property
    def device_name(self) -> str:
        self._debug_call("device_name")
        return self.__class__.__name__

    @property
    def device_address(self) -> str:
        self._debug_call("device_address")
        return ""

    @property
    def labels(self) -> tuple[str, ...]:
        self._debug_call("labels")
        return ()

    def connect_device(self, config: Optional[ConnectConfig] = None) -> None:
        self._debug_call("connect_device", config=config)

    def search_devices(self, method: str) -> None:
        self._debug_call("search_devices", method=method)

    def load_labels(self) -> None:
        self._debug_call("load_labels")

    def add_label(self, label: str) -> None:
        self._debug_call("add_label", label=label)

    def remove_label(self, label: str) -> None:
        self._debug_call("remove_label", label=label)

    def disconnect_device(self) -> None:
        self._debug_call("disconnect_device")

    def start_preview(self) -> None:
        self._debug_call("start_preview")

    def stop_preview(self) -> None:
        self._debug_call("stop_preview")

    def start_record(self, session: Optional[RecordSession] = None) -> None:
        self._debug_call("start_record", session=session)

    def stop_record(self) -> None:
        self._debug_call("stop_record")

    def add_marker(self, label: str, note: str = "", source: str = "ui") -> None:
        self._debug_call("add_marker", label=label, note=note, source=source)
