"""
utils/logger.py

One place to configure logging for the whole app. Import `get_logger(__name__)`
from any module instead of using `print()`, so log level, format, and (later)
log shipping are controlled centrally via config.py / .env.
"""

import logging
import sys

from config import settings

_CONFIGURED = False


def _configure_root_logger():
    global _CONFIGURED
    if _CONFIGURED:
        return

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(handler)
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    _configure_root_logger()
    return logging.getLogger(name)
