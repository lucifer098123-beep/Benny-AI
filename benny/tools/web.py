"""Web tool — ONLY through the gatekeeper. Never trusted with the network."""
from __future__ import annotations

import urllib.request
from . import code_exec  # reuse run_python? no — separate


def fetch(url: str, gatekeeper, query: str = "") -> str:
    """Fetch a URL through the gatekeeper. Returns clean text or a refusal."""
    allowed, reason, info = gatekeeper.check(url, query)
    if not allowed:
        return f"BLOCKED by gatekeeper: {reason}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "benny-agent/0.1"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        return gatekeeper.sanitize_text(raw)
    except Exception as e:
        return f"ERROR fetching: {e}"


TOOL = {
    "name": "web",
    "description": "fetch — web access ONLY via the default-deny gatekeeper",
    "functions": {},
}
