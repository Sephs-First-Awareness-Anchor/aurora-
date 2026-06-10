#!/usr/bin/env python3
"""
Lineage-bound trait materialization for newly added runtime code.

New code should not appear as an untraced helper. This module lets new traits
declare:
  - staged recapitulation from the 5 constraints
  - bound operations / methods that express those stages
  - system ripple writebacks that are applied through the same lineage
    artifact layout Aurora already uses

It is intentionally lighter than the full ability lineage compiler, but it
reuses the same core stage/writeback schema and writes selected lineage
artifacts into aurora_state/ability_lineages so runtime activation remains
grounded in genealogy artifacts.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Sequence, Tuple

_STATE_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aurora_state")

from aurora_internal.aurora_ability_lineage_compiler import (
    CompiledLineagePath,
    LineageStage,
    SystemWriteback,
)


def _slug(token: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in str(token or "").strip().lower()).strip("_")


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


@dataclass(frozen=True)
class OperationBinding:
    module: str
    qualname: str
    stage_ids: Tuple[str, ...]
    dominant_axis: str
    purpose_lane: str
    ripple_domains: Tuple[str, ...] = tuple()
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "module": self.module,
            "qualname": self.qualname,
            "stage_ids": list(self.stage_ids),
            "dominant_axis": self.dominant_axis,
            "purpose_lane": self.purpose_lane,
            "ripple_domains": list(self.ripple_domains),
            "notes": self.notes,
        }


@dataclass(frozen=True)
class LineageTraitSpec:
    trait_id: str
    label: str
    rationale: str
    selected_strategy: str
    stages: Tuple[LineageStage, ...]
    bindings: Tuple[OperationBinding, ...] = tuple()
    runtime_patch_targets: Tuple[Dict[str, Any], ...] = tuple()

    def to_path(self) -> CompiledLineagePath:
        return CompiledLineagePath(
            path_id=f"lin_{_slug(self.trait_id)}_{_slug(self.selected_strategy)}",
            target_ability=self.trait_id,
            selected_strategy=self.selected_strategy,
            rationale=self.rationale,
            stages=list(self.stages),
        )


def lineage_bound_operation(
    trait_id: str,
    *,
    dominant_axis: str,
    purpose_lane: str,
    stage_ids: Sequence[str],
    ripple_domains: Sequence[str] = (),
    notes: str = "",
):
    def decorator(fn):
        setattr(
            fn,
            "__aurora_lineage_binding__",
            {
                "trait_id": str(trait_id or "").strip(),
                "dominant_axis": str(dominant_axis or "X").upper(),
                "purpose_lane": str(purpose_lane or "meaning").strip(),
                "stage_ids": [str(item or "").strip() for item in stage_ids if str(item or "").strip()],
                "ripple_domains": [str(item or "").strip() for item in ripple_domains if str(item or "").strip()],
                "notes": str(notes or "").strip(),
            },
        )
        return fn

    return decorator


class LineageBoundTraitRegistry:
    def __init__(self, storage_dir: str = os.path.join(_STATE_ROOT, "ability_lineages")) -> None:
        self.storage_dir = storage_dir
        self._materialized: Dict[str, Dict[str, str]] = {}

    def _initial_shadow_state(self) -> Dict[str, Any]:
        return {
            "memory": {},
            "working_memory": {},
            "pipeline": {},
            "expression": {},
            "rubric": {},
            "genealogy": {},
            "lineage_bound_traits": {},
        }

    def _apply_writeback(self, shadow_state: Dict[str, Any], writeback: SystemWriteback) -> None:
        bucket = shadow_state.setdefault(writeback.subsystem, {})
        current = bucket.get(writeback.key)
        if writeback.mode == "increment":
            bucket[writeback.key] = int(current or 0) + int(writeback.value)
        elif writeback.mode == "set":
            bucket[writeback.key] = writeback.value
        elif writeback.mode == "max":
            bucket[writeback.key] = max(float(current or 0.0), float(writeback.value))
        elif writeback.mode == "append_unique":
            values = list(current or [])
            if writeback.value not in values:
                values.append(writeback.value)
            bucket[writeback.key] = values
        else:
            raise ValueError(f"unsupported writeback mode: {writeback.mode}")

    def materialize(self, spec: LineageTraitSpec) -> Dict[str, str]:
        cached = self._materialized.get(spec.trait_id)
        if cached:
            return cached

        os.makedirs(self.storage_dir, exist_ok=True)
        target_dir = os.path.join(self.storage_dir, spec.trait_id)
        runs_dir = os.path.join(target_dir, "runs")
        os.makedirs(runs_dir, exist_ok=True)

        path = spec.to_path()
        shadow_state = self._initial_shadow_state()
        stage_outputs: List[Dict[str, Any]] = []
        for stage in spec.stages:
            output_id = f"LT:{_slug(spec.trait_id)}:{stage.stage_id}"
            for writeback in stage.system_writebacks:
                self._apply_writeback(shadow_state, writeback)
            stage_outputs.append(
                {
                    "stage_id": stage.stage_id,
                    "generation": int(stage.generation),
                    "output_id": output_id,
                    "output_kind": stage.kind,
                    "dominant_axis": stage.dominant_axis,
                    "constraints": list(stage.constraints),
                    "purpose_lane": stage.purpose_lane,
                    "summary": stage.summary,
                    "ripple_effects": list(stage.ripple_effects),
                }
            )

        shadow_state["lineage_bound_traits"][spec.trait_id] = {
            "label": spec.label,
            "selected_strategy": spec.selected_strategy,
            "rationale": spec.rationale,
            "bindings": [binding.to_dict() for binding in spec.bindings],
            "stage_ids": [stage.stage_id for stage in spec.stages],
            "final_stage_id": spec.stages[-1].stage_id if spec.stages else "",
        }

        runtime_patch_plan = [
            {
                "step_id": f"{spec.trait_id}.systems.merge_state",
                "target": "systems",
                "action": "merge_state",
                "payload": shadow_state,
            }
        ]
        for idx, patch in enumerate(spec.runtime_patch_targets):
            target = str(dict(patch).get("target", "systems") or "systems")
            action = str(dict(patch).get("action", "merge_state") or "merge_state")
            payload = dict(dict(patch).get("payload", {}) or {})
            runtime_patch_plan.append(
                {
                    "step_id": str(dict(patch).get("step_id", f"{spec.trait_id}.patch.{idx}")),
                    "target": target,
                    "action": action,
                    "payload": payload,
                }
            )

        activation_manifest = {
            "manifest_version": 1,
            "created_at": float(time.time()),
            "target_ability": spec.trait_id,
            "path_id": path.path_id,
            "final_output_id": stage_outputs[-1]["output_id"] if stage_outputs else "",
            "final_output_kind": stage_outputs[-1]["output_kind"] if stage_outputs else "",
            "shadow_state": shadow_state,
            "stage_outputs": stage_outputs,
            "runtime_contract": {
                "trait_label": spec.label,
                "bindings": [binding.to_dict() for binding in spec.bindings],
            },
            "runtime_patch_plan": runtime_patch_plan,
        }

        selected_path = os.path.join(target_dir, "selected_path.json")
        selected_activation = os.path.join(target_dir, "selected_activation.json")
        selected_markdown = os.path.join(target_dir, "selected_activation.md")
        version_path = os.path.join(runs_dir, f"{_slug(path.path_id)}_selected_path.json")
        version_activation = os.path.join(runs_dir, f"{_slug(path.path_id)}_selected_activation.json")

        path_payload = path.to_dict()
        path_payload["bindings"] = [binding.to_dict() for binding in spec.bindings]

        for out_path, payload in (
            (selected_path, path_payload),
            (selected_activation, activation_manifest),
            (version_path, path_payload),
            (version_activation, activation_manifest),
        ):
            with open(out_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)

        md_lines = [
            f"# Lineage-Bound Trait: {spec.label}",
            "",
            f"- `trait_id`: `{spec.trait_id}`",
            f"- `path_id`: `{path.path_id}`",
            f"- `strategy`: `{spec.selected_strategy}`",
            "",
            "## Bound Operations",
            "",
        ]
        for binding in spec.bindings:
            md_lines.append(
                f"- `{binding.module}.{binding.qualname}` -> `{binding.dominant_axis}` / `{binding.purpose_lane}` / `{', '.join(binding.stage_ids)}`"
            )
        md_lines.append("")
        with open(selected_markdown, "w", encoding="utf-8") as handle:
            handle.write("\n".join(md_lines))

        result = {
            "selected_path": selected_path,
            "selected_activation": selected_activation,
            "selected_markdown": selected_markdown,
        }
        self._materialized[spec.trait_id] = result
        return result


_REGISTRY: LineageBoundTraitRegistry | None = None


def get_lineage_bound_trait_registry(
    storage_dir: str = os.path.join(_STATE_ROOT, "ability_lineages"),
) -> LineageBoundTraitRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = LineageBoundTraitRegistry(storage_dir=storage_dir)
    return _REGISTRY


def ensure_lineage_trait_materialized(spec: LineageTraitSpec) -> Dict[str, str]:
    return get_lineage_bound_trait_registry().materialize(spec)
_STATE_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aurora_state")
