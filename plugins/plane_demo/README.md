# Plane Demo Plugin

Minimal example driver that exposes synthetic `plane` streams for ModLink Studio.

This demo currently publishes:

- a thermal map stream
- a pressure map stream

Recommended startup from the repository root:

```powershell
uv sync
uv run --with .\plugins\plane_demo modlink-studio
```
