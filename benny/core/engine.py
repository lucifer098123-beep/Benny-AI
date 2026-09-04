"""Agent core — the engine that stitches memory, tools, security, gatekeeper.

Model-agnostic: the 'brain' is a pluggable callable. v1 ships with a
rule-based router + optional cloud/local brain.
"""
from __future__ import annotations

from . import load_config, setup_logging, project_root
from .brain import build_brain
from ..memory import MemoryStore
from ..security.device_lock import DeviceLock
from ..gatekeeper.gatekeeper import Gatekeeper
from ..tools import files, system, code_exec, web

log = setup_logging()


class Agent:
    def __init__(self, ask_callback=None):
        self.cfg = load_config()
        self.root = project_root()
        self.memory = MemoryStore(self.root / self.cfg["paths"]["memory_dir"])
        self.lock = DeviceLock(self.cfg)
        self.gatekeeper = Gatekeeper(
            self.cfg,
            self.root / self.cfg["paths"]["audit_dir"],
            ask_callback=ask_callback,
        )
        self.tools = self._build_tools()
        self.brain = build_brain(self.cfg)

    def _build_tools(self):
        return {
            "files": files.TOOL["functions"],
            "system": system.TOOL["functions"],
            "code_exec": code_exec.TOOL["functions"],
            "web": {"fetch": lambda url, q="": self.gatekeeper_safe_fetch(url, q)},
        }

    def gatekeeper_safe_fetch(self, url, q=""):
        return web.fetch(url, self.gatekeeper, q)

    # ---- security entry ----
    def authenticate(self):
        ok, msg = self.lock.check_and_lock()
        log.info(f"device-check: {msg}")
        return ok, msg

    # ---- tool dispatch ----
    def dispatch(self, tool: str, fn: str, *args, **kwargs):
        if tool not in self.tools or fn not in self.tools[tool]:
            return f"ERROR: no such tool {tool}.{fn}"
        try:
            return self.tools[tool][fn](*args, **kwargs)
        except Exception as e:
            return f"ERROR: {tool}.{fn} raised {e}"

    # ---- the response path (rule-based v1 brain) ----
    def respond(self, user_input: str) -> str:
        self.memory.record_episode("user", user_input)
        new_pat = self.memory.recombine()

        text = user_input.lower().strip()
        out = ""

        if any(k in text for k in ("memory", "pref", "rememb", "know", "learn", "fact")):
            key = self.mock_key(user_input)
            out = self.memory_handler(text, key, user_input)
        elif any(k in text for k in ("file", "folder", "size", "disk", "director")):
            out = self.files_handler(text)
        elif any(k in text for k in ("system", "process", "ram", "memory usage", "cpu")):
            out = self.system_handler(text)
        elif any(k in text for k in ("code", "python", "run", "execute", "script")):
            out = self.code_handler(text)
        elif any(k in text for k in ("web", "fetch", "search", "internet", "http")):
            out = self.web_handler(text)
        elif any(k in text for k in ("help", "what can you do", "commands")):
            out = self.help()
        elif "prune" in text or ("clear" in text and "memory" in text):
            self.memory.purge()
            out = "memory purged. clean slate."
        else:
            out = f"(rule-based v1) got: {user_input}\nUse 'help' to see what I can do."

        self.memory.record_episode("benny", out)
        if new_pat:
            out += f"\n[learned {len(new_pat)} pattern(s)]"
        return out

    def mock_key(self, prompt):
        # simplistic pref extraction: 'remember X is Y'
        parts = prompt.lower().split(" is ", 1)
        return parts[0].replace("remember ", "").strip()

    def memory_handler(self, text, key, raw):
        # 'remember X is Y' -> store pref; 'what do you know' -> recap
        if text.startswith("remember"):
            seg = text.replace("remember", "", 1).strip()
            if " is " in seg:
                k, v = seg.split(" is ", 1)
                self.memory.learn_pref(k.strip(), v.strip(), confidence=0.7)
                return f"remembered: {k.strip()} = {v.strip()}"
        if "know" in text or "pref" in text or "facts" in text:
            prefs = self.memory.all_prefs()
            if not prefs:
                return "i know nothing yet. tell me: 'remember x is y'"
            return "\n".join(f"- {p['key']} = {p['value']}" for p in prefs)
        return "say 'remember x is y' to teach me, or 'what do you know' to review."

    def files_handler(self, text):
        if "size" in text or "disk" in text:
            return self.dispatch("files", "summary")
        if "list" in text or "ls" in text or "show" in text:
            return self.dispatch("files", "list_dir")
        return self.dispatch("files", "summary")

    def system_handler(self, text):
        if "ram" in text or "memory" in text:
            return self.dispatch("system", "memory")
        if "process" in text:
            return self.dispatch("system", "processes")
        return self.dispatch("system", "info")

    def code_handler(self, text):
        return ("run code like: 'python print(1+1)' \n"
                "i sandbox it with a timeout and show the output.")

    def web_handler(self, text):
        return ("web access is behind the default-deny gatekeeper.\n"
                "try: 'fetch https://<allowed-domain>' and i'll ask before fetching.")

    def help(self):
        return (
            "I'm benny — your offline agent. things i can do:\n"
            "  remember <x> is <y>    teach me a fact\n"
            "  what do you know       review what i learned\n"
            "  files summary/size     scan a folder for cleanup\n"
            "  ram / system info      hardware status\n"
            "  code <python>          run a sandboxed snippet\n"
            "  fetch <url>            web (gatekept, asks first)\n"
            "  prune memory           wipe my memory (your call)\n"
            "  help                   this\n"
            "  quit                   exit"
        )
