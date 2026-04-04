from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest
from PyQt6.QtCore import QCoreApplication

from modlink_core import ModLinkEngine, SettingsService
from modlink_qt_bridge import QtModLinkBridge, QtSettingsBridge
from modlink_sdk import Driver, FrameEnvelope, StreamDescriptor

from modlink_new_ui.main_page import MainPageController
from modlink_new_ui.preview.image_controller import ImageStreamController
from modlink_new_ui.preview.models import (
    FieldPreviewSettings,
    RasterPreviewSettings,
    SignalPreviewSettings,
    VideoPreviewSettings,
)
from modlink_new_ui.preview.raster_controller import (
    RasterStreamController,
    VideoStreamController,
)
from modlink_new_ui.preview.signal_controller import SignalStreamController
from modlink_new_ui.preview.store import PreviewStreamSettingsStore

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class PreviewDemoDriver(Driver):
    supported_providers = ("demo",)

    @property
    def device_id(self) -> str:
        return "preview_demo.01"

    def descriptors(self) -> list[StreamDescriptor]:
        return [
            StreamDescriptor(
                device_id=self.device_id,
                modality="demo",
                payload_type="signal",
                nominal_sample_rate_hz=20.0,
                chunk_size=4,
                channel_names=("c1", "c2"),
            )
        ]

    def search(self, provider: str) -> list[object]:
        _ = provider
        return []

    def connect_device(self, config: object) -> None:
        _ = config

    def disconnect_device(self) -> None:
        return

    def start_streaming(self) -> None:
        return

    def stop_streaming(self) -> None:
        return


@pytest.fixture(scope="module")
def qapp() -> QCoreApplication:
    app = QCoreApplication.instance()
    if app is not None:
        return app
    return QCoreApplication([])


def _signal_descriptor() -> StreamDescriptor:
    return StreamDescriptor(
        device_id="signal_demo.01",
        modality="eeg",
        payload_type="signal",
        nominal_sample_rate_hz=100.0,
        chunk_size=4,
        channel_names=("c1", "c2"),
    )


def _raster_descriptor() -> StreamDescriptor:
    return StreamDescriptor(
        device_id="raster_demo.01",
        modality="raster",
        payload_type="raster",
        nominal_sample_rate_hz=50.0,
        chunk_size=2,
        channel_names=("c1",),
    )


def _field_descriptor() -> StreamDescriptor:
    return StreamDescriptor(
        device_id="field_demo.01",
        modality="field",
        payload_type="field",
        nominal_sample_rate_hz=10.0,
        chunk_size=1,
        channel_names=("c1",),
    )


def _video_descriptor() -> StreamDescriptor:
    return StreamDescriptor(
        device_id="video_demo.01",
        modality="video",
        payload_type="video",
        nominal_sample_rate_hz=30.0,
        chunk_size=1,
        channel_names=("r", "g", "b"),
    )


def test_signal_controller_flush_and_settings(qapp: QCoreApplication) -> None:
    _ = qapp
    controller = SignalStreamController(_signal_descriptor())
    frame = FrameEnvelope(
        device_id="signal_demo.01",
        modality="eeg",
        timestamp_ns=123,
        data=np.asarray([[1.0, 2.0, 3.0, 4.0], [4.0, 3.0, 2.0, 1.0]], dtype=np.float32),
        seq=1,
    )

    controller.push_frame(frame)
    assert controller.flush() is True
    assert len(controller.channelData) == 2

    controller.setLayoutMode("stacked")
    controller.setWindowSeconds(4)
    controller.setFilterMode("low_pass")
    controller.setLowCutoffHz(2.0)
    controller.setHighCutoffHz(30.0)
    controller.setNotchEnabled(True)

    exported = controller.export_settings()
    assert controller.layoutMode == "stacked"
    assert exported.window_seconds == 4
    assert exported.filter.mode == "low_pass"
    assert exported.filter.notch_enabled is True


