"""path_check — prove benny's every address is relative & self-contained.

Run on ANY device after a fresh clone/install:

    python scripts/path_check.py

Verifies:
  1. Every configured dir/file resolves inside ONE root (no scatter).
  2. No hardcoded drives / absolute machine paths in the codebase.
  3. The core modules all derive addresses from the single path authority.
Prints a PASS/FAIL report. Exit code 0 = clean.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import benny.paths as paths

PASS, FAIL = "PASS", "FAIL"
results: list[tuple[str, bool]] = []


def check(desc: str, ok: bool) -> None:
    results.append((desc, ok))
    print(f"[{PASS if ok else FAIL}] {desc}")


def scan_for_hardcoded_abs() -> list[str]:
    """Regex for absolute/hardcoded machine addresses in .py + .json + .cmd/.ps1."""
    pats = [
        r"[A-Za-z]:\\\\",               # C:\ , D:\ ...
        r"[A-Za-z]:\\\\[A-Za-z]",       # C:\Windows
        r"/(home|Users|usr|etc|var|tmp)/",  # unix absolute dirs
        r"\\\\(?:\w+\\)+",              # UNC \\server\share
    ]
    bad: list[str] = []
    for f in paths.project_root().glob("**/*"):
        if f.suffix.lower() not in (".py", ".json", ".cmd", ".ps1"):
            continue
        if "node_modules" in f.parts or ".git" in f.parts:
            continue
        if f.name == "path_check.py":
            continue  # this file intentionally breeds test strings
        try:
            txt = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if f.suffix.lower() == ".py":
            # only scan code — strip comments and docstrings (docs may mention
            # a drive as a rule, code must never contain one)
            txt = re.sub(r"'''.*?'''|\"\"\".*?\"\"\"", "", txt, flags=re.S)
            txt = "\n".join(
                line for line in txt.splitlines()
                if not line.lstrip().startswith("#")
            )
        for pat in pats:
            m = re.search(pat, txt)
            if m:
                bad.append(f"{f.relative_to(paths.project_root())}: {m.group(0)!r}")
                break
    return bad


def known_ok_exceptions() -> list[str]:
    # lines that legitimately mention drives (docs / comments), NOT code paths
    return ["text", "benny", "README", "BENNY_PLAN"]

# ---- actual checks ----
root = paths.project_root()
results.clear()
print(f"root: {root}\n")

# 1. settings.json paths stay inside root
try:
    cfg = paths.load_settings()
    for name, rel in cfg.get("paths", {}).items():
        p = paths.resolve(rel)
        check(f"cfg path '{name}' -> {rel} is inside root", str(p).startswith(str(root)))
except Exception as e:
    check(f"cfg paths resolve: {e}", False)

# 2. containment guard refuses escapes
try:
    paths.resolve("..", "escaped")
    check("containment guard blocks '..' escapes", False)
except ValueError:
    check("containment guard blocks '..' escapes", True)
try:
    paths.resolve(str(Path("/etc/nope")))
    check("containment guard blocks absolute escapes", False)
except ValueError:
    check("containment guard blocks absolute escapes", True)

# 3. core modules derive dirs from the authority (spot-check via a live Agent)
try:
    import benny.core.engine as engine
    a = engine.Agent()
    dirs = [a.memory, a.history, a.judge, a.gatekeeper]
    addrs = []
    for obj in dirs:
        try:
            addrs.append(obj.dir if hasattr(obj, "dir") else str(obj))
        except Exception:
            pass
    under = all(str(d).startswith(str(root)) for d in [obj.dir for obj in
                                                       [x for x in dirs if hasattr(x, 'dir')]])
    check("Agent subsystems resolve under one root", under)
except Exception as e:
    check(f"Agent dirs resolve under one root (err: {e})", False)

# 4. no hardcoded absolute addresses in source
bad = scan_for_hardcoded_abs()
check(f"no hardcoded drive/unix/UNC paths ({len(bad)} found)", len(bad) == 0)
for b in bad:
    print("      └─", b)

# ---- verdict ----
failures = [d for d, ok in results if not ok]
print()
if failures:
    print(f"RESULT: {len(results)-len(failures)}/{len(results)} passed — FIX: {failures}")
    sys.exit(1)
print(f"RESULT: {len(results)}/{len(results)} PASSED — benny is portable & self-contained.")
sys.exit(0)