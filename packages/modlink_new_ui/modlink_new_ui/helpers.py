from __future__ import annotations

import base64
import time

import numpy as np
from PyQt6.QtCore import QByteArray, QBuffer, QIODevice
from PyQt6.QtGui import QImage

from modlink_sdk import FrameEnvelope, StreamDescriptor


def format_timestamp_ns(timestamp_ns: int | None) -> str:
    if timestamp_ns is None:
        return "等待数据"
    return time.strftime("%H:%M:%S", time.localtime(timestamp_ns / 1_000_000_000))


def downsample_series(values: np.ndarray, target_points: int = 240) -> list[float]:
    flattened = np.asarray(values, dtype=np.float32).reshape(-1)
    if flattened.size == 0:
        return []
    if flattened.size <= target_points:
        return flattened.tolist()

    indices = np.linspace(0, flattened.size - 1, num=target_points, dtype=np.int32)
    return flattened[indices].tolist()


def normalize_to_uint8(values: np.ndarray) -> np.ndarray:
    payload = np.asarray(values)
    if payload.size == 0:
        return np.zeros((1, 1), dtype=np.uint8)

    if np.issubdtype(payload.dtype, np.floating):
        payload = np.nan_to_num(payload, nan=0.0, posinf=1.0, neginf=0.0)
        payload = np.clip(payload, 0.0, 1.0)
        return (payload * 255.0).astype(np.uint8)

    payload = np.nan_to_num(payload, nan=0.0)
    min_value = float(payload.min())
    max_value = float(payload.max())
    if max_value <= min_value:
        return np.zeros(payload.shape, dtype=np.uint8)
    scaled = (payload - min_value) / (max_value - min_value)
    return np.clip(scaled * 255.0, 0.0, 255.0).astype(np.uint8)


def frame_to_qimage(frame: FrameEnvelope, descriptor: StreamDescriptor) -> QImage | None:
    payload = np.asarray(frame.data)
    if payload.size == 0:
        return None

    if descriptor.payload_type == "video":
        if payload.ndim == 4:
            payload = payload[:, 0, :, :]
        if payload.ndim != 3:
            return None
        if payload.shape[0] in {1, 3, 4}:
            image = np.moveaxis(payload, 0, -1)
        else:
            image = payload
        image = normalize_to_uint8(image)
        if image.ndim == 2:
            image = image[:, :, np.newaxis]
        height, width = image.shape[:2]
        channels = image.shape[2]
        if channels == 1:
            qimage = QImage(
                image.data,
                width,
                height,
                image.strides[0],
                QImage.Format.Format_Grayscale8,
            )
        elif channels == 3:
            qimage = QImage(
                image.data,
                width,
                height,
                image.strides[0],
                QImage.Format.Format_RGB888,
            )
        else:
            qimage = QImage(
                image.data,
                width,
                height,
                image.strides[0],
                QImage.Format.Format_RGBA8888,
            )
        return qimage.copy()

    payload = np.squeeze(payload)
    if payload.ndim == 1:
        payload = payload[np.newaxis, :]
    if payload.ndim != 2:
        return None

    image = normalize_to_uint8(payload)
    height, width = image.shape
    qimage = QImage(
        image.data,
        width,
        height,
        image.strides[0],
        QImage.Format.Format_Grayscale8,
    )
    return qimage.copy()


def qimage_to_data_url(image: QImage | None) -> str:
    if image is None or image.isNull():
        return ""

    byte_array = QByteArray()
    buffer = QBuffer(byte_array)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    encoded = base64.b64encode(bytes(byte_array)).decode("ascii")
    return f"data:image/png;base64,{encoded}"
