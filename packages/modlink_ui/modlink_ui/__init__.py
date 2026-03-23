"""Public UI exports for ModLink Studio."""


def __getattr__(name: str):
    if name == "MainWindow":
        from .main_window import MainWindow

        return MainWindow
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
