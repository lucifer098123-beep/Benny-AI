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

agent: Agent | None = None
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
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        url = urlparse(self.path)
        if url.path != "/chat":
            self._json(404, {"error": "not found"})
            return
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
    global agent, boot_error
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


def main() -> None:
    boot()
    if agent is None:
        print(f"benny webface: {boot_error}")
        sys.exit(1)
    print(f"benny webface v0.1 — {agent.identity.get('core', {}).get('name', 'benny')} @ {HOST}:{PORT}")
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