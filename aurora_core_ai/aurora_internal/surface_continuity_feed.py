#!/usr/bin/env python3
"""Surface -> subsurface continuity packet queue."""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List

_FILE = "surface_continuity_feed.jsonl"


def _path(state_dir: Any) -> Path:
    return Path(state_dir or "aurora_state") / _FILE


def write_continuity_packet(state_dir: Any = None, packet: Dict[str, Any] | None = None, **kwargs: Any) -> Dict[str, Any]:
    data = dict(packet or {})
    data.update(kwargs)
    data.setdefault("ts", time.time())
    p = _path(state_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(data, sort_keys=True, ensure_ascii=True) + "\n")
    return data


def read_and_clear_continuity_packets(state_dir: Any = None, max_packets: int = 256) -> List[Dict[str, Any]]:
    p = _path(state_dir)
    if not p.exists():
        return []
    packets: List[Dict[str, Any]] = []
    try:
        lines = p.read_text(encoding="utf-8").splitlines()
        for line in lines[-int(max_packets):]:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
                if isinstance(item, dict):
                    packets.append(item)
            except Exception:
                pass
        p.unlink(missing_ok=True)
    except Exception:
        return packets
    return packets
