from __future__ import annotations

import time

import numpy as np

from modlink_sdk import StreamDescriptor


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
