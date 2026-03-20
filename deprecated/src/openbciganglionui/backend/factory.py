from __future__ import annotations

from .base import GanglionBackendBase
from .brainflow import BrainFlowGanglionBackend


def create_backend(backend_name: str | None = None) -> GanglionBackendBase:
    """Create the deprecated legacy backend.

    New integrations should prefer ``adapters.create_device_adapter()`` and the
    future contracts in ``core/contracts``.
    """

    selected = str(backend_name or "brainflow").strip().lower()
    if selected not in {"brainflow", "real"}:
        raise ValueError(f"unsupported backend: {selected}")
    return BrainFlowGanglionBackend()
