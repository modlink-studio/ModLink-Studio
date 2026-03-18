from __future__ import annotations

import asyncio
from typing import Iterable

from ..models import DeviceSearchResult

try:
    from bleak import BleakScanner
except Exception as exc:  # pragma: no cover - import path depends on env
    BleakScanner = None
    _BLEAK_IMPORT_ERROR = exc
else:
    _BLEAK_IMPORT_ERROR = None

try:
    from serial.tools import list_ports
except Exception as exc:  # pragma: no cover - import path depends on env
    list_ports = None
    _SERIAL_IMPORT_ERROR = exc
else:
    _SERIAL_IMPORT_ERROR = None


NATIVE_BLE_METHOD = "Native BLE"
DONGLE_METHOD = "Ganglion Dongle"
_LIKELY_GANGLION_TOKENS = ("ganglion", "openbci")
_LIKELY_DONGLE_TOKENS = ("ganglion", "openbci", "bled112", "silicon labs", "cp210")


def discover_devices(method: str, timeout_sec: float = 5.0) -> list[DeviceSearchResult]:
    normalized = str(method).strip() or NATIVE_BLE_METHOD
    if normalized == NATIVE_BLE_METHOD:
        return discover_native_ble_devices(timeout_sec=timeout_sec)
    if normalized == DONGLE_METHOD:
        return discover_dongle_devices()
    raise ValueError(f"unsupported discovery method: {normalized}")


def discover_native_ble_devices(timeout_sec: float = 5.0) -> list[DeviceSearchResult]:
    if BleakScanner is None:
        raise RuntimeError("bleak is not installed") from _BLEAK_IMPORT_ERROR

    devices = asyncio.run(BleakScanner.discover(timeout=max(1.0, float(timeout_sec))))
    results = [
        DeviceSearchResult(
            name=(getattr(device, "name", None) or "BLE device").strip()
            or "BLE device",
            address=(getattr(device, "address", "") or "").strip(),
            method=NATIVE_BLE_METHOD,
            mac_address=(getattr(device, "address", "") or "").strip(),
            serial_number=(getattr(device, "name", None) or "").strip(),
        )
        for device in devices
        if (getattr(device, "address", "") or "").strip()
    ]
    return _preferred_results(results, method=NATIVE_BLE_METHOD)


def discover_dongle_devices() -> list[DeviceSearchResult]:
    if list_ports is None:
        raise RuntimeError("pyserial is not installed") from _SERIAL_IMPORT_ERROR

    ports = list_ports.comports()
    results = [
        DeviceSearchResult(
            name=_port_name(port),
            address=str(getattr(port, "device", "") or "").strip(),
            method=DONGLE_METHOD,
            serial_port=str(getattr(port, "device", "") or "").strip(),
            serial_number=str(getattr(port, "serial_number", "") or "").strip(),
        )
        for port in ports
        if str(getattr(port, "device", "") or "").strip()
    ]
    return _preferred_results(results, method=DONGLE_METHOD)


def _preferred_results(
    results: Iterable[DeviceSearchResult],
    *,
    method: str,
) -> list[DeviceSearchResult]:
    unique: list[DeviceSearchResult] = []
    seen: set[tuple[str, str]] = set()
    for result in results:
        key = (method, result.address or result.serial_port or result.mac_address)
        if key in seen:
            continue
        unique.append(result)
        seen.add(key)

    if method == NATIVE_BLE_METHOD:
        preferred = [
            result
            for result in unique
            if _contains_any_token(
                (result.name, result.address),
                _LIKELY_GANGLION_TOKENS,
            )
        ]
    else:
        preferred = [
            result
            for result in unique
            if _contains_any_token(
                (result.name, result.address, result.serial_port, result.serial_number),
                _LIKELY_DONGLE_TOKENS,
            )
        ]

    ordered = preferred or unique
    return sorted(ordered, key=lambda item: (item.name.lower(), item.address.lower()))


def _contains_any_token(parts: Iterable[str], tokens: Iterable[str]) -> bool:
    haystack = " ".join(
        str(part).strip().lower() for part in parts if str(part).strip()
    )
    return any(token in haystack for token in tokens)


def _port_name(port) -> str:
    description = str(getattr(port, "description", "") or "").strip()
    device = str(getattr(port, "device", "") or "").strip()
    manufacturer = str(getattr(port, "manufacturer", "") or "").strip()
    for candidate in (description, manufacturer, device):
        if candidate:
            return candidate
    return "Serial device"
