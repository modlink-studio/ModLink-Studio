from __future__ import annotations

import time
import unittest

import numpy as np

from modlink_core.drivers import DriverPortal
from modlink_core.events import (
    BackendErrorEvent,
    BackendEventQueue,
    DriverStateChangedEvent,
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
        emitted = self.emit_frame(
            FrameEnvelope(
                device_id=self.device_id,
                modality="demo",
                timestamp_ns=time.time_ns(),
                data=np.ones((1, 4), dtype=np.float32) * self._seq,
                seq=self._seq,
            )
        )
        if emitted:
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
        self.report_error("search warning")
        return [SearchResult(title="Callback Device")]

    def connect_device(self, config: SearchResult) -> None:
        _ = config
        self.set_status("ready", {"mode": "callback"})

    def disconnect_device(self) -> None:
        return

    def start_streaming(self) -> None:
        return

    def stop_streaming(self) -> None:
        return


class PurePythonRuntimeTest(unittest.TestCase):
    def test_loop_driver_runs_on_pure_python_portal(self) -> None:
        events = BackendEventQueue()
        frames: list[FrameEnvelope] = []
        portal = DriverPortal(
            DemoLoopDriver,
            event_queue=events,
            frame_sink=frames.append,
        )

        portal.start()

        connect_task = portal.connect_device(SearchResult(title="Demo Device"))
        self.assertTrue(connect_task.wait(1.0))
        self.assertIsNone(connect_task.error)

        start_task = portal.start_streaming()
        self.assertTrue(start_task.wait(1.0))
        self.assertIsNone(start_task.error)

        deadline = time.time() + 1.0
        while len(frames) < 3 and time.time() < deadline:
            time.sleep(0.02)

        portal.stop()

        self.assertGreaterEqual(len(frames), 3)
        self.assertEqual([0, 1, 2], [frame.seq for frame in frames[:3]])

    def test_driver_context_can_report_errors_without_qt(self) -> None:
        events = BackendEventQueue()
        portal = DriverPortal(DemoCallbackDriver, event_queue=events)
        errors: list[str] = []
        portal.start()

        task = portal.search("demo")
        self.assertTrue(task.wait(1.0))
        self.assertIsNone(task.error)
        errors.extend(
            event.message
            for event in events.drain()
            if isinstance(event, BackendErrorEvent)
        )
        self.assertTrue(errors)

        connect_task = portal.connect_device(SearchResult(title="Callback Device"))
        self.assertTrue(connect_task.wait(1.0))
        self.assertIsNone(connect_task.error)

        states: list[object] = []
        deadline = time.time() + 1.0
        while not states and time.time() < deadline:
            states.extend(
                event.snapshot
                for event in events.drain()
                if isinstance(event, DriverStateChangedEvent)
            )
            time.sleep(0.02)

        self.assertTrue(any("DRIVER_REPORTED_ERROR" in item for item in errors))
        self.assertEqual("connected", portal.state.status)
        portal.stop()


if __name__ == "__main__":
    unittest.main()
