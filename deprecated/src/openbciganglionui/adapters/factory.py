from __future__ import annotations

from ..core.contracts import DeviceAdapter
from .brainflow_adapter import BrainFlowGanglionAdapter


def create_device_adapter(adapter_name: str | None = None) -> DeviceAdapter:
    selected = str(adapter_name or "brainflow").strip().lower()
    if selected not in {"brainflow", "real"}:
        raise ValueError(f"unsupported device adapter: {selected}")
    return BrainFlowGanglionAdapter()
