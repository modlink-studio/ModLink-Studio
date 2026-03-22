# OpenBCI Ganglion Plugin

BrainFlow-backed OpenBCI Ganglion driver plugin for ModLink Studio.

Current status:

- The plugin is discoverable through the `modlink.drivers` entry point.
- `search()` supports both `ble` and `serial` providers.
- `connect_device()` accepts a prior `SearchResult`.
- `LoopDriver` handles the timer lifecycle.
- `loop()` polls BrainFlow and emits fixed-size EEG chunks that match the registered descriptor.

Project layout:

- `pyproject.toml`: plugin package definition and `modlink.drivers` entry point
- `openbciganglion/factory.py`: zero-argument driver factory
- `openbciganglion/driver.py`: thin BrainFlow-backed `LoopDriver` implementation

This project is intentionally not added to the root workspace. That keeps it
undiscovered by default during normal `uv sync` / `uv run modlink-studio`
workflows.

Recommended startup from the repository root:

```powershell
uv sync
uv run --with .\plugins\openbciganglion modlink-studio
```

After that, ModLink Studio can discover the plugin through the
`modlink.drivers` entry point.

If you are actively developing the plugin and want local source edits to be
picked up immediately, use the editable variant:

```powershell
uv sync
uv run --with-editable .\plugins\openbciganglion modlink-studio
```
