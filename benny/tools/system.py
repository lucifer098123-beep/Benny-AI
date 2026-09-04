"""System tool — processes, disk health, monitoring."""
from __future__ import annotations

import os
import platform


def info() -> str:
    lines = [
        f"OS:       {platform.system()} {platform.release()}",
        f"Machine:  {platform.node()} ({platform.machine()})",
        f"Python:   {platform.python_version()}",
    ]
    return "\n".join(lines)


def disk_usage(path: str = "C:\\") -> str:
    try:
        usage = os.statvfs(path)
    except AttributeError:
        # Windows fallback via shutil
        import shutil
        total, used, free = shutil.disk_usage(path)
        return (f"{path} total: {total/1024**3:.1f}GB  "
                f"used: {used/1024**3:.1f}GB  free: {free/1024**3:.1f}GB")
    total = usage.f_frsize * usage.f_blocks
    free = usage.f_frsize * usage.f_bavail
    return f"{path} total: {total/1024**3:.1f}GB  free: {free/1024**3:.1f}GB"


def processes(top: int = 10) -> str:
    """Top RAM consumers via wmic (no psutil dependency)."""
    import subprocess
    try:
        r = subprocess.run(
            ["wmic", "process", "get", "ProcessId,Name,WorkingSetSize", "/format:csv"],
            capture_output=True, text=True, timeout=10,
        )
        rows = []
        for line in r.stdout.splitlines()[1:]:
            if not line.strip():
                continue
            parts = line.split(",")
            # format: Node,ProcessId,WorkingSetSize,Name (order varies)
            try:
                pid = parts[1].strip()
                ws = int(parts[2].strip() or 0)
                name = parts[3].strip() if len(parts) > 3 else "?"
                rows.append((ws, pid, name))
            except (ValueError, IndexError):
                continue
        rows.sort(reverse=True)
        lines = ["PID  NAME                  MEM_MB"]
        for ws, pid, name in rows[:top]:
            lines.append(f"{pid:<5} {name[:20]:<20} {ws//1024//1024}")
        return "\n".join(lines)
    except Exception as e:
        return f"could not read processes: {e}"


def memory() -> str:
    """RAM usage via ctypes GlobalMemoryStatusEx (no psutil)."""
    import ctypes
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]
    try:
        m = MEMORYSTATUSEX()
        m.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        total = m.ullTotalPhys / 1024**3
        avail = m.ullAvailPhys / 1024**3
        return (f"RAM total: {total:.1f}GB  used: {total-avail:.1f}GB  "
                f"free: {avail:.1f}GB  ({m.dwMemoryLoad}%)")
    except Exception as e:
        return f"could not read memory: {e}"


TOOL = {
    "name": "system",
    "description": "info, disk_usage, processes, memory — system introspection",
    "functions": {
        "info": info,
        "disk_usage": disk_usage,
        "processes": processes,
        "memory": memory,
    },
}
