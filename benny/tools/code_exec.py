"""Code-exec tool — sandboxed script run + debug.

Runs Python snippets in a subprocess with tight limits so Benny can
reason about code WITHOUT endangering the host. Sandbox is a best-effort
timeout/size guard, not a true security boundary.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


def run_python(code: str, timeout: int = 10) -> str:
    if len(code) > 8000:
        return "ERROR: snippet too large (8KB cap)"
    with tempfile.TemporaryDirectory(prefix="benny_exec_") as td:
        f = Path(td) / "snippet.py"
        f.write_text(code, encoding="utf-8")
        try:
            r = subprocess.run(
                [sys.executable, str(f)],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=td,  # run somewhere harmless
            )
            out = (r.stdout or "") + (("\n[stderr]\n" + r.stderr) if r.stderr else "")
            return out.strip() or "(no output)"
        except subprocess.TimeoutExpired:
            return f"ERROR: timed out after {timeout}s"
        except Exception as e:
            return f"ERROR: {e}"


def run_shell(cmd: str, timeout: int = 15) -> str:
    """Run a shell command with a timeout. Use sparingly — Benny treats
    the host as read-mostly; destructive ops require explicit user action."""
    if len(cmd) > 2000:
        return "ERROR: command too large"
    try:
        r = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        out = (r.stdout or "") + (("\n[stderr]\n" + r.stderr) if r.stderr else "")
        return out.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return f"ERROR: timed out after {timeout}s"
    except Exception as e:
        return f"ERROR: {e}"


TOOL = {
    "name": "code_exec",
    "description": "run_python, run_shell — sandboxed script/debug execution",
    "functions": {
        "run_python": run_python,
        "run_shell": run_shell,
    },
}
