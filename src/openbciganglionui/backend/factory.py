from __future__ import annotations

import os

from .base import GanglionBackendBase
from .brainflow import BrainFlowGanglionBackend
from .mock_backend import MockGanglionBackend


def create_backend(backend_name: str | None = None) -> GanglionBackendBase:
    selected = str(
        backend_name or os.getenv("OPENBCI_BACKEND", "brainflow")
    ).strip().lower()

    if selected in {"brainflow", "real"}:
        return BrainFlowGanglionBackend()
    if selected in {"mock", "demo"}:
        return MockGanglionBackend()

    raise ValueError(f"unsupported backend: {selected}")
