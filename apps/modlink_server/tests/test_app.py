from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

from modlink_core import EventStreamOverflowError, SettingsService
from modlink_sdk import Driver, FrameEnvelope, SearchResult, StreamDescriptor

from modlink_server.app import create_app, _iter_sse_messages


class ApiDemoDriver(Driver):
    supported_providers = ("demo",)

    def __init__(self, device_id: str = "api_demo.01") -> None:
        super().__init__()
        self._device_id = device_id
        self.connected = False
        self.streaming = False
        self.shutdown_called = False

    @property
    def device_id(self) -> str:
        return self._device_id

    def descriptors(self) -> list[StreamDescriptor]:
        return [
            StreamDescriptor(
                device_id=self.device_id,
                modality="demo",
                payload_type="signal",
                nominal_sample_rate_hz=10.0,
                chunk_size=4,
                channel_names=("demo",),
            )
        ]

    def search(self, provider: str) -> list[SearchResult]:
        if provider != "demo":
            raise ValueError("unsupported provider")
        return [
            SearchResult(
                title="API Demo Device",
                subtitle="demo",
                extra={"token": "demo"},
            )
        ]

    def connect_device(self, config: SearchResult) -> None:
        _ = config
        self.connected = True

    def disconnect_device(self) -> None:
        self.connected = False
        self.streaming = False

    def start_streaming(self) -> None:
        if not self.connected:
            raise RuntimeError("device is not connected")
        self.streaming = True

    def stop_streaming(self) -> None:
        self.streaming = False

    def on_shutdown(self) -> None:
        self.shutdown_called = True

    def emit_demo_frame(self, *, seq: int = 1) -> bool:
        return self.emit_frame(
            FrameEnvelope(
                device_id=self.device_id,
                modality="demo",
                timestamp_ns=123,
                data=np.ascontiguousarray([[1.0, 2.0, 3.0, 4.0]], dtype=np.float32),
                seq=seq,
            )
        )


class TimeoutSearchDriver(ApiDemoDriver):
    @property
    def device_id(self) -> str:
        return "timeout_demo.01"

    def search(self, provider: str) -> list[SearchResult]:
        raise TimeoutError("search timed out")


@pytest.fixture
def settings(tmp_path: Path) -> SettingsService:
    path = tmp_path / "settings.json"
    settings = SettingsService(path=path)
    settings.set("acquisition.storage.root_dir", str(tmp_path / "recordings"), persist=False)
    return settings


def test_app_lifespan_starts_and_shuts_down_engine(settings: SettingsService) -> None:
    driver = ApiDemoDriver()
    app = create_app(driver_factories=[lambda: driver], settings=settings)

    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["ok"] is True

    assert driver.shutdown_called is True


def test_http_driver_endpoints_and_error_mapping(settings: SettingsService) -> None:
    driver = ApiDemoDriver()
    app = create_app(driver_factories=[lambda: driver], settings=settings)

    with TestClient(app) as client:
        drivers = client.get("/drivers")
        assert drivers.status_code == 200
        assert drivers.json()[0]["driver_id"] == driver.device_id

        search = client.post(
            f"/drivers/{driver.device_id}/search",
            json={"provider": "demo"},
        )
        assert search.status_code == 200
        assert search.json()[0]["title"] == "API Demo Device"

        bad_search = client.post(
            f"/drivers/{driver.device_id}/search",
            json={"provider": "bad"},
        )
        assert bad_search.status_code == 400
        assert bad_search.json()["error"]["type"] == "ValueError"

        connect = client.post(
            f"/drivers/{driver.device_id}/connect",
            json={
                "title": "API Demo Device",
                "subtitle": "demo",
                "extra": {"token": "demo"},
            },
        )
        assert connect.status_code == 200

        start = client.post(f"/drivers/{driver.device_id}/start-streaming")
        assert start.status_code == 200

        snapshot = client.get(f"/drivers/{driver.device_id}")
        assert snapshot.status_code == 200
        assert snapshot.json()["is_connected"] is True
        assert snapshot.json()["is_streaming"] is True

        stop = client.post(f"/drivers/{driver.device_id}/stop-streaming")
        assert stop.status_code == 200
        disconnect = client.post(f"/drivers/{driver.device_id}/disconnect")
        assert disconnect.status_code == 200


