"""benny/paths.py — the single path authority.

Every address benny touches resolves from ONE root: the project folder this
file lives in. Nothing is ever welded to a machine:

  - No hardcoded drives (no ``C:\\``), no OS-scattered config dirs
    (no Program Files, no ``~/.config``, no AppData).
  - The whole install is self-contained: move the folder anywhere or copy
    it to another device and every path still resolves.
  - A containment guard REFUSES any configured path that would escape the
    root. Config files, memory, audits and logs are forced to stay inside
    the source tree — one clean all-in-one address.

Usage::

    import benny.paths as paths
    root = paths.project_root()          # the all-in-one install address
    cfg  = paths.load_settings()
    logf = paths.resolve("data", "logs", "benny.log")
"""
from __future__ import annotations

import json
from pathlib import Path

# The all-in-one install address: the folder containing the `benny/` package.
# Resolved relative to this source file, so it works on any device regardless
# of where the project sits (C:\Benny-AI, D:\ai\benny, /home/x/benny, …).
_ROOT = Path(__file__).resolve().parent.parent


def project_root() -> Path:
    """The single, portable install address. Everything lives under here."""
    return _ROOT


def _inside(root: Path, p: Path) -> Path:
    """Return the resolved path, refusing anything outside the root."""
    p = p.resolve()
    if p == root or root in p.parents:
        return p
    raise ValueError(
        f"path escapes benny's root ({root}): {p} — "
        "benny keeps every file inside one self-contained folder."
    )


def resolve(*parts: str) -> Path:
    """Resolve a project-relative address. Relative-only, self-contained.

    ``paths.resolve("data", "logs")`` -> ``<root>/data/logs``.
    Refuses ``..`` or absolute parts that would leave the project folder.
    """
    rel = str(Path(*parts))
    if Path(rel).is_absolute():
        raise ValueError(f"absolute address not allowed: {rel}")
    return _inside(_ROOT, _ROOT / rel)


def load_settings() -> dict:
    """Load config/settings.json (always project-relative)."""
    cfg_path = _ROOT / "config" / "settings.json"
    with open(cfg_path, "r", encoding="utf-8") as f:
        return json.load(f)


def config_path() -> Path:
    """Address of the main config file."""
    return _ROOT / "config" / "settings.json"