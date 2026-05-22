"""Aurora sleep cycle state shared by Surface and Subsurface."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

_SLEEP_STATE_FILENAME = "surface_sleep_mode.json"
AWAKE_DURATION_S: float = 8 * 3600
SLEEP_DURATION_S: float = 2 * 3600


def _resolve(state_dir: Any = None) -> Path:
    if state_dir is not None:
        return Path(str(state_dir))
    return Path(__file__).resolve().parents[2] / "aurora_state"


def _write_atomic(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)


def read_sleep_state(state_dir: Any = None) -> Dict[str, Any]:
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


def is_sleeping(state_dir: Any = None) -> bool:
    state = read_sleep_state(state_dir)
    if not bool(state.get("sleeping", False)):
        return False
    wake_at = float(state.get("wake_at", 0.0) or 0.0)
    if wake_at and time.time() >= wake_at:
        exit_sleep(state_dir)
        return False
    return True


def enter_sleep(state_dir: Any = None, *, duration_s: float = SLEEP_DURATION_S) -> float:
    root = _resolve(state_dir)
    now = time.time()
    wake_at = now + float(duration_s or 0.0)
    payload = {
        "sleeping": True,
        "sleep_entered_at": now,
        "sleep_entered_at_str": time.strftime("%Y-%m-%d %H:%M:%S"),
        "wake_at": wake_at,
        "wake_at_str": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(wake_at)),
        "duration_s": float(duration_s or 0.0),
        "dream_triggered": False,
    }
    _write_atomic(root / _SLEEP_STATE_FILENAME, payload)
    return wake_at


def mark_dream_triggered(state_dir: Any = None) -> None:
    path = _resolve(state_dir) / _SLEEP_STATE_FILENAME
    data = read_sleep_state(state_dir)
    data["dream_triggered"] = True
    _write_atomic(path, data)


def exit_sleep(state_dir: Any = None) -> None:
    path = _resolve(state_dir) / _SLEEP_STATE_FILENAME
    payload = {
        "sleeping": False,
        "woke_at": time.time(),
        "woke_at_str": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    _write_atomic(path, payload)


class SleepCycleManager:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.created_at = time.time()
        self.last_tick = 0.0
        self.tick_count = 0

    def tick(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        self.last_tick = time.time()
        self.tick_count += 1
        return {
            "slept": False,
            "tick_count": self.tick_count,
            "reason": "compatibility_noop",
        }

    def status(self) -> Dict[str, Any]:
        return {
            "available": True,
            "created_at": self.created_at,
            "last_tick": self.last_tick,
            "tick_count": self.tick_count,
        }
