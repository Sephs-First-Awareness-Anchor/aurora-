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
            if key in target and not isinstance(target[key], dict) and getattr(target[key], "__class__", None) not in (None, type(None), int, float, bool, str, list, tuple, set):
                _merge_state_into_target(target[key], value)
                applied[key] = value
            else:
                target[key] = _deep_merge(target.get(key), value) if key in target else value
                applied[key] = target[key]
        return applied
    for key, value in payload.items():
        existing = getattr(target, key, None)
        merged = _deep_merge(existing, value) if existing is not None else value
        setattr(target, key, merged)
        applied[key] = merged
    return applied


def _manifest_trait_records(manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
    shadow_state = dict((manifest or {}).get("shadow_state", {}) or {})
    traits = dict(shadow_state.get("lineage_bound_traits", {}) or {})
    return [dict(value or {}) for value in traits.values() if isinstance(value, dict)]


def _manifest_viability_summary(manifest: Dict[str, Any]) -> Dict[str, Any]:
    trait_records = _manifest_trait_records(manifest)
    viable_traits: List[Dict[str, Any]] = []
    excluded_traits: List[Dict[str, Any]] = []
    max_viability = 0.0
    min_viability = 1.0
    for record in trait_records:
        status = str(record.get("ontological_status", "") or "").strip().lower()
        try:
            viability = float(record.get("viable_band_alignment", 1.0) or 1.0)
        except Exception:
            viability = 1.0
        viability = max(0.0, min(1.0, viability))
        max_viability = max(max_viability, viability)
        min_viability = min(min_viability, viability)
        if status in {"excluded", "unviable", "inactive"} or viability <= 0.0:
            excluded_traits.append(dict(record))
        else:
            viable_traits.append(dict(record))
    if not trait_records:
        min_viability = 1.0
        max_viability = 1.0
    return {
        "trait_count": len(trait_records),
        "viable_traits": viable_traits,
        "excluded_traits": excluded_traits,
        "has_viable_traits": bool(viable_traits) or not trait_records,
        "all_excluded": bool(trait_records) and not bool(viable_traits),
        "max_viability": max_viability,
        "min_viability": min_viability,
    }


def _sanitize_manifest_for_runtime_activation(manifest: Dict[str, Any]) -> Dict[str, Any]:
    sanitized = dict(manifest or {})
    shadow_state = dict(sanitized.get("shadow_state", {}) or {})
    traits = dict(shadow_state.get("lineage_bound_traits", {}) or {})
    kept_traits: Dict[str, Any] = {}
    viability_notes: List[Dict[str, Any]] = []
    for trait_id, trait in traits.items():
        record = dict(trait or {}) if isinstance(trait, dict) else {}
        status = str(record.get("ontological_status", "") or "").strip().lower()
        try:
            viability = float(record.get("viable_band_alignment", 1.0) or 1.0)
        except Exception:
            viability = 1.0
        viability = max(0.0, min(1.0, viability))
        if status in {"excluded", "unviable", "inactive"} or viability <= 0.0:
            viability_notes.append({
                "trait_id": str(trait_id or ""),
                "ontological_status": status,
                "viable_band_alignment": viability,
                "reason": "excluded_by_clause_ii",
            })
            continue
        kept_traits[str(trait_id or "")] = record
    if shadow_state:
        shadow_state["lineage_bound_traits"] = kept_traits
        if viability_notes:
            shadow_state["viability_notes"] = list(viability_notes)
        sanitized["shadow_state"] = shadow_state
    if viability_notes:
        sanitized["viability_notes"] = list(viability_notes)
    return sanitized


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

    sanitized_manifests = [_sanitize_manifest_for_runtime_activation(manifest) for manifest in manifests]

    combined_state: Dict[str, Any] = {}
    for manifest in sanitized_manifests:
        combined_state = _deep_merge(combined_state, dict(manifest.get("shadow_state", {}) or {}))

    for manifest, sanitized_manifest in zip(manifests, sanitized_manifests):
        target_ability = str(manifest.get("target_ability", "") or "")
        viability = _manifest_viability_summary(manifest)
        effective_manifest = sanitized_manifest
        report["loaded_targets"].append(target_ability)
        report.setdefault("manifest_viability", []).append({
            "target_ability": target_ability,
            "trait_count": int(viability.get("trait_count", 0) or 0),
            "viable_trait_count": len(list(viability.get("viable_traits", []) or [])),
            "excluded_trait_count": len(list(viability.get("excluded_traits", []) or [])),
            "max_viability": float(viability.get("max_viability", 0.0) or 0.0),
            "min_viability": float(viability.get("min_viability", 0.0) or 0.0),
        })
        if viability.get("all_excluded", False):
            report["pending_steps"].append({
                "step_id": f"{target_ability}:manifest_viability",
                "target": "systems",
                "reason": "manifest_has_only_excluded_traits",
            })
            continue
        if viability.get("excluded_traits"):
            report["pending_steps"].append({
                "step_id": f"{target_ability}:manifest_viability",
                "target": "systems",
                "reason": "manifest_filtered_by_clause_ii",
                "excluded_traits": list(viability.get("excluded_traits", []) or [])[:6],
            })
        for step in list(effective_manifest.get("runtime_patch_plan", []) or []):
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
                        applied_payload = dict(target_obj.apply_lineage_activation(effective_manifest, payload=payload) or {})
                    except TypeError:
                        applied_payload = dict(target_obj.apply_lineage_activation(effective_manifest) or {})
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

    _systems_set(systems, "lineage_activation_manifests", sanitized_manifests)
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
