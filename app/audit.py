"""Append-only, hash-chained audit trail (JSON Lines).

Each record stores the hash of the previous record, so deleting or editing any line breaks the
chain and `verify()` finds where. This is the ALCOA+ idea (attributable, contemporaneous, original)
applied to the tool's own outputs: who asked what, which passages were retrieved, which prompt,
model, rules and corpus versions produced the answer.
"""
from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timezone
from pathlib import Path

GENESIS = "0" * 64


def _canonical(record: dict) -> str:
    return json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()


def _lock_for(path: Path) -> threading.Lock:
    """One lock per log file, shared by every AuditLog instance: the pipeline creates a new instance per
    request, and two requests in parallel must not both read the same last hash (W55)."""
    key = str(path.resolve()).lower()
    with _LOCKS_GUARD:
        return _LOCKS.setdefault(key, threading.Lock())


class AuditLog:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = _lock_for(path)

    def _last_hash(self) -> str:
        if not self.path.exists():
            return GENESIS
        last = ""
        with open(self.path, "rb") as f:
            for line in f:
                if line.strip():
                    last = line
        return json.loads(last)["hash"] if last else GENESIS

    def append(self, event: str, payload: dict) -> dict:
        with self._lock:
            body = {"ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"), "event": event, **payload}
            body["prev_hash"] = self._last_hash()
            body["hash"] = hashlib.sha256((body["prev_hash"] + _canonical(body)).encode()).hexdigest()
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(_canonical(body) + "\n")
            return body

    def verify(self) -> tuple[bool, int | None]:
        """Return (ok, first_bad_line). Recomputes every hash from the start of the file."""
        prev = GENESIS
        if not self.path.exists():
            return True, None
        with open(self.path, encoding="utf-8") as f:
            for n, line in enumerate(f, 1):
                if not line.strip():
                    continue
                rec = json.loads(line)
                stored = rec.pop("hash")
                if rec.get("prev_hash") != prev:
                    return False, n
                if hashlib.sha256((prev + _canonical(rec)).encode()).hexdigest() != stored:
                    return False, n
                prev = stored
        return True, None

    def find(self, request_id: str) -> list[dict]:
        if not self.path.exists():
            return []
        with open(self.path, encoding="utf-8") as f:
            return [r for r in (json.loads(x) for x in f if x.strip()) if r.get("request_id") == request_id]
