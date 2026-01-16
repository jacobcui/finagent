from __future__ import annotations

import logging
import os
import sys
from typing import Optional

_configured = False


def _configure_logging() -> None:
    global _configured
    if _configured:
        return
    level_name = os.getenv("FINAGENT_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    root = logging.getLogger()
    root.setLevel(level)
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        root.addHandler(handler)
    _configured = True


def get_logger(name: Optional[str] = None) -> logging.Logger:
    _configure_logging()
    return logging.getLogger(name)
