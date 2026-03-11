# OpenBCI Ganglion UI

This repository is prepared for a desktop UI built with `PyQt6` and `PyQt6-Fluent-Widgets`, managed by `uv`.

## Quick start

```powershell
uv sync
uv run openbciganglionui
```

You can also launch it as a module:

```powershell
uv run python -m openbciganglionui
```

## Project layout

```text
src/openbciganglionui/
  app.py          # QApplication bootstrap
  backend/        # backend contract, events and mock implementation
  main_window.py  # FluentWindow and starter pages
  __main__.py     # python -m entrypoint
```

## Development

Install development tools and run lint checks:

```powershell
uv sync --dev
uv run ruff check .
```

## Notes

- The current setup targets Python 3.13 because that interpreter is already available on this machine.
- `PyQt6-Fluent-Widgets` is GPLv3-licensed. If this project will be distributed in a way that conflicts with GPL obligations, review the package licensing before continuing.
