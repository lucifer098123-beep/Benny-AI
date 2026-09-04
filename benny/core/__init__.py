"""Core utilities: logging, config loading, path resolution."""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path


def project_root() -> Path:
    """Resolve the project root (Benny-AI/) regardless of import location."""
    return Path(__file__).resolve().parent.parent.parent


def load_config() -> dict:
    cfg_path = project_root() / "config" / "settings.json"
    with open(cfg_path, "r", encoding="utf-8") as f:
        return json.load(f)


def setup_logging(name: str = "benny") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        log_dir = project_root() / "data" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(log_dir / "benny.log", encoding="utf-8")
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        logger.addHandler(handler)
    return logger


def config_path() -> Path:
    return project_root() / "config" / "settings.json"
