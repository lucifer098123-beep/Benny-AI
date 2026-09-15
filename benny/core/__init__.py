"""Core utilities: logging, config loading, path resolution.

Every file address is delegated to ``benny.paths`` — the single path
authority. It guarantees relative-only, self-contained resolution: benny
never writes outside its own project folder, on any device.
"""
from __future__ import annotations

import logging
from pathlib import Path

import benny.paths as paths

project_root = paths.project_root


def resolve(*parts: str):
    """Resolve a project-relative address (see benny.paths.resolve)."""
    return paths.resolve(*parts)


def load_config() -> dict:
    """Load config/settings.json, resolving relative paths at call sites."""
    return paths.load_settings()


def setup_logging(name: str = "benny") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        log_dir = paths.resolve("data", "logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(log_dir / "benny.log", encoding="utf-8")
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        logger.addHandler(handler)
    return logger


def config_path() -> Path:
    return paths.config_path()
