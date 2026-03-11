# Backend Contract

This document defines the backend contract consumed by the UI layer.

## Scope

The UI layer may depend on backend code in exactly these ways:

1. Import `GanglionBackendBase` as the only runtime backend port.
2. Import event/config/session models from `backend.models`.
3. Call public methods on a `GanglionBackendBase` instance.
4. Subscribe to signals emitted by a `GanglionBackendBase` instance.

The UI layer must not:

- import a concrete backend implementation such as `MockGanglionBackend`
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
- `sig_record -> RecordEvent`
- `sig_error -> ErrorEvent`
- `sig_search -> SearchEvent`
- `sig_labels -> LabelsEvent`
- `sig_save_dir -> SaveDirEvent`

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

## Mock Backend Specific Semantics

Defined by `mock_backend.py`.

- After `connect_device()` succeeds, `MockGanglionBackend` auto-starts preview.
- Therefore the observed state sequence is typically:
  - `connecting -> connected -> previewing`
- Reconnect resets:
  - `seq`
  - `sample_index0`
  - burst runtime state
- Label storage and default save directory are persisted to app-data files.
- Stream generation shape is controlled by:
  - `ConnectConfig.fs`
  - `ConnectConfig.n_channels`
  - `ConnectConfig.chunk_size`

## UI Boundary Check

Current UI imports should only need:

- `GanglionBackendBase`
- `DeviceState`
- event/config/session models from `models.py`

If a UI file needs to import a concrete backend class, that is a boundary violation and should be moved to the app composition root.
