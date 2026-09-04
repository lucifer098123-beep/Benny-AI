"""Free-floating memory engine — the moat.

Everything the agent knows lives HERE, in JSON files, OUTSIDE any model.
The model is a swappable engine; memory carries over 1:1 on every upgrade.

Memory types:
  - episodes  : timestamped conversation/action records
  - prefs     : learned preferences (list of {key, value, confidence})
  - patterns  : recurring behaviours detected by the recombination engine
"""
from __future__ import annotations

import json
import re
import time
from collections import defaultdict
from pathlib import Path
from typing import Any


class MemoryStore:
    def __init__(self, memory_dir: str | Path):
        self.dir = Path(memory_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.episodes_file = self.dir / "episodes.json"
        self.prefs_file = self.dir / "prefs.json"
        self.patterns_file = self.dir / "patterns.json"
        self._episodes: list[dict[str, Any]] = self._load(self.episodes_file, [])
        self._prefs: list[dict[str, Any]] = self._load(self.prefs_file, [])
        self._patterns: dict[str, Any] = self._load(self.patterns_file, {})

    @staticmethod
    def _load(path: Path, default):
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return default
        return default

    @staticmethod
    def _dump(path: Path, data) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ---- episodes ----
    def record_episode(self, role: str, content: str, meta: dict | None = None) -> None:
        self._episodes.append({
            "ts": time.time(),
            "role": role,
            "content": content,
            "meta": meta or {},
        })
        # keep bounded
        if len(self._episodes) > 2000:
            self._episodes = self._episodes[-2000:]
        self._dump(self.episodes_file, self._episodes)

    def recent_episodes(self, n: int = 20) -> list[dict[str, Any]]:
        return self._episodes[-n:]

    # ---- preferences ----
    def learn_pref(self, key: str, value: Any, confidence: float = 0.5) -> None:
        for pref in self._prefs:
            if pref["key"] == key:
                # damped update: keep newer info weighted slightly higher
                pref["value"] = value
                pref["confidence"] = max(pref.get("confidence", 0), confidence)
                pref["ts"] = time.time()
                self._dump(self.prefs_file, self._prefs)
                return
        self._prefs.append({"key": key, "value": value, "confidence": confidence, "ts": time.time()})
        self._dump(self.prefs_file, self._prefs)

    def get_pref(self, key: str, default=None):
        for pref in self._prefs:
            if pref["key"] == key:
                return pref["value"]
        return default

    def all_prefs(self) -> list[dict[str, Any]]:
        return self._prefs

    # ---- recombination engine (the "growth") ----
    def recombine(self) -> list[str]:
        """Scan recent episodes, detect repeat patterns, cache as muscle-memory.
        Returns newly discovered patterns.
        """
        text = " ".join(e["content"].lower() for e in self._episodes[-200:])
        words = re.findall(r"[a-z0-9]{4,}", text)
        counts = defaultdict(int)
        for w in words:
            counts[w] += 1
        bigrams = defaultdict(int)
        for a, b in zip(words, words[1:]):
            bigrams[f"{a} {b}"] += 1

        new = []
        for phrase, c in bigrams.items():
            if c >= 3 and phrase not in self._patterns:
                self._patterns[phrase] = {"count": c, "first_seen": time.time()}
                new.append(phrase)
        for w, c in counts.items():
            if c >= 5 and w not in self._patterns:
                self._patterns[w] = {"count": c, "first_seen": time.time()}
                new.append(w)
        if new:
            self._dump(self.patterns_file, self._patterns)
        return new

    def patterns(self) -> dict[str, Any]:
        return self._patterns

    def purge(self) -> None:
        """Hard reset — your call when you want a clean slate."""
        self._episodes = []
        self._prefs = []
        self._patterns = {}
        for f in (self.episodes_file, self.prefs_file, self.patterns_file):
            if f.exists():
                f.unlink()

    def file_count(self) -> int:
        return len(self._episodes) + len(self._prefs) + len(self._patterns)
