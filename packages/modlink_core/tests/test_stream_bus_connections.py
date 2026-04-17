from __future__ import annotations

import json
import queue
import threading
import time
import unittest
from concurrent.futures import Future
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import numpy as np

from modlink_core import RecordingBackend, SettingsStore, StreamBus
from modlink_core.event_stream import BackendEventBroker, EventStreamOverflowError
from modlink_core.events import (
    DriverConnectionLostEvent,
    RecordingFailedEvent,
    SettingChangedEvent,
)
from modlink_core.settings import (
    SettingsGroup,
    SettingsInt,
    SettingsStore as SettingsServiceType,
    SettingsStr,
    ValueSpec,
)
from modlink_core.storage import recordings_dir
from modlink_sdk import FrameEnvelope, StreamDescriptor


class TinyFrameStreamRecordingBackend(RecordingBackend):
    def _open_frame_stream(self):
        return self._bus.open_frame_stream(
            maxsize=1,
            drop_policy="error",
            consumer_name="recording",
        )


class SlowShutdownRecordingBackend(RecordingBackend):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.allow_shutdown = threading.Event()

    def _shutdown_worker(self) -> None:
        self.allow_shutdown.wait(1.0)
        super()._shutdown_worker()


class StreamBusConnectionTest(unittest.TestCase):
    def test_event_stream_overflow_raises_local_error(self) -> None:
        broker = BackendEventBroker()
        stream = broker.open_stream(maxsize=1)

        broker.publish(DriverConnectionLostEvent(driver_id="demo.01", detail=None))
        broker.publish(DriverConnectionLostEvent(driver_id="demo.01", detail="again"))

        with self.assertRaises(EventStreamOverflowError):
            stream.read(timeout=0.1)
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

    def test_error_policy_overflow_does_not_block_other_consumers(self) -> None:
        broker = BackendEventBroker()
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

        self.assertEqual([2, 3], [frame.seq for frame in _drain_frames(preview_stream)])

        recorder_stream.close()
        preview_stream.close()

    def test_recording_backend_stops_recording_on_frame_stream_overflow(self) -> None:
        broker = BackendEventBroker()
        event_stream = broker.open_stream()
        bus = StreamBus(event_broker=broker)
        bus.add_descriptor(_demo_descriptor())
        settings = _build_settings_service()
        backend = TinyFrameStreamRecordingBackend(
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
        start_summary = start_future.result(1.0)
        self.assertTrue(backend.is_recording)

        for seq in range(20):
            bus.ingest_frame(_demo_frame(seq=seq))

        _wait_for(lambda: not backend.is_recording, timeout=2.0)

        events = _drain_events(event_stream, timeout=0.2)
        failure_event = next(event for event in events if isinstance(event, RecordingFailedEvent))
        self.assertEqual("frame_stream_overflow", failure_event.reason)
        self.assertEqual(start_summary.recording_id, failure_event.recording_id)
        manifest = json.loads(
            (Path(failure_event.recording_path) / "recording.json").read_text(encoding="utf-8")
        )
        self.assertEqual("overflow_case", manifest["recording_label"])
        self.assertEqual([_demo_descriptor().stream_id], manifest["stream_ids"])
        self.assertFalse(hasattr(failure_event, "session_name"))

        backend.shutdown()
        event_stream.close()

    def test_recording_backend_publishes_failed_recording_on_write_error(self) -> None:
        broker = BackendEventBroker()
        event_stream = broker.open_stream()
        bus = StreamBus(event_broker=broker)
        bus.add_descriptor(_demo_descriptor())
        settings = _build_settings_service()
        with patch(
            "modlink_core.recording.backend.append_recording_frame",
            side_effect=RuntimeError("append failed"),
        ):
            backend = RecordingBackend(
                bus,
                settings=settings,
                publish_event=broker.publish,
            )
            backend.start()
            start_future = backend.start_recording("write_failure_case")
            start_summary = start_future.result(1.0)
            bus.ingest_frame(_demo_frame(seq=1))
            failure_event = _wait_for_recording_failed(event_stream, timeout=1.0)

        self.assertEqual("write_failed", failure_event.reason)
        self.assertEqual(start_summary.recording_id, failure_event.recording_id)
        manifest = json.loads(
            (Path(failure_event.recording_path) / "recording.json").read_text(encoding="utf-8")
        )
        self.assertEqual("write_failure_case", manifest["recording_label"])
        self.assertEqual([_demo_descriptor().stream_id], manifest["stream_ids"])
        self.assertFalse(
            any(
                getattr(event, "kind", None) == "acquisition_state_changed"
                for event in _drain_events(event_stream, timeout=0.05)
            )
        )
        backend.shutdown()
        event_stream.close()

    def test_recording_backend_shutdown_timeout_does_not_pretend_stopped(self) -> None:
        broker = BackendEventBroker()
        bus = StreamBus(event_broker=broker)
        bus.add_descriptor(_demo_descriptor())
        settings = _build_settings_service()
        backend = SlowShutdownRecordingBackend(
            bus,
            settings=settings,
            publish_event=broker.publish,
        )
        backend.start()

        with self.assertRaisesRegex(TimeoutError, "recording shutdown timed out"):
            backend.shutdown(timeout_ms=10)

        self.assertTrue(backend.is_started)
        backend.allow_shutdown.set()
        _wait_for(lambda: not backend.is_started, timeout=1.0)
        backend.shutdown(timeout_ms=100)

    def test_recording_backend_writes_completed_manifest_on_normal_stop(self) -> None:
        broker = BackendEventBroker()
        event_stream = broker.open_stream()
        bus = StreamBus(event_broker=broker)
        bus.add_descriptor(_demo_descriptor())
        settings = _build_settings_service()
        backend = RecordingBackend(
            bus,
            settings=settings,
            publish_event=broker.publish,
        )
        backend.start()
        start_future = backend.start_recording("completed_case")
        start_summary = start_future.result(1.0)

        bus.ingest_frame(_demo_frame(seq=1))
        stop_future = backend.stop_recording()
        stop_summary = stop_future.result(1.0)

        self.assertEqual(start_summary.recording_id, stop_summary.recording_id)
        self.assertEqual("completed", stop_summary.status)
        recording_dir = Path(stop_summary.recording_path)
        self.assertEqual(
            recording_dir,
            recordings_dir(settings) / stop_summary.recording_id,
        )
        manifest = json.loads((recording_dir / "recording.json").read_text(encoding="utf-8"))
        self.assertEqual("completed_case", manifest["recording_label"])
        self.assertEqual([_demo_descriptor().stream_id], manifest["stream_ids"])
        events = _drain_events(event_stream, timeout=0.05)
        self.assertFalse(
            any(getattr(event, "kind", None) == "acquisition_state_changed" for event in events)
        )
        self.assertFalse(any(isinstance(event, RecordingFailedEvent) for event in events))
        backend.shutdown()
        event_stream.close()

    def test_recording_commands_fail_through_future(self) -> None:
        broker = BackendEventBroker()
        bus = StreamBus(event_broker=broker)
        bus.add_descriptor(_demo_descriptor())
        settings = _build_settings_service()
        backend = RecordingBackend(
            bus,
            settings=settings,
            publish_event=broker.publish,
        )

        with self.assertRaisesRegex(RuntimeError, "ACQ_NOT_STARTED"):
            backend.start_recording("command_failure_case").result(0.1)

        backend.start()
        with self.assertRaisesRegex(RuntimeError, "ACQ_STOP_IGNORED"):
            backend.stop_recording().result(1.0)
        with self.assertRaisesRegex(RuntimeError, "ACQ_MARKER_REJECTED"):
            backend.add_marker("marker").result(1.0)
        with self.assertRaisesRegex(RuntimeError, "ACQ_SEGMENT_REJECTED"):
            backend.add_segment(1, 2, "segment").result(1.0)
        start_summary = backend.start_recording("first_recording").result(1.0)
        self.assertTrue(start_summary.recording_id.startswith("rec_"))
        with self.assertRaisesRegex(RuntimeError, "ACQ_ALREADY_RECORDING"):
            backend.start_recording("second_recording").result(1.0)

        backend.stop_recording().result(1.0)
        backend.shutdown()

    def test_multiple_engines_do_not_share_settings_state(self) -> None:
        settings_a = _build_settings_service()
        settings_b = _build_settings_service()
        _declare_preview_rate_settings(settings_a)
        _declare_preview_rate_settings(settings_b)

        settings_a.ui.preview.rate_hz = 30
        settings_b.ui.preview.rate_hz = 60

        self.assertEqual(30, settings_a.ui.preview.rate_hz.value)
        self.assertEqual(60, settings_b.ui.preview.rate_hz.value)
        self.assertNotEqual(settings_a.snapshot(), settings_b.snapshot())

    def test_recording_root_dir_read_does_not_mutate_settings(self) -> None:
        broker = BackendEventBroker()
        event_stream = broker.open_stream()
        bus = StreamBus(event_broker=broker)
        settings = _build_empty_settings_service()
        backend = RecordingBackend(
            bus,
            settings=settings,
            publish_event=broker.publish,
        )

        root_dir = backend.root_dir

        self.assertIsInstance(root_dir, Path)
        self.assertEqual("", settings.storage.root_dir.value)
        self.assertEqual("", settings.storage.export_root_dir.value)
        self.assertFalse(
            any(
                isinstance(event, SettingChangedEvent)
                for event in _drain_events(event_stream, timeout=0.05)
            )
        )
        event_stream.close()

    def test_settings_service_concurrent_updates_keep_valid_json(self) -> None:
        settings = _build_concurrent_settings_service()
        errors: list[Exception] = []

        def _worker(worker_id: int) -> None:
            try:
                for seq in range(25):
                    setattr(
                        settings.ui,
                        f"worker_{worker_id}",
                        {"seq": seq, "labels": [worker_id, seq]},
                    )
                    settings.save()
                    _ = getattr(settings.ui, f"worker_{worker_id}").value
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
            len([key for key in payload["values"]["ui"] if key.startswith("worker_")]),
        )


