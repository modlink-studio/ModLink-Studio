# Legacy Backend Contract

This document defines the current legacy backend contract consumed by the UI layer.

The future target architecture now lives in:

- `docs/platform_contract.md`
- `docs/platform_migration_plan.md`

This legacy contract remains useful while the repository is still in migration.
New architectural work should target the future platform contract first.

This document defines the backend contract consumed by the current UI layer.

## Scope

The UI layer may depend on backend code in exactly these ways:

1. Import `GanglionBackendBase` as the only runtime backend port.
2. Import event/config/session models from `backend.models`.
3. Call public methods on a `GanglionBackendBase` instance.
4. Subscribe to signals emitted by a `GanglionBackendBase` instance.

The UI layer must not:

- import a concrete backend implementation such as `BrainFlowGanglionBackend`
- read backend private attributes
- depend on backend-internal timers, buffers, or storage layout
- infer semantics from display messages

## Port Surface

Defined in `base.py`.

Public intent methods:

- `connect_device(config)`
- `search_devices(method)`
- `load_labels()`
- `add_label(label)`
- `remove_label(label)`
- `load_save_dir()`
- `set_save_dir(save_dir)`
- `disconnect_device()`
- `start_preview()`
- `stop_preview()`
- `start_record(session)`
- `stop_record()`
- `add_marker(label, note="", source="ui")`
- `start_segment(label, note="", source="ui")`
- `stop_segment(note="", source="ui")`

Snapshot properties:

- `state`
- `device_name`
- `device_address`
- `labels`
- `default_save_dir`

Signals:

- `sig_state -> StateEvent`
- `sig_stream -> StreamChunk`
- `sig_marker -> MarkerEvent`
- `sig_segment -> SegmentEvent`
- `sig_record -> RecordEvent`
- `sig_error -> ErrorEvent`
- `sig_search -> SearchEvent`
- `sig_labels -> LabelsEvent`
- `sig_save_dir -> SaveDirEvent`

## Connection Models

`ConnectConfig` and `DeviceSearchResult` may carry transport-specific connection
fields in addition to the UI display fields:

- `serial_port`
- `mac_address`
- `serial_number`
- `firmware_hint`
- `timeout_sec`

UI consumers should treat these as data-only fields and continue using backend
intent methods instead of constructing transport-specific logic themselves.

## Event Semantics

Defined in `models.py`.

### StateEvent

- Represents the latest accepted runtime state.
- `message` is display-oriented and must not be treated as stable control logic.

### StreamChunk

- `data.shape == (n_samples, n_channels)`
- `len(channel_names) == n_channels`
- `sample_index0` is the absolute sample index of `data[0]` within the current stream epoch.
- UI consumers should build x-axis data as `sample_index0 + arange(n_samples)`.
- Consumers must tolerate:
  - forward gaps
  - backward resets after reconnect/restart

### RecordEvent

- `is_recording` is the accepted new recording state after the operation.
- UI should follow this event instead of assuming that a button click succeeded.
- `sample_index`, when present, is the backend's best-known stream anchor for
  the transition moment and is suitable for timeline annotations.
- `recording_mode` indicates whether the session semantics are clip-based or continuous.

### SegmentEvent

- Represents the accepted start/stop of a labeled interval within a continuous recording session.
- `action` is backend-defined but should be stable enough for UI branching within one implementation.
- `start_sample_index` and `end_sample_index` use the same stream epoch as `StreamChunk.sample_index0`.

### LabelsEvent / SaveDirEvent

- Always represent the latest full snapshot, not a delta patch.

## Common Behavior Semantics

These semantics are expected from any backend implementation unless explicitly documented otherwise.

### Connection

- `connect_device()` is an intent, not a synchronous result.
- Once accepted, the backend should emit `CONNECTING`.
- It must eventually emit either:
  - a connected/ready state, or
  - `ERROR`

### Disconnection

- `disconnect_device()` should stop active preview/record work before reaching `DISCONNECTED`.
- Once accepted, the backend should emit `DISCONNECTING`.

### Preview / Streaming

- `start_preview()` is the intent to begin live stream emission.
- Once active, `sig_stream` should emit `StreamChunk` events.
- `stop_preview()` should stop future `sig_stream` emissions for the current epoch.

### Recording

- `start_record()` should only be considered successful after a `RecordEvent(is_recording=True)` emission.
- `stop_record()` should only be considered successful after a `RecordEvent(is_recording=False)` emission.
- UI should not optimistically assume record state changes before the event.
- Continuous-recording backends may expose labeled sub-intervals via `start_segment()` / `stop_segment()`.

## BrainFlow Backend Specific Semantics

Defined by `backend/brainflow/backend.py`.

- After `connect_device()` succeeds, `BrainFlowGanglionBackend` auto-starts preview.
- Therefore the observed state sequence is typically:
  - `connecting -> connected -> previewing`
- Reconnect resets:
  - `seq`
  - `sample_index0`
  - runtime recording/segment state

## UI Boundary Check

Current UI imports should only need:

- `GanglionBackendBase`
- `DeviceState`
- event/config/session models from `models.py`

If a UI file needs to import a concrete backend class, that is a boundary violation and should be moved to the app composition root.
