#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Small operational fault ledger for best-effort Aurora boundaries.

The ledger is deliberately operational rather than cognitive.  A recoverable
fallback remains visible without making the process unready, a subsystem
failure makes readiness explicit, and an internal invariant failure cannot be
hidden behind a generic degraded label.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import traceback
from pathlib import Path
from typing import Any, Dict, Mapping, Optional


_MAX_MEMORY_FAULTS = 100
_MAX_PERSISTED_FAULTS = 5000
_MAX_MESSAGE = 320

EXPECTED_FALLBACK_SEVERITIES = frozenset({"info", "informational", "warning", "expected_fallback"})
SUBSYSTEM_DEGRADATION_SEVERITIES = frozenset({"degraded", "subsystem_degradation", "subsystem"})
INVARIANT_SEVERITIES = frozenset({"invariant", "invariant_violation", "critical", "fatal"})


def _severity_from_exception(
    severity: Any,
    *,
    exc: Optional[BaseException] = None,
    exception_type: str = "",
    message: str = "",
    operation: str = "",
    context: Optional[Mapping[str, Any]] = None,
) -> str:
    """Normalize a fault into one of the three operational classes.

    ``auto`` is used by instrumented exception boundaries.  It distinguishes
    normal absence/configuration fallbacks from evidence that an internal
    contract or required API has been violated.  Explicit ``warning`` and
    ``invariant`` labels always win over inference.
    """
    raw = str(severity or "auto").strip().lower().replace("-", "_")
    if raw in {"informational", "expected_fallback"}:
        return "warning"
    if raw == "info":
        return "info"
    if raw == "warning":
        return "warning"
    if raw in INVARIANT_SEVERITIES:
        return "invariant_violation"
    if raw in SUBSYSTEM_DEGRADATION_SEVERITIES:
        return "subsystem_degradation"

    exc_type = str(exception_type or (type(exc).__name__ if exc else "RuntimeFault"))
    text = f"{message or str(exc or '')} {operation} {dict(context or {})}".lower()
    invariant_types = {
        "AssertionError",
        "AttributeError",
        "NameError",
        "UnboundLocalError",
        "TypeError",
        "ValueError",
        "KeyError",
        "IndexError",
    }
    if exc_type in invariant_types:
        return "invariant_violation"
    if (
        "cannot import name" in text
        or "required api" in text
        or "undefined variable" in text
        or "has no attribute" in text
        or "contract violation" in text
    ):
        return "invariant_violation"

    # Missing optional state, optional modules, offline network, and local
    # resource/configuration absence are expected fallbacks unless the caller
    # explicitly labeled them as a subsystem or invariant failure.
    expected_types = {
        "FileNotFoundError",
        "ModuleNotFoundError",
        "ConnectionError",
        "TimeoutError",
        "PermissionError",
        "NotImplementedError",
        "OSError",
    }
    if exc_type in expected_types:
        return "warning"
    if "no module named" in text or any(
        token in text
        for token in ("offline", "network unreachable", "missing state")
    ):
        return "warning"
    return "subsystem_degradation"


def _active_state_dir(
    target: Optional[Mapping[str, Any]],
    state_dir: Optional[str] = None,
) -> Path:
    return Path(
        str(
            (target.get("state_dir") if isinstance(target, Mapping) else None)
            or state_dir
            or os.environ.get("AURORA_STATE_DIR")
            or "aurora_state"
        )
    )


