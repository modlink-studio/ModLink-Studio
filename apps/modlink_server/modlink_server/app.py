from __future__ import annotations

import asyncio
import base64
import dataclasses
import json
import logging
import queue
import time
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from modlink_core import (
    EventStreamOverflowError,
    FrameStreamOverflowError,
    ModLinkEngine,
    SettingsService,
    StreamClosedError,
)
from modlink_core.drivers import discover_driver_factories
from modlink_sdk import DriverFactory, SearchResult

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_SSE_POLL_TIMEOUT_SECONDS = 0.25
DEFAULT_SSE_HEARTBEAT_INTERVAL_SECONDS = 15.0

logger = logging.getLogger(__name__)


class SearchRequest(BaseModel):
    provider: str


class ConnectRequest(BaseModel):
    title: str
    subtitle: str = ""
    device_id: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)

    def to_search_result(self) -> SearchResult:
        return SearchResult(
            title=self.title,
            subtitle=self.subtitle,
            device_id=self.device_id,
            extra=dict(self.extra),
        )


class StartRecordingRequest(BaseModel):
    session_name: str
    recording_label: str | None = None


class MarkerRequest(BaseModel):
    label: str | None = None


class SegmentRequest(BaseModel):
    start_ns: int
    end_ns: int
    label: str | None = None


class SettingWriteRequest(BaseModel):
    value: Any
    persist: bool = True


