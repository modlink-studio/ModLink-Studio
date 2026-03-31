from __future__ import annotations

from concurrent.futures import Future
import queue
import threading
import time
import unittest

import numpy as np

from modlink_core.drivers import DriverPortal
from modlink_core.events import (
    BackendErrorEvent,
    BackendEventBroker,
    DriverConnectionLostEvent,
)
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

    def test_executor_failure_publishes_backend_error(self) -> None:
        broker = BackendEventBroker()
        event_stream = broker.open_stream()
        portal = DriverPortal(DemoFailingStartupDriver, publish_event=broker.publish)

        portal.start()

        event = _wait_for_event(event_stream, BackendErrorEvent, timeout=1.0)

        self.assertEqual("driver_executor:demo_fail_start.01", event.source)
        self.assertIn("DRIVER_EXECUTOR_FAILED", event.message)
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


if __name__ == "__main__":
    unittest.main()