def record_runtime_fault(
    systems: Optional[Dict[str, Any]],
    *,
    subsystem: str,
    operation: str,
    exc: Optional[BaseException] = None,
    severity: str = "auto",
    context: Optional[Dict[str, Any]] = None,
    state_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Record a bounded, structured breadcrumb for a runtime boundary."""
    target = systems if isinstance(systems, dict) else {}
    try:
        active_state_dir = _active_state_dir(target, state_dir)
        active_state_dir.mkdir(parents=True, exist_ok=True)
        message = str(exc or "unknown runtime fault").strip()
        trace = (
            "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            if exc
            else ""
        )
        normalized_severity = _severity_from_exception(
            severity,
            exc=exc,
            message=message,
            operation=operation,
            context=context,
        )
        record: Dict[str, Any] = {
            "schema_version": 2,
            "timestamp": time.time(),
            "subsystem": str(subsystem or "unknown")[:100],
            "operation": str(operation or "unknown")[:160],
            "severity": normalized_severity,
            "exception_type": type(exc).__name__ if exc else "RuntimeFault",
            "message": message[:_MAX_MESSAGE],
            "traceback_hash": hashlib.sha256(trace.encode("utf-8", "replace")).hexdigest()[:16],
            "context": dict(context or {}),
        }
        with open(active_state_dir / "runtime_faults.jsonl", "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

        if target:
            faults = list(target.get("_runtime_faults", []) or [])
            faults.append(dict(record))
            target["_runtime_faults"] = faults[-_MAX_MEMORY_FAULTS:]
            target["_last_runtime_fault"] = dict(record)
            if normalized_severity == "invariant_violation":
                target["_runtime_unready"] = True
                target["_runtime_unready_reason"] = (
                    f"invariant violation in {record['operation']}: {record['message']}"
                )
                target["_runtime_status"] = "unready"
                target["_runtime_ready"] = False
            elif normalized_severity == "subsystem_degradation":
                target["_runtime_status"] = "degraded"
                target["_runtime_ready"] = False
        return record
    except Exception:
        # Diagnostics cannot be allowed to break a fail-soft boundary.
        return {}


def _systems_from_scope(scope: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    """Find the active systems dictionary used by an exception boundary."""
    for key in ("systems", "target_systems", "_systems"):
        value = scope.get(key)
        if isinstance(value, dict):
            return value

    owner = scope.get("self")
    for attr in ("systems", "_systems"):
        try:
            value = getattr(owner, attr, None)
        except Exception:
            value = None
        if isinstance(value, dict):
            return value
    return None


def _state_dir_from_scope(scope: Mapping[str, Any]) -> Optional[str]:
    """Resolve a state directory when a boundary has no systems dictionary."""
    for key in ("state_dir", "_state_dir", "storage_dir", "_storage_dir"):
        value = scope.get(key)
        if value:
            return str(value)
    owner = scope.get("self")
    for attr in ("state_dir", "_state_dir", "storage_dir", "_storage_dir"):
        try:
            value = getattr(owner, attr, None)
        except Exception:
            value = None
        if value:
            return str(value)
    return None


def record_exception_from_locals(
    scope: Mapping[str, Any],
    *,
    module: str,
    operation: str,
    exc: BaseException,
    context: Optional[Dict[str, Any]] = None,
    severity: str = "auto",
) -> Dict[str, Any]:
    """Record a swallowed exception using a handler's local scope."""
    try:
        local_context = dict(context or {})
        local_context.setdefault("module", str(module or "unknown"))
        systems = _systems_from_scope(scope)
        return record_runtime_fault(
            systems,
            subsystem=str(module or "unknown"),
            operation=str(operation or "exception_handler"),
            exc=exc,
            severity=str(severity or "auto"),
            context=local_context,
            state_dir=_state_dir_from_scope(scope),
        )
    except Exception:
        return {}


def _read_persisted_faults(target: Mapping[str, Any]) -> list:
    path = _active_state_dir(target) / "runtime_faults.jsonl"
    if not path.exists():
        return []
    records = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if len(records) >= _MAX_PERSISTED_FAULTS:
                    break
                try:
                    payload = json.loads(line)
                except (TypeError, ValueError):
                    continue
                if isinstance(payload, dict):
                    _payload_severity = str(payload.get("severity", "auto") or "auto")
                    # v1 archives used ``degraded`` for every class. Re-run
                    # those records through inference so old early-boot
                    # invariant failures are not permanently softened.
                    if _legacy_degraded_should_be_inferred(payload):
                        _payload_severity = "auto"
                    payload["severity"] = _severity_from_exception(
                        _payload_severity,
                        exception_type=str(payload.get("exception_type", "") or ""),
                        message=str(payload.get("message", "") or ""),
                        operation=str(payload.get("operation", "") or ""),
                        context=payload.get("context") if isinstance(payload.get("context"), Mapping) else {},
                    )
                    records.append(payload)
    except (OSError, UnicodeError):
        return []
    return records


def _fault_key(fault: Mapping[str, Any]) -> tuple:
    return (
        str(fault.get("timestamp", "") or ""),
        str(fault.get("operation", "") or ""),
        str(fault.get("traceback_hash", "") or ""),
    )


def _fault_timestamp(fault: Mapping[str, Any]) -> float:
    try:
        return float(fault.get("timestamp", 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _legacy_degraded_should_be_inferred(fault: Mapping[str, Any]) -> bool:
    """Identify v1 records whose single label hid their real severity."""
    try:
        version = int(fault.get("schema_version", 1) or 1)
    except (TypeError, ValueError):
        version = 1
    return version < 2 and str(fault.get("severity", "") or "").lower() == "degraded"


def fault_summary(systems: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """Merge in-memory and active-state ledgers, deduplicated by event key."""
    target = systems if isinstance(systems, Mapping) else {}
    in_memory = [fault for fault in list(target.get("_runtime_faults", []) or []) if isinstance(fault, Mapping)]
    persisted = _read_persisted_faults(target)

    merged: Dict[tuple, Dict[str, Any]] = {}
    severity_rank = {"info": 0, "warning": 1, "subsystem_degradation": 2, "invariant_violation": 3}
    for raw_fault in persisted + in_memory:
        fault = dict(raw_fault)
        _fault_severity = str(fault.get("severity", "auto") or "auto")
        if _legacy_degraded_should_be_inferred(fault):
            _fault_severity = "auto"
        fault["severity"] = _severity_from_exception(
            _fault_severity,
            exception_type=str(fault.get("exception_type", "") or ""),
            message=str(fault.get("message", "") or ""),
            operation=str(fault.get("operation", "") or ""),
            context=fault.get("context") if isinstance(fault.get("context"), Mapping) else {},
        )
        key = _fault_key(fault)
        previous = merged.get(key)
        if previous is None or severity_rank.get(fault["severity"], 0) > severity_rank.get(previous.get("severity", "info"), 0):
            merged[key] = fault

    faults = sorted(merged.values(), key=_fault_timestamp)
    by_subsystem: Dict[str, int] = {}
    by_severity: Dict[str, int] = {}
    for fault in faults:
        subsystem = str(fault.get("subsystem") or "unknown")
        severity = str(fault.get("severity") or "subsystem_degradation")
        by_subsystem[subsystem] = by_subsystem.get(subsystem, 0) + 1
        by_severity[severity] = by_severity.get(severity, 0) + 1

    invariant_count = by_severity.get("invariant_violation", 0)
    degraded_count = by_severity.get("subsystem_degradation", 0)
    operational_count = invariant_count + degraded_count
    return {
        "count": operational_count,
        "total": len(faults),
        "degraded_count": degraded_count,
        "invariant_count": invariant_count,
        "warning_count": by_severity.get("warning", 0),
        "info_count": by_severity.get("info", 0),
        "last": dict(faults[-1]) if faults else dict(target.get("_last_runtime_fault") or {}),
        "by_subsystem": dict(sorted(by_subsystem.items())),
        "by_severity": dict(sorted(by_severity.items())),
    }


__all__ = [
    "EXPECTED_FALLBACK_SEVERITIES",
    "INVARIANT_SEVERITIES",
    "SUBSYSTEM_DEGRADATION_SEVERITIES",
    "fault_summary",
    "record_exception_from_locals",
    "record_runtime_fault",
]
