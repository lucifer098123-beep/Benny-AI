"""Vision lane — benny's eyes.

A second approved brain path: build.nvidia's free NIM API
(meta/llama-3.2-11b-vision-instruct) reads an image (or gif frame-samples)
and describes/answers it. Same trust class as the text brain: prompts out,
personal data stays home. No third-party deps — pure stdlib urllib.
"""
from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request


def _load_nvidia_key() -> str | None:
    from ..core import project_root
    sf = project_root() / "config" / "secrets.json"
    if sf.exists():
        try:
            data = json.loads(sf.read_text(encoding="utf-8"))
            return data.get("nvidia_api_key")
        except Exception:
            return None
    return None


class VisionBrain:
    """Reads an image and answers a question about it (VLM)."""

    name = "nvidia-vision"
    endpoint = "https://integrate.api.nvidia.com/v1/chat/completions"
    model = "meta/llama-3.2-11b-vision-instruct"
    model_heavy = "meta/llama-3.2-90b-vision-instruct"

    def __init__(self, token: str | None = None):
        self.token = token or _load_nvidia_key()

    @property
    def ready(self) -> bool:
        return bool(self.token)

    def describe(self, image_url: str | None = None, image_b64: str | None = None,
                 question: str = "Describe what's in this image in one or two sentences.",
                 heavy: bool = False, timeout: int = 120) -> str:
        if not self.ready:
            return "vision-error: nvidia key missing — add nvidia_api_key to config/secrets.json"
        if not image_url and not image_b64:
            return "vision-error: no image given"

        img = {"type": "image_url", "image_url": {"url": image_url}} if image_url else {
            "type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
        body = {
            "model": self.model_heavy if heavy else self.model,
            "messages": [{"role": "user", "content": [img, {"type": "text", "text": question}]}],
            "max_tokens": 512,
            "temperature": 0.3,
        }
        req = urllib.request.Request(
            self.endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip() or "(empty)"
        except urllib.error.HTTPError as e:
            if e.code == 401:
                return "vision-error: nvidia key rejected"
            if e.code == 404 or e.code == 410:
                return f"vision-error: model unavailable on build.nvidia ({e.code}) — catalog went stale, use the 11b model"
            return f"vision-error: nvidia api {e.code}"
        except Exception as e:
            return f"vision-error: {e}"


def encode_file(path: str) -> str | None:
    """Base64-encode a local image file for direct vision calls."""
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("ascii")
    except Exception:
        return None