def test_raster_field_and_video_controllers_emit_images(qapp: QCoreApplication) -> None:
    _ = qapp
    raster = RasterStreamController(_raster_descriptor())
    field = ImageStreamController(_field_descriptor())
    video = VideoStreamController(_video_descriptor())

    raster_emitted: list[object] = []
    field_emitted: list[object] = []
    video_emitted: list[object] = []

    raster.imageChanged.connect(lambda image: raster_emitted.append(image))
    field.imageChanged.connect(lambda image: field_emitted.append(image))
    video.imageChanged.connect(lambda image: video_emitted.append(image))

    raster.push_frame(
        FrameEnvelope(
            device_id="raster_demo.01",
            modality="raster",
            timestamp_ns=1,
            data=np.asarray([[[0.0, 1.0, 2.0], [2.0, 1.0, 0.0]]], dtype=np.float32),
            seq=1,
        )
    )
    field.push_frame(
        FrameEnvelope(
            device_id="field_demo.01",
            modality="field",
            timestamp_ns=1,
            data=np.asarray([[[[0.1, 0.5], [0.9, 0.3]]]], dtype=np.float32),
            seq=1,
        )
    )
    video.push_frame(
        FrameEnvelope(
            device_id="video_demo.01",
            modality="video",
            timestamp_ns=1,
            data=np.asarray(
                [
                    [[255, 0], [0, 255]],
                    [[0, 255], [255, 0]],
                    [[0, 0], [255, 255]],
                ],
                dtype=np.uint8,
            ),
            seq=1,
        )
    )

    assert raster.flush() is True
    assert field.flush() is True
    assert video.flush() is True
    assert raster_emitted
    assert field_emitted
    assert video_emitted
    assert not raster.currentImage.isNull()
    assert not field.currentImage.isNull()
    assert not video.currentImage.isNull()

    raster.apply_settings(
        RasterPreviewSettings(
            window_seconds=4,
            interpolation="bilinear",
            transform="flip_horizontal",
            value_range_mode="manual",
            manual_min=0.0,
            manual_max=2.0,
        )
    )
    field.apply_settings(
        FieldPreviewSettings(
            interpolation="bicubic",
            transform="rotate_90",
            value_range_mode="manual",
            manual_min=0.0,
            manual_max=1.0,
        )
    )
    video.apply_settings(
        VideoPreviewSettings(
            color_format="bgr",
            scale_mode="fill",
            aspect_mode="stretch",
            transform="rotate_180",
        )
    )

    assert raster.interpolation == "bilinear"
    assert field.transformMode == "rotate_90"
    assert video.colorFormat == "bgr"
    assert video.fillMode == "stretch"


def test_preview_store_roundtrip(qapp: QCoreApplication, tmp_path: Path) -> None:
    _ = qapp
    settings = SettingsService(path=tmp_path / "settings.json")
    bridge = QtSettingsBridge(settings)
    store = PreviewStreamSettingsStore(bridge)
    descriptor = _signal_descriptor()

    store.save(
        descriptor,
        SignalPreviewSettings(window_seconds=4, layout_mode="stacked"),
    )
    loaded = store.load(descriptor)

    assert loaded.window_seconds == 4
    assert loaded.layout_mode == "stacked"


def test_main_page_loads_and_saves_stream_settings(
    qapp: QCoreApplication, tmp_path: Path
) -> None:
    _ = qapp
    settings = SettingsService(path=tmp_path / "settings.json")
    descriptor = PreviewDemoDriver().descriptors()[0]
    settings.set(
        "ui.preview.streams",
        {
            descriptor.stream_id: {
                "payload_type": "signal",
                "settings": {
                    "window_seconds": 4,
                    "layout_mode": "stacked",
                    "visible_channel_indices": [],
                    "y_range_mode": "auto",
                    "manual_y_min": -1.0,
                    "manual_y_max": 1.0,
                    "filter": {
                        "family": "butterworth",
                        "mode": "none",
                        "order": 4,
                        "low_cutoff_hz": 1.0,
                        "high_cutoff_hz": 40.0,
                        "notch_enabled": False,
                        "notch_frequencies_hz": [],
                        "notch_q": 30.0,
                        "chebyshev1_ripple_db": 1.0,
                    },
                },
            }
        },
        persist=False,
    )
    runtime = ModLinkEngine(driver_factories=[PreviewDemoDriver], settings=settings)
    bridge = QtModLinkBridge(runtime)
    controller = MainPageController(bridge)

    previews = controller.previews
    assert previews
    preview_controller = previews[0].controller
    assert preview_controller.windowSeconds == 4
    assert preview_controller.layoutMode == "stacked"

    preview_controller.setWindowSeconds(12)
    snapshot = settings.snapshot()
    assert snapshot["ui"]["preview"]["streams"][descriptor.stream_id]["settings"]["window_seconds"] == 12

    bridge.shutdown()


def test_main_page_preview_items_stay_stable_during_flush(
    qapp: QCoreApplication, tmp_path: Path
) -> None:
    _ = qapp
    settings = SettingsService(path=tmp_path / "settings.json")
    runtime = ModLinkEngine(driver_factories=[PreviewDemoDriver], settings=settings)
    bridge = QtModLinkBridge(runtime)
    controller = MainPageController(bridge)
    descriptor = PreviewDemoDriver().descriptors()[0]

    events: list[int] = []
    controller.previewsChanged.connect(lambda: events.append(1))

    previews_before = controller.previews
    assert previews_before
    preview_item = previews_before[0]

    frame = FrameEnvelope(
        device_id=descriptor.device_id,
        modality=descriptor.modality,
        timestamp_ns=123,
        data=np.asarray([[1.0, 2.0, 3.0, 4.0]], dtype=np.float32),
        seq=1,
    )
    controller._on_frame(frame)
    controller._flush_previews()

    previews_after = controller.previews
    assert previews_after[0] is preview_item
    assert preview_item.frameCount == 1
    assert "已接收 1 帧" in preview_item.summaryText
    assert events == []

    bridge.shutdown()
