"""Files/disk tool — find, organize, clean, report sizes."""
from __future__ import annotations

import os
from pathlib import Path


def list_dir(path: str = ".", depth: int = 1) -> str:
    p = Path(path).expanduser().resolve()
    if not p.exists():
        return f"ERROR: {p} does not exist"
    if not p.is_dir():
        return f"ERROR: {p} is not a directory"
    out = []
    for root, dirs, files in os.walk(p):
        rel = os.path.relpath(root, p)
        if rel.count(os.sep) >= depth and rel != ".":
            dirs[:] = []
            continue
        level = 0 if rel == "." else rel.count(os.sep) + 1
        indent = "  " * level
        out.append(f"{indent}{os.path.basename(root)}/")
        for fname in sorted(files):
            try:
                size = os.path.getsize(os.path.join(root, fname))
            except OSError:
                size = 0
            out.append(f"{indent}  {fname}  ({size//1024}KB)")
    return "\n".join(out) if out else "(empty)"


def dir_size(path: str = ".") -> str:
    p = Path(path).expanduser().resolve()
    if not p.is_dir():
        return f"ERROR: {p} not a dir"
    total = 0
    for root, _, files in os.walk(p):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return f"{path}: {total/1024/1024:.1f} MB"


def find_by_ext(path: str, ext: str) -> str:
    ext = ext.lstrip(".").lower()
    p = Path(path).expanduser().resolve()
    if not p.is_dir():
        return f"ERROR: {p} not a dir"
    hits = []
    for root, _, files in os.walk(p):
        for f in files:
            if f.lower().endswith("." + ext):
                size = 0
                try:
                    size = os.path.getsize(os.path.join(root, f))
                except OSError:
                    pass
                hits.append(f"{os.path.join(root, f)}  ({size//1024}KB)")
    return "\n".join(hits) if hits else f"no .{ext} files found"


def summary(path: str = ".") -> str:
    """Group files by extension + sizes, for cleanup decisions."""
    p = Path(path).expanduser().resolve()
    by_ext = {}
    total = 0
    for root, _, files in os.walk(p):
        for f in files:
            ext = Path(f).suffix.lower() or "(none)"
            by_ext.setdefault(ext, [0, 0])
            try:
                s = os.path.getsize(os.path.join(root, f))
            except OSError:
                s = 0
            by_ext[ext][0] += 1
            by_ext[ext][1] += s
            total += s
    lines = [f"TOTAL: {total/1024/1024:.1f} MB in {len(by_ext)} file types"]
    for ext, (count, size) in sorted(by_ext.items(), key=lambda x: -x[1][1]):
        lines.append(f"  {ext:>8}  {count:>4} files  {size/1024/1024:7.1f} MB")
    return "\n".join(lines)


TOOL = {
    "name": "files",
    "description": "list_dir, dir_size, find_by_ext, summary — inspect & clean files",
    "functions": {
        "list_dir": list_dir,
        "dir_size": dir_size,
        "find_by_ext": find_by_ext,
        "summary": summary,
    },
}
