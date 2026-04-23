from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from platformdirs import user_log_path

DEFAULT_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
DEFAULT_MAX_LOG_BYTES = 5 * 1024 * 1024
DEFAULT_BACKUP_COUNT = 5
_MANAGED_HANDLER_FLAG = "_modlink_managed_handler"
_MANAGED_LOGGER_NAMES = (
    "modlink_core",
    "modlink_ui",
    "modlink_server",
    "modlink_studio",
    "uvicorn",
    "uvicorn.error",
    "uvicorn.access",
)


def configure_host_logging(
    *,
    log_path: str | Path | None = None,
    app_name: str = "ModLink Studio",
    app_author: str = "ModLink",
    log_filename: str = "modlink.log",
    console: bool = True,
    debug: bool = False,
    max_bytes: int = DEFAULT_MAX_LOG_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
) -> Path:
    resolved_path = (
        Path(log_path)
        if log_path is not None
        else Path(user_log_path(app_name, app_author)) / log_filename
    )
    resolved_path.parent.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    _remove_managed_handlers(root_logger)
    root_logger.setLevel(logging.WARNING)
    log_level = logging.DEBUG if debug else logging.INFO

    formatter = logging.Formatter(DEFAULT_LOG_FORMAT)
    file_handler = RotatingFileHandler(
        resolved_path,
        maxBytes=max(1, int(max_bytes)),
        backupCount=max(1, int(backup_count)),
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    _mark_managed(file_handler)
    root_logger.addHandler(file_handler)

    if console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        _mark_managed(console_handler)
        root_logger.addHandler(console_handler)

    for logger_name in _MANAGED_LOGGER_NAMES:
        logger = logging.getLogger(logger_name)
        logger.setLevel(log_level)
        logger.propagate = True

    logging.captureWarnings(True)
    logging.getLogger(__name__).info(
        "Configured logging at %s (level=%s)",
        resolved_path,
        logging.getLevelName(log_level),
    )
    return resolved_path


def _remove_managed_handlers(logger: logging.Logger) -> None:
    for handler in list(logger.handlers):
        if not getattr(handler, _MANAGED_HANDLER_FLAG, False):
            continue
        logger.removeHandler(handler)
        handler.close()


def _mark_managed(handler: logging.Handler) -> None:
    setattr(handler, _MANAGED_HANDLER_FLAG, True)
