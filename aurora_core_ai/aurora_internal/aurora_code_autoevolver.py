#!/usr/bin/env python3
"""
AURORA CODE AUTO-EVOLVER
========================
Applies constrained code mutations, runs simulation-gated selection,
and rolls back rejected mutations.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import importlib
import inspect
import json
import os
import pprint
import re
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

_NONEXISTENT_BACKUP = "__AURORA_NONEXISTENT__"
_GENERATED_SURFACES_REL = "aurora_internal/aurora_evolved_surfaces.py"
_DESCRIPTOR_STATE_REL = "aurora_state/operation_descriptors.json"
_GENEALOGY_OUTPUT_DIR = "aurora_runtime_output"
_REFLECTION_LIMIT = 160
_FUNCTION_OVERRIDE_LIMIT = 128
_CLASS_REFLECTION_LIMIT = 32
_NATIVE_BLOCK_BEGIN = "# AURORA_EVOLVED_NATIVE_BEGIN"
_NATIVE_BLOCK_END = "# AURORA_EVOLVED_NATIVE_END"
_CONSTRAINT_TO_AXIS = {
    "existence": "X",
    "temporal": "T",
    "energy": "N",
    "boundary": "B",
    "agency": "A",
}

_ROUTING_TYPE_TO_REWRITE_BIAS: Dict[str, str] = {
    "reasoning_gap":     "governance_routing",
    "stability_gap":     "lineage_memory",
    "articulation_gap":  "perceptual_synthesis",
    "knowledge_gap":     "lineage_memory",
    "tool_gap":          "dimensional_balancing",
    "boundary_gap":      "dimensional_balancing",
}

_TIMING_AXIS_HINTS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("agency", ("aurora_runtime.py", "aurora_governance_persistence_gateway.py", "constraint_genealogy.py")),
    ("temporal", ("aurora_internal/aurora_evolved_surfaces.py", "aurora_dimensional_systems.py")),
    ("boundary", ("aurora_expression_perception.py", "aurora_governance_persistence_gateway.py")),
)


class CodeAutoEvolver:
    def __init__(self, repo_root: str):
        self.repo_root = os.path.abspath(repo_root)
        self._genealogy_artifact_cache: Dict[str, Any] = {}
        self._alignment_cache: Dict[str, Any] = {}
        self._genealogy_strategy_cache: Dict[str, Any] = {}
        self._rewrite_feedback_cache: Dict[str, Any] = {}
        self._contract_profile_cache: Dict[str, Any] = {}

    def _file_stamp(self, path: str) -> Tuple[int, int]:
        try:
            st = os.stat(path)
            return int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1_000_000_000))), int(st.st_size)
        except Exception:
            return 0, 0

    def _descriptor_cache_stamp(self, operations: Optional[List[Dict[str, Any]]] = None) -> Tuple[int, int, int]:
        path = self._abs_path(_DESCRIPTOR_STATE_REL)
        mtime_ns, size = self._file_stamp(path)
        return mtime_ns, size, int(len(operations or []))

    def apply_operator(self, operator_key: str, target_files: Iterable[str]) -> Dict[str, Any]:
        key = str(operator_key or "").strip().lower()
        started_at = time.time()
        plan = self._build_update_plan(key, target_files)
        updates = dict(plan.get("updates", {}) or {})
        detail_rows = list(plan.get("details", []) or [])

        backups: Dict[str, str] = {}
        changed: List[str] = []
        details: List[Dict[str, Any]] = []
        file_timings: List[Dict[str, Any]] = []

        for path, updated in updates.items():
            existed = os.path.exists(path)
            original = ""
            if existed:
                try:
                    with open(path, "r", encoding="utf-8") as fh:
                        original = fh.read()
                except Exception:
                    continue
            if updated == original:
                continue
            backups[path] = original if existed else _NONEXISTENT_BACKUP
            folder = os.path.dirname(path)
            if folder:
                os.makedirs(folder, exist_ok=True)
            write_started = time.time()
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(updated)
            write_duration = float(time.time() - write_started)
            changed.append(path)
            file_timings.append({
                "file": path,
                "bytes_before": int(len(original.encode("utf-8")) if isinstance(original, str) else 0),
                "bytes_after": int(len(updated.encode("utf-8")) if isinstance(updated, str) else 0),
                "write_duration_s": round(write_duration, 6),
                "timing_axes": self._timing_axes_for_path(path),
                "timing_role": self._timing_role_for_path(path),
            })

        if changed:
            changed_set = set(changed)
            for row in detail_rows:
                file_path = str(row.get("file", "") or "")
                if file_path in changed_set:
                    details.append(dict(row))
            if not details:
                details = [{"file": path, "change": "updated by autoevolver"} for path in changed]

        return {
            "operator_key": key,
            "changed_files": changed,
            "change_count": len(changed),
            "duration_s": float(time.time() - started_at),
            "file_timings": file_timings,
            "backups": backups,
            "details": details,
            "manifest": dict(plan.get("manifest", {}) or {}),
        }

    def _timing_axes_for_path(self, path: str) -> List[str]:
        norm = str(path or "").replace("\\", "/")
        axes: List[str] = []
        for axis, hints in _TIMING_AXIS_HINTS:
            if any(hint in norm for hint in hints):
                axes.append(axis)
        return axes

    def _timing_role_for_path(self, path: str) -> str:
        norm = str(path or "").replace("\\", "/")
        if norm.endswith("/aurora_state/operation_descriptors.json") or "/aurora_state/" in norm:
            return "descriptor_state"
        if norm.endswith("/aurora_internal/aurora_evolved_surfaces.py"):
            return "generated_surface"
        if any(
            marker in norm for marker in (
                "/aurora_expression_perception.py",
                "/aurora_dimensional_systems.py",
                "/aurora_governance_persistence_gateway.py",
                "/aurora_runtime.py",
                "/aurora_internal/constraint_genealogy.py",
            )
        ):
            return "strategic_source"
        if "/aurora_internal/" in norm or norm.endswith(".py"):
            return "native_source"
        return "other"

    def rollback(self, backups: Dict[str, str]) -> None:
        for path, content in (backups or {}).items():
            try:
                if content == _NONEXISTENT_BACKUP:
                    if os.path.exists(path):
                        os.remove(path)
                    continue
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(content)
            except Exception:
                continue

    def _build_update_plan(self, operator_key: str, target_files: Iterable[str]) -> Dict[str, Any]:
        key = str(operator_key or "").strip().lower()
        files = self._target_paths(key, target_files)
        updates: Dict[str, str] = {}
        details: List[Dict[str, Any]] = []
        manifest: Dict[str, Any] = {}

        if key in {"latent_promotion", "architectural_reflection"}:
            target = files[0] if files else self._abs_path(_GENERATED_SURFACES_REL)
            plan = self._build_developmental_surface_updates(target)
            return {
                "updates": dict(plan.get("updates", {}) or {}),
                "details": list(plan.get("details", []) or []),
                "manifest": dict(plan.get("manifest", {}) or {}),
            }
        if key == "native_surface_projection":
            plan = self._build_native_projection_updates()
            return {
                "updates": dict(plan.get("updates", {}) or {}),
                "details": list(plan.get("details", []) or []),
                "manifest": dict(plan.get("manifest", {}) or {}),
            }

        for path in files:
            original = ""
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as fh:
                        original = fh.read()
                except Exception:
                    continue
            updated = original
            change_note = ""

            if key == "telemetry_probe":
                updated, change_note = self._apply_telemetry_probe(path, original)
            elif key == "agency_surface":
                updated, change_note = self._apply_agency_surface(path, original)

            if updated != original:
                updates[path] = updated
                details.append({"file": path, "change": change_note or "updated by autoevolver"})

        return {"updates": updates, "details": details, "manifest": manifest}

    def _target_paths(self, operator_key: str, target_files: Iterable[str]) -> List[str]:
        key = str(operator_key or "").strip().lower()
        raw_files = [self._abs_path(p) for p in (target_files or [])]
        raw_files = [p for p in raw_files if p]
        if key in {"latent_promotion", "architectural_reflection"}:
            if not raw_files:
                raw_files = [self._abs_path(_GENERATED_SURFACES_REL)]
            return sorted(set(raw_files))
        return sorted(set(p for p in raw_files if os.path.isfile(p)))

    def _abs_path(self, raw: str) -> str:
        p = str(raw or "").strip()
        if not p:
            return ""
        if os.path.isabs(p):
            return os.path.abspath(p)
        return os.path.abspath(os.path.join(self.repo_root, p))

    def _clean_rel_path(self, raw: str) -> str:
        txt = str(raw or "").replace("\\", "/").strip()
        txt = txt.replace(" .py", ".py")
        return txt

    def _module_name_from_relpath(self, raw: str) -> str:
        rel = self._clean_rel_path(raw)
        if rel.endswith(".py"):
            rel = rel[:-3]
        parts = [seg.strip() for seg in rel.split("/") if seg.strip()]
        return ".".join(parts)

    def _load_descriptor_state(self) -> Optional[Dict[str, Any]]:
        path = self._abs_path(_DESCRIPTOR_STATE_REL)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, dict) else None
        except Exception:
            return None

    def _operation_chain(self, op_id: str, module_name: str) -> List[str]:
        oid = str(op_id or "").strip()
        module = str(module_name or "").strip()
        if oid.startswith("latent."):
            oid = oid[7:]
        if module and oid.startswith(module + "."):
            oid = oid[len(module) + 1:]
        parts = [seg for seg in oid.split(".") if seg]
        if module:
            mod_parts = [seg for seg in module.split(".") if seg]
            if parts[: len(mod_parts)] == mod_parts:
                parts = parts[len(mod_parts):]
        return parts

    def _sanitize_identifier(self, raw: str, prefix: str = "surface") -> str:
        txt = re.sub(r"[^0-9a-zA-Z_]+", "_", str(raw or "").strip().lower())
        txt = re.sub(r"_+", "_", txt).strip("_")
        if not txt:
            txt = prefix
        if txt[0].isdigit():
            txt = f"{prefix}_{txt}"
        return txt

    def _surface_method_name(self, op_id: str, kind: str) -> str:
        base = str(op_id or "")
        # Strip any accumulated prefixes so repeated mutations never stack names
        for _pfx in ("reflect_evolved_", "latent_surface_", "reflect_surface_",
                     "evolved_surface_", "reflect_", "latent_"):
            if base.startswith(_pfx):
                base = base[len(_pfx):]
                break
        if kind == "latent":
            base = base.replace("latent.", "latent_")
            return self._sanitize_identifier(base, prefix="latent_surface")
        return self._sanitize_identifier(f"reflect_{base}", prefix="reflect_surface")

    def _surface_score(self, row: Dict[str, Any]) -> float:
        hist = dict(row.get("developmental_effect_history", {}) or {})
        summary = dict(hist.get("developmental_summary", {}) or {})
        ripple = dict(hist.get("ripple_effects", {}) or {})
        score = float(summary.get("system_impact_score", 0.0) or 0.0)
        score += float(summary.get("reflection_strength", 0.0) or 0.0) * 0.25
        score += float(row.get("latent_weight", 0.0) or 0.0) * 0.35
        score += min(0.25, float(ripple.get("cross_diversity_links", 0) or 0) * 0.01)
        score += min(0.15, float(ripple.get("derived_from_origin_descendants", 0) or 0) * 0.001)
        return score

    def _empty_slot_channels(self) -> "frozenset[str]":
        """
        Return the set of NC channels that appear in at least one unoccupied
        slot of the 625 pressure map.  Used to bias candidate selection toward
        operations that would fill empty evolutionary territory.
        Falls back to an empty frozenset if the pressure map is unavailable.
        """
        try:
            import sys as _sys
            if self.repo_root not in _sys.path:
                _sys.path.insert(0, self.repo_root)
            from aurora_625_pressure_map import build_from_descriptors  # type: ignore
            descriptors_path = self._abs_path(_DESCRIPTOR_STATE_REL)
            state_dir = self._abs_path("aurora_state")
            pmap = build_from_descriptors(
                descriptors_path=descriptors_path,
                state_dir=state_dir,
                save=False,
            )
            channels: set = set()
            for slot, profile in pmap.profiles.items():
                if not profile.is_occupied:
                    row_ch, col_ch = slot.split("\u00d7")
                    channels.add(row_ch)
                    channels.add(col_ch)
            # also include compound virtual channels from axis emergence
            try:
                from aurora_internal.aurora_axis_emergence import empty_virtual_channels  # type: ignore
                channels.update(empty_virtual_channels(self.repo_root))
            except Exception:
                pass
            return frozenset(channels)
        except Exception:
            return frozenset()

    def _empty_slot_pressure(self, row: Dict[str, Any], empty_channels: "frozenset[str]") -> float:
        """
        Score bonus for operations whose active axis signature projects into
        NC channels that appear in empty pressure slots.

        An operation touching axes X and T naturally activates NC channels
        NC:X>X, NC:X>T, NC:T>X, NC:T>T.  If any of those appear in the
        empty-slot channel set, the operation is a candidate for filling
        unexplored evolutionary territory and gets a boost (capped at 0.30).
        """
        if not empty_channels:
            return 0.0
        counts = self._operation_axis_counts(row)
        active = [ax for ax, n in counts.items() if n > 0]
        if not active:
            return 0.0
        op_channels: set = set()
        for src in active:
            for dst in active:
                op_channels.add(f"NC:{src}>{dst}")
        overlap = len(op_channels & empty_channels)
        return min(0.30, overlap * 0.06)

    def _fallback_effect_modes(self, row: Dict[str, Any], target_kind: str) -> List[str]:
        constraints = [str(x).strip().lower() for x in (row.get("constraints", []) or []) if str(x).strip()]
        kind = str(target_kind or row.get("kind", "") or "operation").strip().lower()
        modes: List[str] = []
        if "existence" in constraints:
            modes.append("state_schema_change")
        if "temporal" in constraints:
            modes.append("temporal_orchestration_change")
        if "energy" in constraints:
            modes.append("cost_pressure_change")
        if "boundary" in constraints:
            modes.append("interface_boundary_change")
        if "agency" in constraints:
            modes.append("adaptive_steering_change")
        if kind == "class":
            modes.append("class_lineage_surface")
        elif kind == "latent":
            modes.append("latent_route_surface")
        else:
            modes.append("lineage_surface")
        return list(dict.fromkeys(modes))

    def _ensure_developmental_effect_history(
        self,
        row: Dict[str, Any],
        module_name: str,
        lineage_kind: str,
    ) -> Dict[str, Any]:
        hist = dict(row.get("developmental_effect_history", {}) or {})
        op_id = str(row.get("op_id", "") or "")
        chain = self._operation_chain(op_id, module_name)
        target_kind = str(
            row.get("target_kind", "") or row.get("kind", "") or lineage_kind or "operation"
        ).strip().lower()
        constraints = [str(x).strip().lower() for x in (row.get("constraints", []) or []) if str(x).strip()]
        direct = dict(hist.get("direct_system_effects", {}) or {})
        effect_modes = list(direct.get("effect_modes", []) or self._fallback_effect_modes(row, target_kind))
        effect_phrases = list(direct.get("effect_phrases", []) or [])
        if not effect_phrases:
            effect_phrases = [
                f"{target_kind} growth reflected through {module_name or 'runtime'}",
                f"{'.'.join(chain) or op_id or 'surface'} changed downstream system pressure",
            ]
        direct["effect_modes"] = list(dict.fromkeys(effect_modes))
        direct["effect_phrases"] = list(dict.fromkeys(effect_phrases))
        direct["required_system_changes"] = list(dict.fromkeys(list(direct.get("required_system_changes", []) or []) + [
            f"lineage_registration:{module_name or 'runtime'}",
            f"growth_reflection:{target_kind}",
        ]))
        direct["system_effects"] = list(dict.fromkeys(list(direct.get("system_effects", []) or []) + effect_phrases))
        direct["growth_chain"] = list(chain)
        hist["direct_system_effects"] = direct

        ripple = dict(hist.get("ripple_effects", {}) or {})
        ripple["origin_module"] = str(ripple.get("origin_module", "") or module_name)
        ripple["origin_owner"] = str(ripple.get("origin_owner", "") or (".".join(chain[:-1]) if len(chain) > 1 else module_name))
        ripple["propagated_modules"] = sorted({
            *[str(x) for x in (ripple.get("propagated_modules", []) or []) if str(x).strip()],
            *([module_name] if module_name else []),
        })
        ripple["propagated_subsystems"] = sorted({
            *[str(x) for x in (ripple.get("propagated_subsystems", []) or []) if str(x).strip()],
            *([".".join(module_name.split(".")[:2])] if module_name else []),
        })
        ripple["cross_diversity_links"] = int(ripple.get("cross_diversity_links", 0) or max(1, len(set(constraints)) + max(0, len(effect_modes) - 1)))
        ripple["derived_from_origin_descendants"] = int(ripple.get("derived_from_origin_descendants", 0) or max(1, len(chain)))
        growth_events = list(ripple.get("growth_events", []) or [])
        if not growth_events:
            growth_events = [{
                "stage": "emergence",
                "module": module_name,
                "lineage_kind": str(lineage_kind),
                "target_kind": target_kind,
            }]
        ripple["growth_events"] = growth_events
        hist["ripple_effects"] = ripple

        summary = dict(hist.get("developmental_summary", {}) or {})
        impact = float(summary.get("system_impact_score", 0.0) or 0.0)
        if impact <= 0.0:
            impact = min(1.0, (0.18 * len(set(constraints))) + (0.12 * len(effect_modes)) + (0.05 * len(chain)))
        summary["system_impact_score"] = round(float(impact), 6)
        summary["reflection_strength"] = round(float(max(summary.get("reflection_strength", 0.0) or 0.0, min(1.0, 0.20 + (0.08 * len(effect_modes))))), 6)
        summary["growth_reflected"] = True
        summary["lineage_kind"] = str(lineage_kind)
        hist["developmental_summary"] = summary
        hist["growth_lineage"] = {
            "op_chain": list(chain),
            "module": module_name,
            "lineage_kind": str(lineage_kind),
            "target_kind": target_kind,
            "constraints": list(constraints),
            "present_in_system": True,
        }
        hist["system_reflection_required"] = True
        hist["growth_reflection_complete"] = True
        return hist

    def _load_genealogy_artifacts(self) -> Dict[str, Any]:
        base = self._abs_path(_GENEALOGY_OUTPUT_DIR)
        cache_key: List[Tuple[str, int, int]] = []
        for _, name in (
            ("abilities", "abilities.json"),
            ("links", "links.json"),
            ("couplings", "couplings.json"),
            ("pair_stats", "pair_stats.json"),
        ):
            cache_key.append((name, *self._file_stamp(os.path.join(base, name))))
        if tuple(cache_key) == tuple(self._genealogy_artifact_cache.get("key", ()) or ()):
            cached = self._genealogy_artifact_cache.get("value", {})
            return dict(cached) if isinstance(cached, dict) else {"abilities": {}, "links": {}, "couplings": {}, "pair_stats": {}}
        out: Dict[str, Any] = {"abilities": {}, "links": {}, "couplings": {}, "pair_stats": {}}
        for key, name in (
            ("abilities", "abilities.json"),
            ("links", "links.json"),
            ("couplings", "couplings.json"),
            ("pair_stats", "pair_stats.json"),
        ):
            path = os.path.join(base, name)
            if not os.path.exists(path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    raw = json.load(fh)
                out[key] = raw if isinstance(raw, dict) else {}
            except Exception:
                out[key] = {}
        self._genealogy_artifact_cache = {"key": tuple(cache_key), "value": out}
        return out

    def _operation_axis_counts(self, row: Dict[str, Any]) -> Dict[str, int]:
        counts = {ax: 0 for ax in ("X", "T", "N", "B", "A")}
        for raw in (row.get("constraints", []) or []):
            ax = _CONSTRAINT_TO_AXIS.get(str(raw or "").strip().lower())
            if ax:
                counts[ax] += 1
        hist = dict(row.get("developmental_effect_history", {}) or {})
        direct = dict(hist.get("direct_system_effects", {}) or {})
        effect_modes = set(str(x) for x in (direct.get("effect_modes", []) or []))
        mode_map = {
            "state_schema_change": "X",
            "temporal_orchestration_change": "T",
            "cost_pressure_change": "N",
            "interface_boundary_change": "B",
            "adaptive_steering_change": "A",
            "gateway_surface": "B",
            "lineage_surface": "B",
            "latent_route_surface": "A",
        }
        for mode, ax in mode_map.items():
            if mode in effect_modes:
                counts[ax] += 1
        if not any(counts.values()):
            counts["X"] = 1
        return counts

    def _counts_to_signature(self, counts: Dict[str, int]) -> str:
        parts = []
        for ax in ("X", "T", "N", "B", "A"):
            val = int(counts.get(ax, 0) or 0)
            if val > 0:
                parts.append(f"{ax}^{val}")
        return "*".join(parts) if parts else "X^1"

    def _signature_to_counts(self, signature: str) -> Dict[str, int]:
        counts = {ax: 0 for ax in ("X", "T", "N", "B", "A")}
        for raw in str(signature or "").split("*"):
            part = raw.strip()
            if not part:
                continue
            if "^" in part:
                ax, val = part.split("^", 1)
            else:
                ax, val = part, "1"
            ax = str(ax).strip().upper()
            try:
                num = int(float(str(val).strip()))
            except Exception:
                num = 0
            if ax in counts and num > 0:
                counts[ax] += num
        return counts

    def _counts_similarity(self, left: Dict[str, int], right: Dict[str, int]) -> float:
        axes = ("X", "T", "N", "B", "A")
        overlap = 0.0
        total = 0.0
        for ax in axes:
            lv = float(max(0, int(left.get(ax, 0) or 0)))
            rv = float(max(0, int(right.get(ax, 0) or 0)))
            overlap += min(lv, rv)
            total += max(lv, rv)
        if total <= 0.0:
            return 0.0
        return overlap / total

    def _genealogy_strategy(self, operations: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        cache_key = self._descriptor_cache_stamp(operations)
        if cache_key == tuple(self._genealogy_strategy_cache.get("key", ()) or ()):
            cached = self._genealogy_strategy_cache.get("value", {})
            return dict(cached) if isinstance(cached, dict) else {}
        artifacts = self._load_genealogy_artifacts()
        roots = dict((artifacts.get("couplings", {}) or {}).get("roots", {}) or {})
        abilities = dict(artifacts.get("abilities", {}) or {})
        links = dict(artifacts.get("links", {}) or {})
        origin_counts = dict((artifacts.get("couplings", {}) or {}).get("origin_counts", {}) or {})

        ability_signatures: List[Tuple[str, List[str]]] = []
        for rec in abilities.values():
            if not isinstance(rec, dict):
                continue
            tags = [str(x) for x in (rec.get("effect_tags", []) or [])]
            sigs = []
            for tag in tags:
                if tag.startswith("origin_signature:"):
                    sigs.append(tag.split(":", 1)[1].strip())
            ability_signatures.append((str(rec.get("id", "") or ""), sigs))

        link_signatures: List[str] = []
        for rec in links.values():
            if not isinstance(rec, dict):
                continue
            for tag in (rec.get("tags", []) or []):
                txt = str(tag or "")
                if txt.startswith("origin_signature:") or txt.startswith("signature:"):
                    link_signatures.append(txt.split(":", 1)[1].strip())

        out: Dict[str, Dict[str, Any]] = {}
        for row in (operations or []):
            if not isinstance(row, dict):
                continue
            op_id = str(row.get("op_id", "") or "")
            if not op_id or op_id.startswith("latent."):
                continue
            counts = self._operation_axis_counts(row)
            signature = self._counts_to_signature(counts)
            best_sig = ""
            best_root: Dict[str, Any] = {}
            best_similarity = 0.0
            for sig, rec in roots.items():
                if not isinstance(rec, dict):
                    continue
                sim = self._counts_similarity(counts, self._signature_to_counts(sig))
                if sim > best_similarity:
                    best_similarity = sim
                    best_sig = str(sig)
                    best_root = rec
            ability_hits = 0
            for _, sigs in ability_signatures:
                if signature in sigs:
                    ability_hits += 1
            link_hits = sum(1 for sig in link_signatures if sig == signature)
            regulation = dict(best_root.get("regulation", {}) or {})
            persistence_tax = float(regulation.get("persistence_tax_factor", 0.0) or 0.0)
            sustainability = float(regulation.get("sustainability_score", 0.0) or 0.0)
            representation = float(regulation.get("representation_score", 0.0) or 0.0)
            inheritance_breaches = int(best_root.get("inheritance_breach_count", 0) or 0)
            origin_activity = int(origin_counts.get(f"({signature})x({best_sig})", 0) or 0) + int(origin_counts.get(f"({best_sig})x({signature})", 0) or 0)
            pressure = (
                best_similarity * 0.35
                + min(0.2, ability_hits * 0.01)
                + min(0.2, link_hits * 0.01)
                + min(0.15, origin_activity * 0.005)
                + min(0.15, persistence_tax * 0.02)
                + min(0.1, inheritance_breaches * 0.03)
            )
            out[op_id] = {
                "signature": signature,
                "best_coupling_signature": best_sig,
                "coupling_similarity": round(best_similarity, 6),
                "ability_hits": int(ability_hits),
                "link_hits": int(link_hits),
                "origin_activity": int(origin_activity),
                "persistence_tax_factor": round(persistence_tax, 6),
                "sustainability_score": round(sustainability, 6),
                "representation_score": round(representation, 6),
                "inheritance_breach_count": int(inheritance_breaches),
                "genealogy_pressure": round(pressure, 6),
                "rewrite_bias": (
                    "lineage_memory"
                    if "constraint_genealogy" in self._module_name_from_relpath(row.get("file", ""))
                    else (
                        "governance_routing"
                        if "governance_persistence_gateway" in self._module_name_from_relpath(row.get("file", ""))
                        else (
                            "perceptual_synthesis"
                            if "aurora_expression_perception" in self._module_name_from_relpath(row.get("file", ""))
                            else (
                                "dimensional_balancing"
                                if "aurora_dimensional_systems" in self._module_name_from_relpath(row.get("file", ""))
                                else "generic"
                            )
                        )
                    )
                ),
            }
        self._genealogy_strategy_cache = {"key": cache_key, "value": out}
        return out

    def _development_alignment(self, operations: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        cache_key = self._descriptor_cache_stamp(operations)
        if cache_key == tuple(self._alignment_cache.get("key", ()) or ()):
            cached = self._alignment_cache.get("value", {})
            return dict(cached) if isinstance(cached, dict) else {}
        by_module: Dict[str, float] = {}
        by_kind: Dict[Tuple[str, str], float] = {}
        for row in (operations or []):
            if not isinstance(row, dict):
                continue
            op_id = str(row.get("op_id", "") or "")
            if not op_id or op_id.startswith("latent."):
                continue
            module_name = self._module_name_from_relpath(row.get("file", ""))
            kind = str(row.get("kind", "") or "")
            score = float(self._surface_score(row))
            by_module[module_name] = max(float(by_module.get(module_name, 0.0) or 0.0), score)
            by_kind[(module_name, kind)] = max(float(by_kind.get((module_name, kind), 0.0) or 0.0), score)

        out: Dict[str, Dict[str, Any]] = {}
        for row in (operations or []):
            if not isinstance(row, dict):
                continue
            op_id = str(row.get("op_id", "") or "")
            if not op_id or op_id.startswith("latent."):
                continue
            module_name = self._module_name_from_relpath(row.get("file", ""))
            kind = str(row.get("kind", "") or "")
            score = float(self._surface_score(row))
            module_peak = float(by_module.get(module_name, score) or score)
            kind_peak = float(by_kind.get((module_name, kind), module_peak) or module_peak)
            gap = max(0.0, max(module_peak, kind_peak) - score)
            hist = dict(row.get("developmental_effect_history", {}) or {})
            ripple = dict(hist.get("ripple_effects", {}) or {})
            cross_links = int(ripple.get("cross_diversity_links", 0) or 0)
            out[op_id] = {
                "current_score": round(score, 6),
                "module_peak_score": round(module_peak, 6),
                "kind_peak_score": round(kind_peak, 6),
                "alignment_gap": round(gap, 6),
                "cross_diversity_links": cross_links,
                "needs_alignment": bool(gap >= 0.18 and cross_links > 0),
                "module": module_name,
                "kind": kind,
            }
        self._alignment_cache = {"key": cache_key, "value": out}
        return out

    def _feedback_pressure(self, module_name: str, rewrite_bias: str, artifacts: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        artifacts = dict(artifacts or self._load_genealogy_artifacts() or {})
        abilities = dict(artifacts.get("abilities", {}) or {})
        couplings = dict(artifacts.get("couplings", {}) or {})
        pressure = 0.0
        adoption = 0.0
        trials = 0.0
        timing_credit = 0.0
        timing_penalty = 0.0

        for rec in abilities.values():
            if not isinstance(rec, dict):
                continue
            tags = [str(x) for x in (rec.get("effect_tags", []) or [])]
            if "code_evolution" not in tags:
                continue
            module_hit = False
            bias_hit = False
            accepted = False
            agency_credit = 0.0
            temporal_penalty = 0.0
            for tag in tags:
                if tag == f"mutation_module:{module_name}":
                    module_hit = True
                elif tag == f"rewrite_profile:{self._rewrite_profile_for_module(module_name)}":
                    module_hit = True
                elif tag == f"mutation_status:accepted":
                    accepted = True
                elif tag.startswith("agency_time_credit:"):
                    try:
                        agency_credit = max(agency_credit, float(tag.split(":", 1)[1]))
                    except Exception:
                        pass
                elif tag.startswith("temporal_overhead_penalty:"):
                    try:
                        temporal_penalty = max(temporal_penalty, float(tag.split(":", 1)[1]))
                    except Exception:
                        pass
            notes = str(rec.get("notes", "") or "")
            if rewrite_bias and rewrite_bias in notes:
                bias_hit = True
            if module_hit or bias_hit:
                pressure += 0.14 if accepted else 0.06
                timing_credit += 0.08 * agency_credit
                timing_penalty += 0.06 * temporal_penalty

        experiments = dict(couplings.get("experiments", {}) or {})
        for rec in (experiments.get("adoptions", []) or []):
            if not isinstance(rec, dict):
                continue
            mods = [str(x) for x in (rec.get("target_modules", []) or [])]
            shape = str(rec.get("shape", "") or "")
            trigger = str(rec.get("trigger_mode", "") or "")
            if module_name in mods or shape == self._rewrite_profile_for_module(module_name):
                adoption += 0.12 if trigger == "code_evolution" else 0.04
                timing_credit += 0.05 * float(rec.get("agency_time_credit", 0.0) or 0.0)
                timing_penalty += 0.04 * float(rec.get("temporal_overhead_penalty", 0.0) or 0.0)
            if rewrite_bias and shape == rewrite_bias:
                adoption += 0.03
        for rec in (experiments.get("trials", []) or []):
            if not isinstance(rec, dict):
                continue
            mods = [str(x) for x in (rec.get("target_modules", []) or [])]
            shape = str(rec.get("shape", "") or "")
            trigger = str(rec.get("trigger_mode", "") or "")
            if module_name in mods or shape == self._rewrite_profile_for_module(module_name):
                trials += 0.04 if trigger == "code_evolution" else 0.01
                timing_credit += 0.02 * float(rec.get("agency_time_credit", 0.0) or 0.0)
                timing_penalty += 0.02 * float(rec.get("temporal_overhead_penalty", 0.0) or 0.0)
            if rewrite_bias and shape == rewrite_bias:
                trials += 0.01
        net_timing = max(-0.15, min(0.20, timing_credit - timing_penalty))
        return {
            "module_feedback": round(min(0.40, pressure + adoption + trials + net_timing), 6),
            "feedback_adoption": round(adoption, 6),
            "feedback_trials": round(trials, 6),
            "feedback_timing_credit": round(timing_credit, 6),
            "feedback_timing_penalty": round(timing_penalty, 6),
        }

    def _rewrite_family_feedback(
        self,
        module_name: str,
        rewrite_profile: str,
        rewrite_bias: str,
        artifacts: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        artifacts = dict(artifacts or self._load_genealogy_artifacts() or {})
        cache_key = (
            self._module_name_from_relpath(module_name),
            str(rewrite_profile or ""),
            str(rewrite_bias or ""),
            tuple(sorted((self._genealogy_artifact_cache.get("key", ()) or ()))),
        )
        if cache_key == tuple(self._rewrite_feedback_cache.get("key", ()) or ()):
            cached = self._rewrite_feedback_cache.get("value", {})
            return dict(cached) if isinstance(cached, dict) else {}
        abilities = dict(artifacts.get("abilities", {}) or {})
        couplings = dict(artifacts.get("couplings", {}) or {})
        module_name = str(module_name or "")
        rewrite_profile = str(rewrite_profile or "")
        rewrite_bias = str(rewrite_bias or "")
        trials = 0
        accepted = 0
        rejected = 0
        mutation_score_sum = 0.0
        timing_credit = 0.0
        timing_penalty = 0.0
        adoption_count = 0
        adoption_credit = 0.0
        adoption_penalty = 0.0

        for rec in abilities.values():
            if not isinstance(rec, dict):
                continue
            tags = [str(x) for x in (rec.get("effect_tags", []) or [])]
            notes = str(rec.get("notes", "") or "")
            if "code_evolution" not in tags and "Code evolution outcome" not in notes:
                continue
            module_hit = False
            bias_hit = False
            status = ""
            mutation_score = 0.0
            agency_credit = 0.0
            temporal_overhead = 0.0
            for tag in tags:
                if tag == f"mutation_module:{module_name}" or tag == f"rewrite_profile:{rewrite_profile}":
                    module_hit = True
                elif tag == "mutation_status:accepted":
                    status = "accepted"
                elif tag == "mutation_status:rejected":
                    status = "rejected"
                elif tag.startswith("mutation_score:"):
                    try:
                        mutation_score = float(tag.split(":", 1)[1])
                    except Exception:
                        mutation_score = 0.0
                elif tag.startswith("agency_time_credit:"):
                    try:
                        agency_credit = max(agency_credit, float(tag.split(":", 1)[1]))
                    except Exception:
                        agency_credit = 0.0
                elif tag.startswith("temporal_overhead_penalty:"):
                    try:
                        temporal_overhead = max(temporal_overhead, float(tag.split(":", 1)[1]))
                    except Exception:
                        temporal_overhead = 0.0
            if not module_hit and module_name and module_name in notes:
                module_hit = True
            if rewrite_bias and rewrite_bias in notes:
                bias_hit = True
            if not (module_hit or bias_hit):
                continue
            trials += 1
            accepted += 1 if status == "accepted" else 0
            rejected += 1 if status == "rejected" else 0
            mutation_score_sum += float(mutation_score)
            timing_credit += float(agency_credit)
            timing_penalty += float(temporal_overhead)

        experiments = dict(couplings.get("experiments", {}) or {})
        for rec in (experiments.get("adoptions", []) or []):
            if not isinstance(rec, dict):
                continue
            mods = [str(x) for x in (rec.get("target_modules", []) or [])]
            shape = str(rec.get("shape", "") or "")
            if module_name in mods or shape in {rewrite_profile, rewrite_bias}:
                adoption_count += 1
                adoption_credit += float(rec.get("agency_time_credit", 0.0) or 0.0)
                adoption_penalty += float(rec.get("temporal_overhead_penalty", 0.0) or 0.0)

        total_trials = max(1, int(trials))
        acceptance_rate = float(accepted / total_trials) if trials else 0.0
        rejection_rate = float(rejected / total_trials) if trials else 0.0
        mean_mutation_score = float(mutation_score_sum / total_trials) if trials else 0.0
        mean_credit = float((timing_credit + (0.5 * adoption_credit)) / max(1, trials + adoption_count))
        mean_penalty = float((timing_penalty + (0.5 * adoption_penalty)) / max(1, trials + adoption_count))
        if trials >= 2 and rejection_rate >= 0.6 and mean_penalty >= mean_credit:
            adaptation_mode = "conservative"
        elif acceptance_rate >= 0.5 and mean_credit > mean_penalty:
            adaptation_mode = "expansive"
        elif adoption_count > 0 or rewrite_bias in {"lineage_memory", "governance_routing", "perceptual_synthesis", "dimensional_balancing"}:
            adaptation_mode = "integrative"
        else:
            adaptation_mode = "balanced"
        confidence = min(
            1.0,
            (0.18 * trials)
            + (0.10 * adoption_count)
            + (0.24 * acceptance_rate)
            + (0.14 * mean_credit)
            - (0.10 * mean_penalty),
        )
        feedback = {
            "trial_count": int(trials),
            "accepted_count": int(accepted),
            "rejected_count": int(rejected),
            "acceptance_rate": round(max(0.0, acceptance_rate), 6),
            "rejection_rate": round(max(0.0, rejection_rate), 6),
            "mean_mutation_score": round(max(0.0, mean_mutation_score), 6),
            "timing_credit": round(max(0.0, mean_credit), 6),
            "timing_penalty": round(max(0.0, mean_penalty), 6),
            "adoption_count": int(adoption_count),
            "adaptation_mode": str(adaptation_mode),
            "confidence": round(max(0.0, min(1.0, confidence)), 6),
        }
        self._rewrite_feedback_cache = {"key": cache_key, "value": dict(feedback)}
        return feedback

    def _select_reflection_candidates(self, operations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        alignment = self._development_alignment(operations)
        artifacts = self._load_genealogy_artifacts()
        genealogy = self._genealogy_strategy(operations)
        function_ranked: List[Tuple[float, Dict[str, Any]]] = []
        class_ranked: List[Tuple[float, Dict[str, Any]]] = []
        module_bias_ranked: Dict[str, List[Tuple[float, Dict[str, Any]]]] = {}
        _empty_channels = self._empty_slot_channels()
        for row in (operations or []):
            op_id = str(row.get("op_id", "") or "")
            if not op_id or op_id.startswith("latent."):
                continue
            hist = dict(row.get("developmental_effect_history", {}) or {})
            summary = dict(hist.get("developmental_summary", {}) or {})
            ripple = dict(hist.get("ripple_effects", {}) or {})
            align = dict(alignment.get(op_id, {}) or {})
            gene = dict(genealogy.get(op_id, {}) or {})
            module_name = self._module_name_from_relpath(row.get("file", ""))
            rewrite_bias = str(gene.get("rewrite_bias", "") or "generic")
            feedback = self._feedback_pressure(module_name, rewrite_bias, artifacts)
            impact = float(summary.get("system_impact_score", 0.0) or 0.0)
            gap = float(align.get("alignment_gap", 0.0) or 0.0)
            xlinks = int(ripple.get("cross_diversity_links", 0) or 0)
            gpressure = float(gene.get("genealogy_pressure", 0.0) or 0.0)
            fb_pressure = float(feedback.get("module_feedback", 0.0) or 0.0)
            slot_pressure = self._empty_slot_pressure(row, _empty_channels)
            if impact < 0.65 and gap < 0.30 and gpressure < 0.25 and fb_pressure < 0.05 and slot_pressure < 0.10 and not bool(align.get("needs_alignment", False)):
                continue
            if xlinks < 1 and slot_pressure < 0.15 and not (
                rewrite_bias in {"perceptual_synthesis", "dimensional_balancing", "governance_routing", "lineage_memory"}
                and gap >= 0.45
                and gpressure >= 0.40
            ):
                continue
            score = self._surface_score(row) + gap * 1.5 + min(0.15, xlinks * 0.01) + gpressure + fb_pressure + slot_pressure
            kind = str(row.get("kind", "") or "")
            if kind in {"function", "async_function"}:
                function_ranked.append((score, row))
                if rewrite_bias != "generic":
                    module_bias_ranked.setdefault(rewrite_bias, []).append((score, row))
            elif kind == "class":
                class_ranked.append((score, row))
                if rewrite_bias != "generic":
                    module_bias_ranked.setdefault(rewrite_bias, []).append((score, row))
        function_ranked.sort(key=lambda item: item[0], reverse=True)
        class_ranked.sort(key=lambda item: item[0], reverse=True)
        for ranked in module_bias_ranked.values():
            ranked.sort(key=lambda item: item[0], reverse=True)
        out: List[Dict[str, Any]] = []
        seen: set[str] = set()
        # Derive bias iteration order from routing_type in adapter_hints.json.
        # If a routing_type is present, promote its mapped rewrite_bias to first
        # so the evolver selects semantically aligned operators before generic ones.
        _bias_order = ["lineage_memory", "governance_routing", "perceptual_synthesis", "dimensional_balancing"]
        try:
            _hints_path = self._abs_path("aurora_state/adapter_hints.json")
            with open(_hints_path) as _fh:
                _hints_data = json.load(_fh)
            _routing_type = str(_hints_data.get("routing_type", "") or "")
            _routed_bias = _ROUTING_TYPE_TO_REWRITE_BIAS.get(_routing_type, "")
            if _routed_bias and _routed_bias in _bias_order:
                _bias_order.remove(_routed_bias)
                _bias_order.insert(0, _routed_bias)
        except Exception:
            pass
        for bias in _bias_order:
            ranked = module_bias_ranked.get(bias, [])
            picks = 0
            for _, row in ranked:
                op_id = str(row.get("op_id", "") or "")
                if op_id in seen:
                    continue
                seen.add(op_id)
                out.append(row)
                picks += 1
                if picks >= 4:
                    break
        for _, row in function_ranked:
            op_id = str(row.get("op_id", "") or "")
            if op_id in seen:
                continue
            seen.add(op_id)
            out.append(row)
            if len(out) >= _FUNCTION_OVERRIDE_LIMIT:
                break
        class_count = 0
        for _, row in class_ranked:
            op_id = str(row.get("op_id", "") or "")
            if op_id in seen:
                continue
            seen.add(op_id)
            out.append(row)
            class_count += 1
            if class_count >= _CLASS_REFLECTION_LIMIT or len(out) >= _REFLECTION_LIMIT:
                break
        return out

    def _build_developmental_surface_updates(self, target_path: str) -> Dict[str, Any]:
        state = self._load_descriptor_state()
        if state is None:
            return {"updates": {}, "details": [], "manifest": {}}

        latent_rows = [dict(row) for row in (state.get("latent_operations", []) or []) if isinstance(row, dict)]
        ops = [dict(row) for row in (state.get("operations", []) or []) if isinstance(row, dict)]
        alignment = self._development_alignment(ops)
        genealogy = self._genealogy_strategy(ops)
        reflection_rows = self._select_reflection_candidates(ops)
        render = self._render_evolved_surfaces(latent_rows, reflection_rows, alignment, genealogy)
        state_updated = self._update_descriptor_state(state, render, target_path)
        descriptor_path = self._abs_path(_DESCRIPTOR_STATE_REL)
        updates: Dict[str, str] = {
            os.path.abspath(target_path): str(render.get("module_text", "") or ""),
            descriptor_path: json.dumps(state_updated, ensure_ascii=True, indent=2, sort_keys=True),
        }
        details = [
            {
                "file": os.path.abspath(target_path),
                "change": (
                    f"generated {int(render['manifest'].get('latent_count', 0))} promoted latent methods "
                    f"and {int(render['manifest'].get('reflection_count', 0))} architectural reflections"
                ),
            },
            {
                "file": descriptor_path,
                "change": "updated present representations for promoted and reflected lineage surfaces",
            },
        ]
        return {"updates": updates, "details": details, "manifest": dict(render.get("manifest", {}) or {})}

    def _can_activate_override(self, row: Dict[str, Any]) -> bool:
        if str(row.get("kind", "") or "") != "reflection":
            return False
        if str(row.get("target_kind", "") or "") not in {"function", "async_function"}:
            return False
        chain = list(row.get("op_chain", []) or [])
        if not chain:
            return False
        leaf = str(chain[-1] or "")
        if not leaf:
            return False
        if leaf == "__init__":
            return False
        if leaf.startswith("_"):
            module_name = self._module_name_from_relpath(row.get("file", ""))
            hist = dict(row.get("developmental_effect_history", {}) or {})
            direct = dict(hist.get("direct_system_effects", {}) or {})
            profile = self._infer_contract_profile(
                module_name=module_name,
                chain=chain,
                target_kind=str(row.get("target_kind", "") or ""),
                constraints=list(row.get("constraints", []) or []),
                effect_modes=list(direct.get("effect_modes", []) or []),
            )
            if int(profile.get("required_args", 0) or 0) > 0:
                return False
            if bool(profile.get("async_callable", False)):
                return False
            if int(profile.get("kwonly_args", 0) or 0) > 0:
                return False
            return True
        return True

    def _can_bind_latent_projection(self, row: Dict[str, Any]) -> bool:
        if str(row.get("kind", "") or "") != "latent":
            return False
        chain = list(row.get("op_chain", []) or [])
        if len(chain) < 2:
            return False
        leaf = str(chain[-1] or "")
        if not leaf or leaf.startswith("_"):
            return False
        owner_chain = chain[:-1]
        module_name = self._module_name_from_relpath(row.get("file", ""))
        owner = self._resolve_module_target(module_name, owner_chain)
        native_projection = dict(row.get("native_projection", {}) or {})
        existing_mode = str(native_projection.get("mode", "") or "")
        if owner is None:
            return False
        if hasattr(owner, leaf) and existing_mode != "latent_binding":
            return False
        if not (inspect.isclass(owner) or callable(owner) or hasattr(owner, "__dict__")):
            return False
        return True

    def _strip_generated_block(self, text: str) -> str:
        if _NATIVE_BLOCK_BEGIN not in text:
            return text
        pattern = re.compile(
            re.escape(_NATIVE_BLOCK_BEGIN) + r".*?" + re.escape(_NATIVE_BLOCK_END) + r"\n?",
            re.DOTALL,
        )
        return re.sub(pattern, "", text).rstrip() + "\n"

    def _name_taken(self, text: str, name: str) -> bool:
        safe = re.escape(str(name))
        patterns = [
            rf"(?m)^def\s+{safe}\b",
            rf"(?m)^class\s+{safe}\b",
            rf"(?m)^{safe}\s*=",
        ]
        return any(re.search(pat, text) is not None for pat in patterns)

    def _preferred_native_export_name(
        self,
        row: Dict[str, Any],
        surface_method: str,
        kind: str,
        existing_text: str,
        used_names: set[str],
    ) -> str:
        module_name = self._module_name_from_relpath(row.get("file", ""))
        chain = self._operation_chain(row.get("op_id", ""), module_name)
        candidates: List[str] = []
        if kind == "latent":
            if chain:
                candidates.append(chain[-1])
            if len(chain) >= 2:
                candidates.append(f"{chain[-2]}_{chain[-1]}")
            candidates.append(f"evolved_{chain[-1] if chain else surface_method}")
        else:
            tail = chain[-1] if chain else surface_method
            candidates.extend([f"{tail}_evolved", f"evolved_{tail}"])
        candidates.append(surface_method)
        for raw in candidates:
            name = self._sanitize_identifier(raw, prefix="evolved_surface")
            if name in used_names:
                continue
            if self._name_taken(existing_text, name):
                continue
            used_names.add(name)
            return name
        fallback = self._sanitize_identifier(f"evolved_{surface_method}", prefix="evolved_surface")
        while fallback in used_names or self._name_taken(existing_text, fallback):
            fallback = self._sanitize_identifier(f"{fallback}_x", prefix="evolved_surface")
        used_names.add(fallback)
        return fallback

    def _rewrite_profile_for_module(self, module_name: str) -> str:
        if module_name == "aurora_internal.constraint_genealogy":
            return "constraint_genealogy"
        if module_name == "aurora_governance_persistence_gateway":
            return "governance_gateway"
        if module_name == "aurora_expression_perception":
            return "perception_synthesis"
        if module_name == "aurora_dimensional_systems":
            return "dimensional_balancing"
        return "generic"

    def _resolve_module_target(self, module_name: str, chain: List[str]) -> Any:
        try:
            module = importlib.import_module(str(module_name or "").strip())
        except Exception:
            return None
        current: Any = module
        for attr in (chain or []):
            if not attr or not hasattr(current, attr):
                return None
            try:
                current = getattr(current, attr)
            except Exception:
                return None
        return current

    def _infer_contract_profile(
        self,
        module_name: str,
        chain: List[str],
        target_kind: str,
        constraints: Optional[List[str]] = None,
        effect_modes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        cache_key = (
            str(module_name or ""),
            tuple(chain or []),
            str(target_kind or ""),
            tuple(sorted(str(x).strip().lower() for x in (constraints or []) if str(x).strip())),
            tuple(sorted(str(x).strip().lower() for x in (effect_modes or []) if str(x).strip())),
        )
        if cache_key == tuple(self._contract_profile_cache.get("key", ()) or ()):
            cached = self._contract_profile_cache.get("value", {})
            return dict(cached) if isinstance(cached, dict) else {}
        target = self._resolve_module_target(module_name, chain)
        profile: Dict[str, Any] = {
            "target_kind": str(target_kind or ""),
            "callable": bool(callable(target)),
            "class_target": bool(inspect.isclass(target)),
            "async_callable": bool(inspect.iscoroutinefunction(target)),
            "stateful_owner": bool(len(chain or []) >= 2),
            "required_args": 0,
            "optional_args": 0,
            "kwonly_args": 0,
            "varargs": False,
            "varkw": False,
            "accepts_payload": False,
            "signature_text": "",
            "return_hint": "",
            "doc_hint": "",
            "effect_density": int(len(effect_modes or [])),
            "constraint_density": int(len(constraints or [])),
        }
        if target is not None:
            try:
                sig = inspect.signature(target)
                params = list(sig.parameters.values())
                payload_names = {"payload", "data", "record", "state", "event", "amount", "value"}
                required = 0
                optional = 0
                kwonly = 0
                for idx, p in enumerate(params):
                    if idx == 0 and p.name in {"self", "cls"}:
                        continue
                    if p.kind == inspect.Parameter.KEYWORD_ONLY:
                        kwonly += 1
                    if p.kind == inspect.Parameter.VAR_POSITIONAL:
                        profile["varargs"] = True
                    elif p.kind == inspect.Parameter.VAR_KEYWORD:
                        profile["varkw"] = True
                    elif p.default is inspect._empty:
                        required += 1
                    else:
                        optional += 1
                    if p.name in payload_names:
                        profile["accepts_payload"] = True
                profile["required_args"] = int(required)
                profile["optional_args"] = int(optional)
                profile["kwonly_args"] = int(kwonly)
                profile["signature_text"] = str(sig)
                ann = getattr(sig, "return_annotation", inspect._empty)
                if ann is not inspect._empty:
                    profile["return_hint"] = getattr(ann, "__name__", str(ann))
            except Exception:
                pass
            try:
                doc = inspect.getdoc(target) or ""
                if doc:
                    profile["doc_hint"] = str(doc.splitlines()[0]).strip()[:160]
            except Exception:
                pass
        if not profile["return_hint"]:
            effect_set = set(str(x).strip().lower() for x in (effect_modes or []) if str(x).strip())
            if "state_schema_change" in effect_set:
                profile["return_hint"] = "state_record"
            elif "interface_boundary_change" in effect_set or "gateway_surface" in effect_set:
                profile["return_hint"] = "boundary_record"
            elif "adaptive_steering_change" in effect_set:
                profile["return_hint"] = "decision_record"
            elif str(target_kind or "") == "class":
                profile["return_hint"] = "class_surface"
            else:
                profile["return_hint"] = "generic_record"
        contract_mode = "stateful" if profile["stateful_owner"] else "stateless"
        if profile["async_callable"]:
            contract_mode = "async_" + contract_mode
        profile["contract_mode"] = contract_mode
        self._contract_profile_cache = {"key": cache_key, "value": dict(profile)}
        return profile

    def _native_strategy_payload(self, row: Dict[str, Any], module_name: str) -> Dict[str, Any]:
        genealogy = dict(row.get("genealogy_strategy", {}) or {})
        rewrite_profile = self._rewrite_profile_for_module(module_name)
        op_chain = list(row.get("op_chain", []) or [])
        target_kind = str(row.get("target_kind", "") or "")
        constraints = list(row.get("constraints", []) or [])
        effect_modes = list(row.get("effect_modes", []) or [])
        family_feedback = self._rewrite_family_feedback(
            module_name=module_name,
            rewrite_profile=rewrite_profile,
            rewrite_bias=str(genealogy.get("rewrite_bias", "") or "generic"),
        )
        contract_profile = self._infer_contract_profile(
            module_name=module_name,
            chain=op_chain,
            target_kind=target_kind,
            constraints=constraints,
            effect_modes=effect_modes,
        )
        return {
            "op_id": str(row.get("op_id", "") or ""),
            "module": str(module_name or ""),
            "kind": str(row.get("kind", "") or ""),
            "target_kind": target_kind,
            "rewrite_profile": rewrite_profile,
            "alignment_gap": float(row.get("alignment_gap", 0.0) or 0.0),
            "alignment_target_score": float(row.get("alignment_target_score", 0.0) or 0.0),
            "constraints": constraints,
            "effect_modes": effect_modes,
            "effect_phrases": list(row.get("effect_phrases", []) or []),
            "cross_diversity_links": int(row.get("cross_diversity_links", 0) or 0),
            "surface_score": float(row.get("surface_score", self._surface_score(row)) or 0.0),
            "signature": str(genealogy.get("signature", "") or ""),
            "best_coupling_signature": str(genealogy.get("best_coupling_signature", "") or ""),
            "coupling_similarity": float(genealogy.get("coupling_similarity", 0.0) or 0.0),
            "ability_hits": int(genealogy.get("ability_hits", 0) or 0),
            "link_hits": int(genealogy.get("link_hits", 0) or 0),
            "origin_activity": int(genealogy.get("origin_activity", 0) or 0),
            "persistence_tax_factor": float(genealogy.get("persistence_tax_factor", 0.0) or 0.0),
            "sustainability_score": float(genealogy.get("sustainability_score", 0.0) or 0.0),
            "representation_score": float(genealogy.get("representation_score", 0.0) or 0.0),
            "inheritance_breach_count": int(genealogy.get("inheritance_breach_count", 0) or 0),
            "genealogy_pressure": float(genealogy.get("genealogy_pressure", 0.0) or 0.0),
            "rewrite_bias": str(genealogy.get("rewrite_bias", "") or "generic"),
            "rewrite_feedback": dict(family_feedback),
            "contract_profile": dict(contract_profile),
        }

    def _native_wrapper_block(self, rows: List[Dict[str, Any]]) -> str:
        module_name = self._module_name_from_relpath((rows[0].get("file", "") if rows else ""))
        strategies: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            op_chain = list(row.get("op_chain", []) or [])
            target_key = ".".join(op_chain) if op_chain else str(row.get("op_id", "") or "")
            if not target_key:
                continue
            strategies[target_key] = self._native_strategy_payload(row, module_name)
        body: List[str] = [
            _NATIVE_BLOCK_BEGIN,
            "try:",
            "    import inspect as _aurora_native_inspect",
            "except Exception:",
            "    _aurora_native_inspect = None",
            "",
            "try:",
            "    from aurora_internal.aurora_evolved_surfaces import AuroraEvolvedSurfaceEngine as _AuroraEvolvedSurfaceEngine",
            "except Exception:",
            "    _AuroraEvolvedSurfaceEngine = None",
            "",
            "_AURORA_NATIVE_EVOLVED_ENGINE = None",
            "",
            "def _aurora_native_evolved_engine():",
            "    global _AURORA_NATIVE_EVOLVED_ENGINE",
            "    if _AURORA_NATIVE_EVOLVED_ENGINE is None and _AuroraEvolvedSurfaceEngine is not None:",
            "        _AURORA_NATIVE_EVOLVED_ENGINE = _AuroraEvolvedSurfaceEngine()",
            "    return _AURORA_NATIVE_EVOLVED_ENGINE",
            "",
            f"_AURORA_NATIVE_MODULE = {module_name!r}",
            "",
            "_AURORA_NATIVE_EVOLVED_ORIGINALS = {}",
            "_AURORA_NATIVE_EVOLVED_LAST = {}",
            f"_AURORA_NATIVE_STRATEGIES = {pprint.pformat(strategies, width=100, sort_dicts=True)}",
            "",
            "def _aurora_target_strategy(target_key):",
            "    return dict(_AURORA_NATIVE_STRATEGIES.get(str(target_key), {}) or {})",
            "",
            "def _aurora_target_feedback(target_key):",
            "    strategy = _aurora_target_strategy(target_key)",
            "    return dict(strategy.get('rewrite_feedback', {}) or {})",
            "",
            "def _aurora_assign_target(chain, value):",
            "    if not chain:",
            "        return False",
            "    if len(chain) == 1:",
            "        globals()[chain[0]] = value",
            "        return True",
            "    current = globals().get(chain[0])",
            "    if current is None:",
            "        return False",
            "    for attr in chain[1:-1]:",
            "        if not hasattr(current, attr):",
            "            return False",
            "        current = getattr(current, attr)",
            "    setattr(current, chain[-1], value)",
            "    return True",
            "",
            "def _aurora_get_target(chain):",
            "    if not chain:",
            "        return None",
            "    if len(chain) == 1:",
            "        return globals().get(chain[0])",
            "    current = globals().get(chain[0])",
            "    if current is None:",
            "        return None",
            "    for attr in chain[1:]:",
            "        if not hasattr(current, attr):",
            "            return None",
            "        current = getattr(current, attr)",
            "    return current",
            "",
            "def _aurora_bind_owner_attribute(owner_chain, attr_name, value):",
            "    owner = _aurora_get_target(owner_chain)",
            "    if owner is None or not attr_name:",
            "        return False",
            "    try:",
            "        setattr(owner, attr_name, value)",
            "        return True",
            "    except Exception:",
            "        return False",
            "",
            "def _aurora_store_reflection(target_key, reflection, args):",
            "    if not args:",
            "        return",
            "    owner = args[0]",
            "    if not hasattr(owner, '__dict__'):",
            "        return",
            "    current = getattr(owner, '_aurora_evolved_reflections', None)",
            "    if not isinstance(current, dict):",
            "        current = {}",
            "    current[str(target_key)] = reflection",
            "    try:",
            "        setattr(owner, '_aurora_evolved_reflections', current)",
            "    except Exception:",
            "        pass",
            "",
            "def _aurora_store_owner_state(attribute, target_key, value, args):",
            "    if not args:",
            "        return",
            "    owner = args[0]",
            "    if not hasattr(owner, '__dict__'):",
            "        return",
            "    current = getattr(owner, attribute, None)",
            "    if not isinstance(current, dict):",
            "        current = {}",
            "    current[str(target_key)] = value",
            "    try:",
            "        setattr(owner, attribute, current)",
            "    except Exception:",
            "        pass",
            "",
            "def _aurora_apply_constraint_genealogy_rewrite(target_key, result, reflection, args, kwargs):",
            "    strategy = _aurora_target_strategy(target_key)",
            "    feedback = _aurora_target_feedback(target_key)",
            "    bias = str(strategy.get('rewrite_bias', 'lineage_memory') or 'lineage_memory')",
            "    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')",
            "    effect_modes = list(strategy.get('effect_modes', []) or [])",
            "    _aurora_store_reflection(target_key, reflection, args)",
            "    _aurora_store_owner_state('_aurora_genealogy_strategy', target_key, strategy, args)",
            "    if isinstance(result, dict):",
            "        enriched = dict(result)",
            "        enriched['_aurora_evolved_reflection'] = reflection",
            "        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'constraint_genealogy') or 'constraint_genealogy')",
            "        enriched['_aurora_genealogy_strategy'] = strategy",
            "        enriched['_aurora_rewrite_feedback'] = feedback",
            "        enriched['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)",
            "        if bias == 'lineage_memory' or 'lineage_surface' in effect_modes:",
            "            enriched['lineage_memory'] = {",
            "                'coupling_signature': strategy.get('best_coupling_signature', ''),",
            "                'link_hits': int(strategy.get('link_hits', 0) or 0),",
            "                'ability_hits': int(strategy.get('ability_hits', 0) or 0),",
            "            }",
            "        if 'state_schema_change' in effect_modes or bias == 'lineage_memory':",
            "            enriched['state_transition_pressure'] = {",
            "                'pressure': float(strategy.get('genealogy_pressure', 0.0) or 0.0),",
            "                'persistence_tax_factor': float(strategy.get('persistence_tax_factor', 0.0) or 0.0),",
            "            }",
            "        if str(target_key).endswith('.summary') or 'chain_report' in str(target_key) or str(target_key).endswith('.to_dict'):",
            "            enriched['evolutionary_context'] = {",
            "                'coupling_signature': strategy.get('best_coupling_signature', ''),",
            "                'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),",
            "                'rewrite_bias': bias,",
            "                'cross_diversity_links': int(strategy.get('cross_diversity_links', 0) or 0),",
            "            }",
            "        if mode in {'expansive', 'integrative'}:",
            "            enriched['lineage_adaptation'] = {",
            "                'mode': mode,",
            "                'confidence': float(feedback.get('confidence', 0.0) or 0.0),",
            "                'trial_count': int(feedback.get('trial_count', 0) or 0),",
            "                'accepted_count': int(feedback.get('accepted_count', 0) or 0),",
            "                'adoption_count': int(feedback.get('adoption_count', 0) or 0),",
            "            }",
            "        if mode == 'conservative':",
            "            enriched['lineage_stability_guard'] = {",
            "                'rejected_count': int(feedback.get('rejected_count', 0) or 0),",
            "                'rejection_rate': float(feedback.get('rejection_rate', 0.0) or 0.0),",
            "                'timing_penalty': float(feedback.get('timing_penalty', 0.0) or 0.0),",
            "            }",
            "        return enriched",
            "    if result is None and isinstance(reflection, dict):",
            "        fallback = dict(reflection)",
            "        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'constraint_genealogy') or 'constraint_genealogy')",
            "        fallback['_aurora_genealogy_strategy'] = strategy",
            "        fallback['_aurora_rewrite_feedback'] = feedback",
            "        fallback['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)",
            "        fallback['lineage_adaptation_mode'] = mode",
            "        return fallback",
            "    _aurora_store_owner_state(",
            "        '_aurora_genealogy_scalar_observations',",
            "        target_key,",
            "        {",
            "            'result': result,",
            "            'strategy': strategy,",
            "            'reflection': reflection,",
            "        },",
            "        args,",
            "    )",
            "    return result",
            "",
            "def _aurora_apply_governance_rewrite(target_key, result, reflection, args, kwargs):",
            "    strategy = _aurora_target_strategy(target_key)",
            "    feedback = _aurora_target_feedback(target_key)",
            "    bias = str(strategy.get('rewrite_bias', 'governance_routing') or 'governance_routing')",
            "    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')",
            "    effect_modes = list(strategy.get('effect_modes', []) or [])",
            "    _aurora_store_reflection(target_key, reflection, args)",
            "    _aurora_store_owner_state('_aurora_governance_strategy', target_key, strategy, args)",
            "    if isinstance(result, dict):",
            "        enriched = dict(result)",
            "        enriched['_aurora_evolved_reflection'] = reflection",
            "        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'governance_gateway') or 'governance_gateway')",
            "        enriched['_aurora_genealogy_strategy'] = strategy",
            "        enriched['_aurora_rewrite_feedback'] = feedback",
            "        enriched['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)",
            "        enriched['governance_evolution_context'] = {",
            "            'coupling_signature': strategy.get('best_coupling_signature', ''),",
            "            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),",
            "            'rewrite_bias': bias,",
            "        }",
            "        if bias == 'governance_routing' or 'gateway_surface' in effect_modes:",
            "            enriched['governance_routing'] = {",
            "                'sustainability_score': float(strategy.get('sustainability_score', 0.0) or 0.0),",
            "                'representation_score': float(strategy.get('representation_score', 0.0) or 0.0),",
            "                'origin_activity': int(strategy.get('origin_activity', 0) or 0),",
            "            }",
            "        if 'state_schema_change' in effect_modes:",
            "            enriched['persistence_burden'] = {",
            "                'persistence_tax_factor': float(strategy.get('persistence_tax_factor', 0.0) or 0.0),",
            "                'inheritance_breach_count': int(strategy.get('inheritance_breach_count', 0) or 0),",
            "            }",
            "        if mode in {'expansive', 'integrative'}:",
            "            enriched['governance_adaptation'] = {",
            "                'mode': mode,",
            "                'confidence': float(feedback.get('confidence', 0.0) or 0.0),",
            "                'acceptance_rate': float(feedback.get('acceptance_rate', 0.0) or 0.0),",
            "                'timing_credit': float(feedback.get('timing_credit', 0.0) or 0.0),",
            "            }",
            "        if mode == 'conservative':",
            "            enriched['persistence_guard'] = {",
            "                'rejection_rate': float(feedback.get('rejection_rate', 0.0) or 0.0),",
            "                'timing_penalty': float(feedback.get('timing_penalty', 0.0) or 0.0),",
            "                'trial_count': int(feedback.get('trial_count', 0) or 0),",
            "            }",
            "        return enriched",
            "    if result is None and isinstance(reflection, dict):",
            "        fallback = dict(reflection)",
            "        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'governance_gateway') or 'governance_gateway')",
            "        fallback['_aurora_genealogy_strategy'] = strategy",
            "        fallback['_aurora_rewrite_feedback'] = feedback",
            "        fallback['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)",
            "        fallback['governance_evolution_context'] = {",
            "            'coupling_signature': strategy.get('best_coupling_signature', ''),",
            "            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),",
            "            'rewrite_bias': bias,",
            "        }",
            "        fallback['governance_adaptation_mode'] = mode",
            "        return fallback",
            "    _aurora_store_owner_state(",
            "        '_aurora_governance_evolution_state',",
            "        target_key,",
            "        {",
            "            'result': result,",
            "            'strategy': strategy,",
            "            'reflection': reflection,",
            "        },",
            "        args,",
            "    )",
            "    return result",
            "",
            "def _aurora_apply_perception_rewrite(target_key, result, reflection, args, kwargs):",
            "    strategy = _aurora_target_strategy(target_key)",
            "    feedback = _aurora_target_feedback(target_key)",
            "    bias = str(strategy.get('rewrite_bias', 'perceptual_synthesis') or 'perceptual_synthesis')",
            "    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')",
            "    effect_modes = list(strategy.get('effect_modes', []) or [])",
            "    _aurora_store_reflection(target_key, reflection, args)",
            "    _aurora_store_owner_state('_aurora_perception_strategy', target_key, strategy, args)",
            "    if isinstance(result, dict):",
            "        enriched = dict(result)",
            "        enriched['_aurora_evolved_reflection'] = reflection",
            "        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'perception_synthesis') or 'perception_synthesis')",
            "        enriched['_aurora_genealogy_strategy'] = strategy",
            "        enriched['_aurora_rewrite_feedback'] = feedback",
            "        enriched['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)",
            "        enriched['perception_evolution_context'] = {",
            "            'coupling_signature': strategy.get('best_coupling_signature', ''),",
            "            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),",
            "            'rewrite_bias': bias,",
            "        }",
            "        if bias == 'perceptual_synthesis' or 'adaptive_steering_change' in effect_modes:",
            "            enriched['perception_synthesis'] = {",
            "                'representation_score': float(strategy.get('representation_score', 0.0) or 0.0),",
            "                'ability_hits': int(strategy.get('ability_hits', 0) or 0),",
            "                'link_hits': int(strategy.get('link_hits', 0) or 0),",
            "            }",
            "        if 'interface_boundary_change' in effect_modes or 'gateway_surface' in effect_modes:",
            "            enriched['boundary_integration'] = {",
            "                'cross_diversity_links': int(strategy.get('cross_diversity_links', 0) or 0),",
            "                'coupling_similarity': float(strategy.get('coupling_similarity', 0.0) or 0.0),",
            "            }",
            "        if mode in {'expansive', 'integrative'}:",
            "            enriched['association_expansion'] = {",
            "                'mode': mode,",
            "                'confidence': float(feedback.get('confidence', 0.0) or 0.0),",
            "                'timing_credit': float(feedback.get('timing_credit', 0.0) or 0.0),",
            "                'acceptance_rate': float(feedback.get('acceptance_rate', 0.0) or 0.0),",
            "            }",
            "        if mode == 'conservative':",
            "            enriched['perception_stability'] = {",
            "                'rejection_rate': float(feedback.get('rejection_rate', 0.0) or 0.0),",
            "                'timing_penalty': float(feedback.get('timing_penalty', 0.0) or 0.0),",
            "                'trial_count': int(feedback.get('trial_count', 0) or 0),",
            "            }",
            "        return enriched",
            "    if result is None and isinstance(reflection, dict):",
            "        fallback = dict(reflection)",
            "        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'perception_synthesis') or 'perception_synthesis')",
            "        fallback['_aurora_genealogy_strategy'] = strategy",
            "        fallback['_aurora_rewrite_feedback'] = feedback",
            "        fallback['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)",
            "        fallback['perception_evolution_context'] = {",
            "            'coupling_signature': strategy.get('best_coupling_signature', ''),",
            "            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),",
            "            'rewrite_bias': bias,",
            "        }",
            "        if bias == 'perceptual_synthesis' or 'adaptive_steering_change' in effect_modes:",
            "            fallback['perception_synthesis'] = {",
            "                'representation_score': float(strategy.get('representation_score', 0.0) or 0.0),",
            "                'ability_hits': int(strategy.get('ability_hits', 0) or 0),",
            "                'link_hits': int(strategy.get('link_hits', 0) or 0),",
            "            }",
            "        fallback['perception_adaptation_mode'] = mode",
            "        return fallback",
            "    _aurora_store_owner_state(",
            "        '_aurora_perception_evolution_state',",
            "        target_key,",
            "        {",
            "            'result': result,",
            "            'strategy': strategy,",
            "            'reflection': reflection,",
            "        },",
            "        args,",
            "    )",
            "    return result",
            "",
            "def _aurora_apply_dimensional_rewrite(target_key, result, reflection, args, kwargs):",
            "    strategy = _aurora_target_strategy(target_key)",
            "    feedback = _aurora_target_feedback(target_key)",
            "    bias = str(strategy.get('rewrite_bias', 'dimensional_balancing') or 'dimensional_balancing')",
            "    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')",
            "    effect_modes = list(strategy.get('effect_modes', []) or [])",
            "    _aurora_store_reflection(target_key, reflection, args)",
            "    _aurora_store_owner_state('_aurora_dimensional_strategy', target_key, strategy, args)",
            "    if isinstance(result, dict):",
            "        enriched = dict(result)",
            "        enriched['_aurora_evolved_reflection'] = reflection",
            "        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'dimensional_balancing') or 'dimensional_balancing')",
            "        enriched['_aurora_genealogy_strategy'] = strategy",
            "        enriched['_aurora_rewrite_feedback'] = feedback",
            "        enriched['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)",
            "        enriched['dimensional_evolution_context'] = {",
            "            'coupling_signature': strategy.get('best_coupling_signature', ''),",
            "            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),",
            "            'rewrite_bias': bias,",
            "        }",
            "        if bias == 'dimensional_balancing' or 'cost_pressure_change' in effect_modes:",
            "            enriched['dimensional_balancing'] = {",
            "                'sustainability_score': float(strategy.get('sustainability_score', 0.0) or 0.0),",
            "                'persistence_tax_factor': float(strategy.get('persistence_tax_factor', 0.0) or 0.0),",
            "                'origin_activity': int(strategy.get('origin_activity', 0) or 0),",
            "            }",
            "        if 'temporal_orchestration_change' in effect_modes:",
            "            enriched['temporal_coordination'] = {",
            "                'signature': strategy.get('signature', ''),",
            "                'inheritance_breach_count': int(strategy.get('inheritance_breach_count', 0) or 0),",
            "            }",
            "        if mode in {'expansive', 'integrative'}:",
            "            enriched['balancing_momentum'] = {",
            "                'mode': mode,",
            "                'confidence': float(feedback.get('confidence', 0.0) or 0.0),",
            "                'timing_credit': float(feedback.get('timing_credit', 0.0) or 0.0),",
            "                'adoption_count': int(feedback.get('adoption_count', 0) or 0),",
            "            }",
            "        if mode == 'conservative':",
            "            enriched['dimensional_dampening'] = {",
            "                'rejection_rate': float(feedback.get('rejection_rate', 0.0) or 0.0),",
            "                'timing_penalty': float(feedback.get('timing_penalty', 0.0) or 0.0),",
            "                'trial_count': int(feedback.get('trial_count', 0) or 0),",
            "            }",
            "        return enriched",
            "    if result is None and isinstance(reflection, dict):",
            "        fallback = dict(reflection)",
            "        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'dimensional_balancing') or 'dimensional_balancing')",
            "        fallback['_aurora_genealogy_strategy'] = strategy",
            "        fallback['_aurora_rewrite_feedback'] = feedback",
            "        fallback['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)",
            "        fallback['dimensional_evolution_context'] = {",
            "            'coupling_signature': strategy.get('best_coupling_signature', ''),",
            "            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),",
            "            'rewrite_bias': bias,",
            "        }",
            "        if bias == 'dimensional_balancing' or 'cost_pressure_change' in effect_modes:",
            "            fallback['dimensional_balancing'] = {",
            "                'sustainability_score': float(strategy.get('sustainability_score', 0.0) or 0.0),",
            "                'persistence_tax_factor': float(strategy.get('persistence_tax_factor', 0.0) or 0.0),",
            "                'origin_activity': int(strategy.get('origin_activity', 0) or 0),",
            "            }",
            "        fallback['dimensional_adaptation_mode'] = mode",
            "        return fallback",
            "    _aurora_store_owner_state(",
            "        '_aurora_dimensional_evolution_state',",
            "        target_key,",
            "        {",
            "            'result': result,",
            "            'strategy': strategy,",
            "            'reflection': reflection,",
            "        },",
            "        args,",
            "    )",
            "    return result",
            "",
            "def _aurora_apply_result_rewrite(target_key, result, reflection, args, kwargs):",
            "    if _AURORA_NATIVE_MODULE == 'aurora_internal.constraint_genealogy':",
            "        return _aurora_apply_constraint_genealogy_rewrite(target_key, result, reflection, args, kwargs)",
            "    if _AURORA_NATIVE_MODULE == 'aurora_governance_persistence_gateway':",
            "        return _aurora_apply_governance_rewrite(target_key, result, reflection, args, kwargs)",
            "    if _AURORA_NATIVE_MODULE == 'aurora_expression_perception':",
            "        return _aurora_apply_perception_rewrite(target_key, result, reflection, args, kwargs)",
            "    if _AURORA_NATIVE_MODULE == 'aurora_dimensional_systems':",
            "        return _aurora_apply_dimensional_rewrite(target_key, result, reflection, args, kwargs)",
            "    _aurora_store_reflection(target_key, reflection, args)",
            "    strategy = _aurora_target_strategy(target_key)",
            "    feedback = _aurora_target_feedback(target_key)",
            "    contract = dict(strategy.get('contract_profile', {}) or {})",
            "    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')",
            "    if isinstance(result, dict):",
            "        enriched = dict(result)",
            "        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'generic') or 'generic')",
            "        enriched['_aurora_genealogy_strategy'] = strategy",
            "        enriched['_aurora_rewrite_feedback'] = feedback",
            "        enriched['_aurora_contract_profile'] = contract",
            "        enriched['_aurora_evolved_reflection'] = reflection",
            "        enriched['generic_adaptation'] = {",
            "            'mode': mode,",
            "            'confidence': float(feedback.get('confidence', 0.0) or 0.0),",
            "            'contract_mode': str(contract.get('contract_mode', 'unknown') or 'unknown'),",
            "            'return_hint': str(contract.get('return_hint', '') or ''),",
            "        }",
            "        return enriched",
            "    if result is None and isinstance(reflection, dict):",
            "        fallback = dict(reflection)",
            "        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'generic') or 'generic')",
            "        fallback['_aurora_genealogy_strategy'] = strategy",
            "        fallback['_aurora_rewrite_feedback'] = feedback",
            "        fallback['_aurora_contract_profile'] = contract",
            "        fallback['generic_adaptation_mode'] = mode",
            "        return fallback",
            "    if result is not None:",
            "        _aurora_store_owner_state(",
            "            '_aurora_generic_evolution_state',",
            "            target_key,",
            "            {",
            "                'result_type': type(result).__name__,",
            "                'contract_mode': str(contract.get('contract_mode', 'unknown') or 'unknown'),",
            "                'return_hint': str(contract.get('return_hint', '') or ''),",
            "                'adaptation_mode': mode,",
            "            },",
            "            args,",
            "        )",
            "    return result",
            "",
            "def _aurora_make_override(export_name, target_key):",
            "    original = _AURORA_NATIVE_EVOLVED_ORIGINALS.get(target_key)",
            "    def _override(*args, **kwargs):",
            "        result = None",
            "        if callable(original):",
            "            result = original(*args, **kwargs)",
            "        engine = _aurora_native_evolved_engine()",
            "        reflection = {",
            "            'available': False,",
            "            'reason': 'evolved_surface_engine_unavailable',",
            "            'target': target_key,",
            "        }",
            "        if engine is not None:",
            "            reflection = globals()[export_name]({'args_len': len(args), 'kwargs_keys': sorted(kwargs.keys())})",
            "        _AURORA_NATIVE_EVOLVED_LAST[target_key] = reflection",
            "        rewritten = _aurora_apply_result_rewrite(target_key, result, reflection, args, kwargs)",
            "        if rewritten is not None:",
            "            return rewritten",
            "        if result is not None:",
            "            return result",
            "        return reflection",
            "    _override.__name__ = str(target_key).split('.')[-1]",
            "    _override.__qualname__ = _override.__name__",
            "    if callable(original):",
            "        _override.__doc__ = getattr(original, '__doc__', None)",
            "        _override.__wrapped__ = original",
            "        if _aurora_native_inspect is not None:",
            "            try:",
            "                _override.__signature__ = _aurora_native_inspect.signature(original)",
            "            except Exception:",
            "                pass",
            "    return _override",
            "",
            "def _aurora_make_latent_binding(export_name, target_key):",
            "    def _binding(*args, **kwargs):",
            "        payload = kwargs.pop('payload', None)",
            "        if payload is None and args:",
            "            owner = args[0]",
            "            if hasattr(owner, '__dict__'):",
            "                payload = {",
            "                    'bound_target': target_key,",
            "                    'owner_type': type(owner).__name__,",
            "                    'owner_module': type(owner).__module__,",
            "                }",
            "            elif len(args) == 1:",
            "                payload = args[0]",
            "            else:",
            "                payload = {'bound_target': target_key, 'arg_count': len(args)}",
            "        result = globals()[export_name](payload=payload, **kwargs)",
            "        _AURORA_NATIVE_EVOLVED_LAST[target_key] = {'latent_binding_active': True, 'last_result_type': type(result).__name__}",
            "        if args:",
            "            _aurora_store_owner_state('_aurora_latent_bindings', target_key, result, args)",
            "        return result",
            "    _binding.__name__ = str(target_key).split('.')[-1]",
            "    _binding.__qualname__ = _binding.__name__",
            "    _binding.__doc__ = f'Latent evolved binding for {target_key}'",
            "    _binding._aurora_latent_binding_target = target_key",
            "    return _binding",
            "",
        ]
        exports: Dict[str, str] = {}
        overrides: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            export_name = str(row.get("native_export", "") or "")
            surface_method = str(row.get("surface_method", "") or "")
            op_id = str(row.get("op_id", "") or "")
            kind = str(row.get("kind", "") or "")
            body.extend([
                f"def {export_name}(payload=None, **kwargs):",
                "    engine = _aurora_native_evolved_engine()",
                "    if engine is None:",
                "        return {",
                f"            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': {op_id!r}, 'kind': {kind!r}",
                "        }",
                f"    return getattr(engine, {surface_method!r})(payload=payload, **kwargs)",
                "",
            ])
            exports[op_id] = export_name
            target_kind = str(row.get("target_kind", "") or "")
            op_chain = list(row.get("op_chain", []) or [])
            target_key = ".".join(op_chain)
            if self._can_activate_override(row) and op_chain:
                body.extend([
                    f"if _aurora_get_target({op_chain!r}) is not None:",
                    f"    _AURORA_NATIVE_EVOLVED_ORIGINALS[{target_key!r}] = _aurora_get_target({op_chain!r})",
                    f"    _aurora_assign_target({op_chain!r}, _aurora_make_override({export_name!r}, {target_key!r}))",
                    f"    _AURORA_NATIVE_EVOLVED_LAST[{target_key!r}] = {{'alignment_gap': {float(row.get('alignment_gap', 0.0) or 0.0)!r}, 'override_active': True}}",
                    "",
                ])
                overrides[op_id] = {
                    "target": target_key,
                    "mode": "callable_override",
                    "export": export_name,
                }
            elif self._can_bind_latent_projection(row) and op_chain:
                owner_chain = op_chain[:-1]
                leaf = op_chain[-1]
                body.extend([
                    f"_aurora_existing_binding = _aurora_get_target({owner_chain!r})",
                    f"if _aurora_existing_binding is not None:",
                    f"    _aurora_existing_attr = getattr(_aurora_existing_binding, {leaf!r}, None)",
                    f"    if _aurora_existing_attr is None or getattr(_aurora_existing_attr, '_aurora_latent_binding_target', '') == {target_key!r}:",
                    f"        _aurora_bind_owner_attribute({owner_chain!r}, {leaf!r}, _aurora_make_latent_binding({export_name!r}, {target_key!r}))",
                    f"        _AURORA_NATIVE_EVOLVED_LAST[{target_key!r}] = {{'latent_binding_active': True}}",
                    "",
                ])
                overrides[op_id] = {
                    "target": target_key,
                    "mode": "latent_binding",
                    "export": export_name,
                }
            elif kind == "reflection" and target_kind == "class" and op_chain:
                body.extend([
                    f"if _aurora_get_target({op_chain!r}) is not None:",
                    f"    setattr(_aurora_get_target({op_chain!r}), 'evolved_reflection', staticmethod({export_name}))",
                    f"    setattr(_aurora_get_target({op_chain!r}), '_aurora_alignment_gap', {float(row.get('alignment_gap', 0.0) or 0.0)!r})",
                    f"    setattr(_aurora_get_target({op_chain!r}), '_aurora_alignment_target_score', {float(row.get('alignment_target_score', 0.0) or 0.0)!r})",
                    "",
                ])
                overrides[op_id] = {
                    "target": target_key,
                    "mode": "class_reflection_hook",
                    "export": export_name,
                }
        body.append(f"AURORA_NATIVE_EVOLVED_EXPORTS = {pprint.pformat(exports, width=100, sort_dicts=True)}")
        body.append(f"AURORA_NATIVE_EVOLUTION_OVERRIDES = {pprint.pformat(overrides, width=100, sort_dicts=True)}")
        body.append(_NATIVE_BLOCK_END)
        return "\n".join(body) + "\n"

    def _build_native_projection_updates(self) -> Dict[str, Any]:
        state = self._load_descriptor_state()
        if state is None:
            return {"updates": {}, "details": [], "manifest": {}}
        updates: Dict[str, str] = {}
        details: List[Dict[str, Any]] = []
        projected: List[Dict[str, Any]] = []
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        ops_rows = [dict(row) for row in (state.get("operations", []) or []) if isinstance(row, dict)]
        alignment = self._development_alignment(ops_rows)
        genealogy = self._genealogy_strategy(ops_rows)

        for row in (state.get("latent_operations", []) or []):
            if not isinstance(row, dict) or not bool(row.get("implemented")):
                continue
            present = dict(row.get("present_representation", {}) or {})
            surface_method = str(present.get("method", "") or "")
            file_rel = self._clean_rel_path(row.get("file", ""))
            module_name = self._module_name_from_relpath(file_rel)
            hist = dict(row.get("developmental_effect_history", {}) or {})
            direct = dict(hist.get("direct_system_effects", {}) or {})
            if not surface_method or not file_rel:
                continue
            grouped.setdefault(file_rel, []).append({
                "op_id": str(row.get("op_id", "") or ""),
                "file": file_rel,
                "kind": "latent",
                "surface_method": surface_method,
                "op_chain": self._operation_chain(row.get("op_id", ""), module_name),
                "target_kind": str(row.get("kind", "") or ""),
                "constraints": list(row.get("constraints", []) or []),
                "effect_modes": list(direct.get("effect_modes", []) or []),
                "effect_phrases": list(direct.get("effect_phrases", []) or []),
                "surface_score": float(self._surface_score(row) or 0.0),
            })

        for row in (state.get("operations", []) or []):
            if not isinstance(row, dict):
                continue
            present = dict(row.get("current_evolved_representation", {}) or {})
            surface_method = str(present.get("method", "") or "")
            file_rel = self._clean_rel_path(row.get("file", ""))
            module_name = self._module_name_from_relpath(file_rel)
            op_id = str(row.get("op_id", "") or "")
            hist = dict(row.get("developmental_effect_history", {}) or {})
            direct = dict(hist.get("direct_system_effects", {}) or {})
            ripple = dict(hist.get("ripple_effects", {}) or {})
            if not surface_method or not file_rel:
                continue
            grouped.setdefault(file_rel, []).append({
                "op_id": op_id,
                "file": file_rel,
                "kind": "reflection",
                "surface_method": surface_method,
                "op_chain": self._operation_chain(op_id, module_name),
                "target_kind": str(row.get("kind", "") or ""),
                "alignment_gap": float((alignment.get(op_id, {}) or {}).get("alignment_gap", 0.0) or 0.0),
                "alignment_target_score": float(max(
                    (alignment.get(op_id, {}) or {}).get("module_peak_score", 0.0) or 0.0,
                    (alignment.get(op_id, {}) or {}).get("kind_peak_score", 0.0) or 0.0,
                )),
                "constraints": list(row.get("constraints", []) or []),
                "effect_modes": list(direct.get("effect_modes", []) or []),
                "effect_phrases": list(direct.get("effect_phrases", []) or []),
                "cross_diversity_links": int(ripple.get("cross_diversity_links", 0) or 0),
                "surface_score": float(self._surface_score(row) or 0.0),
                "genealogy_strategy": dict(genealogy.get(op_id, {}) or {}),
            })

        for file_rel, rows in grouped.items():
            abs_path = self._abs_path(file_rel)
            if not os.path.exists(abs_path):
                continue
            try:
                with open(abs_path, "r", encoding="utf-8") as fh:
                    original = fh.read()
            except Exception:
                continue
            base_text = self._strip_generated_block(original)
            used_names: set[str] = set()
            projected_rows: List[Dict[str, Any]] = []
            for row in rows:
                export_name = self._preferred_native_export_name(
                    row=row,
                    surface_method=str(row.get("surface_method", "") or ""),
                    kind=str(row.get("kind", "") or ""),
                    existing_text=base_text,
                    used_names=used_names,
                )
                projected_row = dict(row)
                projected_row["native_export"] = export_name
                projected_rows.append(projected_row)
                projected.append(dict(projected_row))
            block = self._native_wrapper_block(projected_rows)
            updates[abs_path] = base_text.rstrip() + "\n\n" + block
            details.append({
                "file": abs_path,
                "change": f"projected {len(projected_rows)} evolved surfaces into native module exports",
            })

        state_updated = self._update_descriptor_state_with_native_projections(state, projected)
        descriptor_path = self._abs_path(_DESCRIPTOR_STATE_REL)
        updates[descriptor_path] = json.dumps(state_updated, ensure_ascii=True, indent=2, sort_keys=True)
        details.append({
            "file": descriptor_path,
            "change": "recorded native evolved-surface projections and developmental alignment targets",
        })
        manifest = {
            "native_projection_files": len(grouped),
            "native_projection_count": len(projected),
            "active_evolution_overrides": sum(1 for row in projected if self._can_activate_override(row)),
            "latent_bindings": sum(1 for row in projected if self._can_bind_latent_projection(row)),
            "class_reflection_hooks": sum(1 for row in projected if str(row.get("kind", "") or "") == "reflection" and str(row.get("target_kind", "") or "") == "class"),
        }
        return {"updates": updates, "details": details, "manifest": manifest}

    def _latent_meta(self, row: Dict[str, Any]) -> Dict[str, Any]:
        op_id = str(row.get("op_id", "") or "")
        file_rel = self._clean_rel_path(row.get("file", ""))
        module_name = self._module_name_from_relpath(file_rel)
        origin_op_id = str(row.get("origin_op_id", "") or "")
        origin_chain = self._operation_chain(origin_op_id, module_name)
        hist = dict(row.get("developmental_effect_history", {}) or {})
        direct = dict(hist.get("direct_system_effects", {}) or {})
        constraints = list(row.get("constraints", []) or [])
        effect_modes = list(direct.get("effect_modes", []) or [])
        contract_profile = self._infer_contract_profile(
            module_name=module_name,
            chain=origin_chain,
            target_kind=str(row.get("kind", "") or ""),
            constraints=constraints,
            effect_modes=effect_modes,
        )
        return {
            "constraints": constraints,
            "effect_modes": effect_modes,
            "effect_phrases": list(direct.get("effect_phrases", []) or []),
            "file": file_rel,
            "kind": "latent",
            "latent_reason": str(row.get("latent_reason", "") or ""),
            "module": module_name,
            "op_id": op_id,
            "origin_chain": origin_chain,
            "origin_op_id": origin_op_id,
            "representation_kind": "promoted_latent_operation",
            "surface_score": round(self._surface_score(row), 6),
            "contract_profile": dict(contract_profile),
        }

    def _reflection_meta(
        self,
        row: Dict[str, Any],
        alignment: Optional[Dict[str, Any]] = None,
        genealogy: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        op_id = str(row.get("op_id", "") or "")
        file_rel = self._clean_rel_path(row.get("file", ""))
        module_name = self._module_name_from_relpath(file_rel)
        chain = self._operation_chain(op_id, module_name)
        hist = dict(row.get("developmental_effect_history", {}) or {})
        direct = dict(hist.get("direct_system_effects", {}) or {})
        ripple = dict(hist.get("ripple_effects", {}) or {})
        align = dict(alignment or {})
        gene = dict(genealogy or {})
        constraints = list(row.get("constraints", []) or [])
        effect_modes = list(direct.get("effect_modes", []) or [])
        contract_profile = self._infer_contract_profile(
            module_name=module_name,
            chain=chain,
            target_kind=str(row.get("kind", "") or ""),
            constraints=constraints,
            effect_modes=effect_modes,
        )
        return {
            "alignment_gap": float(align.get("alignment_gap", 0.0) or 0.0),
            "alignment_target_score": float(max(align.get("module_peak_score", 0.0) or 0.0, align.get("kind_peak_score", 0.0) or 0.0)),
            "genealogy_pressure": float(gene.get("genealogy_pressure", 0.0) or 0.0),
            "genealogy_signature": str(gene.get("signature", "") or ""),
            "genealogy_bias": str(gene.get("rewrite_bias", "") or "generic"),
            "coupling_similarity": float(gene.get("coupling_similarity", 0.0) or 0.0),
            "best_coupling_signature": str(gene.get("best_coupling_signature", "") or ""),
            "constraints": constraints,
            "cross_diversity_links": int(ripple.get("cross_diversity_links", 0) or 0),
            "effect_modes": effect_modes,
            "effect_phrases": list(direct.get("effect_phrases", []) or []),
            "file": file_rel,
            "kind": "reflection",
            "module": module_name,
            "op_chain": chain,
            "op_id": op_id,
            "representation_kind": "architectural_reflection_surface",
            "surface_score": round(self._surface_score(row), 6),
            "contract_profile": dict(contract_profile),
        }

    def _render_evolved_surfaces(
        self,
        latent_rows: List[Dict[str, Any]],
        reflection_rows: List[Dict[str, Any]],
        alignment: Optional[Dict[str, Dict[str, Any]]] = None,
        genealogy: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        registry: Dict[str, Dict[str, Any]] = {}
        latent_map: Dict[str, str] = {}
        reflection_map: Dict[str, str] = {}
        method_blocks: List[str] = []
        alignment = dict(alignment or {})
        genealogy = dict(genealogy or {})

        for row in latent_rows:
            op_id = str(row.get("op_id", "") or "")
            if not op_id:
                continue
            method_name = self._surface_method_name(op_id, kind="latent")
            meta = self._latent_meta(row)
            registry[method_name] = meta
            latent_map[op_id] = method_name
            method_blocks.append(
                f"    def {method_name}(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:\n"
                f"        meta = dict(self._registry.get({method_name!r}, {{}}) or {{}})\n"
                f"        return self._activate_surface({method_name!r}, meta, payload=payload, **kwargs)\n"
            )

        for row in reflection_rows:
            op_id = str(row.get("op_id", "") or "")
            if not op_id:
                continue
            method_name = self._surface_method_name(op_id, kind="reflection")
            meta = self._reflection_meta(row, alignment.get(op_id), genealogy.get(op_id))
            registry[method_name] = meta
            reflection_map[op_id] = method_name
            method_blocks.append(
                f"    def {method_name}(self, payload: Any = None, **kwargs: Any) -> Dict[str, Any]:\n"
                f"        meta = dict(self._registry.get({method_name!r}, {{}}) or {{}})\n"
                f"        return self._reflect_surface({method_name!r}, meta, payload=payload, **kwargs)\n"
            )

        module_text = self._module_template(registry, method_blocks, latent_map, reflection_map)
        manifest = {
            "latent_count": len(latent_map),
            "reflection_count": len(reflection_map),
            "method_count": int(len(registry)),
            "latent_methods": latent_map,
            "reflection_methods": reflection_map,
        }
        return {"module_text": module_text, "manifest": manifest}

    def _module_template(
        self,
        registry: Dict[str, Dict[str, Any]],
        method_blocks: List[str],
        latent_map: Dict[str, str],
        reflection_map: Dict[str, str],
    ) -> str:
        registry_literal = pprint.pformat(registry, width=100, sort_dicts=True)
        manifest_literal = pprint.pformat(
            {
                "latent_methods": latent_map,
                "reflection_methods": reflection_map,
                "method_count": len(registry),
            },
            width=100,
            sort_dicts=True,
        )
        methods = "\n".join(method_blocks).rstrip()
        if methods:
            methods = "\n" + methods + "\n"
        return f'''#!/usr/bin/env python3
"""
AURORA EVOLVED SURFACES
=======================
Generated from developmental lineage state.
Do not hand-edit generated methods; regenerate through the code autoevolver.
"""

from __future__ import annotations

import importlib
import inspect
import os
import time
from typing import Any, Dict, List, Optional


_SURFACE_REGISTRY: Dict[str, Dict[str, Any]] = {registry_literal}
_SURFACE_MANIFEST: Dict[str, Any] = {manifest_literal}


class AuroraEvolvedSurfaceEngine:
    def __init__(self, systems: Any = None, state_dir: Optional[str] = None):
        self.systems = systems
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.state_dir = os.path.abspath(state_dir or os.path.join(repo_root, "aurora_state"))
        self._registry = dict(_SURFACE_REGISTRY)
        self._events: List[Dict[str, Any]] = []
        self._surface_state: Dict[str, Any] = {{"activations": [], "reflections": []}}

    def list_capabilities(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for name in sorted(self._registry.keys()):
            meta = dict(self._registry.get(name, {{}}) or {{}})
            out.append({{
                "name": name,
                "kind": str(meta.get("kind", "") or ""),
                "constraints": list(meta.get("constraints", []) or []),
                "op_id": str(meta.get("op_id", "") or ""),
                "representation_kind": str(meta.get("representation_kind", "") or ""),
                "surface_score": float(meta.get("surface_score", 0.0) or 0.0),
            }})
        return out

    def describe_capability(self, name: str) -> Dict[str, Any]:
        return dict(self._registry.get(str(name), {{}}) or {{}})

    def capability_report(self) -> Dict[str, Any]:
        latent = 0
        reflection = 0
        for meta in self._registry.values():
            kind = str((meta or {{}}).get("kind", "") or "")
            if kind == "latent":
                latent += 1
            elif kind == "reflection":
                reflection += 1
        return {{
            "available": bool(self._registry),
            "surface_count": int(len(self._registry)),
            "latent_count": int(latent),
            "reflection_count": int(reflection),
            "recent_events": list(self._events[-10:]),
        }}

    def lineage_manifest(self) -> Dict[str, Any]:
        return dict(_SURFACE_MANIFEST)

    def _system_summary(self) -> Dict[str, Any]:
        systems = self.systems
        if systems is None:
            return {{"available": False, "active_components": [], "axis_pressure": {{}}}}
        active: List[str] = []
        for name in (
            "contract", "lattice", "dimensional", "perception", "identity", "simulation",
            "chamber", "genealogy", "checkpoint", "aurora", "autonomy", "drive_sync",
        ):
            if getattr(systems, name, None) is not None:
                active.append(name)
        axis_pressure: Dict[str, float] = {{}}
        chamber = getattr(systems, "chamber", None)
        if chamber is not None:
            try:
                st = chamber.status()
                axis_pressure = {{
                    ax: float(v)
                    for ax, v in (st.get("intent_pressure", {{}}) or {{}}).items()
                }}
            except Exception:
                pass
        return {{"available": True, "active_components": active, "axis_pressure": axis_pressure}}

    def _resolve_origin(self, meta: Dict[str, Any]) -> Any:
        module_name = str(meta.get("module", "") or "").strip()
        chain = list(meta.get("origin_chain") or meta.get("op_chain") or [])
        if not module_name:
            return None
        try:
            module = importlib.import_module(module_name)
        except Exception:
            return None
        target: Any = module
        for attr in chain:
            if not attr or not hasattr(target, attr):
                return None
            target = getattr(target, attr)
        return target

    def _invoke_origin(self, origin: Any, payload: Any, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        if not callable(origin):
            return {{"called": False, "reason": "origin_not_callable"}}
        try:
            sig = inspect.signature(origin)
        except Exception:
            sig = None
        try:
            if sig is None:
                if payload is not None:
                    return {{"called": True, "result": origin(payload, **kwargs)}}
                return {{"called": True, "result": origin(**kwargs)}}
            params = list(sig.parameters.values())
            accepts_var = any(p.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD) for p in params)
            positional = [p for p in params if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)]
            required = [p for p in positional if p.default is inspect._empty]
            if not params:
                return {{"called": True, "result": origin()}}
            if payload is not None and (accepts_var or positional):
                return {{"called": True, "result": origin(payload, **kwargs)}}
            if not required:
                return {{"called": True, "result": origin(**kwargs)}}
        except Exception as exc:
            return {{"called": False, "reason": f"origin_error: {{exc}}"}}
        return {{"called": False, "reason": "origin_signature_not_satisfied"}}

    def _record_event(self, event: Dict[str, Any]) -> None:
        self._events.append(dict(event))
        if len(self._events) > 64:
            self._events = self._events[-64:]

    def _log_pressure_event(self, record: Dict[str, Any]) -> None:
        """Append a compact pressure record to surface_pressure_log.jsonl."""
        try:
            import json as _json
            log_path = os.path.join(self.state_dir, "surface_pressure_log.jsonl")
            entry = {{
                "surface":        str(record.get("method", "") or ""),
                "op_id":          str(record.get("op_id", "") or ""),
                "kind":           str(record.get("kind", "") or ""),
                "signature":      str(record.get("signature", "") or ""),
                "expected_axes":  list(record.get("expected_axes", []) or []),
                "effect_modes":   list(record.get("effect_modes", []) or []),
                "effect_phrases": list(record.get("effect_phrases", []) or []),
                "surface_score":  float(record.get("surface_score", 0.0) or 0.0),
                "genealogy_pressure": float(record.get("genealogy_pressure", 0.0) or 0.0),
                "axis_pressure":  dict(record.get("axis_pressure_snapshot", {{}}) or {{}}),
                "timestamp":      float(record.get("timestamp", 0.0) or 0.0),
            }}
            with open(log_path, "a", encoding="utf-8") as _f:
                _f.write(_json.dumps(entry) + "\\n")
            try:
                if os.path.getsize(log_path) > 32 * 1024 * 1024:
                    with open(log_path, "rb") as _src:
                        _src.seek(-8 * 1024 * 1024, os.SEEK_END)
                        _src.readline()
                        _tail = _src.read()
                    with open(log_path, "wb") as _dst:
                        _dst.write(_tail)
            except Exception:
                pass
        except Exception:
            pass

    def _activation_record(self, method_name: str, meta: Dict[str, Any], payload: Any, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        summary = self._system_summary()
        _CONSTRAINT_AXIS = {{"existence": "X", "temporal": "T", "energy": "N", "boundary": "B", "agency": "A"}}
        expected_axes = list(dict.fromkeys(
            _CONSTRAINT_AXIS.get(str(c).strip().lower(), "")
            for c in (meta.get("constraints", []) or [])
            if _CONSTRAINT_AXIS.get(str(c).strip().lower())
        ))
        return {{
            "method": method_name,
            "kind": str(meta.get("kind", "") or ""),
            "op_id": str(meta.get("op_id", "") or ""),
            "signature": str(meta.get("signature", "") or ""),
            "constraints": list(meta.get("constraints", []) or []),
            "expected_axes": expected_axes,
            "contract_profile": dict(meta.get("contract_profile", {{}}) or {{}}),
            "effect_modes": list(meta.get("effect_modes", []) or []),
            "effect_phrases": list(meta.get("effect_phrases", []) or []),
            "surface_score": float(meta.get("surface_score", 0.0) or 0.0),
            "genealogy_pressure": float(meta.get("genealogy_pressure", 0.0) or 0.0),
            "timestamp": float(time.time()),
            "payload_present": payload is not None,
            "kwargs_keys": sorted(kwargs.keys()),
            "system_summary": summary,
            "axis_pressure_snapshot": dict(summary.get("axis_pressure", {{}}) or {{}}),
        }}

    def _activate_surface(self, method_name: str, meta: Dict[str, Any], payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        record = self._activation_record(method_name, meta, payload, dict(kwargs))
        record["latent_reason"] = str(meta.get("latent_reason", "") or "")
        record["effect_phrases"] = list(meta.get("effect_phrases", []) or [])
        origin = self._resolve_origin(meta)
        invocation = self._invoke_origin(origin, payload, dict(kwargs))
        record["origin"] = {{
            "module": str(meta.get("module", "") or ""),
            "op_id": str(meta.get("origin_op_id", "") or ""),
            "resolved": origin is not None,
            **invocation,
        }}
        effects = set(str(x) for x in (meta.get("effect_modes", []) or []))
        if "state_schema_change" in effects:
            self._surface_state["last_state_change"] = {{"method": method_name, "at": record["timestamp"]}}
        if "gateway_surface" in effects or "latent_route_surface" in effects:
            routed = list(self._surface_state.get("routed_packets", []) or [])
            routed.append({{"method": method_name, "payload": payload, "at": record["timestamp"]}})
            self._surface_state["routed_packets"] = routed[-32:]
        if "lineage_surface" in effects and getattr(self.systems, "genealogy", None) is not None:
            genealogy = getattr(self.systems, "genealogy")
            record["genealogy_state"] = {{
                "abilities": int(len(getattr(genealogy, "abilities", {{}}) or {{}})),
                "links": int(len(getattr(genealogy, "links", {{}}) or {{}})),
            }}
        activations = list(self._surface_state.get("activations", []) or [])
        activations.append(record)
        self._surface_state["activations"] = activations[-64:]
        self._record_event({{"type": "activation", "method": method_name, "timestamp": record["timestamp"]}})
        self._log_pressure_event(record)
        return record

    def _reflect_surface(self, method_name: str, meta: Dict[str, Any], payload: Any = None, **kwargs: Any) -> Dict[str, Any]:
        record = self._activation_record(method_name, meta, payload, dict(kwargs))
        origin = self._resolve_origin(meta)
        record["origin"] = {{
            "module": str(meta.get("module", "") or ""),
            "op_id": str(meta.get("op_id", "") or ""),
            "resolved": origin is not None,
            "callable": bool(callable(origin)),
        }}
        if bool(kwargs.pop("call_origin", False)):
            record["origin_call"] = self._invoke_origin(origin, payload, dict(kwargs))
        reflections = list(self._surface_state.get("reflections", []) or [])
        reflections.append(record)
        self._surface_state["reflections"] = reflections[-64:]
        self._record_event({{"type": "reflection", "method": method_name, "timestamp": record["timestamp"]}})
        self._log_pressure_event(record)
        return record

    def __getattr__(self, name: str):
        # Fallback for any evolved surface method that was renamed or dropped by a mutation.
        # Prevents AttributeError from crashing callers — degrades gracefully instead.
        if name.startswith('__'):
            raise AttributeError(name)
        # Try partial-name match: find the closest surviving reflect_ method
        _all_methods = [m for m in vars(type(self)) if m.startswith('reflect_')]
        candidates = [m for m in _all_methods if m.startswith(name) or name.startswith(m)]
        if candidates:
            best = max(candidates, key=len)
            return object.__getattribute__(self, best)
        def _unavailable(payload=None, **kwargs):
            return {{'available': False, 'reason': f'evolved_surface_method_renamed: {{name}}',
                    'op_id': name, 'kind': 'reflection'}}
        return _unavailable
{methods}

__all__ = ["AuroraEvolvedSurfaceEngine"]
'''

    def _update_descriptor_state(self, state: Dict[str, Any], render: Dict[str, Any], module_path: str) -> Dict[str, Any]:
        out = json.loads(json.dumps(state))
        manifest = dict(render.get("manifest", {}) or {})
        module_rel = os.path.relpath(module_path, self.repo_root).replace("\\", "/")
        module_name = self._module_name_from_relpath(module_rel)

        latent_methods = dict(manifest.get("latent_methods", {}) or {})
        reflection_methods = dict(manifest.get("reflection_methods", {}) or {})

        for row in out.get("latent_operations", []) or []:
            if not isinstance(row, dict):
                continue
            op_id = str(row.get("op_id", "") or "")
            row["developmental_effect_history"] = self._ensure_developmental_effect_history(
                row,
                self._module_name_from_relpath(self._clean_rel_path(row.get("file", ""))),
                "latent",
            )
            method_name = latent_methods.get(op_id)
            if not method_name:
                continue
            row["implemented"] = True
            row["present_representation"] = {
                "module": module_name,
                "file": module_rel,
                "class": "AuroraEvolvedSurfaceEngine",
                "method": method_name,
                "kind": "promoted_latent_operation",
            }
            hist = dict(row.get("developmental_effect_history", {}) or {})
            hist["present_representation"] = dict(row["present_representation"])
            row["developmental_effect_history"] = hist

        ops_rows = list(out.get("operations", []) or [])
        alignment = self._development_alignment(ops_rows)
        genealogy = self._genealogy_strategy(ops_rows)

        for row in out.get("operations", []) or []:
            if not isinstance(row, dict):
                continue
            op_id = str(row.get("op_id", "") or "")
            row["developmental_effect_history"] = self._ensure_developmental_effect_history(
                row,
                self._module_name_from_relpath(self._clean_rel_path(row.get("file", ""))),
                "operation",
            )
            row["developmental_alignment"] = dict(alignment.get(op_id, {}) or {})
            row["genealogy_strategy"] = dict(genealogy.get(op_id, {}) or {})
            method_name = reflection_methods.get(op_id)
            hist = dict(row.get("developmental_effect_history", {}) or {})
            hist["genealogy_strategy"] = dict(genealogy.get(op_id, {}) or {})
            if not method_name:
                row.pop("current_evolved_representation", None)
                hist.pop("current_evolved_representation", None)
                row["developmental_effect_history"] = hist
                continue
            row["current_evolved_representation"] = {
                "module": module_name,
                "file": module_rel,
                "class": "AuroraEvolvedSurfaceEngine",
                "method": method_name,
                "kind": "architectural_reflection_surface",
            }
            hist["current_evolved_representation"] = dict(row["current_evolved_representation"])
            row["developmental_effect_history"] = hist

        summary = dict(out.get("summary", {}) or {})
        summary["evolved_surfaces_materialized"] = True
        summary["promoted_latent_operations"] = int(len(latent_methods))
        summary["architectural_reflection_surfaces"] = int(len(reflection_methods))
        summary["evolved_surface_module"] = module_rel
        summary["developmental_alignment_tracked"] = int(len(alignment))
        summary["growth_reflection_rows"] = int(sum(
            1
            for row in (list(out.get("operations", []) or []) + list(out.get("latent_operations", []) or []))
            if isinstance(row, dict) and bool(dict(row.get("developmental_effect_history", {}) or {}).get("growth_reflection_complete"))
        ))
        out["summary"] = summary
        out["evolved_surface_manifest"] = {
            "module": module_name,
            "file": module_rel,
            **manifest,
        }
        return out

    def _update_descriptor_state_with_native_projections(
        self,
        state: Dict[str, Any],
        projected: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        out = json.loads(json.dumps(state))
        by_op: Dict[str, Dict[str, Any]] = {}
        for row in projected:
            if not isinstance(row, dict):
                continue
            op_id = str(row.get("op_id", "") or "")
            file_rel = self._clean_rel_path(row.get("file", ""))
            export_name = str(row.get("native_export", "") or "")
            if not op_id or not file_rel or not export_name:
                continue
            by_op[op_id] = {
                "file": file_rel,
                "module": self._module_name_from_relpath(file_rel),
                "export": export_name,
                "kind": str(row.get("kind", "") or ""),
                "mode": (
                    "callable_override" if self._can_activate_override(row)
                    else (
                        "latent_binding" if self._can_bind_latent_projection(row)
                        else (
                            "class_reflection_hook"
                            if str(row.get("kind", "") or "") == "reflection" and str(row.get("target_kind", "") or "") == "class"
                            else "projection_export"
                        )
                    )
                ),
                "source_surface_method": str(row.get("surface_method", "") or ""),
                "target_kind": str(row.get("target_kind", "") or ""),
                "op_chain": list(row.get("op_chain", []) or []),
                "rewrite_profile": self._rewrite_profile_for_module(self._module_name_from_relpath(file_rel)),
                "alignment_gap": float(row.get("alignment_gap", 0.0) or 0.0),
                "alignment_target_score": float(row.get("alignment_target_score", 0.0) or 0.0),
                "constraints": list(row.get("constraints", []) or []),
                "effect_modes": list(row.get("effect_modes", []) or []),
                "effect_phrases": list(row.get("effect_phrases", []) or []),
                "genealogy_strategy": dict(row.get("genealogy_strategy", {}) or {}),
            }

        ops_rows = list(out.get("operations", []) or [])
        alignment = self._development_alignment(ops_rows)
        genealogy = self._genealogy_strategy(ops_rows)

        for row in out.get("latent_operations", []) or []:
            if not isinstance(row, dict):
                continue
            op_id = str(row.get("op_id", "") or "")
            row["developmental_effect_history"] = self._ensure_developmental_effect_history(
                row,
                self._module_name_from_relpath(self._clean_rel_path(row.get("file", ""))),
                "latent",
            )
            native = by_op.get(op_id)
            if not native:
                row.pop("native_projection", None)
                hist = dict(row.get("developmental_effect_history", {}) or {})
                hist.pop("native_projection", None)
                row["developmental_effect_history"] = hist
                continue
            row["native_projection"] = dict(native)
            hist = dict(row.get("developmental_effect_history", {}) or {})
            hist["native_projection"] = dict(native)
            row["developmental_effect_history"] = hist

        for row in out.get("operations", []) or []:
            if not isinstance(row, dict):
                continue
            op_id = str(row.get("op_id", "") or "")
            row["developmental_effect_history"] = self._ensure_developmental_effect_history(
                row,
                self._module_name_from_relpath(self._clean_rel_path(row.get("file", ""))),
                "operation",
            )
            row["developmental_alignment"] = dict(alignment.get(op_id, {}) or {})
            row["genealogy_strategy"] = dict(genealogy.get(op_id, {}) or {})
            native = by_op.get(op_id)
            if native:
                row["native_projection"] = dict(native)
                hist = dict(row.get("developmental_effect_history", {}) or {})
                hist["native_projection"] = dict(native)
                hist["genealogy_strategy"] = dict(genealogy.get(op_id, {}) or {})
                row["developmental_effect_history"] = hist
            else:
                row.pop("native_projection", None)
                hist = dict(row.get("developmental_effect_history", {}) or {})
                hist.pop("native_projection", None)
                hist["genealogy_strategy"] = dict(genealogy.get(op_id, {}) or {})
                row["developmental_effect_history"] = hist

        summary = dict(out.get("summary", {}) or {})
        summary["native_surface_projections"] = int(len(by_op))
        summary["developmental_alignment_tracked"] = int(len(alignment))
        summary["active_evolution_overrides"] = int(sum(1 for spec in by_op.values() if str(spec.get("mode", "") or "") == "callable_override"))
        summary["latent_bindings"] = int(sum(1 for spec in by_op.values() if str(spec.get("mode", "") or "") == "latent_binding"))
        summary["class_reflection_hooks"] = int(sum(1 for spec in by_op.values() if str(spec.get("mode", "") or "") == "class_reflection_hook"))
        summary["growth_reflection_rows"] = int(sum(
            1
            for row in (list(out.get("operations", []) or []) + list(out.get("latent_operations", []) or []))
            if isinstance(row, dict) and bool(dict(row.get("developmental_effect_history", {}) or {}).get("growth_reflection_complete"))
        ))
        out["summary"] = summary
        out["native_surface_manifest"] = {
            "projection_count": int(len(by_op)),
            "files": sorted({spec["file"] for spec in by_op.values()}),
        }
        return out

    def _apply_telemetry_probe(self, path: str, content: str) -> Tuple[str, str]:
        # Concrete, functional evolution for facade stack:
        # add quick helper APIs so downstream systems can call chamber/snapshot directly.
        if os.path.basename(path) != "aurora_code_evolution_stack.py":
            return content, ""
        if "def build_code_evolution_chamber(" in content:
            return content, ""

        insert = """

