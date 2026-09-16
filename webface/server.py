"""benny webface — the browser face for benny. Stays private, zero deps.

Serves a static chat UI on localhost and relays to the same Agent the
terminal runs. The engine/memory/gatekeeper are untouched — this is a
front door, not a rebuild.

v0.3 merged: sessions + model port + approval gate + path authority.
"""
from __future__ import annotations

import json
import sys
import time
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import benny.paths as paths  # noqa: E402  (needs the sys.path insert above)

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
HOST = "127.0.0.1"
PORT = 7749
SESSIONS_DIR = ROOT.parent / "data" / "webface_sessions"

# sys.path so `python -m benny.webface` or `python webface/server.py` both work
if str(ROOT.parent) not in sys.path:
    sys.path.insert(0, str(ROOT.parent))

from benny.core.engine import Agent  # noqa: E402
from benny.core.vision import VisionBrain  # noqa: E402

agent: Agent | None = None
vision: VisionBrain | None = None
boot_error: str | None = None
_sess_lock = threading.Lock()


# ---- session store (disk-backed, survives restarts) ----
def _sess_path(session_id: str) -> Path:
    return SESSIONS_DIR / f"{session_id}.json"


def _sess_load(session_id: str) -> dict | None:
    try:
        with _sess_lock:
            p = _sess_path(session_id)
            if not p.exists():
                return None
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _sess_save(data: dict) -> None:
    with _sess_lock:
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        data["updated"] = time.time()
        _sess_path(data["id"]).write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def _sess_new() -> dict:
    sid = uuid.uuid4().hex[:12]
    data = {"id": sid, "title": "new chat", "created": time.time(),
            "updated": time.time(), "messages": []}
    _sess_save(data)
    return data


def _sess_list() -> list[dict]:
    out = []
    with _sess_lock:
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        for p in SESSIONS_DIR.glob("*.json"):
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                out.append({
                    "id": d["id"], "title": d.get("title", "new chat"),
                    "created": d.get("created", 0), "updated": d.get("updated", 0),
                    "count": len(d.get("messages", [])),
                })
            except Exception:
                continue
    out.sort(key=lambda s: s["updated"], reverse=True)
    return out


def _sess_delete(session_id: str) -> bool:
    with _sess_lock:
        p = _sess_path(session_id)
        if p.exists():
            p.unlink()
            return True
    return False


def _sess_history(data: dict) -> list:
    """The brain gets last-10-turns context, in {role, content} form."""
    return [{"role": m.get("role"), "content": m.get("content")}
            for m in data.get("messages", [])]


# ---- flat conversation history (backwards compat, data/conversations/) ----
MAX_HISTORY = 500
CONVERSATIONS = paths.resolve(
    paths.load_settings()["paths"]["conversation_dir"]
) / "conversations.json"


