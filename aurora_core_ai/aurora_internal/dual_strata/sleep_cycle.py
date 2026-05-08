"""
Aurora sleep cycle — Surface dormancy, Subsurface continuity.

Architectural law:
    Surface inactivity = dormancy, not death, as long as Subsurface remains active.
    During sleep: no live intake, no interaction, but continuity work continues.
    Waking = Surface re-emerges over an already-continuing Subsurface.

Schedule: 8 hours awake, 2 hours asleep.
During sleep: Subsurface runs a dream burst to integrate what was accumulated.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

_SLEEP_STATE_FILENAME = "surface_sleep_mode.json"

AWAKE_DURATION_S: float = 8 * 3600   # 8 hours awake
SLEEP_DURATION_S: float = 2 * 3600   # 2 hours asleep


def _resolve(state_dir: Any) -> Path:
    if state_dir is not None:
        return Path(str(state_dir))
    return Path(__file__).resolve().parents[2] / "aurora_state"


def read_sleep_state(state_dir: Any) -> Dict[str, Any]:
    path = _resolve(state_dir) / _SLEEP_STATE_FILENAME
    if not path.exists():
        return {"sleeping": False}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {"sleeping": False}


def is_sleeping(state_dir: Any) -> bool:
    return bool(read_sleep_state(state_dir).get("sleeping", False))


def enter_sleep(state_dir: Any, *, duration_s: float = SLEEP_DURATION_S) -> float:
    """
    Mark Surface as sleeping. Returns the wake_at timestamp.
    Called by Subsurface when the awake duration has elapsed.
    """
    root = _resolve(state_dir)
    now = time.time()
    wake_at = now + duration_s
    payload = {
        "sleeping": True,
        "sleep_entered_at": now,
        "sleep_entered_at_str": time.strftime("%Y-%m-%d %H:%M:%S"),
        "wake_at": wake_at,
        "wake_at_str": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(wake_at)),
        "duration_s": duration_s,
        "dream_triggered": False,
    }
    _write_atomic(root / _SLEEP_STATE_FILENAME, payload)
    return wake_at


def mark_dream_triggered(state_dir: Any) -> None:
    """Record that the dream burst was fired for this sleep period."""
    path = _resolve(state_dir) / _SLEEP_STATE_FILENAME
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data["dream_triggered"] = True
            _write_atomic(path, data)
    except Exception:
        pass


def exit_sleep(state_dir: Any) -> None:
    """
    Clear the sleep state. Called by Subsurface at wake_at.
    Surface will resume on its next loop iteration.
    """
    path = _resolve(state_dir) / _SLEEP_STATE_FILENAME
    payload = {
        "sleeping": False,
        "woke_at": time.time(),
        "woke_at_str": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    _write_atomic(path, payload)


def _write_atomic(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)
