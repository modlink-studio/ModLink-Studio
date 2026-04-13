from __future__ import annotations

import queue
import threading
import time
import unittest
from concurrent.futures import Future
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import numpy as np

from modlink_core import ModLinkEngine
from modlink_core.acquisition import RecordingBackend
from modlink_core.drivers import DriverPortal
from modlink_core.event_stream import BackendEventBroker, EventStreamOverflowError
from modlink_core.events import (
    DriverConnectionLostEvent,
    DriverExecutorFailedEvent,
)
from modlink_core.settings import SettingsService
from modlink_sdk import Driver, FrameEnvelope, LoopDriver, SearchResult, StreamDescriptor


class DemoLoopDriver(LoopDriver):
    supported_providers = ("demo",)
    loop_interval_ms = 10

    def __init__(self) -> None:
        super().__init__()
        self._connected = False
        self._seq = 0

    @property
    def device_id(self) -> str:
        return "demo_loop.01"

    def descriptors(self) -> list[StreamDescriptor]:
        return [
            StreamDescriptor(
                device_id=self.device_id,
                modality="demo",
                payload_type="signal",
                nominal_sample_rate_hz=100.0,
                chunk_size=4,
                channel_names=("demo",),
            )
        ]

    def search(self, provider: str) -> list[SearchResult]:
        if provider != "demo":
            raise ValueError("unsupported provider")
        return [SearchResult(title="Demo Device")]

    def connect_device(self, config: SearchResult) -> None:
        _ = config
        self._connected = True

    def disconnect_device(self) -> None:
        self._connected = False

    def on_loop_started(self) -> None:
        if not self._connected:
            raise RuntimeError("device is not connected")
        self._seq = 0

    def loop(self) -> None:
        self.emit_frame(
            FrameEnvelope(
                device_id=self.device_id,
                modality="demo",
                timestamp_ns=time.time_ns(),
                data=np.ones((1, 4), dtype=np.float32) * self._seq,
                seq=self._seq,
            )
        )
        self._seq += 1


class DemoDisconnectingDriver(Driver):
    supported_providers = ("demo",)

    def __init__(self) -> None:
        super().__init__()
        self._connected = False
        self._thread: threading.Thread | None = None

    @property
    def device_id(self) -> str:
        return "demo_disconnect.01"

    def descriptors(self) -> list[StreamDescriptor]:
        return [
            StreamDescriptor(
                device_id=self.device_id,
                modality="demo",
                payload_type="signal",
                nominal_sample_rate_hz=1.0,
                chunk_size=1,
                channel_names=("demo",),
            )
        ]

    def search(self, provider: str) -> list[SearchResult]:
        if provider != "demo":
            raise ValueError("unsupported provider")
        return [SearchResult(title="Disconnecting Device")]

    def connect_device(self, config: SearchResult) -> None:
        _ = config
        self._connected = True

    def disconnect_device(self) -> None:
        self._connected = False

    def start_streaming(self) -> None:
        if not self._connected:
            raise RuntimeError("device is not connected")
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._disconnect_later, daemon=True)
        self._thread.start()

    def stop_streaming(self) -> None:
        thread = self._thread
        self._thread = None
        if thread is not None and thread.is_alive():
            thread.join(timeout=1.0)

    def on_shutdown(self) -> None:
        self.stop_streaming()

    def _disconnect_later(self) -> None:
        time.sleep(0.03)
        self.emit_connection_lost({"code": "DEMO_CONNECTION_LOST"})


class DemoLateEmitLoopDriver(LoopDriver):
    supported_providers = ("demo",)
    loop_interval_ms = 0

    def __init__(self) -> None:
        super().__init__()
        self._connected = False
        self.loop_entered = threading.Event()
        self.allow_finish = threading.Event()
        self.late_emit_result: bool | None = None

    @property
    def device_id(self) -> str:
        return "demo_late_emit.01"

    def descriptors(self) -> list[StreamDescriptor]:
        return [
            StreamDescriptor(
                device_id=self.device_id,
                modality="demo",
                payload_type="signal",
                nominal_sample_rate_hz=1.0,
                chunk_size=1,
                channel_names=("demo",),
            )
        ]

    def search(self, provider: str) -> list[SearchResult]:
        if provider != "demo":
            raise ValueError("unsupported provider")
        return [SearchResult(title="Late Emit Device")]

    def connect_device(self, config: SearchResult) -> None:
        _ = config
        self._connected = True

    def disconnect_device(self) -> None:
        self._connected = False

    def on_loop_started(self) -> None:
        if not self._connected:
            raise RuntimeError("device is not connected")

    def loop(self) -> None:
        self.loop_entered.set()
        self.allow_finish.wait(5.0)
        self.late_emit_result = self.emit_frame(
            FrameEnvelope(
                device_id=self.device_id,
                modality="demo",
                timestamp_ns=time.time_ns(),
                data=np.ones((1, 1), dtype=np.float32),
                seq=999,
            )
        )
        self.emit_connection_lost("LATE_CONNECTION_LOST")


