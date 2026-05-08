#!/usr/bin/env python3
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional


_BASE_DIR = Path(__file__).resolve().parents[2]
_DEFAULT_STATE_DIR = _BASE_DIR / "aurora_state"


def _resolve_state_dir(state_dir: Optional[str | Path] = None) -> Path:
    if state_dir is None:
        return _DEFAULT_STATE_DIR
    if isinstance(state_dir, Path):
        return state_dir
    return Path(str(state_dir))


def _state_paths(state_dir: Optional[str | Path] = None) -> Dict[str, Path]:
    root = _resolve_state_dir(state_dir)
    return {
        "queue": root / "surface_turn_queue.json",
        "result": root / "surface_turn_result.json",
        "status": root / "surface_daemon_status.json",
    }


def _read_json(path: Path, default: Any) -> Any:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)


def surface_daemon_alive(max_age: float = 20.0, state_dir: Optional[str | Path] = None) -> bool:
    status = _read_json(_state_paths(state_dir)["status"], {})
    if not isinstance(status, dict):
        return False
    updated_at = float(status.get("updated_at", 0.0) or 0.0)
    return bool(
        updated_at
        and (time.time() - updated_at) <= max_age
        and str(status.get("stratum_role", "") or "") == "surface"
    )


def queue_surface_turn(
    text: str,
    *,
    source: str = "surface_channel",
    session_id: str = "surface_channel",
    auto_search_enabled: bool = False,
    record_exchange: bool = True,
    track_evolutionary_trace: bool = True,
    run_periodic_maintenance: bool = True,
    mode_name: str = "BOUNDED",
    state_dir: Optional[str | Path] = None,
) -> str:
    content = str(text or "").strip()
    if not content:
        return ""

    paths = _state_paths(state_dir)
    state = _read_json(paths["queue"], {"pending": []})
    if not isinstance(state, dict):
        state = {"pending": []}
    pending = list(state.get("pending") or [])
    turn_id = uuid.uuid4().hex
    pending.append(
        {
            "id": turn_id,
            "content": content,
            "source": str(source or "surface_channel"),
            "session_id": str(session_id or "surface_channel"),
            "auto_search_enabled": bool(auto_search_enabled),
            "record_exchange": bool(record_exchange),
            "track_evolutionary_trace": bool(track_evolutionary_trace),
            "run_periodic_maintenance": bool(run_periodic_maintenance),
            "mode_name": str(mode_name or "BOUNDED"),
            "queued_at": time.time(),
            "status": "queued",
        }
    )
    state["pending"] = pending
    state["updated_at"] = time.time()
    _write_json(paths["queue"], state)
    return turn_id


def await_surface_turn(
    turn_id: str,
    *,
    timeout_s: float = 45.0,
    poll_s: float = 0.25,
    state_dir: Optional[str | Path] = None,
) -> Dict[str, Any]:
    if not turn_id:
        return {}

    result_file = _state_paths(state_dir)["result"]
    deadline = time.time() + max(float(timeout_s or 0.0), 0.0)
    while time.time() <= deadline:
        result = _read_json(result_file, {})
        if isinstance(result, dict) and str(result.get("id", "") or "") == str(turn_id):
            return result
        time.sleep(max(float(poll_s or 0.0), 0.05))
    return {}


def request_surface_turn(
    text: str,
    *,
    source: str = "surface_channel",
    session_id: str = "surface_channel",
    auto_search_enabled: bool = False,
    record_exchange: bool = True,
    track_evolutionary_trace: bool = True,
    run_periodic_maintenance: bool = True,
    mode_name: str = "BOUNDED",
    timeout_s: float = 45.0,
    state_dir: Optional[str | Path] = None,
) -> Dict[str, Any]:
    if not surface_daemon_alive(state_dir=state_dir):
        return {}
    turn_id = queue_surface_turn(
        text,
        source=source,
        session_id=session_id,
        auto_search_enabled=auto_search_enabled,
        record_exchange=record_exchange,
        track_evolutionary_trace=track_evolutionary_trace,
        run_periodic_maintenance=run_periodic_maintenance,
        mode_name=mode_name,
        state_dir=state_dir,
    )
    return await_surface_turn(turn_id, timeout_s=timeout_s, state_dir=state_dir)
