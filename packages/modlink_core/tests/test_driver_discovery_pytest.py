from __future__ import annotations

from typing import Any

import pytest

from modlink_core.drivers import discovery
from modlink_core.drivers.discovery import discover_driver_factories


class FakeEntryPoint:
    def __init__(self, name: str, loaded: object) -> None:
        self.name = name
        self._loaded = loaded

    def load(self) -> object:
        if isinstance(self._loaded, Exception):
            raise self._loaded
        return self._loaded


def test_discover_driver_factories_sorts_and_loads_callables(monkeypatch: pytest.MonkeyPatch) -> None:
    def factory_alpha() -> str:
        return "alpha"

    def factory_zulu() -> str:
        return "zulu"

    captured: dict[str, Any] = {}

    def fake_entry_points(*, group: str) -> list[FakeEntryPoint]:
        captured["group"] = group
        return [
            FakeEntryPoint("zulu", factory_zulu),
            FakeEntryPoint("alpha", factory_alpha),
        ]

    monkeypatch.setattr(discovery, "entry_points", fake_entry_points)

    factories = discover_driver_factories(group="custom.group")

    assert captured == {"group": "custom.group"}
    assert factories == [factory_alpha, factory_zulu]


def test_discover_driver_factories_rejects_non_callable_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        discovery,
        "entry_points",
        lambda *, group: [FakeEntryPoint("broken", object())],
    )

    with pytest.raises(TypeError, match="entry point 'broken'"):
        discover_driver_factories()


def test_discover_driver_factories_propagates_load_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        discovery,
        "entry_points",
        lambda *, group: [FakeEntryPoint("broken", RuntimeError("load failed"))],
    )

    with pytest.raises(RuntimeError, match="load failed"):
        discover_driver_factories()
