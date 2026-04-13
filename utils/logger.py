"""
Centralized logging configuration for the Stock Market AI System.
Provides color console output and rotating file logs.
"""

import logging
import logging.handlers
import sys
from pathlib import Path

try:
    import colorlog
    HAS_COLORLOG = True
except ImportError:
    HAS_COLORLOG = False

from config import LOG_CONFIG, LOGS_DIR


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name (typically __name__ of the calling module)

    Returns:
        Configured Logger instance
    """
    logger = logging.getLogger(name)

    # Don't add handlers if already configured
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, LOG_CONFIG["level"]))

    # ── Console Handler ──────────────────────────────────────
    if HAS_COLORLOG:
        console_formatter = colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s%(reset)s | %(cyan)s%(name)s%(reset)s "
            "| %(log_color)s%(levelname)s%(reset)s | %(message)s",
            datefmt=LOG_CONFIG["date_format"],
            log_colors={
                "DEBUG":    "white",
                "INFO":     "green",
                "WARNING":  "yellow",
                "ERROR":    "red",
                "CRITICAL": "bold_red",
            },
        )
    else:
        console_formatter = logging.Formatter(
            LOG_CONFIG["format"],
            datefmt=LOG_CONFIG["date_format"],
        )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # ── File Handler (Rotating) ───────────────────────────────
    log_file = LOGS_DIR / f"{name.replace('.', '_')}.log"
    file_formatter = logging.Formatter(
        LOG_CONFIG["format"],
        datefmt=LOG_CONFIG["date_format"],
    )
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=LOG_CONFIG["max_bytes"],
        backupCount=LOG_CONFIG["backup_count"],
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def get_agent_logger(agent_name: str) -> logging.Logger:
    """
    Get a logger specifically for an agent, with 'Agent.' prefix.
    """
    return get_logger(f"Agent.{agent_name}")
