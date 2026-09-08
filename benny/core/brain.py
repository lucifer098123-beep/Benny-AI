"""Pluggable brain — model-agnostic, per the motherboard theory.

The brain is a swappable engine. v1 ships with:
  - rule_brain : zero-dependency local fallback (always works, offline)
  - gemini     : free-tier Gemini (needs GOOGLE_API_KEY; ₹0, 500 req/day)

To plug any other model (ollama, etc.), subclass or pass an async callable.
The memory/tools/security NEVER change when the brain swaps.
"""
from __future__ import annotations

import json
import os
import urllib.request


class Brain:
    """Interface any model backend implements."""

    name = "base"

    def generate(self, prompt: str, system: str = "") -> str:
        raise NotImplementedError


class RuleBrain(Brain):
    """The v1 default — offline, no key, instant. No real 'intelligence',
    just deterministic handlers. Good until a real model is plugged in."""

    name = "rule"

    def generate(self, prompt: str, system: str = "") -> str:
        return prompt  # caller handles routing


class GeminiBrain(Brain):
    """Free-tier Gemini via the generativelanguage API. Needs GOOGLE_API_KEY
    in the environment or config/env. ₹0 up to 500 req/day (Flash)."""

    model = os.environ.get("BENNY_GEMINI_MODEL", "gemini-2.5-flash")
    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent"
    )

    def __init__(self):
        self.key = os.environ.get("GOOGLE_API_KEY")
        if self.key is None:
            # try local secrets file (gitignored)
            from ..core import project_root
            sf = project_root() / "config" / "secrets.json"
            if sf.exists():
                try:
                    self.key = json.loads(sf.read_text(encoding="utf-8")).get("google_api_key")
                except Exception:
                    self.key = None

    @property
    def ready(self) -> bool:
        return bool(self.key)

    def generate(self, prompt: str, system: str = "") -> str:
        if not self.ready:
            return "NO_BRAIN_KEY"
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


class OllamaBrain(Brain):
    """Local, offline model via Ollama (localhost:11434).

    No data ever leaves the machine — the model has no route out, which is
    exactly the gatekeeper's default-deny stance. Pick the model tag from
    config (e.g. 'llama3.2:3b'). If Ollama isn't running, falls through to
    the rule brain so benny still answers.
    """

    name = "ollama"
    endpoint = "http://localhost:11434/api/chat"

    def __init__(self, model: str | None = None):
        self.model = model or "llama3.2:3b"

    @property
    def ready(self) -> bool:
        # Ollama is up if the version endpoint answers quickly.
        try:
            req = urllib.request.Request(
                "http://localhost:11434/api/version", method="GET"
            )
            with urllib.request.urlopen(req, timeout=2) as resp:
                return resp.status == 200
        except Exception:
            return False

    def generate(self, prompt: str, system: str = "") -> str:
        if not self.ready:
            return "NO_OLLAMA"
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        body = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.7, "num_predict": 512},
        }
        req = urllib.request.Request(
            self.endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data.get("message", {}).get("content", "").strip() or "(empty)"
        except Exception as e:
            return f"brain-error: {e}"


def build_brain(cfg: dict) -> Brain:
    """Choose brain based on config ('none' | 'gemini' | 'ollama' | 'rule')."""
    mode = cfg.get("brain", {}).get("mode", "none")
    if mode == "gemini":
        b = GeminiBrain()
        if b.ready:
            return b
        # fall through to rule if no key
    if mode == "ollama":
        model = cfg.get("brain", {}).get("workhorse") or "llama3.2:3b"
        b = OllamaBrain(model=model)
        if b.ready:
            return b
        # fall through to rule if Ollama isn't running
    return RuleBrain()
