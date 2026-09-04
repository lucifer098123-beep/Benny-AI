"""Device binding + lock + tamper response.

Locks Benny to THIS machine via a hardware fingerprint. Same model on a
different laptop = different IDs = locked out.

Currently fingerprint is opt-in (enabled: false) so first-run works
anywhere. Flip it on once you've set your device IDs.
"""
from __future__ import annotations

import json
import platform
import subprocess
import time
from pathlib import Path


def _wmic_capture(cmd: list[str]) -> list[str]:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return [line.strip() for line in out.stdout.splitlines() if line.strip()]
    except Exception:
        return []


class DeviceLock:
    def __init__(self, cfg: dict):
        c = cfg.get("security", {}).get("fingerprint", {})
        self.enabled = c.get("enabled", False)
        self.device_ids = set(c.get("device_ids", []))
        self.max_failures = cfg.get("security", {}).get("tamper", {}).get("max_failures", 3)
        self._fail_file = Path(__file__).resolve().parent.parent.parent / "data" / "security" / "failures.json"

    def current_fingerprint(self) -> dict:
        fp = {
            "machine": platform.node(),
            "platform": platform.platform(),
            "processor": platform.processor(),
        }
        # CPU processor ID (Intel)
        for line in _wmic_capture(["wmic", "cpu", "get", "processorid"]):
            if line and line.lower() not in ("processorid",):
                fp["cpu_id"] = line
        # System UUID
        for line in _wmic_capture(["wmic", "csproduct", "get", "uuid"]):
            if line and line.lower() not in ("uuid",):
                fp["uuid"] = line
        # Motherboard serial
        for line in _wmic_capture(["wmic", "baseboard", "get", "serialnumber"]):
            if line and line.lower() not in ("serialnumber",):
                fp["mobo_serial"] = line
        return fp

    def is_bound(self) -> bool:
        if not self.enabled:
            return True  # not enforced yet
        fp = self.current_fingerprint()
        return any(v in self.device_ids for v in fp.values())

    def check_and_lock(self) -> tuple[bool, str]:
        """Returns (allowed, message). On repeated failure, lock out."""
        if not self.enabled:
            return True, "device-binding disabled (opt-in)"
        if self.is_bound():
            self._clear_failures()
            return True, "device-bound OK"
        fails = self._bump_failure()
        if fails >= self.max_failures:
            return False, f"LOCKED: {fails} fingerprint mismatches"
        return False, f"device mismatch ({fails}/{self.max_failures})"

    def _fail_path(self) -> Path:
        self._fail_file.parent.mkdir(parents=True, exist_ok=True)
        return self._fail_file

    def _bump_failure(self) -> int:
        p = self._fail_path()
        data = {}
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        data["count"] = data.get("count", 0) + 1
        data["last"] = time.time()
        p.write_text(json.dumps(data), encoding="utf-8")
        return data["count"]

    def _clear_failures(self) -> None:
        p = self._fail_path()
        if p.exists():
            p.unlink()
