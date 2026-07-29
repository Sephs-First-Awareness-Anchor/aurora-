# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Explicit readiness semantics for Aurora's operational runtime.

The cognitive architecture may continue operating in a degraded mode, but
degraded is not healthy and therefore is not ready by default.  A caller must
explicitly opt into degraded readiness.  An unready runtime can never be
ready, regardless of that opt-in.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from aurora_internal.aurora_runtime_faults import fault_summary


def _truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def compute_runtime_health(
    systems: Optional[Mapping[str, Any]] = None,
    *,
    allow_degraded: bool = False,
) -> Dict[str, Any]:
    """Compute the readiness law without mutating the runtime."""
    target = systems if isinstance(systems, Mapping) else {}
    explicit_unready = bool(
        target.get("_runtime_unready")
        or target.get("_boot_failed")
        or target.get("_self_check_failed")
    )
    faults = fault_summary(target)
    if explicit_unready:
        overall = "unready"
        reason = str(
            target.get("_runtime_unready_reason")
            or target.get("_boot_failure_reason")
            or "runtime marked unready"
        )
    elif faults.get("invariant_count", 0):
        overall = "unready"
        reason = "runtime invariant violations recorded"
    elif faults["count"]:
        overall = "degraded"
        reason = "runtime faults recorded"
    else:
        overall = "healthy"
        reason = "no runtime faults recorded"

    # This is intentionally explicit rather than `overall != "unready"`.
    ready = (
        overall == "healthy"
        or (overall == "degraded" and bool(allow_degraded))
    ) and overall != "unready"
    return {
        "overall": overall,
        "ready": bool(ready),
        "allow_degraded": bool(allow_degraded),
        "reason": reason,
        "faults": faults,
        "timestamp": time.time(),
    }


def publish_runtime_health(
    systems: Dict[str, Any],
    *,
    allow_degraded: Optional[bool] = None,
) -> Dict[str, Any]:
    """Store and persist the current health view in the active state tree."""
    if allow_degraded is None:
        allow_degraded = bool(systems.get("_allow_degraded", False))
    health = compute_runtime_health(systems, allow_degraded=bool(allow_degraded))
    systems["_runtime_health"] = dict(health)
    systems["_runtime_status"] = health["overall"]
    systems["_runtime_ready"] = bool(health["ready"])

    state_dir = Path(
        str(
            systems.get("state_dir")
            or os.environ.get("AURORA_STATE_DIR")
            or "aurora_state"
        )
    )
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
        target = state_dir / "runtime_health.json"
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(health, indent=2, default=str), encoding="utf-8")
        os.replace(temporary, target)
    except Exception as exc:
        # A health result that cannot be persisted is itself an operational
        # readiness failure. Keep the reason in memory instead of silently
        # claiming that the report succeeded.
        message = f"runtime health persistence failed: {exc}"
        logging.getLogger("aurora.runtime_health").error(message)
        health["overall"] = "unready"
        health["ready"] = False
        health["reason"] = message
        health["persistence_error"] = str(exc)
        systems["_runtime_unready"] = True
        systems["_runtime_unready_reason"] = message
        systems["_runtime_health_write_error"] = str(exc)
        systems["_runtime_status"] = "unready"
        systems["_runtime_ready"] = False
        systems["_runtime_health"] = dict(health)
    return health


def mark_runtime_unready(
    systems: Dict[str, Any],
    reason: str,
) -> Dict[str, Any]:
    """Mark a runtime unready; unlike degradation, this cannot be overridden."""
    systems["_runtime_unready"] = True
    systems["_runtime_unready_reason"] = str(reason or "runtime marked unready")
    return publish_runtime_health(systems, allow_degraded=False)


__all__ = [
    "compute_runtime_health",
    "mark_runtime_unready",
    "publish_runtime_health",
]
