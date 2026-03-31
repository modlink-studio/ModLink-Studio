from __future__ import annotations

import queue
import time
import unittest

import numpy as np

from modlink_core.drivers import DriverPortal
from modlink_core.events import BackendEventBroker, DriverStateChangedEvent
from modlink_sdk import (
    Driver,
    DriverHost,
    FrameEnvelope,
    LoopDriver,
    SearchResult,
    StreamDescriptor,
)


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
        if self._seq >= 3:
            self.stop_streaming()


class DemoCallbackDriver(Driver):
    supported_providers = ("demo",)

    @property
    def device_id(self) -> str:
        return "demo_callback.01"

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
        return [SearchResult(title="Callback Device")]

    def connect_device(self, config: SearchResult) -> None:
        _ = config
        return

    def disconnect_device(self) -> None:
        return

    def start_streaming(self) -> None:
        return

    def stop_streaming(self) -> None:
        return


class DemoAttachHostDriver(Driver):
    supported_providers = ("demo",)

    def __init__(self) -> None:
        super().__init__()
        self.host_attached = False

    @property
    def device_id(self) -> str:
        return "demo_attach_host.01"

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

    def attach_host(self, host: DriverHost) -> None:
        super().attach_host(host)
        self.host_attached = True
        host.call_later(1.0, lambda: None)

    def search(self, provider: str) -> list[SearchResult]:
        if provider != "demo":
            raise ValueError("unsupported provider")
        return [SearchResult(title="Attach Host Device")]

    def connect_device(self, config: SearchResult) -> None:
        _ = config
        return

    def disconnect_device(self) -> None:
        return

    def start_streaming(self) -> None:
        return

    def stop_streaming(self) -> None:
        return


class PurePythonRuntimeTest(unittest.TestCase):
    def test_loop_driver_runs_on_pure_python_portal(self) -> None:
        broker = BackendEventBroker()
        event_stream = broker.open_stream()
        frames: list[FrameEnvelope] = []
        portal = DriverPortal(
            DemoLoopDriver,
            publish_event=broker.publish,
            frame_sink=frames.append,
        )

        portal.start()

        connect_task = portal.connect_device(SearchResult(title="Demo Device"))
        self.assertTrue(connect_task.wait(1.0))
        self.assertIsNone(connect_task.error)
        self.assertFalse(hasattr(connect_task, "add_done_callback"))

        start_task = portal.start_streaming()
        self.assertTrue(start_task.wait(1.0))
        self.assertIsNone(start_task.error)

        deadline = time.time() + 1.0
        while (len(frames) < 3 or portal.state.is_streaming) and time.time() < deadline:
            time.sleep(0.02)

        portal.stop()
        event_stream.close()

        self.assertGreaterEqual(len(frames), 3)
        self.assertEqual([0, 1, 2], [frame.seq for frame in frames[:3]])
        self.assertFalse(portal.state.is_streaming)

    def test_driver_context_can_update_state_without_qt(self) -> None:
        broker = BackendEventBroker()
        event_stream = broker.open_stream()
        portal = DriverPortal(DemoCallbackDriver, publish_event=broker.publish)
        portal.start()

        task = portal.search("demo")
        self.assertTrue(task.wait(1.0))
        self.assertIsNone(task.error)

        connect_task = portal.connect_device(SearchResult(title="Callback Device"))
        self.assertTrue(connect_task.wait(1.0))
        self.assertIsNone(connect_task.error)

        states: list[object] = []
        deadline = time.time() + 1.0
        while not states and time.time() < deadline:
            states.extend(
                event.snapshot
                for event in _drain_events(event_stream)
                if isinstance(event, DriverStateChangedEvent)
            )
            time.sleep(0.02)

        self.assertTrue(portal.state.is_connected)
        self.assertFalse(portal.state.is_streaming)
        portal.stop()
        event_stream.close()

    def test_driver_task_fails_immediately_when_runtime_not_started(self) -> None:
        broker = BackendEventBroker()
        portal = DriverPortal(DemoCallbackDriver, publish_event=broker.publish)

        task = portal.search("demo")

        self.assertTrue(task.wait(0.1))
        self.assertTrue(task.is_failed)
        self.assertIsInstance(task.error, RuntimeError)
        self.assertIn("not running", str(task.error))

    def test_attach_host_can_use_host_before_runtime_start(self) -> None:
        broker = BackendEventBroker()
        driver = DemoAttachHostDriver()

        portal = DriverPortal(lambda: driver, publish_event=broker.publish)

        self.assertEqual("demo_attach_host.01", portal.driver_id)
        self.assertTrue(driver.host_attached)


def _drain_events(stream, *, timeout: float = 0.05) -> list[object]:
    items: list[object] = []
    try:
        items.append(stream.read(timeout=timeout))
    except queue.Empty:
        return items
    items.extend(stream.read_many())
    return items


if __name__ == "__main__":
    unittest.main()
