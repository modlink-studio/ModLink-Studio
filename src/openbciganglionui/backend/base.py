from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal

from .models import ConnectConfig, DeviceState, RecordSession


class GanglionBackendBase(QObject):
    """Contract for all backend implementations used by the UI layer.

    The UI is allowed to do exactly two kinds of things with a backend object:

    1. Call the public intent methods defined on this class.
    2. Subscribe to the signals defined on this class and consume payloads from
       ``backend.models``.

    The UI must not depend on a concrete backend implementation, private
    backend attributes, or backend-specific timing quirks unless those quirks
    are explicitly documented as part of the contract.

    Signal payload contract:
    - ``sig_state``: emits ``StateEvent``
    - ``sig_stream``: emits ``StreamChunk``
    - ``sig_marker``: emits ``MarkerEvent``
    - ``sig_record``: emits ``RecordEvent``
    - ``sig_error``: emits ``ErrorEvent``
    - ``sig_search``: emits ``SearchEvent``
    - ``sig_labels``: emits ``LabelsEvent``
    - ``sig_save_dir``: emits ``SaveDirEvent``

    Method contract:
    - Public methods are intents. They return ``None`` and report accepted work,
      rejected work, and state transitions via signals.
    - Unless a subclass documents otherwise, methods should be idempotent when
      called in an invalid state. Invalid calls may be ignored or converted to
      ``sig_error`` events, but they must not mutate the runtime into an
      inconsistent state.
    """

    sig_state = pyqtSignal(object)
    sig_stream = pyqtSignal(object)
    sig_marker = pyqtSignal(object)
    sig_record = pyqtSignal(object)
    sig_error = pyqtSignal(object)
    sig_search = pyqtSignal(object)
    sig_labels = pyqtSignal(object)
    sig_save_dir = pyqtSignal(object)

    def _not_implemented(self, member: str) -> None:
        raise NotImplementedError(
            f"{type(self).__name__} must implement GanglionBackendBase.{member}"
        )

    @property
    def state(self) -> DeviceState:
        """Return the backend's latest stable device state snapshot."""

        self._not_implemented("state")

    @property
    def device_name(self) -> str:
        """Return the latest known device name for UI display."""

        self._not_implemented("device_name")

    @property
    def device_address(self) -> str:
        """Return the latest known device address for UI display."""

        self._not_implemented("device_address")

    @property
    def labels(self) -> tuple[str, ...]:
        """Return the latest in-memory label snapshot."""

        self._not_implemented("labels")

    @property
    def default_save_dir(self) -> str:
        """Return the latest in-memory default recording directory."""

        self._not_implemented("default_save_dir")

    def connect_device(self, config: ConnectConfig | None = None) -> None:
        """Request a device connection attempt.

        Expected common behavior:
        - Emits ``CONNECTING`` via ``sig_state`` when a connection attempt starts.
        - Eventually emits either a connected state or an error state.
        - Any backend-specific post-connect behavior, such as auto-preview, must
          be documented by the concrete implementation.
        """

        self._not_implemented("connect_device")

    def search_devices(self, method: str) -> None:
        """Request a device search using a backend-defined transport method."""

        self._not_implemented("search_devices")

    def load_labels(self) -> None:
        """Load labels from the backend's persistence layer and emit ``sig_labels``."""

        self._not_implemented("load_labels")

    def add_label(self, label: str) -> None:
        """Add a label and emit the resulting label snapshot via ``sig_labels``."""

        self._not_implemented("add_label")

    def remove_label(self, label: str) -> None:
        """Remove a label and emit the resulting label snapshot via ``sig_labels``."""

        self._not_implemented("remove_label")

    def load_save_dir(self) -> None:
        """Load the persisted default save directory and emit ``sig_save_dir``."""

        self._not_implemented("load_save_dir")

    def set_save_dir(self, save_dir: str) -> None:
        """Persist the default save directory and emit ``sig_save_dir``."""

        self._not_implemented("set_save_dir")

    def disconnect_device(self) -> None:
        """Request a device disconnect.

        Expected common behavior:
        - Stops any active streaming or recording work.
        - Emits ``DISCONNECTING`` when accepted.
        - Eventually emits ``DISCONNECTED``.
        """

        self._not_implemented("disconnect_device")

    def start_preview(self) -> None:
        """Request transition into preview/streaming mode."""

        self._not_implemented("start_preview")

    def stop_preview(self) -> None:
        """Request transition out of preview/streaming mode."""

        self._not_implemented("stop_preview")

    def start_record(self, session: RecordSession | None = None) -> None:
        """Request transition into recording mode.

        Concrete implementations should document which prior state is required
        before recording can begin.
        """

        self._not_implemented("start_record")

    def stop_record(self) -> None:
        """Request transition out of recording mode."""

        self._not_implemented("stop_record")

    def add_marker(self, label: str, note: str = "", source: str = "ui") -> None:
        """Request insertion of a marker into the active stream/recording session."""

        self._not_implemented("add_marker")