def create_app(
    *,
    driver_factories: Sequence[DriverFactory] | None = None,
    settings: SettingsService | None = None,
    event_stream_maxsize: int = 1024,
    frame_stream_maxsize: int = 256,
    sse_heartbeat_interval_seconds: float = DEFAULT_SSE_HEARTBEAT_INTERVAL_SECONDS,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        resolved_settings = settings or SettingsService()
        resolved_factories = (
            tuple(driver_factories)
            if driver_factories is not None
            else tuple(discover_driver_factories())
        )
        engine = ModLinkEngine(
            driver_factories=resolved_factories,
            settings=resolved_settings,
        )
        app.state.engine = engine
        app.state.event_stream_maxsize = max(1, int(event_stream_maxsize))
        app.state.frame_stream_maxsize = max(1, int(frame_stream_maxsize))
        app.state.sse_heartbeat_interval_seconds = max(0.0, float(sse_heartbeat_interval_seconds))
        try:
            yield
        finally:
            engine.shutdown()

    app = FastAPI(lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.exception_handler(HTTPException)(_handle_http_exception)
    app.exception_handler(ValueError)(_handle_value_error)
    app.exception_handler(RuntimeError)(_handle_runtime_error)
    app.exception_handler(TimeoutError)(_handle_timeout_error)
    app.exception_handler(Exception)(_handle_unexpected_error)

    @app.get("/health")
    def health(request: Request) -> dict[str, Any]:
        engine = _engine(request)
        return {
            "ok": True,
            "driver_count": len(engine.driver_portals()),
            "acquisition": _json_payload(engine.recording_snapshot()),
        }

    @app.get("/drivers")
    def drivers(request: Request) -> list[dict[str, Any]]:
        engine = _engine(request)
        return [_json_payload(snapshot) for snapshot in engine.driver_snapshots()]

    @app.get("/drivers/{driver_id}")
    def driver_snapshot(driver_id: str, request: Request) -> dict[str, Any]:
        portal = _require_driver_portal(request, driver_id)
        return _json_payload(portal.snapshot())

    @app.post("/drivers/{driver_id}/search")
    async def search_driver(
        driver_id: str,
        body: SearchRequest,
        request: Request,
    ) -> list[dict[str, Any]]:
        portal = _require_driver_portal(request, driver_id)
        results = await _await_future(portal.search(body.provider))
        return [_json_payload(item) for item in results]

    @app.post("/drivers/{driver_id}/connect")
    async def connect_driver(
        driver_id: str,
        body: ConnectRequest,
        request: Request,
    ) -> dict[str, bool]:
        portal = _require_driver_portal(request, driver_id)
        await _await_future(portal.connect_device(body.to_search_result()))
        return {"ok": True}

    @app.post("/drivers/{driver_id}/disconnect")
    async def disconnect_driver(driver_id: str, request: Request) -> dict[str, bool]:
        portal = _require_driver_portal(request, driver_id)
        await _await_future(portal.disconnect_device())
        return {"ok": True}

    @app.post("/drivers/{driver_id}/start-streaming")
    async def start_driver_streaming(
        driver_id: str,
        request: Request,
    ) -> dict[str, bool]:
        portal = _require_driver_portal(request, driver_id)
        await _await_future(portal.start_streaming())
        return {"ok": True}

    @app.post("/drivers/{driver_id}/stop-streaming")
    async def stop_driver_streaming(
        driver_id: str,
        request: Request,
    ) -> dict[str, bool]:
        portal = _require_driver_portal(request, driver_id)
        await _await_future(portal.stop_streaming())
        return {"ok": True}

    @app.get("/streams/descriptors")
    def stream_descriptors(request: Request) -> dict[str, dict[str, Any]]:
        engine = _engine(request)
        return {
            stream_id: _json_payload(descriptor)
            for stream_id, descriptor in engine.bus.descriptors().items()
        }

    @app.get("/acquisition")
    def acquisition_snapshot(request: Request) -> dict[str, Any]:
        engine = _engine(request)
        return _json_payload(engine.recording_snapshot())

    @app.post("/acquisition/start-recording")
    async def start_recording(
        body: StartRecordingRequest,
        request: Request,
    ) -> dict[str, bool]:
        engine = _engine(request)
        await _await_future(
            engine.recording.start_recording(
                session_name=body.session_name,
                recording_label=body.recording_label,
            )
        )
        return {"ok": True}

    @app.post("/acquisition/stop-recording")
    async def stop_recording(request: Request) -> dict[str, bool]:
        engine = _engine(request)
        await _await_future(engine.recording.stop_recording())
        return {"ok": True}

    @app.post("/acquisition/markers")
    async def add_marker(body: MarkerRequest, request: Request) -> dict[str, bool]:
        engine = _engine(request)
        await _await_future(engine.recording.add_marker(body.label))
        return {"ok": True}

    @app.post("/acquisition/segments")
    async def add_segment(body: SegmentRequest, request: Request) -> dict[str, bool]:
        engine = _engine(request)
        await _await_future(
            engine.recording.add_segment(
                start_ns=body.start_ns,
                end_ns=body.end_ns,
                label=body.label,
            )
        )
        return {"ok": True}

    @app.get("/settings")
    def settings_snapshot(request: Request) -> dict[str, Any]:
        engine = _engine(request)
        return engine.settings_snapshot()

    @app.put("/settings/{key:path}")
    def set_setting(
        key: str,
        body: SettingWriteRequest,
        request: Request,
    ) -> dict[str, bool]:
        engine = _engine(request)
        engine.settings.set(key, body.value, persist=body.persist)
        return {"ok": True}

    @app.delete("/settings/{key:path}")
    def remove_setting(
        key: str,
        request: Request,
        persist: bool = True,
    ) -> dict[str, bool]:
        engine = _engine(request)
        engine.settings.remove(key, persist=persist)
        return {"ok": True}

    @app.get("/events")
    async def events(request: Request) -> StreamingResponse:
        engine = _engine(request)
        event_stream = engine.open_event_stream(maxsize=request.app.state.event_stream_maxsize)
        logger.info("Opened SSE event stream")
        return StreamingResponse(
            _iter_sse_messages(
                request,
                event_stream,
                heartbeat_interval_seconds=request.app.state.sse_heartbeat_interval_seconds,
            ),
            media_type="text/event-stream",
        )

    @app.websocket("/frames")
    async def frames(websocket: WebSocket) -> None:
        engine = _engine_from_scope(websocket)
        selected_stream_ids = {
            stream_id.strip()
            for stream_id in websocket.query_params.getlist("stream_id")
            if stream_id.strip()
        }
        frame_stream = engine.bus.open_frame_stream(
            maxsize=websocket.app.state.frame_stream_maxsize,
            drop_policy="drop_oldest",
            consumer_name="fastapi",
        )
        await websocket.accept()
        try:
            while True:
                try:
                    first_frame = await asyncio.to_thread(frame_stream.read, timeout=0.25)
                except queue.Empty:
                    continue
                except StreamClosedError:
                    return
                except FrameStreamOverflowError:
                    continue

                try:
                    frames_batch = [first_frame, *frame_stream.read_many()]
                except StreamClosedError:
                    return
                for frame in frames_batch:
                    if selected_stream_ids and frame.stream_id not in selected_stream_ids:
                        continue
                    await websocket.send_json(_frame_payload(engine, frame))
        except WebSocketDisconnect:
            return
        finally:
            frame_stream.close()

    return app


def main() -> None:
    uvicorn.run(
        create_app(),
        host=DEFAULT_HOST,
        port=DEFAULT_PORT,
    )


def _engine(request: Request) -> ModLinkEngine:
    return request.app.state.engine


def _engine_from_scope(websocket: WebSocket) -> ModLinkEngine:
    return websocket.app.state.engine


def _require_driver_portal(request: Request, driver_id: str):
    portal = _engine(request).driver_portal(driver_id)
    if portal is None:
        raise HTTPException(status_code=404, detail=f"driver '{driver_id}' was not found")
    return portal


async def _await_future(future: Any) -> Any:
    return await asyncio.wrap_future(future)


def _json_payload(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return jsonable_encoder(dataclasses.asdict(value))
    return jsonable_encoder(value)


def _frame_payload(engine: ModLinkEngine, frame: Any) -> dict[str, Any]:
    descriptor = engine.bus.descriptor(frame.stream_id)
    return {
        "kind": "frame",
        "stream_id": frame.stream_id,
        "device_id": frame.device_id,
        "modality": frame.modality,
        "payload_type": descriptor.payload_type if descriptor is not None else None,
        "timestamp_ns": frame.timestamp_ns,
        "seq": frame.seq,
        "dtype": str(frame.data.dtype),
        "shape": list(frame.data.shape),
        "data_base64": base64.b64encode(frame.data.tobytes(order="C")).decode("ascii"),
        "extra": jsonable_encoder(frame.extra),
    }


def _sse_message(event_name: str, payload: dict[str, Any]) -> str:
    return f"event: {event_name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _sse_comment(comment: str) -> str:
    return f": {comment}\n\n"


async def _iter_sse_messages(
    request: Request,
    event_stream: Any,
    *,
    heartbeat_interval_seconds: float = DEFAULT_SSE_HEARTBEAT_INTERVAL_SECONDS,
) -> AsyncIterator[str]:
    last_sent_at = time.monotonic()
    try:
        while True:
            if await request.is_disconnected():
                logger.info("SSE client disconnected")
                return
            try:
                event = await asyncio.to_thread(
                    event_stream.read,
                    timeout=DEFAULT_SSE_POLL_TIMEOUT_SECONDS,
                )
            except queue.Empty:
                if (
                    heartbeat_interval_seconds >= 0.0
                    and time.monotonic() - last_sent_at >= heartbeat_interval_seconds
                ):
                    last_sent_at = time.monotonic()
                    yield _sse_comment("keepalive")
                continue
            except StreamClosedError:
                logger.info("SSE event stream closed")
                return
            except EventStreamOverflowError:
                logger.warning("SSE event stream overflowed; requesting client resync")
                yield _sse_message(
                    "resync_required",
                    {"reason": "event_stream_overflow"},
                )
                return
            last_sent_at = time.monotonic()
            yield _sse_message(event.kind, _json_payload(event))
    finally:
        event_stream.close()
        logger.info("Closed SSE event stream")


async def _handle_http_exception(_request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": "HTTPException",
                "message": str(exc.detail),
            }
        },
    )


async def _handle_value_error(_request: Request, exc: ValueError) -> JSONResponse:
    return _error_response(400, exc)


async def _handle_runtime_error(_request: Request, exc: RuntimeError) -> JSONResponse:
    logger.warning("Server request failed with runtime error: %s", exc)
    return _error_response(409, exc)


async def _handle_timeout_error(_request: Request, exc: TimeoutError) -> JSONResponse:
    logger.warning("Server request timed out: %s", exc)
    return _error_response(504, exc)


async def _handle_unexpected_error(_request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Server request failed unexpectedly")
    return _error_response(500, exc)


def _error_response(status_code: int, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "type": type(exc).__name__,
                "message": str(exc),
            }
        },
    )
