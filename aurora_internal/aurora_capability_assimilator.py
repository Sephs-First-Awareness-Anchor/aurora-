"""
aurora_capability_assimilator.py
─────────────────────────────────────────────────────────────────────────────
Wires new capabilities into the genealogy fossil record and dream training
curriculum so every evolution layer is known to the training system.

Three registration pathways:

  1. Frontier ops (ExistenceBoundaryAgencyGate etc.)
     → register_manual_code_assimilation()
     Each covers a 3-axis combo that was completely absent from the descriptor
     pool. The genealogy now tracks them as new abilities.

  2. Gen-2 evolved surfaces
     → register_code_evolution_outcome()
     Evolved surfaces are code evolution outcomes that were accepted (they
     passed the autoevolver's simulation gate before being written).

  3. Compound axes (from AxisEmergenceDetector)
     → register_manual_code_assimilation()
     Each new compound axis channel is a structural capability that emerged
     from observed pressure co-occurrence.

  4. Dream curriculum seeding
     → FailPointLedger.record_fail() for under-represented dimensions
     Dimensions that map to the new capability spaces get seed fail signals
     so the dream curriculum prioritises training sessions that exercise them.

Deduplication:
  All methods are idempotent — already-registered abilities are skipped.
  A lightweight bloom-set is persisted at aurora_state/assimilated_ids.json.
─────────────────────────────────────────────────────────────────────────────
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any, Dict, List, Optional, Set, Tuple

_ASSIMILATED_REL = "aurora_state/assimilated_ids.json"

_CONSTRAINT_TO_AXIS = {
    "existence": "X",
    "temporal":  "T",
    "energy":    "N",
    "boundary":  "B",
    "agency":    "A",
}

# Which dream dimensions best capture each new frontier axis combo
_FRONTIER_DIMENSIONS: Dict[str, List[str]] = {
    "ExistenceBoundaryAgencyGate":      ["adaptive_strategy_selection", "boundary_calibration"],
    "TemporalEnergyBoundaryScheduler":  ["coherence_maintenance",       "boundary_calibration"],
    "TemporalEnergyAgencyPacer":        ["adaptive_strategy_selection", "context_carryover"],
    "EnergyBoundaryAgencySelector":     ["adaptive_strategy_selection", "semantic_precision"],
}

# Dimensions that map to compound/emergent capabilities (low fail count → seed)
_EMERGENCE_DIMENSIONS = ["adaptive_strategy_selection", "semantic_precision", "perspective_integration"]


class CapabilityAssimilator:
    """
    Registers all new capabilities into the genealogy and dream curriculum.

    Usage:
        assimilator = CapabilityAssimilator(repo_root)
        result = assimilator.assimilate_all(genealogy, fail_ledger=ledger)
    """

    def __init__(self, repo_root: str):
        self.repo_root = os.path.abspath(repo_root)
        self._assimilated: Set[str] = self._load_assimilated()

    # ── public ────────────────────────────────────────────────────────────────

    def assimilate_all(
        self,
        genealogy: Any,
        fail_ledger: Any = None,
    ) -> Dict[str, Any]:
        """
        Run all assimilation steps. Safe to call multiple times.

        genealogy:   ConstraintGenealogyLogger instance
        fail_ledger: FailPointLedger instance (optional — skipped if None)
        """
        r_frontier  = self.assimilate_frontier_ops(genealogy)
        r_gen2      = self.assimilate_gen2_surfaces(genealogy)
        r_compounds = self.assimilate_compound_axes(genealogy)
        r_curriculum = (
            self.seed_curriculum(fail_ledger)
            if fail_ledger is not None
            else {"seeded": 0}
        )

        total_new = (
            r_frontier.get("registered", 0) +
            r_gen2.get("registered", 0) +
            r_compounds.get("registered", 0)
        )
        if total_new > 0:
            self._save_assimilated()

        return {
            "frontier":   r_frontier,
            "gen2":       r_gen2,
            "compounds":  r_compounds,
            "curriculum": r_curriculum,
            "total_new":  total_new,
        }

    def assimilate_frontier_ops(self, genealogy: Any) -> Dict[str, Any]:
        """
        Register the 4 frontier operation classes into the genealogy
        using register_manual_code_assimilation().
        """
        if not hasattr(genealogy, "register_manual_code_assimilation"):
            return {"registered": 0, "error": "method_not_found"}

        try:
            from aurora_internal.aurora_frontier_ops import _FRONTIER_CLASSES  # type: ignore
        except Exception as exc:
            return {"registered": 0, "error": str(exc)}

        registered = 0
        skipped    = 0
        for cls in _FRONTIER_CLASSES:
            cls_name    = cls.__name__
            assim_id    = f"frontier_op:{cls_name}"
            if assim_id in self._assimilated:
                skipped += 1
                continue

            constraints = list(cls.CONSTRAINTS)  # type: ignore[attr-defined]
            axes = [_CONSTRAINT_TO_AXIS[c] for c in constraints if c in _CONSTRAINT_TO_AXIS]
            sig  = "*".join(f"{ax}^2" for ax in axes)
            dominant_ax = axes[0] if axes else "X"

            payload = {
                "change_id":        f"frontier_{cls_name.lower()}",
                "constraints":      constraints,
                "dominant_axis":    dominant_ax,
                "target_files":     ["aurora_internal/aurora_frontier_ops.py"],
                "target_modules":   ["aurora_internal.aurora_frontier_ops"],
                "rewrite_profile":  "dimensional_balancing",
                "axis_signature":   sig,
                "purpose_lane":     "intelligence",
                "source":           "frontier_capability_seeding",
                "change_kind":      "new_capability",
            }
            try:
                result = genealogy.register_manual_code_assimilation(payload)
                if result.get("registered", True) is not False:
                    self._assimilated.add(assim_id)
                    registered += 1
                else:
                    skipped += 1
            except Exception:
                skipped += 1

        return {"registered": registered, "skipped": skipped}

    def assimilate_gen2_surfaces(self, genealogy: Any) -> Dict[str, Any]:
        """
        Register all gen-2 evolved surfaces into the genealogy as code
        evolution outcomes via register_code_evolution_outcome().
        Only surfaces with surface_score >= 0.30 are registered.
        """
        if not hasattr(genealogy, "register_code_evolution_outcome"):
            return {"registered": 0, "error": "method_not_found"}

        registry = self._load_surface_registry()
        if not registry:
            return {"registered": 0, "skipped": 0, "reason": "registry_empty"}

        registered = 0
        skipped    = 0
        for surface_name, meta in registry.items():
            s_score  = float(meta.get("surface_score", 0.0) or 0.0)
            if s_score < 0.30:
                skipped += 1
                continue

            assim_id = f"gen2_surface:{surface_name}"
            if assim_id in self._assimilated:
                skipped += 1
                continue

            constraints  = list(meta.get("constraints", []) or [])
            gpressure    = float(meta.get("genealogy_pressure", 0.0) or 0.0)
            effect_modes = list(meta.get("effect_modes", []) or [])
            sig          = str(meta.get("genealogy_signature", "") or meta.get("signature", "") or "")
            kind_raw     = str(meta.get("kind", "reflection") or "reflection")

            payload = {
                "mutation_id":         f"gen2_{surface_name}",
                "constraints":         constraints,
                "operator_key":        "architectural_reflection",
                "accepted":            True,
                "changed_files":       ["aurora_internal/aurora_evolved_surfaces.py"],
                "target_files":        ["aurora_internal/aurora_evolved_surfaces.py"],
                "target_modules":      ["aurora_internal.aurora_evolved_surfaces"],
                "score":               s_score,
                "avg_fitness":         gpressure,
                "genealogy_pressure":  gpressure,
                "change_count":        1,
                "compile_failures":    0,
                "conflicts_delta":     0.0,
                "apply_duration_s":    0.001,
                "agency_time_credit":  min(1.0, gpressure),
                "temporal_overhead_penalty": 0.0,
                "rewrite_profile":     "lineage_memory",
                "effect_modes":        effect_modes,
            }
            try:
                result = genealogy.register_code_evolution_outcome(payload)
                if result.get("registered", True) is not False:
                    self._assimilated.add(assim_id)
                    registered += 1
                else:
                    skipped += 1
            except Exception:
                skipped += 1

        return {"registered": registered, "skipped": skipped, "total_in_registry": len(registry)}

    def assimilate_compound_axes(self, genealogy: Any) -> Dict[str, Any]:
        """
        Register any newly emerged compound axes into the genealogy.
        """
        if not hasattr(genealogy, "register_manual_code_assimilation"):
            return {"registered": 0, "error": "method_not_found"}

        compounds = self._load_compound_axes()
        if not compounds:
            return {"registered": 0, "skipped": 0}

        registered = 0
        skipped    = 0
        for compound_key, data in compounds.items():
            assim_id = f"compound_axis:{compound_key}"
            if assim_id in self._assimilated:
                skipped += 1
                continue

            axes       = list(data.get("axes", []) or [])
            co_occ     = float(data.get("co_occurrence", 0.0) or 0.0)
            generation = int(data.get("generation", 1) or 1)

            # map axis letters back to constraint names
            axis_to_constraint = {v: k for k, v in _CONSTRAINT_TO_AXIS.items()}
            constraints = [axis_to_constraint.get(ax, ax.lower()) for ax in axes]
            sig = "*".join(f"{ax}^2" for ax in axes)
            dominant_ax = axes[0] if axes else "X"

            payload = {
                "change_id":       f"compound_axis_{compound_key}",
                "constraints":     constraints,
                "dominant_axis":   dominant_ax,
                "target_files":    ["aurora_state/compound_axes.json"],
                "target_modules":  ["aurora_internal.aurora_axis_emergence"],
                "rewrite_profile": "perceptual_synthesis",
                "axis_signature":  sig,
                "purpose_lane":    "intelligence",
                "source":          "axis_emergence",
                "change_kind":     f"compound_axis_gen{generation}",
            }
            try:
                result = genealogy.register_manual_code_assimilation(payload)
                if result.get("registered", True) is not False:
                    self._assimilated.add(assim_id)
                    registered += 1
                else:
                    skipped += 1
            except Exception:
                skipped += 1

        return {"registered": registered, "skipped": skipped}

    def seed_curriculum(self, fail_ledger: Any) -> Dict[str, Any]:
        """
        Seed the dream curriculum with training priorities for the new
        capability dimensions. Only seeds dimensions that have very low
        fail counts (< 5) — avoids polluting well-trained dimensions.

        fail_ledger: FailPointLedger instance
        """
        if not hasattr(fail_ledger, "record_fail"):
            return {"seeded": 0, "error": "method_not_found"}

        seed_id = "curriculum_seed:frontier_and_emergence"
        if seed_id in self._assimilated:
            return {"seeded": 0, "reason": "already_seeded"}

        seeded = 0

        # seed frontier op dimensions
        for cls_name, dimensions in _FRONTIER_DIMENSIONS.items():
            for dim in dimensions:
                try:
                    rec = getattr(fail_ledger, "_records", {}).get(dim)
                    current_count = int(getattr(rec, "fail_count", 0) or 0) if rec else 0
                    if current_count < 5:
                        # inject a moderate-severity signal to activate training
                        fail_ledger.record_fail(
                            dimension=dim,
                            severity=0.55,
                            example={
                                "conversation_id": f"frontier_seed_{cls_name}_{dim}",
                                "user_turns": [
                                    f"[CAPABILITY SEED] {cls_name} requires training on {dim}. "
                                    f"New axis combination unlocked — needs integration."
                                ],
                                "aurora_turns": ["[capability not yet exercised]"],
                                "scores": {dim: 0.55},
                                "tags": ["frontier_capability_seed", f"cls:{cls_name}"],
                            }
                        )
                        seeded += 1
                except Exception:
                    pass

        # seed emergence dimensions (always low count — compound axes just emerged)
        for dim in _EMERGENCE_DIMENSIONS:
            try:
                rec = getattr(fail_ledger, "_records", {}).get(dim)
                current_count = int(getattr(rec, "fail_count", 0) or 0) if rec else 0
                if current_count < 5:
                    fail_ledger.record_fail(
                        dimension=dim,
                        severity=0.45,
                        example={
                            "conversation_id": f"emergence_seed_{dim}",
                            "user_turns": [
                                f"[EMERGENCE SEED] New compound axis space opened — "
                                f"{dim} training needed to integrate compound pressure patterns."
                            ],
                            "aurora_turns": ["[compound capability not yet expressed]"],
                            "scores": {dim: 0.45},
                            "tags": ["compound_axis_seed", f"dim:{dim}"],
                        }
                    )
                    seeded += 1
            except Exception:
                pass

        if seeded > 0:
            self._assimilated.add(seed_id)
            try:
                fail_ledger.save()
            except Exception:
                pass

        return {"seeded": seeded}

    # ── helpers ───────────────────────────────────────────────────────────────

    def _load_surface_registry(self) -> Dict[str, Any]:
        try:
            import importlib
            importlib.invalidate_caches()
            mod = importlib.import_module("aurora_internal.aurora_evolved_surfaces")
            mod = importlib.reload(mod)
            reg = getattr(mod, "_SURFACE_REGISTRY", None)
            return dict(reg) if isinstance(reg, dict) else {}
        except Exception:
            return {}

    def _load_compound_axes(self) -> Dict[str, Any]:
        path = os.path.join(self.repo_root, "aurora_state", "compound_axes.json")
        if not os.path.exists(path):
            return {}
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _load_assimilated(self) -> Set[str]:
        path = os.path.join(self.repo_root, _ASSIMILATED_REL)
        if not os.path.exists(path):
            return set()
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            return set(data) if isinstance(data, list) else set()
        except Exception:
            return set()

    def _save_assimilated(self) -> None:
        path = os.path.join(self.repo_root, _ASSIMILATED_REL)
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(sorted(self._assimilated), fh, indent=2)
        except Exception:
            pass