class DemoFailingStartupDriver(Driver):
    supported_providers = ("demo",)

    @property
    def device_id(self) -> str:
        return "demo_fail_start.01"

    def descriptors(self) -> list[StreamDescriptor]:
        return [
            StreamDescriptor(
                device_id=self.device_id,
                modality="demo",
                payload_type="signal",
                nominal_sample_rate_hz=1.0,
                chunk_size=1,
                channel_names=("demo",),
            )
        ]

    def on_runtime_started(self) -> None:
        raise RuntimeError("startup failed")

    def search(self, provider: str) -> list[SearchResult]:
        if provider != "demo":
            raise ValueError("unsupported provider")
        return [SearchResult(title="Failing Driver")]

    def connect_device(self, config: SearchResult) -> None:
        _ = config

    def disconnect_device(self) -> None:
        return

    def start_streaming(self) -> None:
        return

    def stop_streaming(self) -> None:
        return


class DemoImmediateEmitDriver(Driver):
    supported_providers = ("demo",)

    def __init__(self, device_id: str = "demo_emit.01") -> None:
        super().__init__()
        self._device_id = device_id
        self.last_emit_result: bool | None = None

    @property
    def device_id(self) -> str:
        return self._device_id

    def descriptors(self) -> list[StreamDescriptor]:
        return [
            StreamDescriptor(
                device_id=self.device_id,
                modality="demo",
                payload_type="signal",
                nominal_sample_rate_hz=1.0,
                chunk_size=1,
                channel_names=("demo",),
            )
        ]

    def search(self, provider: str) -> list[SearchResult]:
        if provider != "demo":
            raise ValueError("unsupported provider")
        return [SearchResult(title="Immediate Emit Device")]

    def connect_device(self, config: SearchResult) -> None:
        _ = config

    def disconnect_device(self) -> None:
        return

    def start_streaming(self) -> None:
        self.last_emit_result = self.emit_frame(
            FrameEnvelope(
                device_id=self.device_id,
                modality="demo",
                timestamp_ns=time.time_ns(),
                data=np.ones((1, 1), dtype=np.float32),
                seq=1,
            )
        )

    def stop_streaming(self) -> None:
        return


class DemoLifecycleHookDriver(Driver):
    supported_providers = ("demo",)

    def __init__(self, device_id: str = "demo_lifecycle.01") -> None:
        super().__init__()
        self._device_id = device_id
        self.started_thread_name: str | None = None
        self.stopped_thread_name: str | None = None
        self.stopped_event = threading.Event()

    @property
    def device_id(self) -> str:
        return self._device_id

    def descriptors(self) -> list[StreamDescriptor]:
        return [
            StreamDescriptor(
                device_id=self.device_id,
                modality="demo",
                payload_type="signal",
                nominal_sample_rate_hz=1.0,
                chunk_size=1,
                channel_names=("demo",),
            )
        ]

    def on_runtime_started(self) -> None:
        self.started_thread_name = threading.current_thread().name

    def on_shutdown(self) -> None:
        self.stopped_thread_name = threading.current_thread().name
        self.stopped_event.set()

    def search(self, provider: str) -> list[SearchResult]:
        if provider != "demo":
            raise ValueError("unsupported provider")
        return []

    def connect_device(self, config: SearchResult) -> None:
        _ = config

    def disconnect_device(self) -> None:
        return

    def start_streaming(self) -> None:
        return

    def stop_streaming(self) -> None:
        return


