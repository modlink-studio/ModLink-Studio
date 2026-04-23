from __future__ import annotations

import ctypes
import logging
import sys
import threading

logger = logging.getLogger(__name__)


def install_debug_bootstrap() -> None:
    _ensure_debug_console()
    _install_debug_exception_hooks()


def _install_debug_exception_hooks() -> None:
    previous_sys_excepthook = sys.excepthook
    previous_thread_excepthook = threading.excepthook

    def _sys_excepthook(exc_type, exc_value, exc_traceback) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            previous_sys_excepthook(exc_type, exc_value, exc_traceback)
            return
        logger.critical(
            "Unhandled exception reached the main thread",
            exc_info=(exc_type, exc_value, exc_traceback),
        )
        previous_sys_excepthook(exc_type, exc_value, exc_traceback)

    def _thread_excepthook(args: threading.ExceptHookArgs) -> None:
        if issubclass(args.exc_type, KeyboardInterrupt):
            previous_thread_excepthook(args)
            return
        thread_name = args.thread.name if args.thread is not None else "<unknown>"
        logger.critical(
            "Unhandled exception reached background thread %s",
            thread_name,
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )
        previous_thread_excepthook(args)

    sys.excepthook = _sys_excepthook
    threading.excepthook = _thread_excepthook


def _ensure_debug_console() -> None:
    if sys.platform != "win32":
        return

    kernel32 = ctypes.windll.kernel32
    if kernel32.GetConsoleWindow():
        return

    attach_parent_process = ctypes.c_uint(-1).value
    attached = bool(kernel32.AttachConsole(attach_parent_process))
    if not attached:
        error_code = kernel32.GetLastError()
        if error_code != 5 and not kernel32.AllocConsole():
            return

    sys.stdout = open("CONOUT$", "w", encoding="utf-8", buffering=1, errors="replace")
    sys.stderr = open("CONOUT$", "w", encoding="utf-8", buffering=1, errors="replace")
    sys.stdin = open("CONIN$", "r", encoding="utf-8", errors="replace")
