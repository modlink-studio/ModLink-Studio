from __future__ import annotations

from concurrent.futures import Future
import json
import queue
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import numpy as np

from modlink_core import AcquisitionBackend, SettingsService, StreamBus
from modlink_core.events import (
    BackendErrorEvent,
    BackendEventBroker,
    DriverConnectionLostEvent,
    RecordingFailedEvent,
)
from modlink_core.acquisition.storage.manager import RecordingStorage
from modlink_core.settings.service import SettingsService as SettingsServiceType
from modlink_sdk import FrameEnvelope, StreamDescriptor


class TinyFrameStreamAcquisitionBackend(AcquisitionBackend):
    def _open_frame_stream(self):
        return self._bus.open_frame_stream(
            maxsize=1,
            drop_policy="error",
            consumer_name="acquisition",
        )


class StreamBusConnectionTest(unittest.TestCase):
    def test_event_stream_overflow_emits_backend_error(self) -> None:
        broker = BackendEventBroker()
        stream = broker.open_stream(maxsize=1)

        broker.publish(
            DriverConnectionLostEvent(driver_id="demo.01", detail=None)
        )
        broker.publish(
            DriverConnectionLostEvent(driver_id="demo.01", detail="again")
        )

        event = stream.read(timeout=0.1)
        self.assertIsInstance(event, BackendErrorEvent)
        self.assertEqual("event_stream", event.source)
        self.assertEqual("EVENT_STREAM_OVERFLOW", event.message)
        stream.close()

    def test_frame_streams_are_multi_consumer_and_drop_oldest_independently(self) -> None:
        broker = BackendEventBroker()
        bus = StreamBus(event_broker=broker)
        descriptor = _demo_descriptor()
        bus.add_descriptor(descriptor)
        fast_stream = bus.open_frame_stream(maxsize=2, consumer_name="fast")
        slow_stream = bus.open_frame_stream(maxsize=2, consumer_name="slow")

        for seq in range(4):
            bus.ingest_frame(_demo_frame(seq=seq))

        self.assertEqual([2, 3], [frame.seq for frame in _drain_frames(fast_stream)])
        self.assertEqual([2, 3], [frame.seq for frame in _drain_frames(slow_stream)])
        self.assertEqual(2, fast_stream.dropped_count)
        self.assertEqual(2, slow_stream.dropped_count)

        fast_stream.close()
        slow_stream.close()

    def test_error_policy_overflow_publishes_event_without_blocking_other_consumers(self) -> None:
        broker = BackendEventBroker()
        event_stream = broker.open_stream()
        bus = StreamBus(event_broker=broker)
        descriptor = _demo_descriptor()
        bus.add_descriptor(descriptor)
        recorder_stream = bus.open_frame_stream(
            maxsize=1,
            drop_policy="error",
            consumer_name="recorder",
        )
        preview_stream = bus.open_frame_stream(
            maxsize=2,
            drop_policy="drop_oldest",
            consumer_name="preview",
        )

        bus.ingest_frame(_demo_frame(seq=1))
        bus.ingest_frame(_demo_frame(seq=2))
        bus.ingest_frame(_demo_frame(seq=3))

        with self.assertRaisesRegex(Exception, "recorder"):
            recorder_stream.read(timeout=0.1)

        errors = [
            event
            for event in _drain_events(event_stream)
            if isinstance(event, BackendErrorEvent)
            and event.source == "frame_stream"
        ]
        self.assertTrue(
            any(event.message == "FRAME_STREAM_OVERFLOW:recorder" for event in errors)
        )
        self.assertEqual([2, 3], [frame.seq for frame in _drain_frames(preview_stream)])

        recorder_stream.close()
        preview_stream.close()
        event_stream.close()

    def test_acquisition_backend_stops_recording_on_frame_stream_overflow(self) -> None:
        broker = BackendEventBroker()
        event_stream = broker.open_stream()
        bus = StreamBus(event_broker=broker)
        bus.add_descriptor(_demo_descriptor())
        settings = _build_settings_service()
        backend = TinyFrameStreamAcquisitionBackend(
            bus,
            settings=settings,
            publish_event=broker.publish,
        )
        original_on_frame_worker = backend._on_frame_worker

        def _slow_on_frame(frame: object) -> None:
            time.sleep(0.03)
            original_on_frame_worker(frame)

        backend._on_frame_worker = _slow_on_frame  # type: ignore[method-assign]
        backend.start()
        start_future = backend.start_recording("overflow_case")
        self.assertIsInstance(start_future, Future)
        self.assertIsNone(start_future.result(1.0))
        self.assertTrue(backend.is_recording)

        for seq in range(20):
            bus.ingest_frame(_demo_frame(seq=seq))

        _wait_for(lambda: not backend.is_recording, timeout=2.0)

        events = _drain_events(event_stream, timeout=0.2)
        failure_event = next(
            event
            for event in events
            if isinstance(event, RecordingFailedEvent)
        )
        self.assertEqual("frame_stream_overflow", failure_event.reason)
        manifest = json.loads(
            (Path(failure_event.recording_path) / "recording.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual("failed", manifest["status"])

        backend.shutdown()
        event_stream.close()

    def test_acquisition_backend_publishes_failed_recording_on_write_error(self) -> None:
        broker = BackendEventBroker()
        event_stream = broker.open_stream()
        bus = StreamBus(event_broker=broker)
        bus.add_descriptor(_demo_descriptor())
        settings = _build_settings_service()

        class FailingAppendStorage(RecordingStorage):
            def append_frame(self, frame: FrameEnvelope) -> None:
                raise RuntimeError("append failed")

        with patch(
            "modlink_core.acquisition.backend.RecordingStorage",
            FailingAppendStorage,
        ):
            backend = AcquisitionBackend(
                bus,
                settings=settings,
                publish_event=broker.publish,
            )
            backend.start()
            start_future = backend.start_recording("write_failure_case")
            self.assertIsNone(start_future.result(1.0))
            bus.ingest_frame(_demo_frame(seq=1))
            failure_event = _wait_for_recording_failed(event_stream, timeout=1.0)

        self.assertEqual("write_failed", failure_event.reason)
        manifest = json.loads(
            (Path(failure_event.recording_path) / "recording.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual("failed", manifest["status"])
        backend.shutdown()
        event_stream.close()

    def test_acquisition_backend_publishes_failed_recording_on_finalize_error(self) -> None:
        broker = BackendEventBroker()
        event_stream = broker.open_stream()
        bus = StreamBus(event_broker=broker)
        bus.add_descriptor(_demo_descriptor())
        settings = _build_settings_service()

        class FailingFinalizeStorage(RecordingStorage):
            def finalize(self, *, stopped_at_ns: int, status: str = "completed") -> None:
                raise RuntimeError("finalize failed")

        with patch(
            "modlink_core.acquisition.backend.RecordingStorage",
            FailingFinalizeStorage,
        ):
            backend = AcquisitionBackend(
                bus,
                settings=settings,
                publish_event=broker.publish,
            )
            backend.start()
            start_future = backend.start_recording("finalize_failure_case")
            self.assertIsNone(start_future.result(1.0))
            stop_future = backend.stop_recording()
            failure_event = _wait_for_recording_failed(event_stream, timeout=1.0)

        with self.assertRaisesRegex(RuntimeError, "ACQ_STOP_FAILED: finalize_failed"):
            stop_future.result(1.0)
        self.assertEqual("finalize_failed", failure_event.reason)
        manifest = json.loads(
            (Path(failure_event.recording_path) / "recording.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual("failed", manifest["status"])
        backend.shutdown()
        event_stream.close()

    def test_acquisition_backend_writes_completed_manifest_on_normal_stop(self) -> None:
        broker = BackendEventBroker()
        event_stream = broker.open_stream()
        bus = StreamBus(event_broker=broker)
        bus.add_descriptor(_demo_descriptor())
        settings = _build_settings_service()
        backend = AcquisitionBackend(
            bus,
            settings=settings,
            publish_event=broker.publish,
        )
        backend.start()
        start_future = backend.start_recording("completed_case")
        self.assertIsNone(start_future.result(1.0))

        bus.ingest_frame(_demo_frame(seq=1))
        stop_future = backend.stop_recording()
        self.assertIsNone(stop_future.result(1.0))

        session_dir = Path(settings.get("acquisition.storage.root_dir")) / "session_completed_case"
        recording_dirs = [path for path in session_dir.iterdir() if path.is_dir()]
        self.assertEqual(1, len(recording_dirs))
        manifest = json.loads(
            (recording_dirs[0] / "recording.json").read_text(encoding="utf-8")
        )
        self.assertEqual("completed", manifest["status"])
        self.assertFalse(
            any(
                isinstance(event, RecordingFailedEvent)
                for event in _drain_events(event_stream, timeout=0.05)
            )
        )
        backend.shutdown()
        event_stream.close()

    def test_acquisition_commands_fail_through_future(self) -> None:
        broker = BackendEventBroker()
        bus = StreamBus(event_broker=broker)
        bus.add_descriptor(_demo_descriptor())
        settings = _build_settings_service()
        backend = AcquisitionBackend(
            bus,
            settings=settings,
            publish_event=broker.publish,
        )

        with self.assertRaisesRegex(RuntimeError, "ACQ_NOT_STARTED"):
            backend.start_recording("command_failure_case").result(0.1)

        backend.start()
        with self.assertRaisesRegex(RuntimeError, "ACQ_INVALID_SESSION_NAME"):
            backend.start_recording("   ").result(1.0)
        with self.assertRaisesRegex(RuntimeError, "ACQ_MARKER_REJECTED"):
            backend.add_marker("marker").result(1.0)
        with self.assertRaisesRegex(RuntimeError, "ACQ_SEGMENT_REJECTED"):
            backend.add_segment(1, 2, "segment").result(1.0)

        backend.shutdown()

    def test_multiple_engines_do_not_share_settings_state(self) -> None:
        settings_a = _build_settings_service()
        settings_b = _build_settings_service()

        settings_a.set("ui.preview.rate_hz", 30, persist=False)
        settings_b.set("ui.preview.rate_hz", 60, persist=False)

        self.assertEqual(30, settings_a.get("ui.preview.rate_hz"))
        self.assertEqual(60, settings_b.get("ui.preview.rate_hz"))
        self.assertNotEqual(settings_a.snapshot(), settings_b.snapshot())

    def test_settings_service_concurrent_updates_keep_valid_json(self) -> None:
        settings = _build_settings_service()
        errors: list[Exception] = []

        def _worker(worker_id: int) -> None:
            try:
                for seq in range(25):
                    settings.set(
                        f"ui.worker_{worker_id}",
                        {"seq": seq, "labels": [worker_id, seq]},
                        persist=True,
                    )
                    _ = settings.get(f"ui.worker_{worker_id}")
                    _ = settings.snapshot()
            except Exception as exc:
                errors.append(exc)

        threads = [
            threading.Thread(target=_worker, args=(worker_id,), daemon=True)
            for worker_id in range(4)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual([], errors)
        payload = json.loads(settings._path.read_text(encoding="utf-8"))
        self.assertIsInstance(payload, dict)
        self.assertEqual(
            4,
            len([key for key in payload["ui"] if key.startswith("worker_")]),
        )


def _demo_descriptor() -> StreamDescriptor:
    return StreamDescriptor(
        device_id="demo.01",
        modality="demo",
        payload_type="signal",
        nominal_sample_rate_hz=100.0,
        chunk_size=4,
        channel_names=("demo",),
    )


def _demo_frame(*, seq: int) -> FrameEnvelope:
    return FrameEnvelope(
        device_id="demo.01",
        modality="demo",
        timestamp_ns=time.time_ns(),
        data=np.ones((1, 4), dtype=np.float32),
        seq=seq,
    )


def _drain_frames(stream, *, timeout: float = 0.05) -> list[FrameEnvelope]:
    frames: list[FrameEnvelope] = []
    try:
        frames.append(stream.read(timeout=timeout))
    except queue.Empty:
        return frames
    frames.extend(stream.read_many())
    return frames


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


def _wait_for_recording_failed(stream, *, timeout: float) -> RecordingFailedEvent:
    deadline = time.time() + timeout
    while time.time() < deadline:
        for item in _drain_events(stream, timeout=0.05):
            if isinstance(item, RecordingFailedEvent):
                return item
        time.sleep(0.01)
    raise AssertionError("RecordingFailedEvent was not published before timeout")


def _build_settings_service() -> SettingsServiceType:
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