class DemoFailingShutdownDriver(Driver):
    supported_providers = ("demo",)

    @property
    def device_id(self) -> str:
        return "demo_fail_shutdown.01"

    def descriptors(self) -> list[StreamDescriptor]:
        return []

    def search(self, provider: str) -> list[SearchResult]:
        if provider != "demo":
            raise ValueError("unsupported provider")
        return []

    def connect_device(self, config: SearchResult) -> None:
        _ = config

    def disconnect_device(self) -> None:
        return

    def start_streaming(self) -> None:
        return

    def stop_streaming(self) -> None:
        return

    def on_shutdown(self) -> None:
        raise RuntimeError("shutdown failed")


class DemoSlowShutdownDriver(Driver):
    supported_providers = ("demo",)

    def __init__(self) -> None:
        super().__init__()
        self.allow_shutdown = threading.Event()
        self.shutdown_finished = threading.Event()

    @property
    def device_id(self) -> str:
        return "demo_slow_shutdown.01"

    def descriptors(self) -> list[StreamDescriptor]:
        return []

    def search(self, provider: str) -> list[SearchResult]:
        if provider != "demo":
            raise ValueError("unsupported provider")
        return []

    def connect_device(self, config: SearchResult) -> None:
        _ = config

    def disconnect_device(self) -> None:
        return

    def start_streaming(self) -> None:
        return

    def stop_streaming(self) -> None:
        return

    def on_shutdown(self) -> None:
        self.allow_shutdown.wait(1.0)
        self.shutdown_finished.set()


class DemoHangingStartupDriver(Driver):
    supported_providers = ("demo",)

    def __init__(self) -> None:
        super().__init__()
        self.allow_start = threading.Event()
        self.shutdown_called = threading.Event()

    @property
    def device_id(self) -> str:
        return "demo_hanging_start.01"

    def descriptors(self) -> list[StreamDescriptor]:
        return [
            StreamDescriptor(
                device_id=self.device_id,
                modality="demo",
                payload_type="signal",
                nominal_sample_rate_hz=1.0,
                chunk_size=1,
                channel_names=("demo",),
            )
        ]

    def on_runtime_started(self) -> None:
        self.allow_start.wait(1.0)

    def on_shutdown(self) -> None:
        self.shutdown_called.set()

    def search(self, provider: str) -> list[SearchResult]:
        if provider != "demo":
            raise ValueError("unsupported provider")
        return []

    def connect_device(self, config: SearchResult) -> None:
        _ = config

    def disconnect_device(self) -> None:
        return

    def start_streaming(self) -> None:
        return

    def stop_streaming(self) -> None:
        return


