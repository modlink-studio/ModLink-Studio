from __future__ import annotations

import queue
import time
import unittest

import numpy as np

from modlink_core import AcquisitionBackend, StreamBus
from modlink_core.events import BackendEventQueue
from modlink_sdk import FrameEnvelope, StreamDescriptor


class StreamBusConnectionTest(unittest.TestCase):
    def test_acquisition_backend_disconnects_from_bus_on_shutdown(self) -> None:
        event_queue = BackendEventQueue()
        bus = StreamBus(event_queue=event_queue)
        descriptor = StreamDescriptor(
            device_id="demo.01",
            modality="demo",
            payload_type="signal",
            nominal_sample_rate_hz=100.0,
            chunk_size=4,
            channel_names=("demo",),
        )
        frame = FrameEnvelope(
            device_id="demo.01",
            modality="demo",
            timestamp_ns=time.time_ns(),
            data=np.ones((1, 4), dtype=np.float32),
            seq=1,
        )
        received: list[FrameEnvelope] = []

        bus.add_descriptor(descriptor)
        backend = AcquisitionBackend(bus, event_queue=event_queue)
        original_on_frame = backend._on_frame

        def _capture_frame(frame: FrameEnvelope) -> None:
            received.append(frame)
            original_on_frame(frame)

        backend._on_frame = _capture_frame  # type: ignore[method-assign]

        backend.start()
        bus.ingest_frame(frame)
        self.assertEqual([frame], received)

        backend.shutdown()
        bus.ingest_frame(frame)
        self.assertEqual([frame], received)
        with self.assertRaises(queue.Empty):
            backend._command_queue.get_nowait()


if __name__ == "__main__":
    unittest.main()
