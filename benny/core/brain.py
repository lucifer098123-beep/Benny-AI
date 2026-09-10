"""Pluggable brain — model-agnostic, per the motherboard theory.

The brain is a swappable engine. v1 ships with:
  - rule_brain   : zero-dependency local fallback (always works, offline)
  - copilot      : GitHub Copilot API via the user's own gh token (primary,
                   OpenAI-compatible /chat/completions)
  - gemini       : free-tier Gemini (needs GOOGLE_API_KEY; ₹0, 500 req/day)

To plug any other model, subclass Brain or pass an async callable.
The memory/tools/security NEVER change when the brain swaps.
"""
from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request


class Brain:
    """Interface any model backend implements."""

    name = "base"

    def generate(self, prompt: str, system: str = "", heavy: bool = False) -> str:
        raise NotImplementedError


def _load_secret(key: str) -> str | None:
    """Read one key from config/secrets.json (gitignored)."""
    from ..core import project_root
    sf = project_root() / "config" / "secrets.json"
    if sf.exists():
        try:
            data = json.loads(sf.read_text(encoding="utf-8"))
            return data.get(key)
        except Exception:
            return None
    return None


def _gh_token() -> str | None:
    """Get the gh CLI token from the OS keyring — same token as `gh auth status`."""
    try:
        out = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        token = out.stdout.strip()
        return token or None
    except Exception:
        return None


class RuleBrain(Brain):
    """The fallback — offline, no key, instant. No real 'intelligence',
    just deterministic handlers. Used when no cloud brain is wired up."""

    name = "rule"

    def generate(self, prompt: str, system: str = "", heavy: bool = False) -> str:
        return prompt  # caller handles routing


class CopilotBrain(Brain):
    """GitHub Copilot API (api.githubcopilot.com) via the user's own gh token.

    The user's Copilot plan exposes an OpenAI-compatible /chat/completions
    endpoint authenticated with the same token `gh` CLI uses (no new key,
    no separate signup). Models confirmed on this plan:
        gpt-4.1 (heavy) | gpt-4o | gpt-4o-mini (default) | gpt-3.5-turbo

    Token resolution order: config/secrets.json `github_token` ->
    env GITHUB_TOKEN -> `gh auth token` (OS keyring). Standard OpenAI format,
    so this stays a thin urllib call, zero third-party deps.
    """

    name = "copilot"
    endpoint = "https://api.githubcopilot.com/chat/completions"

    def __init__(self, model: str = "gpt-4o-mini", model_heavy: str = "gpt-4.1",
                 token: str | None = None):
        self.model = model
        self.model_heavy = model_heavy
        self.token = token or os.environ.get("GITHUB_TOKEN") \
            or _load_secret("github_token") or _gh_token()

    @property
    def ready(self) -> bool:
        return bool(self.token)

    def generate(self, prompt: str, system: str = "", heavy: bool = False,
                 timeout: int = 90) -> str:
        if not self.ready:
            return "NO_GITHUB_TOKEN"
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        body = {
            "model": self.model_heavy if heavy else self.model,
            "messages": messages,
            "stream": False,
            "temperature": 0.7,
        }
        req = urllib.request.Request(
            self.endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip() or "(empty)"
        except urllib.error.HTTPError as e:
            if e.code == 401:
                return ("brain-error: copilot token rejected — run `gh auth login` "
                        "or add github_token to config/secrets.json")
            if e.code == 429:
                return "brain-error: copilot rate limited — wait a moment and retry"
            return f"brain-error: github api {e.code}"
        except Exception as e:
            return f"brain-error: {e}"


class GeminiBrain(Brain):
    """Free-tier Gemini via the generativelanguage API. Needs GOOGLE_API_KEY
    in the environment or config/secrets.json. ₹0 up to 500 req/day (Flash)."""

    model = os.environ.get("BENNY_GEMINI_MODEL", "gemini-2.5-flash")
    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent"
    )

    def __init__(self):
        self.key = os.environ.get("GOOGLE_API_KEY")
        if self.key is None:
            self.key = _load_secret("google_api_key")

    @property
    def ready(self) -> bool:
        return bool(self.key)

    def generate(self, prompt: str, system: str = "", heavy: bool = False) -> str:
        if not self.ready:
            return "NO_GEMINI_KEY"
        body = {
            "system_instruction": {"parts": [{"text": system}]} if system else None,
            "contents": [{"parts": [{"text": prompt}]}],
        }
        body = {k: v for k, v in body.items() if v is not None}
        req = urllib.request.Request(
            f"{self.endpoint}?key={self.key}",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
            return "".join(p.get("text", "") for p in parts).strip() or "(empty)"
        except Exception as e:
            return f"brain-error: {e}"


def build_brain(cfg: dict) -> Brain:
    """Choose brain based on config ('none' | 'copilot' | 'gemini' | 'rule')."""
    bcfg = cfg.get("brain", {})
    mode = bcfg.get("mode", "none")
    if mode == "copilot":
        b = CopilotBrain(
            model=bcfg.get("model") or "gpt-4o-mini",
            model_heavy=bcfg.get("model_heavy") or "gpt-4.1",
        )
        if b.ready:
            return b
        # no token found — fall through to rule
    if mode == "gemini":
        b = GeminiBrain()
        if b.ready:
            return b
        # no key — fall through to rule
    return RuleBrain()