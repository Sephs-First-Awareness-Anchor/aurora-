#!/usr/bin/env python3
"""Shared persistence utilities for Aurora."""
from __future__ import annotations

import json
import os
import threading
import time
import hashlib
from pathlib import Path
from typing import Any, Dict, Optional

PERSISTENCE_LOCK = threading.RLock()


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def atomic_write_json(path: Path, data: Dict[str, Any], *, indent: int = 2, default=None) -> bool:
    """Atomically write JSON to disk under a process-wide persistence lock."""
    tmp = None
    with PERSISTENCE_LOCK:
        try:
            _ensure_parent(path)
            fd, tmp = __import__('tempfile').mkstemp(dir=str(path.parent), suffix='.tmp')
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=indent, default=default)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
            return True
        except Exception:
            if tmp and os.path.exists(tmp):
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
            return False


def write_breach_report(state_dir: Path, report: Dict[str, Any]) -> Optional[Path]:
    try:
        report_dir = state_dir / "breach_reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        ts = int(time.time() * 1000)
        path = report_dir / f"breach_{ts}.json"
        payload = dict(report)
        payload.setdefault("timestamp", time.time())
        atomic_write_json(path, payload, indent=2, default=str)
        return path
    except Exception:
        return None


def monotonic_check(previous: Dict[str, Any], current: Dict[str, Any], keys: Dict[str, str]) -> Dict[str, Any]:
    """Return monotonicity violations where numeric values decreased."""
    violations = []
    for label, key in keys.items():
        prev = previous.get(key)
        cur = current.get(key)
        if isinstance(prev, (int, float)) and isinstance(cur, (int, float)) and cur < prev:
            violations.append({"field": key, "label": label, "previous": prev, "current": cur})
    return {"ok": not violations, "violations": violations}


def checksum_dict(data: Dict[str, Any]) -> str:
    raw = json.dumps(data, sort_keys=True, default=str)
    return hashlib.md5(raw.encode('utf-8')).hexdigest()
