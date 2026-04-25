---
name: modlink-plugin-author
description: Create, revise, and verify external ModLink Studio driver plugin projects. Use when Codex is asked to build a ModLink or ModLink Studio device plugin, driver package, pyproject entry point, tests, or hardware integration outside the ModLink-Studio repository.
---

# ModLink Plugin Author

## Overview

Build a standalone Python project that depends on `modlink-studio`, exposes a `modlink.drivers` entry point, and can be installed into the same environment as ModLink Studio with `python -m pip install -e .`.

Do not assume the plugin author is working inside the ModLink-Studio repository. Treat the target directory as an external plugin project unless the user explicitly says otherwise.

## Project Shape

Use this layout for a new plugin:

```text
my_driver/
|-- pyproject.toml
|-- README.md
|-- my_driver/
|   |-- __init__.py
|   |-- driver.py
|   `-- factory.py
`-- tests/
    `-- test_smoke.py
```

Use `modlink-studio` as the public dependency. Driver code still imports from `modlink_sdk` because that SDK module is shipped by `modlink-studio`.

```toml
[project]
name = "my-driver"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
    "modlink-studio>=0.3.0rc1",
    "numpy>=2.3.3",
]

[project.entry-points."modlink.drivers"]
my-driver = "my_driver.factory:create_driver"
```

Do not depend on `modlink-sdk` unless the user explicitly has a separately published SDK package. Do not depend on `modlink-core` unless the plugin truly uses runtime internals.

## SDK Contract

Import public driver types from `modlink_sdk`:

```python
from modlink_sdk import Driver, FrameEnvelope, SearchResult, StreamDescriptor
```

`SearchResult` requires `title`:

```python
SearchResult(
    title="My Device",
    subtitle="COM3",
    device_id="my_device.01",
    extra={"port": "COM3"},
)
```

`StreamDescriptor` must describe stable streams before connection. Use `device_id` in `name.XX` form, stable `stream_key`, valid `payload_type`, positive `nominal_sample_rate_hz`, and positive `chunk_size`.

`FrameEnvelope` must use a `device_id` and `stream_key` matching one descriptor. Signal payloads use `data.shape == (channel_count, chunk_size)`.

## Driver Rules

Prefer `Driver` unless the device is naturally expressed as a short polling loop. Use `LoopDriver` for simple polling devices.

Implement:

- `device_id`
- `display_name`
- `descriptors()`
- `search(provider)`
- `connect_device(config)`
- `disconnect_device()`
- `start_streaming()` and `stop_streaming()` for `Driver`, or `loop()` for `LoopDriver`
- `create_driver()` in `factory.py`

Keep hardware access mockable. Tests must not require physical devices, real serial ports, cameras, microphones, network hardware, or vendor services.

For background threads, always provide clean stop paths. Tests must not leave running threads, exhausted mock iterators, or unhandled thread exceptions.

## Verification

Create a project-local virtual environment and install the plugin editable:

```bash
python -m venv .venv
python -m pip install -e . pytest
python -m compileall -q -x ".venv|egg-info|build|dist" .
python -m pytest -W error::pytest.PytestUnhandledThreadExceptionWarning
```

On Windows, run the last three commands with `.venv\Scripts\python.exe`. On macOS/Linux, run them with `.venv/bin/python`.

If verification fails, fix the plugin code or tests and rerun the same commands. Do not skip failing tests to get a green result.
