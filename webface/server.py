"""benny webface — the browser face for benny. Stays private, zero deps.

Serves a static chat UI on localhost and relays to the same Agent the
terminal runs. The engine/memory/gatekeeper are untouched — this is a
front door, not a rebuild.
"""
from __future__ import annotations

import json
import sys
import time
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
HOST = "127.0.0.1"
PORT = 7749

# sys.path so `python -m benny.webface` or `python webface/server.py` both work
if str(ROOT.parent) not in sys.path:
    sys.path.insert(0, str(ROOT.parent))

from benny.core.engine import Agent  # noqa: E402
from benny.core.vision import VisionBrain  # noqa: E402

agent: Agent | None = None
vision: VisionBrain | None = None
boot_error: str | None = None


class WebfaceHandler(BaseHTTPRequestHandler):
    server_version = "benny-webface/0.1"
    protocol_version = "HTTP/1.1"

    # ---- helpers ----
    def _send(self, code: int, body: bytes, ctype: str = "application/json"):
        try:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _json(self, code: int, obj) -> None:
        self._send(code, json.dumps(obj).encode("utf-8"))

    # ---- routes ----
    def do_GET(self):
        url = urlparse(self.path)
        if url.path in ("/", "/index.html"):
            self._serve_file("index.html", "text/html; charset=utf-8")
        elif url.path == "/style.css":
            self._serve_file("style.css", "text/css; charset=utf-8")
        elif url.path == "/app.js":
            self._serve_file("app.js", "text/javascript; charset=utf-8")
        elif url.path == "/favicon.ico":
            self._send(204, b"")
        elif url.path == "/health":
            state = "ready" if agent else "dead"
            self._json(200, {"status": state, "boot_error": boot_error, "boot_ms": getattr(agent, "_boot_ms", None)})
        elif url.path.startswith("/gifs/"):
            self._serve_gif(url.path[len("/gifs/"):])
        else:
            self._json(404, {"error": "not found"})

    def _serve_gif(self, name: str) -> None:
        # local reaction pack — benny only ever serves files from his own box
        if not name or "/" in name or "\\" in name or name.startswith("."):
            self._json(400, {"error": "bad gif name"})
            return
        path = STATIC / "gifs" / name
        if not path.exists():
            self._json(404, {"error": "no such gif"})
            return
        self._send(200, path.read_bytes(), "image/gif")

    def do_POST(self):
        url = urlparse(self.path)
        if url.path == "/chat":
            self._chat()
        elif url.path == "/see":
            self._see()
        else:
            self._json(404, {"error": "not found"})

    def _chat(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode("utf-8"))
            text = str(payload.get("text", "")).strip()
        except Exception:
            self._json(400, {"error": "bad request"})
            return
        if not text:
            self._json(400, {"error": "empty message"})
            return
        if agent is None:
            self._json(503, {"error": "agent not up"})
            return
        t0 = time.monotonic()
        try:
            reply = agent.respond(text)
        except Exception as e:  # never 500 the user with a stack
            reply = f"ERROR: {e}"
        self._json(200, {
            "reply": reply,
            "latency_ms": int((time.monotonic() - t0) * 1000),
            "memory": agent.memory.file_count(),
            "level": agent.calibrate_level(),
            "identity": agent.identity.get("core", {}),
        })

    def _see(self):
        """Vision lane: benny looks at an image (URL or base64) or gif frame-sample."""
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode("utf-8"))
            url = str(payload.get("url", "")).strip()
            img_b64 = str(payload.get("base64", "")).strip()
            question = str(payload.get("question", "")).strip() or \
                "Describe what's in this image in one or two sentences."
            heavy = bool(payload.get("heavy", False))
        except Exception:
            self._json(400, {"error": "bad request"})
            return
        if not url and not img_b64:
            self._json(400, {"error": "no image given — send 'url' or 'base64'"})
            return
        if vision is None or not vision.ready:
            self._json(503, {"error": "vision lane not up — add nvidia_api_key to config/secrets.json"})
            return
        t0 = time.monotonic()
        # gif: the message arrives with several sampled frames as base64 list -> join
        frames = payload.get("frames") or []
        if frames:
            # pipe each sampled frame through the VLM, return the most confident read
            reads = []
            for f in frames[:6]:
                reads.append(vision.describe(image_b64=str(f), question=question, heavy=heavy))
            reply = "\n---\n".join(r for r in reads if not r.startswith("vision-error"))
            if not reply:
                reply = reads[-1]
        else:
            reply = vision.describe(image_url=url or None, image_b64=img_b64 or None,
                                    question=question, heavy=heavy)
        self._json(200, {
            "reply": reply,
            "latency_ms": int((time.monotonic() - t0) * 1000),
        })

    def _serve_file(self, name: str, ctype: str) -> None:
        path = STATIC / name
        if not path.exists():
            self._json(404, {"error": "missing static"})
            return
        self._send(200, path.read_bytes(), ctype)

    # ---- silence the request log spam ----
    def log_message(self, fmt, *args):
        pass


def boot() -> None:
    """Authenticate once, like the terminal does."""
    global agent, vision, boot_error
    # deny-by-default: the browser face has no ask-modal yet, so the gatekeeper
    # auto-answers NO on its behalf (no silent network allowance). audit log still
    # records every attempt. v2 replaces this with a real in-UI approval gate.
    global_agent = Agent(ask_callback=lambda _p: False)
    ok, msg = global_agent.authenticate()
    if not ok:
        boot_error = f"SECURITY: {msg}"
        return
    agent = global_agent
    setattr(agent, "_boot_ms", f"{msg}")
    # vision lane — a second approved brain path (build.nvidia, free key)
    vision = VisionBrain()
    if not vision.ready:
        boot_error = "vision lane missing nvidia key (config/secrets.json nvidia_api_key)"
    print(f"vision lane: {'READY' if vision and vision.ready else 'NOT READY (no key)'}")


def main() -> None:
    boot()
    if agent is None:
        print(f"benny webface: {boot_error}")
        sys.exit(1)
    print(f"benny webface v0.2 — {agent.identity.get('core', {}).get('name', 'benny')} @ {HOST}:{PORT}")
    print(f"security: {getattr(agent, '_boot_ms', 'ok')}")
    print("open http://127.0.0.1:7749  (ctrl+c to stop)")
    httpd = ThreadingHTTPServer((HOST, PORT), WebfaceHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nbye.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()