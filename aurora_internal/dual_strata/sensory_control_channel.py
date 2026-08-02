# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations
from aurora_internal.aurora_runtime_faults import record_exception_from_locals as _aurora_record_exception_from_locals

import json
import time
from pathlib import Path
from typing import Any, Dict


def controls_path(state_dir: str | Path) -> Path:
    return Path(state_dir) / "sensory_controls.json"


def _read_json(path: Path, default: Any) -> Any:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as _aurora_boundary_exc:
            _aurora_record_exception_from_locals(
                locals(),
                module=__name__,
                operation="exception_handler:aurora_internal/dual_strata/sensory_control_channel.py:18",
                exc=_aurora_boundary_exc,
                context={"function": "_read_json", "handler_line": 18, "source_file": "aurora_internal/dual_strata/sensory_control_channel.py"},
            )
            pass
    return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)


def read_sensory_controls(state_dir: str | Path) -> Dict[str, Any]:
    payload = _read_json(controls_path(state_dir), {})
    if not isinstance(payload, dict):
        payload = {}
    return {
        "camera_enabled": bool(payload.get("camera_enabled", True)),
        "updated_at": float(payload.get("updated_at", 0.0) or 0.0),
        "source": str(payload.get("source", "") or ""),
    }


def write_sensory_controls(state_dir: str | Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    current = read_sensory_controls(state_dir)
    current.update(dict(payload or {}))
    current["camera_enabled"] = bool(current.get("camera_enabled", True))
    current["updated_at"] = time.time()
    current["source"] = str(current.get("source", "") or "")
    _write_json(controls_path(state_dir), current)
    return current


def camera_enabled(state_dir: str | Path) -> bool:
    return bool(read_sensory_controls(state_dir).get("camera_enabled", True))


def set_camera_enabled(state_dir: str | Path, enabled: bool, *, source: str = "") -> Dict[str, Any]:
    return write_sensory_controls(
        state_dir,
        {
            "camera_enabled": bool(enabled),
            "source": str(source or ""),
        },
    )