def _load_history() -> list[dict]:
    if CONVERSATIONS.exists():
        try:
            return json.loads(CONVERSATIONS.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_history(msgs: list[dict]) -> None:
    CONVERSATIONS.parent.mkdir(parents=True, exist_ok=True)
    CONVERSATIONS.write_text(json.dumps(msgs[-MAX_HISTORY:]), encoding="utf-8")


def _append_history(who: str, text: str) -> None:
    msgs = _load_history()
    msgs.append({"who": who, "text": text, "ts": time.time()})
    _save_history(msgs)


# ---- gatekeeper approval gate (in-UI modal) ----
APPROVAL_TIMEOUT = 45  # seconds; fail-closed (deny) if the user never answers
_approval_lock = threading.Lock()
_approval = {"pending": False, "url": "", "query": "", "ts": 0.0}
_approval_answer: bool | None = None


def _ask_modal(prompt: str) -> bool:
    """ask_callback for the browser face: registers a pending approval and
    blocks until the user answers in the UI. Default-deny on timeout."""
    global _approval, _approval_answer
    url = query = ""
    for part in prompt.splitlines():
        if part.startswith("Allow Benny to fetch:"):
            url = part.split(":", 1)[1].strip()
        elif part.startswith("(query:"):
            query = part[1:-1].replace("query:", "").strip().rstrip(")")
    with _approval_lock:
        _approval = {"pending": True, "url": url or prompt, "query": query, "ts": time.time()}
        _approval_answer = None
    try:
        deadline = time.monotonic() + APPROVAL_TIMEOUT
        while time.monotonic() < deadline:
            with _approval_lock:
                if not _approval["pending"]:
                    return bool(_approval_answer)
            time.sleep(0.2)
        return False  # fail closed — no answer means no network
    finally:
        with _approval_lock:
            _approval["pending"] = False


class WebfaceHandler(BaseHTTPRequestHandler):
    server_version = "benny-webface/0.3"
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
            self._json(200, {
                "status": state,
                "boot_error": boot_error,
                "boot_ms": getattr(agent, "_boot_ms", None),
                "vision": bool(vision and vision.ready),
                "model": (agent.identity.get("core", {}).get("model")
                          if agent else None),
            })
        elif url.path == "/sessions":
            if agent is None:
                self._json(503, {"error": "agent not up"})
            else:
                self._json(200, {"sessions": _sess_list()})
        elif url.path == "/session":
            q = urlparse(self.path)
            import re as _re
            m = _re.search(r"id=([0-9a-f]{12})", q.query)
            if not m:
                self._json(400, {"error": "missing session id"})
            else:
                d = _sess_load(m.group(1))
                if d is None:
                    self._json(404, {"error": "no such session"})
                else:
                    self._json(200, d)
        elif url.path == "/brain":
            if agent is None:
                self._json(503, {"error": "agent not up"})
            else:
                self._json(200, {"brain": agent.brain_status(), "vision": bool(vision and vision.ready)})
        elif url.path == "/history":
            self._json(200, {"messages": _load_history(), "max": MAX_HISTORY})
        elif url.path == "/approval-status":
            with _approval_lock:
                self._json(200, _approval)
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
        elif url.path == "/session":
            self._session_post()
        elif url.path == "/brain":
            self._brain_post()
        elif url.path == "/clear":
            _save_history([])
            self._json(200, {"ok": True, "messages": 0})
        elif url.path == "/approve":
            self._approve()
        else:
            self._json(404, {"error": "not found"})

    def _session_post(self):
        """POST /session — new session. POST /session?del=<id> — delete."""
        q = urlparse(self.path)
        import re as _re
        m = _re.search(r"del=([0-9a-f]{12})", q.query)
        if m:
            if _sess_delete(m.group(1)):
                self._json(200, {"ok": True})
            else:
                self._json(404, {"error": "no such session"})
            return
        self._json(200, _sess_new())

    def _brain_post(self):
        """POST /brain — the model port. Swap benny's favourite model live."""
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            self._json(400, {"error": "bad request"})
            return
        if agent is None:
            self._json(503, {"error": "agent not up"})
            return
        endpoint = str(payload.get("endpoint", "")).strip() or None
        model = str(payload.get("model", "")).strip() or None
        heavy = str(payload.get("model_heavy", "")).strip() or None
        key = str(payload.get("api_key", "")).strip() or None
        if not model and not key and not endpoint:
            self._json(400, {"error": "send model, endpoint, and/or api_key"})
            return
        try:
            msg = agent.swap_brain(endpoint=endpoint, model=model,
                                   model_heavy=heavy, api_key=key)
        except Exception as e:
            self._json(500, {"error": f"swap failed: {e}"})
            return
        self._json(200, {"ok": True, "message": msg, "brain": agent.brain_status()})

    def _chat(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode("utf-8"))
            text = str(payload.get("text", "")).strip()
            session_id = str(payload.get("session_id", "")).strip() or None
        except Exception:
            self._json(400, {"error": "bad request"})
            return
        if not text:
            self._json(400, {"error": "empty message"})
            return
        if agent is None:
            self._json(503, {"error": "agent not up"})
            return

        # session: load existing or create one on the fly
        data = _sess_load(session_id) if session_id else None
        is_new = False
        if data is None:
            data = _sess_new()
            is_new = True
            session_id = data["id"]

        # title = first thing the user says
        if is_new or data.get("title", "new chat") == "new chat":
            data["title"] = text.strip().splitlines()[0][:48]
            if not data.get("messages"):
                data["title"] = "new chat"

        data["messages"].append({"role": "user", "content": text, "ts": time.time()})

        t0 = time.monotonic()
        try:
            reply = agent.respond(text, history=_sess_history(data))
        except Exception as e:  # never 500 the user with a stack
            reply = f"ERROR: {e}"

        data["messages"].append({"role": "benny", "content": reply, "ts": time.time()})
        if data["title"] in (None, "new chat") and not is_new:
            data["title"] = text.strip().splitlines()[0][:48]
        _sess_save(data)
        _append_history("you", text)
        _append_history("benny", reply)

        self._json(200, {
            "session_id": data["id"],
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
            reads = []
            for f in frames[:6]:
                reads.append(vision.describe(image_b64=str(f), question=question, heavy=heavy))
            reply = "\n---\n".join(r for r in reads if not r.startswith("vision-error"))
            if not reply:
                reply = reads[-1]
        else:
            reply = vision.describe(image_url=url or None, image_b64=img_b64 or None,
                                    question=question, heavy=heavy)
        _append_history("you", f"(image) {question}" if not frames else f"(gif) {question}")
        _append_history("benny", reply)
        self._json(200, {
            "reply": reply,
            "latency_ms": int((time.monotonic() - t0) * 1000),
        })

    def _approve(self):
        """User answered the approval modal: allow or deny the pending fetch."""
        global _approval, _approval_answer
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode("utf-8"))
            approved = bool(payload.get("approved"))
        except Exception:
            self._json(400, {"error": "bad request"})
            return
        with _approval_lock:
            if not _approval["pending"]:
                self._json(409, {"error": "no pending approval"})
                return
            _approval_answer = approved
            _approval["pending"] = False
            _approval["answer"] = approved
        self._json(200, {"ok": True, "approved": approved})

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
    # browser face: the gatekeeper asks the USER in an in-UI modal, not via a
    # silent prompt. unanswered approvals fail closed (deny). audit log keeps
    # every attempt.
    global_agent = Agent(ask_callback=_ask_modal)
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
    print(f"benny webface v0.3 — {agent.identity.get('core', {}).get('name', 'benny')} @ {HOST}:{PORT}")
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
