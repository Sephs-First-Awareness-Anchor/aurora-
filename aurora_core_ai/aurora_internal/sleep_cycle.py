#!/usr/bin/env python3
"""Simple dual-strata sleep cycle state.

Subsurface owns the sleep/wake clock. Surface checks is_sleeping().
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

_FILE = "dual_strata_sleep_state.json"


def _path(state_dir: Any) -> Path:
    return Path(state_dir or "aurora_state") / _FILE


def _read(state_dir: Any) -> Dict[str, Any]:
    p = _path(state_dir)
    try:
        return dict(json.loads(p.read_text(encoding="utf-8")))
    except Exception:
        return {"sleeping": False, "wake_at": 0.0, "dream_triggered": False}


def _write(state_dir: Any, data: Dict[str, Any]) -> None:
    p = _path(state_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(p)


def is_sleeping(state_dir: Any = None) -> bool:
    state = _read(state_dir)
    if not state.get("sleeping"):
        return False
    wake_at = float(state.get("wake_at", 0.0) or 0.0)
    if wake_at and time.time() >= wake_at:
        exit_sleep(state_dir)
        return False
    return True


def enter_sleep(state_dir: Any = None, duration_s: float = 7200.0) -> float:
    wake_at = time.time() + float(duration_s or 0.0)
    _write(state_dir, {"sleeping": True, "wake_at": wake_at, "dream_triggered": False, "entered_at": time.time()})
    return wake_at


def exit_sleep(state_dir: Any = None) -> None:
    state = _read(state_dir)
    state.update({"sleeping": False, "wake_at": 0.0, "dream_triggered": False, "exited_at": time.time()})
    _write(state_dir, state)


def mark_dream_triggered(state_dir: Any = None) -> None:
    state = _read(state_dir)
    state["dream_triggered"] = True
    _write(state_dir, state)


def sleep_state(state_dir: Any = None) -> Dict[str, Any]:
    return _read(state_dir)
