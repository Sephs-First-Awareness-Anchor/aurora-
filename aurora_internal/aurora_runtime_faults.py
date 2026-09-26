#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Operational fault ledger whose live faults also become Aurora experience.

The ledger remains fail-soft and useful to engineering, but a fault that occurs
while Aurora has a live cognitive runtime is no longer telemetry-only.  The raw
occurrence is offered to SediMemory without prescribing what Aurora should
conclude from it.
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


def _severity_from_exception(severity: Any, *, exc: Optional[BaseException] = None,
                             exception_type: str = "", message: str = "",
                             operation: str = "", context: Optional[Mapping[str, Any]] = None) -> str:
    raw = str(severity or "auto").strip().lower().replace("-", "_")
    if raw in {"informational", "expected_fallback"}: return "warning"
    if raw == "info": return "info"
    if raw == "warning": return "warning"
    if raw in INVARIANT_SEVERITIES: return "invariant_violation"
    if raw in SUBSYSTEM_DEGRADATION_SEVERITIES: return "subsystem_degradation"
    exc_type = str(exception_type or (type(exc).__name__ if exc else "RuntimeFault"))
    text = f"{message or str(exc or '')} {operation} {dict(context or {})}".lower()
    if exc_type in {"AssertionError", "AttributeError", "NameError", "UnboundLocalError", "TypeError", "ValueError", "KeyError", "IndexError"}:
        return "invariant_violation"
    if ("cannot import name" in text or "required api" in text or "undefined variable" in text
            or "has no attribute" in text or "contract violation" in text):
        return "invariant_violation"
    if exc_type in {"FileNotFoundError", "ModuleNotFoundError", "ConnectionError", "TimeoutError",
                    "PermissionError", "NotImplementedError", "OSError"}:
        return "warning"
    if "no module named" in text or any(token in text for token in ("offline", "network unreachable", "missing state")):
        return "warning"
    return "subsystem_degradation"


def _active_boot_state_dir_fallback() -> Optional[str]:
    try:
        from aurora_internal.aurora_state_context import get_active_state_dir
        return get_active_state_dir()
    except Exception:
        return None


def _active_state_dir(target: Optional[Mapping[str, Any]], state_dir: Optional[str] = None) -> Path:
    return Path(str((target.get("state_dir") if isinstance(target, Mapping) else None)
                    or state_dir or os.environ.get("AURORA_STATE_DIR")
                    or _active_boot_state_dir_fallback() or "aurora_state"))


def _offer_fault_as_lived_consequence(target: Dict[str, Any], record: Mapping[str, Any]) -> bool:
    """Offer the raw internal occurrence to Aurora's ordinary memory substrate.

    This deliberately does not label a lesson, prescribe a response, create a
    special error concept, or invoke a fallback intelligence.  It exposes only
    what occurred.  A recursion guard is essential because SediMemory itself
    contains fail-soft boundaries that use this fault recorder.
    """
    if not target or target.get("_runtime_fault_experience_guard"):
        return False
    sedimemory = target.get("sedimemory")
    if sedimemory is None or not hasattr(sedimemory, "ingest_event"):
        return False
    target["_runtime_fault_experience_guard"] = True
    try:
        from aurora_internal.aurora_constraint_manifold_patched import ConstraintVector
        from foundational_contract import ExistenceMode
        context = dict(record.get("context") or {})
        content = {
            "source": "internal_runtime",
            "occurrence_type": "runtime_fault",
            "subsystem": record.get("subsystem"),
            "operation": record.get("operation"),
            "severity": record.get("severity"),
            "exception_type": record.get("exception_type"),
            "message": record.get("message"),
            "traceback_hash": record.get("traceback_hash"),
            "context": context,
            "occurred_at": record.get("timestamp"),
            "runtime_continued": True,
        }
        # Neutral coordinate: expose the whole occurrence and let SediMemory's
        # strain filters determine what resonates.  Do not encode a lesson in
        # hand-authored axis weights.
        cv = ConstraintVector(X=0.5, T=0.5, N=0.5, B=0.5, A=0.5)
        sedimemory.ingest_event(
            content=content,
            constraint_vector=cv,
            source="internal_runtime",
            existence_mode=ExistenceMode.AGENTIC,
        )
        target["_last_lived_runtime_fault"] = dict(record)
        return True
    except Exception:
        # Never recurse through record_runtime_fault while translating a fault
        # into experience.  The original fault remains in the operational log.
        return False
    finally:
        target.pop("_runtime_fault_experience_guard", None)


