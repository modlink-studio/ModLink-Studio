from __future__ import annotations

import logging

from modlink_core.logging_setup import configure_host_logging


def test_configure_host_logging_writes_records_to_file(tmp_path) -> None:
    log_path = tmp_path / "modlink.log"
    root_logger = logging.getLogger()

    try:
        configured_path = configure_host_logging(log_path=log_path, console=False)
        logging.getLogger("modlink_core.runtime.engine").info("engine log smoke test")
        for handler in root_logger.handlers:
            if hasattr(handler, "flush"):
                handler.flush()

        assert configured_path == log_path
        assert log_path.exists()
        assert "engine log smoke test" in log_path.read_text(encoding="utf-8")
    finally:
        for handler in list(root_logger.handlers):
            if getattr(handler, "_modlink_managed_handler", False):
                root_logger.removeHandler(handler)
                handler.close()


def test_configure_host_logging_replaces_previous_managed_handlers(tmp_path) -> None:
    log_path = tmp_path / "modlink.log"
    root_logger = logging.getLogger()

    try:
        configure_host_logging(log_path=log_path, console=False)
        configure_host_logging(log_path=log_path, console=False)
        logging.getLogger("modlink_core.recording.backend").info("single line")
        for handler in root_logger.handlers:
            if hasattr(handler, "flush"):
                handler.flush()

        lines = [
            line
            for line in log_path.read_text(encoding="utf-8").splitlines()
            if "single line" in line
        ]
        assert len(lines) == 1
    finally:
        for handler in list(root_logger.handlers):
            if getattr(handler, "_modlink_managed_handler", False):
                root_logger.removeHandler(handler)
                handler.close()


def test_configure_host_logging_enables_debug_records_when_requested(tmp_path) -> None:
    log_path = tmp_path / "modlink-debug.log"
    root_logger = logging.getLogger()

    try:
        configure_host_logging(log_path=log_path, console=False, debug=True)
        logging.getLogger("modlink_core.runtime.engine").debug("debug log smoke test")
        for handler in root_logger.handlers:
            if hasattr(handler, "flush"):
                handler.flush()

        assert "debug log smoke test" in log_path.read_text(encoding="utf-8")
    finally:
        for handler in list(root_logger.handlers):
            if getattr(handler, "_modlink_managed_handler", False):
                root_logger.removeHandler(handler)
                handler.close()