def _demo_descriptor() -> StreamDescriptor:
    return StreamDescriptor(
        device_id="demo.01",
        stream_key="demo",
        payload_type="signal",
        nominal_sample_rate_hz=100.0,
        chunk_size=4,
        channel_names=("demo",),
    )


def _demo_frame(*, seq: int) -> FrameEnvelope:
    return FrameEnvelope(
        device_id="demo.01",
        stream_key="demo",
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
    settings = SettingsStore(path=path)
    settings.add(storage=SettingsGroup(root_dir=SettingsStr(default=""), export_root_dir=SettingsStr(default="")))
    settings.storage.root_dir = str(temp_dir / "data")
    return settings


def _build_empty_settings_service() -> SettingsServiceType:
    temp_root = Path(__file__).resolve().parents[3] / ".tmp-tests" / "modlink_core"
    temp_root.mkdir(parents=True, exist_ok=True)
    temp_dir = temp_root / f"settings_empty_{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    return SettingsStore(path=temp_dir / "settings.json")


def _build_concurrent_settings_service() -> SettingsServiceType:
    settings = _build_settings_service()
    settings.add(
        ui=SettingsGroup(
            worker_0=ValueSpec(default={}),
            worker_1=ValueSpec(default={}),
            worker_2=ValueSpec(default={}),
            worker_3=ValueSpec(default={}),
        )
    )
    return settings


def _declare_preview_rate_settings(settings: SettingsServiceType) -> None:
    settings.add(ui=SettingsGroup(preview=SettingsGroup(rate_hz=SettingsInt(default=30))))


if __name__ == "__main__":
    unittest.main()