class PurePythonRuntimeTest(unittest.TestCase):
    def test_loop_driver_runs_on_pure_python_portal(self) -> None:
        broker = BackendEventBroker()
        frames: list[FrameEnvelope] = []
        portal = DriverPortal(
            DemoLoopDriver,
            publish_event=broker.publish,
            frame_sink=frames.append,
        )

        portal.start()

        connect_future = portal.connect_device(SearchResult(title="Demo Device"))
        self.assertIsInstance(connect_future, Future)
        self.assertIsNone(connect_future.result(1.0))

        start_future = portal.start_streaming()
        self.assertIsNone(start_future.result(1.0))

        _wait_for(lambda: len(frames) >= 3, timeout=1.0)

        stop_future = portal.stop_streaming()
        self.assertIsNone(stop_future.result(1.0))
        portal.stop()

        self.assertGreaterEqual(len(frames), 3)
        self.assertEqual([0, 1, 2], [frame.seq for frame in frames[:3]])
        self.assertFalse(portal.snapshot().is_streaming)

    def test_driver_connection_lost_event_updates_state_without_qt(self) -> None:
        broker = BackendEventBroker()
        event_stream = broker.open_stream()
        portal = DriverPortal(DemoDisconnectingDriver, publish_event=broker.publish)
        portal.start()

        portal.connect_device(SearchResult(title="Disconnecting Device")).result(1.0)
        portal.start_streaming().result(1.0)

        event = _wait_for_event(event_stream, DriverConnectionLostEvent, timeout=1.0)

        self.assertEqual("demo_disconnect.01", event.driver_id)
        self.assertIsInstance(event.detail, dict)
        self.assertFalse(portal.snapshot().is_connected)
        self.assertFalse(portal.snapshot().is_streaming)

        portal.stop()
        event_stream.close()

    def test_driver_future_fails_immediately_when_executor_not_started(self) -> None:
        broker = BackendEventBroker()
        portal = DriverPortal(DemoDisconnectingDriver, publish_event=broker.publish)

        future = portal.search("demo")

        with self.assertRaisesRegex(RuntimeError, "not running"):
            future.result(0.1)

    def test_emit_frame_returns_false_when_sink_rejects_frame(self) -> None:
        broker = BackendEventBroker()
        driver = DemoImmediateEmitDriver("demo_emit_false.01")
        portal = DriverPortal(
            lambda: driver,
            publish_event=broker.publish,
            frame_sink=lambda _frame: False,
        )

        portal.start()
        portal.connect_device(SearchResult(title="Immediate Emit Device")).result(1.0)
        portal.start_streaming().result(1.0)
        portal.stop()

        self.assertFalse(driver.last_emit_result)

    def test_emit_frame_treats_none_returning_sink_as_success(self) -> None:
        broker = BackendEventBroker()
        frames: list[FrameEnvelope] = []
        driver = DemoImmediateEmitDriver("demo_emit_none.01")
        portal = DriverPortal(
            lambda: driver,
            publish_event=broker.publish,
            frame_sink=frames.append,
        )

        portal.start()
        portal.connect_device(SearchResult(title="Immediate Emit Device")).result(1.0)
        portal.start_streaming().result(1.0)
        portal.stop()

        self.assertTrue(driver.last_emit_result)
        self.assertEqual(1, len(frames))

    def test_startup_failure_raises_without_backend_error(self) -> None:
        broker = BackendEventBroker()
        event_stream = broker.open_stream()
        portal = DriverPortal(DemoFailingStartupDriver, publish_event=broker.publish)

        with self.assertRaisesRegex(RuntimeError, "startup failed"):
            portal.start()

        self.assertFalse(portal.is_running)
        self.assertFalse(
            any(
                isinstance(event, DriverExecutorFailedEvent)
                for event in _drain_events(event_stream, timeout=0.05)
            )
        )
        event_stream.close()

    def test_loop_driver_shutdown_drops_late_frame_and_connection_lost(self) -> None:
        broker = BackendEventBroker()
        event_stream = broker.open_stream()
        frames: list[FrameEnvelope] = []
        driver = DemoLateEmitLoopDriver()
        portal = DriverPortal(
            lambda: driver,
            publish_event=broker.publish,
            frame_sink=frames.append,
        )

        portal.start()
        portal.connect_device(SearchResult(title="Late Emit Device")).result(1.0)
        portal.start_streaming().result(1.0)
        self.assertTrue(driver.loop_entered.wait(1.0))

        portal.stop()
        frame_count = len(frames)

        driver.allow_finish.set()
        _wait_for(lambda: not driver.is_looping, timeout=2.0)
        time.sleep(0.05)

        self.assertEqual(frame_count, len(frames))
        self.assertFalse(driver.late_emit_result)
        self.assertFalse(
            any(
                isinstance(event, DriverConnectionLostEvent)
                for event in _drain_events(event_stream, timeout=0.05)
            )
        )
        event_stream.close()

    def test_portal_runs_driver_lifecycle_hooks_on_executor_thread(self) -> None:
        broker = BackendEventBroker()
        driver = DemoLifecycleHookDriver()
        portal = DriverPortal(lambda: driver, publish_event=broker.publish)

        portal.start()
        portal.stop()

        self.assertEqual(
            "modlink.driver.demo_lifecycle.01",
            driver.started_thread_name,
        )
        self.assertEqual(
            "modlink.driver.demo_lifecycle.01",
            driver.stopped_thread_name,
        )

    def test_stop_does_not_publish_backend_error_for_shutdown_failure(self) -> None:
        broker = BackendEventBroker()
        event_stream = broker.open_stream()
        portal = DriverPortal(DemoFailingShutdownDriver, publish_event=broker.publish)

        portal.start()
        with self.assertRaisesRegex(RuntimeError, "shutdown failed"):
            portal.stop(timeout_ms=100)

        self.assertFalse(portal.is_running)
        self.assertFalse(
            any(
                isinstance(event, DriverExecutorFailedEvent)
                for event in _drain_events(event_stream, timeout=0.05)
            )
        )
        event_stream.close()

    def test_stop_timeout_does_not_publish_backend_error(self) -> None:
        broker = BackendEventBroker()
        event_stream = broker.open_stream()
        driver = DemoSlowShutdownDriver()
        portal = DriverPortal(lambda: driver, publish_event=broker.publish)

        portal.start()
        with self.assertRaisesRegex(TimeoutError, "driver shutdown timed out"):
            portal.stop(timeout_ms=10)
        self.assertTrue(portal.is_running)
        driver.allow_shutdown.set()
        self.assertTrue(driver.shutdown_finished.wait(1.0))
        _wait_for(lambda: not portal.is_running, timeout=1.0)

        self.assertFalse(
            any(
                isinstance(event, DriverExecutorFailedEvent)
                for event in _drain_events(event_stream, timeout=0.05)
            )
        )
        event_stream.close()

    def test_event_stream_overflow_raises_local_error(self) -> None:
        broker = BackendEventBroker()
        event_stream = broker.open_stream(maxsize=1)

        broker.publish(DriverConnectionLostEvent(driver_id="demo.01", detail=None))
        broker.publish(DriverConnectionLostEvent(driver_id="demo.01", detail="again"))

        with self.assertRaises(EventStreamOverflowError):
            event_stream.read(timeout=0.1)
        event_stream.close()

    def test_portal_start_times_out(self) -> None:
        broker = BackendEventBroker()
        driver = DemoHangingStartupDriver()
        portal = DriverPortal(lambda: driver, publish_event=broker.publish)

        with self.assertRaisesRegex(TimeoutError, "driver startup timed out"):
            portal.start(timeout_ms=50)

        driver.allow_start.set()
        self.assertTrue(driver.shutdown_called.wait(1.0))

    def test_engine_starts_recording_after_drivers(self) -> None:
        call_order: list[str] = []
        driver_a = DemoLifecycleHookDriver("demo_order_a.01")
        driver_b = DemoLifecycleHookDriver("demo_order_b.01")

        original_start = RecordingBackend.start

        def _record_start(backend: RecordingBackend) -> None:
            call_order.append("recording")
            original_start(backend)

        def _wrap_started(driver: DemoLifecycleHookDriver, driver_id: str):
            def _started() -> None:
                call_order.append(driver_id)
                driver.started_thread_name = threading.current_thread().name

            return _started

        driver_a.on_runtime_started = _wrap_started(driver_a, "demo_order_a.01")  # type: ignore[method-assign]
        driver_b.on_runtime_started = _wrap_started(driver_b, "demo_order_b.01")  # type: ignore[method-assign]

        with patch(
            "modlink_core.runtime.engine.RecordingBackend.start",
            autospec=True,
            side_effect=_record_start,
        ):
            engine = ModLinkEngine(
                driver_factories=[lambda: driver_a, lambda: driver_b],
                settings=_build_settings_service(),
            )

        self.assertEqual(
            ["demo_order_a.01", "demo_order_b.01", "recording"],
            call_order,
        )
        engine.shutdown()

    def test_engine_shutdown_attempts_all_children_and_raises_first_error(self) -> None:
        failing_driver = DemoFailingShutdownDriver()
        healthy_driver = DemoLifecycleHookDriver("demo_shutdown_ok.01")
        recording_called = threading.Event()

        original_shutdown = RecordingBackend.shutdown

        def _record_shutdown(backend: RecordingBackend, *args, **kwargs) -> None:
            recording_called.set()
            original_shutdown(backend, *args, **kwargs)

        with patch(
            "modlink_core.runtime.engine.RecordingBackend.shutdown",
            autospec=True,
            side_effect=_record_shutdown,
        ):
            engine = ModLinkEngine(
                driver_factories=[lambda: failing_driver, lambda: healthy_driver],
                settings=_build_settings_service(),
            )
            with self.assertRaisesRegex(RuntimeError, "shutdown failed"):
                engine.shutdown()

        self.assertTrue(healthy_driver.stopped_event.wait(1.0))
        self.assertTrue(recording_called.wait(1.0))

    def test_engine_rolls_back_started_drivers_when_startup_fails(self) -> None:
        started_driver = DemoLifecycleHookDriver("demo_started.01")
        failing_driver = DemoFailingStartupDriver()
        removed_stream_ids: list[str] = []

        original_remove = __import__(
            "modlink_core.runtime.engine", fromlist=["StreamBus"]
        ).StreamBus.remove_descriptor

        def _spy_remove(bus, stream_id: str) -> None:
            removed_stream_ids.append(stream_id)
            original_remove(bus, stream_id)

        with (
            patch(
                "modlink_core.runtime.engine.StreamBus.remove_descriptor",
                autospec=True,
                side_effect=_spy_remove,
            ),
            patch(
                "modlink_core.runtime.engine.RecordingBackend.start",
                autospec=True,
            ) as recording_start,
        ):
            with self.assertRaisesRegex(RuntimeError, "startup failed"):
                ModLinkEngine(
                    driver_factories=[lambda: started_driver, lambda: failing_driver],
                    settings=_build_settings_service(),
                )

        self.assertTrue(started_driver.stopped_event.wait(1.0))
        self.assertFalse(recording_start.called)
        self.assertEqual(
            {
                next(iter(started_driver.descriptors())).stream_id,
                next(iter(failing_driver.descriptors())).stream_id,
            },
            set(removed_stream_ids),
        )

    def test_engine_rolls_back_started_drivers_when_startup_times_out(self) -> None:
        started_driver = DemoLifecycleHookDriver("demo_started.01")
        hanging_driver = DemoHangingStartupDriver()
        removed_stream_ids: list[str] = []

        original_remove = __import__(
            "modlink_core.runtime.engine", fromlist=["StreamBus"]
        ).StreamBus.remove_descriptor

        def _spy_remove(bus, stream_id: str) -> None:
            removed_stream_ids.append(stream_id)
            original_remove(bus, stream_id)

        with (
            patch(
                "modlink_core.runtime.engine.DEFAULT_DRIVER_STARTUP_TIMEOUT_MS",
                50,
            ),
            patch(
                "modlink_core.runtime.engine.StreamBus.remove_descriptor",
                autospec=True,
                side_effect=_spy_remove,
            ),
            patch(
                "modlink_core.runtime.engine.RecordingBackend.start",
                autospec=True,
            ) as recording_start,
        ):
            with self.assertRaisesRegex(TimeoutError, "driver startup timed out"):
                ModLinkEngine(
                    driver_factories=[lambda: started_driver, lambda: hanging_driver],
                    settings=_build_settings_service(),
                )

        hanging_driver.allow_start.set()
        self.assertTrue(started_driver.stopped_event.wait(1.0))
        self.assertTrue(hanging_driver.shutdown_called.wait(1.0))
        self.assertFalse(recording_start.called)
        self.assertEqual(
            {
                next(iter(started_driver.descriptors())).stream_id,
                next(iter(hanging_driver.descriptors())).stream_id,
            },
            set(removed_stream_ids),
        )

    def test_engine_startup_failure_adds_cleanup_failure_notes(self) -> None:
        started_driver = DemoFailingShutdownDriver()
        failing_driver = DemoFailingStartupDriver()

        with self.assertRaisesRegex(RuntimeError, "startup failed") as ctx:
            ModLinkEngine(
                driver_factories=[lambda: started_driver, lambda: failing_driver],
                settings=_build_settings_service(),
            )

        self.assertTrue(
            any(
                "demo_fail_shutdown.01" in note and "shutdown failed" in note
                for note in getattr(ctx.exception, "__notes__", [])
            )
        )


def _wait_for_event(stream, event_type, *, timeout: float):
    deadline = time.time() + timeout
    while time.time() < deadline:
        for item in _drain_events(stream, timeout=0.05):
            if isinstance(item, event_type):
                return item
        time.sleep(0.01)
    raise AssertionError(f"{event_type.__name__} was not published before timeout")


def _drain_events(stream, *, timeout: float = 0.05) -> list[object]:
    events: list[object] = []
    try:
        events.append(stream.read(timeout=timeout))
    except queue.Empty:
        return events
    events.extend(stream.read_many())
    return events


def _wait_for(predicate, *, timeout: float) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return
        time.sleep(0.02)
    raise AssertionError("condition not reached before timeout")


def _build_settings_service() -> SettingsService:
    temp_root = Path(__file__).resolve().parents[3] / ".tmp-tests" / "modlink_core"
    temp_root.mkdir(parents=True, exist_ok=True)
    temp_dir = temp_root / f"settings_{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    path = temp_dir / "settings.json"
    settings = SettingsService(path=path)
    settings.set("acquisition.storage.root_dir", str(temp_dir / "recordings"), persist=False)
    return settings


if __name__ == "__main__":
    unittest.main()
