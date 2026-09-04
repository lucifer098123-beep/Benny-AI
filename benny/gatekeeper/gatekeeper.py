"""GATEKEEPER — EXTRA-HARD, default-deny network control.

The agent is NEVER trusted with the network. Every byte in/out requires
user awareness and (for new domains) approval. All attempts are audited.

Flow: block → classify → sanitize → (ask) → fetch-clean-text-only
"""
from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.parse
from pathlib import Path
from typing import Callable


class Gatekeeper:
    def __init__(self, cfg: dict, audit_dir: str | Path, ask_callback: Callable | None = None):
        g = cfg.get("gatekeeper", {})
        self.default_deny = g.get("default_deny", True)
        self.https_only = g.get("https_only", True)
        self.no_ip_urls = g.get("no_ip_urls", True)
        self.allow_domains = set(g.get("allow_domains", []))
        self.allow_regex = g.get("allow_regex", [])
        self.ask_on_new = g.get("ask_on_new", True)
        self.audit_enabled = g.get("audit_enabled", True)
        self.blocked_topics = g.get("blocked_topics", [])
        self.audit_dir = Path(audit_dir)
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        # ask_callback(user_prompt) -> bool (True = allow)
        self.ask = ask_callback or (lambda p: False)

    # ---- URI parsing / validation ----
    def _parse(self, url: str):
        url = url.strip()
        if not re.match(r"^https?://", url, re.I):
            return None
        p = urllib.parse.urlparse(url)
        return p

    def _normalize_host(self, host: str) -> str:
        host = host.lower().rstrip(".")
        # strip port if present
        if ":" in host:
            host = host.split(":")[0]
        return host

    def is_ip(self, host: str) -> bool:
        host = self._normalize_host(host)
        # IPv4
        if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", host):
            return True
        # IPv6 heuristics
        if ":" in host and re.search(r"[0-9a-f]", host):
            return True
        return False

    def _classify_topic(self, url: str, query: str) -> str:
        blocked = [t for t in self.blocked_topics if t.lower() in (url + " " + query).lower()]
        return "blocked-topic" if blocked else "unknown"

    # ---- main gate ----
    def check(self, url: str, query: str = "") -> tuple[bool, str, dict]:
        """Return (allowed, reason, info). All checks logged."""
        p = self._parse(url)
        if p is None:
            return False, "must be http(s) URL", {}
        if self.https_only and p.scheme != "https":
            return False, "https-only (no http)", {}
        host = self._normalize_host(p.hostname or "")
        if self.no_ip_urls and self.is_ip(host):
            return False, "IP-address URLs denied", {}

        blocked_topics = [t for t in self.blocked_topics if t.lower() in (url + " " + query).lower()]
        if blocked_topics:
            return False, f"blocked-topic: {blocked_topics[0]}", {}

        info = {"host": host, "url": url, "query": query, "time": time.time()}
        allowed = False
        reason = "default-deny"
        if host in self.allow_domains:
            allowed, reason = True, "allowlist domain"
        elif any(re.search(r, url, re.I) for r in self.allow_regex):
            allowed, reason = True, "allowlist regex"
        elif self.ask_on_new and self.ask(f"Allow Benny to fetch:\n{url}\n(query: {query or 'none'})"):
            allowed, reason = True, "user-approved"
            self.allow_domains.add(host)  # remember for future? (session only unless persisted)

        info["allowed"] = allowed
        info["reason"] = reason
        self._audit(info)
        return allowed, reason, info

    # ---- response sanitizer ----
    @staticmethod
    def sanitize_text(raw: str, max_chars: int = 4000) -> str:
        """Strip tags/scripts, collapse whitespace, cap length."""
        text = re.sub(r"<script.*?</script>", " ", raw, flags=re.S | re.I)
        text = re.sub(r"<style.*?</style>", " ", text, flags=re.S | re.I)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        text = text.strip()
        if len(text) > max_chars:
            text = text[:max_chars] + "…[truncated]"
        return text

    def _audit(self, info: dict) -> None:
        if not self.audit_enabled:
            return
        day = time.strftime("%Y-%m-%d")
        f = self.audit_dir / f"gatekeeper_{day}.jsonl"
        with open(f, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(info) + "\n")

    def recent_audit(self, n: int = 20) -> list[dict]:
        files = sorted(self.audit_dir.glob("gatekeeper_*.jsonl"))
        rows = []
        for f in files[-1:]:
            for line in f.read_text(encoding="utf-8").splitlines():
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass
        return rows[-n:]
