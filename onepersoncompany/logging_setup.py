from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging() -> None:
    root = logging.getLogger()
    if getattr(root, "_opc_logging_configured", False):
        return

    log_dir = Path.cwd() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "onepersoncompany.log"

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        filename=str(log_file),
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.INFO)

    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(file_handler)
    root.addHandler(stream_handler)

    # Keep uvicorn logs and app logs in one place.
    for name in ["uvicorn", "uvicorn.error", "uvicorn.access", "onepersoncompany"]:
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True

    setattr(root, "_opc_logging_configured", True)


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)
