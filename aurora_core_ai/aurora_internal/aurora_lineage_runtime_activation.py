"""
Runtime activation for selected lineage materializations.

Loads autowritten activation manifests from aurora_state/ability_lineages and
applies their patch steps to live Aurora systems. This keeps runtime
capabilities tied to genealogy artifacts instead of ad hoc flags.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple

_STATE_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aurora_state")


def _deep_merge(left: Any, right: Any) -> Any:
    if isinstance(left, dict) and isinstance(right, dict):
        merged = dict(left)
        for key, value in right.items():
            merged[key] = _deep_merge(merged.get(key), value) if key in merged else value
        return merged
    if isinstance(left, list) and isinstance(right, list):
        merged = list(left)
        for item in right:
            if item not in merged:
                merged.append(item)
        return merged
    if isinstance(left, bool) and isinstance(right, bool):
        return bool(left or right)
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return max(left, right)
    return right if right not in (None, "", [], {}) else left


def _read_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return dict(json.load(fh) or {})


def _systems_get(systems: Any, key: str) -> Any:
    if isinstance(systems, dict):
        return systems.get(key)
    return getattr(systems, key, None)


def _systems_set(systems: Any, key: str, value: Any) -> None:
    if isinstance(systems, dict):
        systems[key] = value
        return
    setattr(systems, key, value)


def _resolve_target(systems: Any, target: str, working_memory: Any = None) -> Any:
    token = str(target or "").strip()
    if not token or token == "systems":
        return systems
    if token == "working_memory":
        return working_memory if working_memory is not None else _systems_get(systems, "working_memory")
    current = systems
    for part in token.split("."):
        if part in ("", "systems"):
            continue
        if part == "working_memory":
            current = working_memory if working_memory is not None else _systems_get(systems, "working_memory")
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            current = getattr(current, part, None)
        if current is None:
            return None
    return current


def _apply_attrs(target: Any, payload: Dict[str, Any]) -> Dict[str, Any]:
    applied: Dict[str, Any] = {}
    if target is None:
        return applied
    for key, value in payload.items():
        if isinstance(target, dict):
            target[key] = value
        else:
            setattr(target, key, value)
        applied[key] = value
    return applied


def _merge_state_into_target(target: Any, payload: Dict[str, Any]) -> Dict[str, Any]:
    applied: Dict[str, Any] = {}
    if target is None:
        return applied
    if isinstance(target, dict):
        for key, value in payload.items():
            target[key] = _deep_merge(target.get(key), value) if key in target else value
            applied[key] = target[key]
        return applied
    for key, value in payload.items():
        existing = getattr(target, key, None)
        merged = _deep_merge(existing, value) if existing is not None else value
        setattr(target, key, merged)
        applied[key] = merged
    return applied


def load_selected_activation_manifests(storage_dir: str = os.path.join(_STATE_ROOT, "ability_lineages")) -> List[Dict[str, Any]]:
    root = os.path.abspath(storage_dir)
    out: List[Dict[str, Any]] = []
    if not os.path.isdir(root):
        return out
    for target_name in sorted(os.listdir(root)):
        path = os.path.join(root, target_name, "selected_activation.json")
        if not os.path.exists(path):
            continue
        try:
            payload = _read_json(path)
            payload["_manifest_path"] = path
            out.append(payload)
        except Exception:
            continue
    out.sort(key=lambda rec: (str(rec.get("target_ability", "")), float(rec.get("created_at", 0.0) or 0.0)))
    return out


def apply_selected_lineage_runtime_activation(
    systems: Any,
    *,
    working_memory: Any = None,
    storage_dir: str = os.path.join(_STATE_ROOT, "ability_lineages"),
    verbose: bool = False,
) -> Dict[str, Any]:
    manifests = load_selected_activation_manifests(storage_dir=storage_dir)
    report: Dict[str, Any] = {
        "applied_at": float(time.time()),
        "storage_dir": os.path.abspath(storage_dir),
        "loaded_targets": [],
        "applied_steps": [],
        "pending_steps": [],
        "combined_shadow_state": {},
    }
    if not manifests:
        return report

    combined_state: Dict[str, Any] = {}
    for manifest in manifests:
        combined_state = _deep_merge(combined_state, dict(manifest.get("shadow_state", {}) or {}))

    for manifest in manifests:
        target_ability = str(manifest.get("target_ability", "") or "")
        report["loaded_targets"].append(target_ability)
        for step in list(manifest.get("runtime_patch_plan", []) or []):
            target_name = str(step.get("target", "") or "")
            action = str(step.get("action", "") or "")
            payload = dict(step.get("payload", {}) or {})
            step_id = str(step.get("step_id", "") or f"{target_ability}:{target_name}:{action}")
            target_obj = _resolve_target(systems, target_name, working_memory=working_memory)
            if target_obj is None and target_name == "working_memory" and working_memory is None:
                report["pending_steps"].append({"step_id": step_id, "target": target_name, "reason": "working_memory_unavailable"})
                continue
            if target_obj is None:
                report["pending_steps"].append({"step_id": step_id, "target": target_name, "reason": "target_unavailable"})
                continue

            applied_payload: Dict[str, Any] = {}
            if action == "apply_lineage_activation":
                if hasattr(target_obj, "apply_lineage_activation"):
                    try:
                        applied_payload = dict(target_obj.apply_lineage_activation(manifest, payload=payload) or {})
                    except TypeError:
                        applied_payload = dict(target_obj.apply_lineage_activation(manifest) or {})
                else:
                    applied_payload = _merge_state_into_target(target_obj, payload)
            elif action == "set_attrs":
                applied_payload = _apply_attrs(target_obj, payload)
            elif action == "merge_state":
                applied_payload = _merge_state_into_target(target_obj, payload)
            else:
                report["pending_steps"].append({"step_id": step_id, "target": target_name, "reason": f"unknown_action:{action}"})
                continue

            report["applied_steps"].append({
                "step_id": step_id,
                "target": target_name,
                "action": action,
                "applied": applied_payload,
                "target_ability": target_ability,
            })

    _systems_set(systems, "lineage_activation_manifests", manifests)
    _systems_set(systems, "lineage_activation_state", combined_state)
    _systems_set(
        systems,
        "lineage_activation_report",
        {
            "targets": list(report.get("loaded_targets", []) or []),
            "applied_steps": len(list(report.get("applied_steps", []) or [])),
            "pending_steps": len(list(report.get("pending_steps", []) or [])),
            "updated_at": float(report.get("applied_at", 0.0) or 0.0),
        },
    )
    report["combined_shadow_state"] = combined_state
    if verbose and manifests:
        print(
            "[LINEAGE] Runtime activation: "
            f"targets={len(manifests)} applied={len(report['applied_steps'])} "
            f"pending={len(report['pending_steps'])}"
        )
    return report
_STATE_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aurora_state")