def build_code_evolution_chamber(repo_root: str, output_dir: str = None, config: Any = None) -> CodeEvolutionChamber:
    \"\"\"Convenience constructor used by runtime and tooling.\"\"\"
    return CodeEvolutionChamber(repo_root=repo_root, output_dir=output_dir, config=config)


def quick_code_snapshot(repo_root: str, target_files = None) -> Dict[str, Any]:
    \"\"\"One-call code pressure snapshot for diagnostics and mutation planning.\"\"\"
    evaluator = CodeConstraintEvaluator(repo_root=repo_root)
    snap = evaluator.snapshot(target_files=target_files)
    return snap.to_dict()
"""
        if "__all__ = [" in content:
            updated = content.replace("\n__all__ = [", insert + "\n\n__all__ = [", 1)
        else:
            updated = content + insert
        if '"build_code_evolution_chamber"' not in updated:
            updated = updated.replace(
                "__all__ = [",
                "__all__ = [\n    \"build_code_evolution_chamber\",\n    \"quick_code_snapshot\",",
                1,
            )
        return updated, "added helper APIs for chamber construction and quick snapshots"

    def _apply_agency_surface(self, path: str, content: str) -> Tuple[str, str]:
        # Minimal agency-surface mutation: expose a tiny probe API in runtime facade.
        if os.path.basename(path) != "aurora_code_evolution_stack.py":
            return content, ""
        if "def code_evolution_capabilities(" in content:
            return content, ""
        insert = """

def code_evolution_capabilities() -> Dict[str, Any]:
    \"\"\"Describe currently exposed code evolution primitives.\"\"\"
    return {
        "has_chamber": True,
        "has_snapshot": True,
        "has_mutation_trace": True,
        "has_pressure_vec": True,
    }
"""
        if "__all__ = [" in content:
            updated = content.replace("\n__all__ = [", insert + "\n\n__all__ = [", 1)
        else:
            updated = content + insert
        if '"code_evolution_capabilities"' not in updated:
            updated = updated.replace(
                "__all__ = [",
                "__all__ = [\n    \"code_evolution_capabilities\",",
                1,
            )
        return updated, "added capability surface helper"
