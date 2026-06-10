"""
aurora_second_gen.py
─────────────────────────────────────────────────────────────────────────────
Second-generation evolution injector.

The descriptor pool (operation_descriptors.json) is the input layer for the
CodeAutoEvolver. Currently only hand-written source operations feed it.
Evolved surfaces sit in _SURFACE_REGISTRY but never loop back as evolvable
inputs — so generation depth is stuck at 1.

This module reads _SURFACE_REGISTRY from aurora_evolved_surfaces.py and
synthesizes valid operation descriptor entries for each surface that is not
already in the pool. On the next evolution cycle, the evolver can reflect on
these surfaces exactly as it reflects on base operations — producing surfaces
of surfaces.

Key differences for gen-2 descriptors:
  - kind = "function" (evolved surfaces are methods, treated as functions)
  - file = "aurora_internal/aurora_evolved_surfaces.py"
  - rewrite_bias = "lineage_memory" (highest-priority bias lane in evolver)
  - genealogy_pressure inherited from the source surface
  - cross_diversity_links = ability_hits + link_hits (from surface card)
  - _generation = 2 marker for tracking
─────────────────────────────────────────────────────────────────────────────
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple

_DESCRIPTOR_STATE_REL  = "aurora_state/operation_descriptors.json"
_EVOLVED_SURFACE_FILE  = "aurora_internal/aurora_evolved_surfaces.py"

_CONSTRAINT_TO_AXIS = {
    "existence": "X",
    "temporal":  "T",
    "energy":    "N",
    "boundary":  "B",
    "agency":    "A",
}

_AXES = ("X", "T", "N", "B", "A")


class SecondGenEvolutionInjector:
    """
    Reads evolved surfaces from _SURFACE_REGISTRY and injects them back into
    the operation descriptor pool as generation-2 evolution candidates.

    Usage:
        injector = SecondGenEvolutionInjector(repo_root="/path/to/AuroraO")
        result = injector.inject()
        # result: {"added": 12, "skipped": 148, "pool_size": 2057}
    """

    def __init__(self, repo_root: str):
        self.repo_root = os.path.abspath(repo_root)

    # ── public ────────────────────────────────────────────────────────────────

    def inject(self, min_surface_score: float = 0.30) -> Dict[str, Any]:
        """
        Inject all evolved surfaces above min_surface_score into the descriptor
        pool as generation-2 candidates.

        Already-present op_ids are skipped without writing anything.
        Returns a summary dict.
        """
        registry = self._load_registry()
        if not registry:
            return {"added": 0, "skipped": 0, "error": "registry empty or unavailable"}

        pool_path = os.path.join(self.repo_root, _DESCRIPTOR_STATE_REL)
        state = self._load_pool(pool_path)
        if state is None:
            return {"added": 0, "skipped": 0, "error": f"pool not found: {pool_path}"}

        ops: List[Dict[str, Any]] = list(state.get("operations", []) or [])
        existing_ids = {str(r.get("op_id", "")) for r in ops}

        added = 0
        skipped_score = 0
        skipped_dup = 0

        for surface_name, meta in registry.items():
            score = float(meta.get("surface_score", 0.0) or 0.0)
            if score < min_surface_score:
                skipped_score += 1
                continue

            gen2_op_id = f"evolved.{surface_name}"
            if gen2_op_id in existing_ids:
                skipped_dup += 1
                continue

            descriptor = self._surface_to_descriptor(surface_name, meta)
            ops.append(descriptor)
            existing_ids.add(gen2_op_id)
            added += 1

        if added > 0:
            state["operations"] = ops
            summary = dict(state.get("summary", {}) or {})
            summary["second_gen_injected"] = int(sum(
                1 for r in ops if r.get("_generation") == 2
            ))
            summary["second_gen_last_update"] = float(time.time())
            state["summary"] = summary
            self._save_pool(pool_path, state)

        return {
            "added":          added,
            "skipped_dup":    skipped_dup,
            "skipped_score":  skipped_score,
            "pool_size":      len(ops),
            "registry_size":  len(registry),
        }

    def status(self) -> Dict[str, Any]:
        """Return counts of gen-2 entries currently in the pool."""
        pool_path = os.path.join(self.repo_root, _DESCRIPTOR_STATE_REL)
        state = self._load_pool(pool_path)
        if state is None:
            return {"available": False}
        ops = list(state.get("operations", []) or [])
        gen2 = [r for r in ops if r.get("_generation") == 2]
        return {
            "available":     True,
            "pool_size":     len(ops),
            "gen2_count":    len(gen2),
            "base_count":    len(ops) - len(gen2),
        }

    # ── internals ─────────────────────────────────────────────────────────────

    def _load_registry(self) -> Dict[str, Dict[str, Any]]:
        try:
            import importlib
            importlib.invalidate_caches()
            mod = importlib.import_module("aurora_internal.aurora_evolved_surfaces")
            mod = importlib.reload(mod)
            reg = getattr(mod, "_SURFACE_REGISTRY", None)
            if isinstance(reg, dict):
                return dict(reg)
        except Exception:
            pass
        return {}

    def _load_pool(self, path: str) -> Optional[Dict[str, Any]]:
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, dict) else None
        except Exception:
            return None

    def _save_pool(self, path: str, state: Dict[str, Any]) -> None:
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(state, fh, indent=2, sort_keys=True, ensure_ascii=True)
        except Exception:
            pass

    def _surface_to_descriptor(
        self,
        surface_name: str,
        meta: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Synthesize a generation-2 operation descriptor from a surface registry entry.
        """
        # pull fields from registry entry
        sig          = str(meta.get("genealogy_signature", "") or meta.get("signature", "") or "")
        constraints  = list(meta.get("constraints", []) or [])
        effect_modes = list(meta.get("effect_modes",  []) or [])
        effect_phrases = list(meta.get("effect_phrases", []) or [])
        gpressure    = float(meta.get("genealogy_pressure", 0.0) or 0.0)
        s_score      = float(meta.get("surface_score",     0.0) or 0.0)
        align_gap    = float(meta.get("alignment_gap",     0.0) or 0.0)
        ability_hits = int(meta.get("ability_hits",  0) or 0)
        link_hits    = int(meta.get("link_hits",     0) or 0)
        kind_raw     = str(meta.get("kind", "reflection") or "reflection")
        op_id_src    = str(meta.get("op_id", surface_name) or surface_name)

        cross_links = ability_hits + link_hits

        # axis weights from signature
        axis_weights = self._weights_from_sig(sig, constraints)
        dom_ax = max(axis_weights, key=axis_weights.get, default="X")  # type: ignore[arg-type]
        axes_present = [ax for ax in _AXES if axis_weights.get(ax, 0) > 0.0]

        gen2_op_id = f"evolved.{surface_name}"
        contract = dict(meta.get("contract_profile", {}) or {})
        doc_hint  = str(contract.get("doc_hint", "") or "")

        effect_desc = (
            doc_hint or f"{kind_raw} of '{op_id_src}' — gen-2 evolution candidate"
        )

        return {
            "op_id":       gen2_op_id,
            "kind":        "function",
            "file":        _EVOLVED_SURFACE_FILE,
            "line":        0,
            "constraints": constraints,

            "genealogy_strategy": {
                "signature":               sig,
                "genealogy_pressure":      gpressure,
                "ability_hits":            ability_hits,
                "link_hits":               link_hits,
                "rewrite_bias":            "lineage_memory",   # highest-priority bias lane
                "alignment_gap":           align_gap,
                "best_coupling_signature": sig,
                "coupling_similarity":     1.0,
                "sustainability_score":    s_score,
                "representation_score":    s_score * 0.6,
                "origin_activity":         1,
                "persistence_tax_factor":  1.0 + gpressure,
                "inheritance_breach_count": 0,
            },

            "developmental_alignment": {
                "alignment_gap":     align_gap,
                "current_score":     s_score,
                "needs_alignment":   align_gap >= 0.15,
                "kind":              "function",
                "module":            "aurora_internal.aurora_evolved_surfaces",
                "kind_peak_score":   s_score,
                "module_peak_score": s_score,
                "cross_diversity_links": cross_links,
            },

            "developmental_effect_history": {
                "developmental_summary": {
                    "system_impact_score":   s_score,
                    "reflection_strength":   gpressure,
                    "growth_reflected":      True,
                    "lineage_kind":          "evolved_surface",
                    "generation":            2,
                },
                "ripple_effects": {
                    "cross_diversity_links":           cross_links,
                    "derived_from_origin_descendants": link_hits,
                    "origin_module":    "aurora_internal.aurora_evolved_surfaces",
                    "origin_owner":     "aurora_evolved_surfaces",
                    "propagated_modules":    ["aurora_internal.aurora_evolved_surfaces"],
                    "propagated_subsystems": ["evolved_surfaces"],
                    "growth_events": [{
                        "stage":       "gen2_candidate",
                        "lineage_kind": "evolved_surface",
                        "target_kind":  "function",
                        "module":       "aurora_internal.aurora_evolved_surfaces",
                    }],
                },
                "direct_system_effects": {
                    "effect_modes":   effect_modes,
                    "effect_phrases": effect_phrases or [effect_desc],
                    "growth_chain":   [surface_name, op_id_src],
                    "required_system_changes": [
                        f"lineage_registration:evolved_surfaces",
                        f"gen2_reflection:{surface_name}",
                    ],
                    "system_effects": [
                        f"{surface_name} contributes gen-2 evolutionary lineage",
                        f"signature {sig} deepens through second-generation reflection",
                    ],
                },
                "genealogy_strategy": {
                    "signature":          sig,
                    "genealogy_pressure": gpressure,
                    "rewrite_bias":       "lineage_memory",
                },
                "growth_lineage": {
                    "constraints":   constraints,
                    "lineage_kind":  "evolved_surface",
                    "module":        "aurora_internal.aurora_evolved_surfaces",
                    "op_chain":      [surface_name],
                    "present_in_system": True,
                    "target_kind":   "function",
                },
                "growth_reflection_complete": True,
            },

            "probabilistic_descriptor": {
                "axis_weights":              axis_weights,
                "axis_weights_all":          axis_weights,
                "dominance_axis":            dom_ax,
                "dominant_probability":      axis_weights.get(dom_ax, 0.2),
                "dominance_level":           "moderate" if gpressure >= 0.5 else "soft",
                "dominance_margin":          0.1,
                "dominance_ratio":           2.0,
                "secondary_probability":     0.2,
                "dual_state":                False,
                "dual_state_threshold":      0.2,
                "placement_axes":            axes_present,
                "classification_confidence": min(1.0, s_score + 0.1),
                "classification_scale":      1.0 + gpressure,
                "conceptual_behavior_class": f"gen-2 {kind_raw} — {sig} lineage",
                "causation_questions": {
                    "primary":   "What does this evolved behavior enable at depth?",
                    "secondary": "Which pressure pattern does this deepest lineage serve?",
                },
                "unused_constraint_axis":   "",
                "unused_constraint_weight": 0.0,
            },

            "deterministic_placement": {
                "dominance_axis":    dom_ax,
                "dominant_axis":     dom_ax,
                "dominance_level":   "moderate",
                "dominance_margin":  0.1,
                "dominance_ratio":   2.0,
                "secondary_axis":    axes_present[1] if len(axes_present) > 1 else dom_ax,
                "classification_scale": 1.0 + gpressure,
                "primary_slot":      self._primary_slot(axes_present),
                "root_a":            f"NC:{axes_present[0]}>{axes_present[0]}" if axes_present else "",
                "root_b":            f"NC:{axes_present[1]}>{axes_present[1]}" if len(axes_present) > 1 else "",
                "lineage_stage":     "descendant",
                "lineage_link": {
                    "parent":   op_id_src,
                    "children": [],
                    "cross_diversity_link_count": cross_links,
                },
                "unused_constraint_axis":   "",
                "unused_constraint_weight": 0.0,
            },

            "variant_projection_top": self._nc_projections(axes_present, axis_weights),

            "_generation":   2,
            "_source_surface": surface_name,
            "_injected_at":  float(time.time()),
        }

    def _weights_from_sig(
        self, sig: str, constraints: List[str]
    ) -> Dict[str, float]:
        """
        Parse 'N^2*B^2' into normalized axis weights.
        Falls back to uniform weight across constraint axes.
        """
        counts: Dict[str, int] = {}
        for part in str(sig or "").split("*"):
            part = part.strip()
            if "^" in part:
                ax, n_str = part.split("^", 1)
                try:
                    counts[ax.strip()] = int(float(n_str.strip()))
                except ValueError:
                    pass
            elif part and part in _AXES:
                counts[part] = counts.get(part, 0) + 1

        if not counts:
            # fallback: uniform across constraint axes
            ax_list = [_CONSTRAINT_TO_AXIS[c] for c in constraints if c in _CONSTRAINT_TO_AXIS]
            if ax_list:
                w = round(1.0 / len(ax_list), 6)
                counts = {ax: 1 for ax in ax_list}

        total = sum(counts.values())
        if total == 0:
            return {ax: 0.0 for ax in _AXES}

        return {ax: round(counts.get(ax, 0) / total, 6) for ax in _AXES}

    def _primary_slot(self, axes: List[str]) -> str:
        if len(axes) >= 2:
            return f"NC:{axes[0]}>{axes[1]}×NC:{axes[1]}>{axes[0]}"
        if axes:
            return f"NC:{axes[0]}>{axes[0]}×NC:{axes[0]}>{axes[0]}"
        return ""

    def _nc_projections(
        self,
        axes: List[str],
        weights: Dict[str, float],
    ) -> List[Dict[str, Any]]:
        """Compute top NC channel slot projections from axis weights."""
        if not axes:
            return []
        entries = []
        for row_ax in axes:
            for col_ax in axes:
                w = weights.get(row_ax, 0.0) * weights.get(col_ax, 0.0)
                if w <= 0:
                    continue
                entries.append({
                    "row":    f"NC:{row_ax}>{row_ax}",
                    "col":    f"NC:{row_ax}>{col_ax}",
                    "slot":   f"NC:{row_ax}>{row_ax}×NC:{row_ax}>{col_ax}",
                    "weight": round(w, 8),
                })
        entries.sort(key=lambda e: -e["weight"])
        return entries[:12]


if __name__ == "__main__":
    import sys
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
    injector = SecondGenEvolutionInjector(root)
    result = injector.inject()
    print(json.dumps(result, indent=2))
