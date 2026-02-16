"""
Structured Logging Module
==========================
Replaces print() statements with proper logging.
Logs to both console and rotating file.

Usage:
    from logger import get_logger
    log = get_logger(__name__)
    log.info("Fetched %d tickers", count)
"""

import os
import logging
from logging.handlers import RotatingFileHandler


_loggers = {}


def get_logger(name: str = "trading") -> logging.Logger:
    """Get or create a named logger with console + file handlers."""
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)

    # Avoid adding handlers if already present (e.g. from reimport)
    if logger.handlers:
        _loggers[name] = logger
        return logger

    # Import config lazily to avoid circular imports
    try:
        from config import load_config
        cfg = load_config()
        level = getattr(logging, cfg.logging.level.upper(), logging.INFO)
        log_file = cfg.logging.file
        max_bytes = cfg.logging.max_bytes
        backup_count = cfg.logging.backup_count
    except Exception:
        level = logging.INFO
        log_file = "logs/trading.log"
        max_bytes = 10_485_760
        backup_count = 5

    logger.setLevel(level)

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # File handler with rotation
    try:
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8"
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning("Could not set up file logging: %s", e)

    _loggers[name] = logger
    return logger