def test_http_acquisition_settings_and_timeout_mapping(settings: SettingsService) -> None:
    app = create_app(
        driver_factories=[TimeoutSearchDriver],
        settings=settings,
    )

    with TestClient(app) as client:
        acquisition = client.get("/acquisition")
        assert acquisition.status_code == 200
        assert acquisition.json()["state"] == "idle"

        invalid_recording = client.post(
            "/acquisition/start-recording",
            json={"session_name": "   ", "recording_label": None},
        )
        assert invalid_recording.status_code == 409
        assert invalid_recording.json()["error"]["type"] == "RuntimeError"

        timeout_search = client.post(
            "/drivers/timeout_demo.01/search",
            json={"provider": "demo"},
        )
        assert timeout_search.status_code == 504
        assert timeout_search.json()["error"]["type"] == "TimeoutError"

        update = client.put(
            "/settings/ui.preview.rate_hz",
            json={"value": 30, "persist": False},
        )
        assert update.status_code == 200

        snapshot = client.get("/settings")
        assert snapshot.status_code == 200
        assert snapshot.json()["ui"]["preview"]["rate_hz"] == 30

        delete = client.delete("/settings/ui.preview.rate_hz?persist=false")
        assert delete.status_code == 200


def test_sse_events_stream_emits_driver_connection_lost(settings: SettingsService) -> None:
    driver = ApiDemoDriver()
    app = create_app(driver_factories=[lambda: driver], settings=settings)

    with TestClient(app) as client:
        connect = client.post(
            f"/drivers/{driver.device_id}/connect",
            json={
                "title": "API Demo Device",
                "subtitle": "demo",
                "extra": {"token": "demo"},
            },
        )
        assert connect.status_code == 200
        event_stream = client.app.state.engine.open_event_stream(maxsize=8)
        driver.emit_connection_lost({"code": "DEMO_LOST"})
        event_name, payload = _read_sse_event_from_generator(
            _iter_sse_messages(_ConnectedRequest(), event_stream)
        )

    assert event_name == "driver_connection_lost"
    assert payload["driver_id"] == driver.device_id
    assert payload["detail"] == {"code": "DEMO_LOST"}


def test_sse_events_stream_emits_resync_required_on_overflow(
    settings: SettingsService,
) -> None:
    app = create_app(driver_factories=[ApiDemoDriver], settings=settings)

    with patch(
        "modlink_core.event_stream.EventStream.read",
        side_effect=EventStreamOverflowError("event stream overflowed"),
    ):
        with TestClient(app) as client:
            event_stream = client.app.state.engine.open_event_stream(maxsize=1)
            event_name, payload = _read_sse_event_from_generator(
                _iter_sse_messages(_ConnectedRequest(), event_stream)
            )

    assert event_name == "resync_required"
    assert payload == {"reason": "event_stream_overflow"}


def test_websocket_frames_stream_encodes_signal_frame(settings: SettingsService) -> None:
    driver = ApiDemoDriver()
    app = create_app(driver_factories=[lambda: driver], settings=settings)
    stream_id = driver.descriptors()[0].stream_id

    with TestClient(app) as client:
        with client.websocket_connect(f"/frames?stream_id={stream_id}") as websocket:
            emitted = driver.emit_demo_frame(seq=7)
            assert emitted is True
            payload = websocket.receive_json()

    assert payload["kind"] == "frame"
    assert payload["stream_id"] == stream_id
    assert payload["payload_type"] == "signal"
    assert payload["seq"] == 7
    assert payload["dtype"] == "float32"
    assert payload["shape"] == [1, 4]


def _read_sse_event(lines) -> tuple[str, dict[str, object]]:
    event_name = ""
    payload = {}
    for line in lines:
        if not line:
            if event_name:
                return event_name, payload
            continue
        if line.startswith("event: "):
            event_name = line.removeprefix("event: ")
            continue
        if line.startswith("data: "):
            payload = json.loads(line.removeprefix("data: "))
    raise AssertionError("SSE event was not received")

def _read_sse_event_from_generator(generator) -> tuple[str, dict[str, object]]:
    return _read_sse_event(_collect_sse_lines(generator))


def _collect_sse_lines(generator) -> list[str]:
    chunks: list[str] = []

    async def _read() -> None:
        async for chunk in generator:
            chunks.extend(chunk.splitlines())
            break

    import asyncio

    asyncio.run(_read())
    return chunks


class _ConnectedRequest:
    async def is_disconnected(self) -> bool:
        return False
