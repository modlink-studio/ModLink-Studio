# Plugins

Concrete driver implementations live here instead of under packages/.

Plugins under this directory are intentionally kept out of the root workspace by
default. The recommended way to use a plugin is to attach it at run time with
`uv run --with <path>` or `uv run --with-editable <path>`.

Current plugins:

- `openbciganglion/`: OpenBCI Ganglion driver.

