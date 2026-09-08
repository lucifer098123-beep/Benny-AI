"""Benny's growth ledger — a structured record of who he is and how he grew.

Part of the free-floating memory, OUTSIDE any model. Survives every
motherboard swap. It's how benny knows his own story from V0.

The ledger grows like the recombination engine: every milestone is appended
with a timestamp. The current version is always derivable — the last entry
that bumps it.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class HistoryStore:
    def __init__(self, history_dir: str | Path):
        self.dir = Path(history_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.file = self.dir / "history.json"
        self._entries: list[dict[str, Any]] = self._load(self.file)

    @staticmethod
    def _load(path: Path, default=None):
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return default or []
        return default or []

    @staticmethod
    def _dump(path: Path, data) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @property
    def version(self) -> str:
        """The current version — last entry with a 'version' bump."""
        for e in reversed(self._entries):
            if e.get("version"):
                return str(e["version"])
        return "0.0.0"

    def add_milestone(
        self,
        version: str,
        title: str,
        summary: str,
        shipped: list[str] | None = None,
    ) -> None:
        """Append a growth milestone. `version` bumps visibly in the ledger."""
        self._entries.append({
            "version": version,
            "ts": time.time(),
            "title": title,
            "summary": summary,
            "shipped": shipped or [],
        })
        self._dump(self.file, self._entries)

    def snapshot(self) -> dict[str, Any]:
        """Full structured read — for the 'history'/'growth' command."""
        return {
            "name": "benny",
            "current_version": self.version,
            "milestones": self._entries,
            "count": len(self._entries),
        }

    def render(self) -> str:
        """Human-readable narration benny can speak."""
        lines = [f"i'm benny, and i know my own story. current version: {self.version}"]
        for e in self._entries:
            ts = time.strftime("%Y-%m-%d", time.localtime(e["ts"]))
            lines.append(f"\nV{e['version']} ({ts}) — {e['title']}")
            lines.append(f"  {e['summary']}")
            for item in e.get("shipped", []):
                lines.append(f"  • {item}")
        return "\n".join(lines)