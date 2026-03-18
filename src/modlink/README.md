# ModLink

This package is the clean-slate implementation area for the new ModLink Studio
architecture.

Current module split:

- `device/`: device runtime port
- `bus/`: stream registration, publisher handles, and signal-based frame broadcast
- `acquisition/`: recording owner with marker and segment support
- `settings/`: global settings service
- `runtime/`: minimal composition root
- `shared/`: shared runtime models
- `ui/`: UI package placeholder

The existing `openbciganglionui` package remains untouched as the legacy app
while this package grows into the new runtime.

Bus API notes live in `docs/modlink_streambus.md`.
Device side should expose per-stream frame signals and register them through `StreamBus.register_stream()`.
