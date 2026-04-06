"""Application entry exports for ModLink Studio."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("modlink-studio")
except PackageNotFoundError:
    __version__ = "0.0.0"


def __getattr__(name: str):
    if name == "main":
        from .app import main

        return main
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
