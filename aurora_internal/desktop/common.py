from __future__ import annotations

import hashlib
import json
from pathlib import Path


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False, default=str).encode()).hexdigest()


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return default


def write_json(path, value):
    from aurora_persistence_utils import atomic_write_json
    if not atomic_write_json(Path(path), value, default=str):
        raise OSError(f"could not persist {Path(path).name}")
