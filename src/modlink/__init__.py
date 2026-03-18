"""Fresh ModLink Studio package.

This package is the clean-slate home for the new architecture. It does not
depend on the legacy ``openbciganglionui`` runtime layout.
"""

from .acquisition import (
    AcquisitionTask,
    MarkerRecord,
    RecordingRequest,
    RecordingState,
    RecordingStateEvent,
    SegmentRecord,
)
from .bus import FrameSubscription, StreamBus
from .device import Device
from .runtime import ModLinkRuntime
from .shared import (
    FrameEnvelope,
    FrameSignal,
    StreamDescriptor,
)
from .settings import SettingChangedEvent, SettingsService

__all__ = [
    "AcquisitionTask",
    "Device",
    "FrameSignal",
    "FrameEnvelope",
    "FrameSubscription",
    "MarkerRecord",
    "ModLinkRuntime",
    "RecordingRequest",
    "RecordingState",
    "RecordingStateEvent",
    "SegmentRecord",
    "SettingChangedEvent",
    "SettingsService",
    "StreamBus",
    "StreamDescriptor",
]
