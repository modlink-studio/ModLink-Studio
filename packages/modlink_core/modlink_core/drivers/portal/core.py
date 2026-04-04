from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Future
from concurrent.futures import TimeoutError as FutureTimeoutError

from modlink_sdk import DriverFactory, FrameEnvelope, SearchResult, StreamDescriptor

from ...events import (
    BackendEvent,
    DriverConnectionLostEvent,
    DriverExecutorFailedEvent,
    DriverSnapshot,
)
from .executor import DriverExecutor
from .session import DriverSession
from .state import DeviceState


class DriverPortal:
    """Public driver-facing gateway used by the rest of the system."""

    def __init__(
        self,
        driver_factory: DriverFactory,
        *,
        publish_event: Callable[[BackendEvent], None],
        frame_sink: Callable[[FrameEnvelope], object | None] | None = None,
        parent: object | None = None,
    ) -> None:
        self._parent = parent
        self._publish_event = publish_event
        self._frame_sink = frame_sink
        self._session = DriverSession(
            driver_factory,
            on_connection_lost=self._on_connection_lost,
            on_frame=self._on_session_frame,
            parent=parent,
        )
        self._executor = DriverExecutor(
            f"modlink.driver.{self.driver_id.strip()}",
            on_exit=self._on_executor_exit,
        )

    @property
    def driver_id(self) -> str:
        return self._session.driver_id

    @property
    def display_name(self) -> str:
        return self._session.display_name

    @property
    def supported_providers(self) -> tuple[str, ...]:
        return self._session.supported_providers

    @property
    def is_running(self) -> bool:
        return self._executor.is_running

    @property
    def is_connected(self) -> bool:
        return self._session.state.is_connected

    @property
    def is_streaming(self) -> bool:
        return self._session.state.is_streaming

    @property
    def state(self) -> DeviceState:
        return self._session.state

    def snapshot(self) -> DriverSnapshot:
        return self._session.snapshot(is_running=self.is_running)

    def descriptors(self) -> list[StreamDescriptor]:
        return self._session.descriptors()

    def start(self, *, timeout_ms: int = 5000) -> None:
        self._executor.start()
        startup = self._executor.submit(self._session.on_executor_started)
        try:
            startup.result(max(0.0, timeout_ms) / 1000.0)
        except FutureTimeoutError as exc:
            try:
                self.stop(timeout_ms=timeout_ms)
            except Exception:
                pass
            raise TimeoutError(
                f"driver startup timed out after {timeout_ms}ms: {self.driver_id}"
            ) from exc
        except Exception:
            try:
                self.stop(timeout_ms=timeout_ms)
            except Exception:
                pass
            raise

    def stop(self, *, timeout_ms: int = 3000) -> None:
        self._session.close_context()
        if not self.is_running:
            self._session.mark_stopped()
            return

        first_error: Exception | None = None
        shutdown = self._executor.submit(self._session.on_executor_stopped)
        try:
            shutdown.result(max(0.0, timeout_ms) / 1000.0)
        except FutureTimeoutError:
            first_error = TimeoutError(
                f"driver shutdown timed out after {timeout_ms}ms: {self.driver_id}"
            )
        except Exception as exc:
            first_error = exc

        if not self._executor.stop(timeout_ms=timeout_ms) and first_error is None:
            first_error = TimeoutError(
                f"driver executor stop timed out after {timeout_ms}ms: {self.driver_id}"
            )

        if first_error is not None:
            raise first_error

    def search(self, provider: str) -> Future[object | None]:
        return self._executor.submit(self._session.search, provider)

    def connect_device(self, config: SearchResult) -> Future[object | None]:
        return self._executor.submit(self._session.connect_device, config)

    def disconnect_device(self) -> Future[object | None]:
        return self._executor.submit(self._session.disconnect_device)

    def start_streaming(self) -> Future[object | None]:
        return self._executor.submit(self._session.start_streaming)

    def stop_streaming(self) -> Future[object | None]:
        return self._executor.submit(self._session.stop_streaming)

    def _on_session_frame(self, frame: FrameEnvelope) -> object | None:
        if self._frame_sink is None:
            return None
        return self._frame_sink(frame)

    def _on_connection_lost(self, detail: object | None) -> None:
        self._publish_event(DriverConnectionLostEvent(driver_id=self.driver_id, detail=detail))

    def _on_executor_exit(self, stop_reason: Exception | None) -> None:
        self._session.close_context()
        self._session.mark_stopped()
        if stop_reason is None:
            return
        self._publish_event(
            DriverExecutorFailedEvent(
                driver_id=self.driver_id,
                detail=f"{type(stop_reason).__name__}: {stop_reason}",
            )
        )