def record_runtime_fault(systems: Optional[Dict[str, Any]], *, subsystem: str, operation: str,
                         exc: Optional[BaseException] = None, severity: str = "auto",
                         context: Optional[Dict[str, Any]] = None,
                         state_dir: Optional[str] = None) -> Dict[str, Any]:
    target = systems if isinstance(systems, dict) else {}
    try:
        active_state_dir = _active_state_dir(target, state_dir)
        active_state_dir.mkdir(parents=True, exist_ok=True)
        message = str(exc or "unknown runtime fault").strip()
        trace = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)) if exc else ""
        normalized_severity = _severity_from_exception(severity, exc=exc, message=message,
                                                       operation=operation, context=context)
        record: Dict[str, Any] = {
            "schema_version": 2, "timestamp": time.time(),
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
                target["_runtime_unready_reason"] = f"invariant violation in {record['operation']}: {record['message']}"
                target["_runtime_status"] = "unready"
                target["_runtime_ready"] = False
            elif normalized_severity == "subsystem_degradation":
                target["_runtime_status"] = "degraded"
                target["_runtime_ready"] = False
            _offer_fault_as_lived_consequence(target, record)
        return record
    except Exception:
        return {}


def _project_fault_to_developmental_stream(record: Dict[str, Any], state_dir: Path) -> None:
    """Best-effort, non-recursive projection of a real operational fault
    into Aurora's native developmental timeline (developmental_timeline.jsonl
    -- the same file aurora_developmental_log.py writes to and EEPR reads
    real experiential pressure from). Tagged "runtime_fault_consequence",
    distinct from that module's own "developmental_event"/"metric_snapshot"
    kinds, so existing readers of those kinds are unaffected -- this is
    additive, not a reinterpretation of an existing entry shape.

    Carries: failure signature (subsystem/operation/exception_type/
    traceback_hash -- the same real fields record_runtime_fault already
    computed, never fabricated), occurrence identity (timestamp), and a
    recovery_outcome that starts "unresolved" -- this module has no
    mechanism yet to detect actual recovery, so it says so honestly rather
    than fabricating a resolution. Historical faults read back from this
    file are never replayed as new experience -- nothing in this codebase
    reads developmental_timeline.jsonl back into live processing at boot
    (confirmed: aurora_developmental_log.py only ever appends to it)."""
    try:
        path = state_dir / "developmental_timeline.jsonl"
        entry = {
            "ts": round(time.time(), 3),
            "kind": "runtime_fault_consequence",
            "failure_signature": record.get("traceback_hash", ""),
            "subsystem": record.get("subsystem", ""),
            "operation": record.get("operation", ""),
            "severity": record.get("severity", ""),
            "expected_vs_observed": record.get("message", ""),
            "recovery_outcome": "unresolved",
        }
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
    except Exception:
        # Never allow this projection itself to become a new fault --
        # that would be exactly the recursive fault generation the
        # directive requires avoiding.
        pass


def _systems_from_scope(scope: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    for key in ("systems", "target_systems", "_systems"):
        value = scope.get(key)
        if isinstance(value, dict): return value
    owner = scope.get("self")
    for attr in ("systems", "_systems"):
        try: value = getattr(owner, attr, None)
        except Exception: value = None
        if isinstance(value, dict): return value
    return None


def _state_dir_from_scope(scope: Mapping[str, Any]) -> Optional[str]:
    for key in ("state_dir", "_state_dir", "storage_dir", "_storage_dir"):
        value = scope.get(key)
        if value: return str(value)
    owner = scope.get("self")
    for attr in ("state_dir", "_state_dir", "storage_dir", "_storage_dir"):
        try: value = getattr(owner, attr, None)
        except Exception: value = None
        if value: return str(value)
    return None


def record_exception_from_locals(scope: Mapping[str, Any], *, module: str, operation: str,
                                 exc: BaseException, context: Optional[Dict[str, Any]] = None,
                                 severity: str = "auto") -> Dict[str, Any]:
    try:
        local_context = dict(context or {})
        local_context.setdefault("module", str(module or "unknown"))
        systems = _systems_from_scope(scope)
        return record_runtime_fault(systems, subsystem=str(module or "unknown"),
                                    operation=str(operation or "exception_handler"), exc=exc,
                                    severity=str(severity or "auto"), context=local_context,
                                    state_dir=_state_dir_from_scope(scope))
    except Exception:
        return {}


def _read_persisted_faults(target: Mapping[str, Any]) -> list:
    path = _active_state_dir(target) / "runtime_faults.jsonl"
    if not path.exists(): return []
    records = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if len(records) >= _MAX_PERSISTED_FAULTS: break
                try: payload = json.loads(line)
                except (TypeError, ValueError): continue
                if isinstance(payload, dict):
                    sev = str(payload.get("severity", "auto") or "auto")
                    if _legacy_degraded_should_be_inferred(payload): sev = "auto"
                    payload["severity"] = _severity_from_exception(
                        sev, exception_type=str(payload.get("exception_type", "") or ""),
                        message=str(payload.get("message", "") or ""),
                        operation=str(payload.get("operation", "") or ""),
                        context=payload.get("context") if isinstance(payload.get("context"), Mapping) else {})
                    records.append(payload)
    except (OSError, UnicodeError): return []
    return records


def _fault_key(fault: Mapping[str, Any]) -> tuple:
    return (str(fault.get("timestamp", "") or ""), str(fault.get("operation", "") or ""),
            str(fault.get("traceback_hash", "") or ""))


def _fault_timestamp(fault: Mapping[str, Any]) -> float:
    try: return float(fault.get("timestamp", 0.0) or 0.0)
    except (TypeError, ValueError): return 0.0


def _legacy_degraded_should_be_inferred(fault: Mapping[str, Any]) -> bool:
    try: version = int(fault.get("schema_version", 1) or 1)
    except (TypeError, ValueError): version = 1
    return version < 2 and str(fault.get("severity", "") or "").lower() == "degraded"


def fault_summary(systems: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    target = systems if isinstance(systems, Mapping) else {}
    in_memory = [f for f in list(target.get("_runtime_faults", []) or []) if isinstance(f, Mapping)]
    persisted = _read_persisted_faults(target)
    merged: Dict[tuple, Dict[str, Any]] = {}
    severity_rank = {"info": 0, "warning": 1, "subsystem_degradation": 2, "invariant_violation": 3}
    for raw_fault in persisted + in_memory:
        fault = dict(raw_fault)
        sev = str(fault.get("severity", "auto") or "auto")
        if _legacy_degraded_should_be_inferred(fault): sev = "auto"
        fault["severity"] = _severity_from_exception(
            sev, exception_type=str(fault.get("exception_type", "") or ""),
            message=str(fault.get("message", "") or ""), operation=str(fault.get("operation", "") or ""),
            context=fault.get("context") if isinstance(fault.get("context"), Mapping) else {})
        key = _fault_key(fault)
        previous = merged.get(key)
        if previous is None or severity_rank.get(fault["severity"], 0) > severity_rank.get(previous.get("severity", "info"), 0):
            merged[key] = fault
    faults = sorted(merged.values(), key=_fault_timestamp)
    by_subsystem: Dict[str, int] = {}; by_severity: Dict[str, int] = {}
    for fault in faults:
        subsystem = str(fault.get("subsystem") or "unknown"); sev = str(fault.get("severity") or "subsystem_degradation")
        by_subsystem[subsystem] = by_subsystem.get(subsystem, 0) + 1
        by_severity[sev] = by_severity.get(sev, 0) + 1
    invariant_count = by_severity.get("invariant_violation", 0)
    degraded_count = by_severity.get("subsystem_degradation", 0)
    return {"count": invariant_count + degraded_count, "total": len(faults),
            "degraded_count": degraded_count, "invariant_count": invariant_count,
            "warning_count": by_severity.get("warning", 0), "info_count": by_severity.get("info", 0),
            "last": dict(faults[-1]) if faults else dict(target.get("_last_runtime_fault") or {}),
            "by_subsystem": dict(sorted(by_subsystem.items())), "by_severity": dict(sorted(by_severity.items()))}


__all__ = ["EXPECTED_FALLBACK_SEVERITIES", "INVARIANT_SEVERITIES", "SUBSYSTEM_DEGRADATION_SEVERITIES",
           "fault_summary", "record_exception_from_locals", "record_runtime_fault"]
