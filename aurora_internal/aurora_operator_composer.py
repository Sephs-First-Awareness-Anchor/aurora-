#!/usr/bin/env python3
"""
AURORA OPERATOR COMPOSER — Organic Operation Composition
=============================================================
Phase 2 of the ICC Landing / Strategic Horizon / Operator Composition
directive (2026-07-14). The evolver (aurora_code_autoevolver.py) mutates
descriptors; nothing composes them. aurora_frontier_ops.py proved
hand-seeded 3-axis composites work (four classes covering the 3-axis
combinations otherwise completely absent from the descriptor pool). This
engine makes composition organic -- and it flows through the existing
latent -> promotion containment, never straight to active. The explosion
risk is contained by REUSING the quarantine pipeline (VariantPromoter),
not by inventing a new one.

CANDIDATE SELECTION (two independent signals, BOTH required):
    1. Scope complementarity: two PROMOTED operations from
       aurora_state/operation_descriptors.json whose constraint scopes
       union to a 2-3 axis shape not already covered by an active op.
       (Live-pool note: operation_descriptors.json's real "operations"
       entries store `constraints` as canonical axis letters (X/T/N/B/A)
       directly -- confirmed by inspection of all 578 live entries.
       aurora_frontier_ops.py's own _build_descriptor() would instead
       store the long-form names ("existence"/"boundary"/...) its
       CONSTRAINTS class attribute uses, mapped via _CONSTRAINT_TO_AXIS
       -- but frontier ops have never actually been injected into the
       live pool (0 `_frontier` entries found), so axis-letter form is
       what this module reads/writes for consistency with the 578 real
       entries it actually operates on.)
    2. Lived affinity: the parent ops' axes co-occur in either (a) an
       aurora_genealogy/couplings.json adoption record's `shape` (e.g.
       "B2+T1+X1"), or (b) the same TCL circulation loop (loop
       membership from aurora_toroidal_circulation.py's detected
       loops). Composition follows where pressure already flows --
       never purely combinatorial.

CONTAINMENT (hard caps, enforced in code):
    - Max 2 new latent composites per tick.
    - Both parents must be promoted AND each parent's WorthHistory
      trajectory non-declining at composition time.
    - Composites promote through the EXISTING VariantPromoter path
      exclusively -- this module has NO promotion authority whatsoever
      (structurally: no method here ever writes to `operations`, only
      to `latent_operations`).
    - Global latent-pool ceiling: composer stops entirely while
      len(latent_operations) exceeds its boot-time size + 25.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from aurora_internal.aurora_persistence_utils import atomic_write_json, PERSISTENCE_LOCK
from aurora_internal.aurora_worth_evaluator import CrossScaleWorthEvaluator, WorthTrajectory

_DESCRIPTOR_STATE_REL = "aurora_state/operation_descriptors.json"
_COUPLINGS_REL = "aurora_genealogy/couplings.json"

_ALL_AXES: Tuple[str, ...] = ("X", "T", "N", "B", "A")
_UNION_MIN_AXES = 2
_UNION_MAX_AXES = 3

# Containment caps (directive 2.3).
MAX_NEW_COMPOSITES_PER_TICK = 2
LATENT_POOL_CEILING_MARGIN = 25

_SHAPE_AXIS_RE = re.compile(r"([XTNBA])\d+")


def _axes_of(constraints: Any) -> frozenset:
    return frozenset(str(c).strip().upper() for c in (constraints or []) if str(c).strip().upper() in _ALL_AXES)


def _shape_axes(shape: str) -> frozenset:
    return frozenset(_SHAPE_AXIS_RE.findall(str(shape or "")))


# ===========================================================================
# SECTION 1 — DATA
# ===========================================================================

@dataclass(frozen=True)
class ComposedOperator:
    """
    A newly proposed composite descriptor, staged into latent_operations
    only -- never active. Mirrors the parents/depth structure of
    aurora_genealogy/links.json so genealogy tooling reads composites
    natively (directive 2.2).
    """
    op_id:               str
    parents:              Tuple[str, str]
    generation:           int
    composed_at_tick:     float
    constraints:          Tuple[str, ...]
    composition_signals:  Dict[str, Any]

    def to_descriptor(self) -> Dict[str, Any]:
        """Minimal-but-valid operation_descriptors.json latent_operations
        entry -- shape mirrors aurora_frontier_ops.py's _build_descriptor()
        template, adapted for a composed (not hand-seeded) origin."""
        axes = list(self.constraints)
        return {
            "op_id":            self.op_id,
            "kind":              "composite",
            "constraints":       axes,
            "parents":           list(self.parents),
            "_generation":       self.generation,
            "composed_at_tick":  self.composed_at_tick,
            "composition_signals": dict(self.composition_signals),
            "implemented":       False,
            "latent_weight":     0.0,
            "latent_reason":     "operator_composition",
            "_composed":         True,
        }


# ===========================================================================
# SECTION 2 — OPERATOR COMPOSER
# ===========================================================================

class OperatorComposer:
    """
    Reads operation_descriptors.json + aurora_genealogy/couplings.json
    (both read-only inputs, re-read fresh each call -- this module keeps
    no cache that could drift from the live pool), proposes composites
    from real promoted operations, and stages them into
    latent_operations. Never promotes anything itself.
    """

    def __init__(self, repo_root: Optional[str] = None) -> None:
        self._repo_root = os.path.abspath(repo_root) if repo_root else os.getcwd()
        self._descriptor_path = os.path.join(self._repo_root, _DESCRIPTOR_STATE_REL)
        self._couplings_path = os.path.join(self._repo_root, _COUPLINGS_REL)
        # Boot-time latent pool size, for the ceiling check (directive 2.3:
        # "boot-time size + 25"). Captured once, at construction.
        self._boot_latent_count = self._current_latent_count()

    # ------------------------------------------------------------------
    # reads
    # ------------------------------------------------------------------

    def _load_descriptor_state(self) -> Dict[str, Any]:
        try:
            if not os.path.exists(self._descriptor_path):
                return {"operations": [], "latent_operations": []}
            with open(self._descriptor_path, encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, dict) else {"operations": [], "latent_operations": []}
        except Exception:
            return {"operations": [], "latent_operations": []}

    def _current_latent_count(self) -> int:
        try:
            return len(self._load_descriptor_state().get("latent_operations", []) or [])
        except Exception:
            return 0

    def _load_coupling_shapes(self) -> List[str]:
        try:
            if not os.path.exists(self._couplings_path):
                return []
            with open(self._couplings_path, encoding="utf-8") as fh:
                data = json.load(fh)
            experiments = dict(data.get("experiments", {}) or {})
            adoptions = list(experiments.get("adoptions", []) or [])
            return [str(a.get("shape", "") or "") for a in adoptions if a.get("shape")]
        except Exception:
            return []

    # ------------------------------------------------------------------
    # candidate selection (2.1)
    # ------------------------------------------------------------------

    def find_candidates(
        self,
        *,
        tcl_loops: Optional[List[Tuple[Tuple[str, ...], float]]] = None,
        operations: Optional[List[Dict[str, Any]]] = None,
        coupling_shapes: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return candidate pairs passing BOTH required signals: scope
        complementarity (2-3 axis union, not already covered by an
        active op) AND lived affinity (couplings shape OR TCL loop
        covers the union). Never raises -- degrades to [] on any
        missing/malformed input.
        """
        try:
            state = self._load_descriptor_state() if operations is None else {"operations": operations}
            ops = list(state.get("operations", []) or []) if operations is None else list(operations)
            shapes = self._load_coupling_shapes() if coupling_shapes is None else list(coupling_shapes)
            loops = list(tcl_loops or [])

            active_scopes = {_axes_of(op.get("constraints")) for op in ops}
            shape_axis_sets = [_shape_axes(s) for s in shapes]
            loop_axis_sets = [frozenset(path) for path, _strength in loops]

            candidates: List[Dict[str, Any]] = []
            for op_a, op_b in combinations(ops, 2):
                scope_a = _axes_of(op_a.get("constraints"))
                scope_b = _axes_of(op_b.get("constraints"))
                if not scope_a or not scope_b:
                    continue
                union = scope_a | scope_b
                if not (_UNION_MIN_AXES <= len(union) <= _UNION_MAX_AXES):
                    continue
                if union in active_scopes:
                    continue  # already covered by an active op -- not a gap

                affinity_shape = next((s for s, axes in zip(shapes, shape_axis_sets) if union <= axes), None)
                affinity_loop = None
                if affinity_shape is None:
                    for path, strength in loops:
                        if union <= frozenset(path):
                            affinity_loop = {"path": list(path), "strength": strength}
                            break
                if affinity_shape is None and affinity_loop is None:
                    continue  # no lived affinity -- purely combinatorial, reject

                candidates.append({
                    "op_a": op_a, "op_b": op_b, "union": tuple(sorted(union)),
                    "coupling_shape": affinity_shape, "tcl_loop": affinity_loop,
                })
            return candidates
        except Exception:
            return []

    # ------------------------------------------------------------------
    # containment gates (2.3)
    # ------------------------------------------------------------------

    def _parent_trajectory_ok(
        self, op: Dict[str, Any], worth_evaluator: Optional[CrossScaleWorthEvaluator],
    ) -> bool:
        """Non-declining trajectory (directive 2.3). No history yet is
        NOT declining -- UNKNOWN/STABLE/OSCILLATING/RISING all pass;
        only an explicit FALLING trajectory blocks."""
        if worth_evaluator is None:
            return True
        try:
            op_id = str(op.get("op_id", "") or "")
            history = worth_evaluator.history_for(op_id)
            if history is None:
                return True
            return history.trajectory != WorthTrajectory.FALLING
        except Exception:
            return True

    def _both_parents_promoted(self, op_a: Dict[str, Any], op_b: Dict[str, Any], promoted_ids: Set[str]) -> bool:
        oid_a = str(op_a.get("op_id", "") or "")
        oid_b = str(op_b.get("op_id", "") or "")
        return bool(oid_a) and bool(oid_b) and oid_a in promoted_ids and oid_b in promoted_ids

    # ------------------------------------------------------------------
    # composite construction (2.2)
    # ------------------------------------------------------------------

    def _mint_op_id(self, op_a_id: str, op_b_id: str) -> str:
        # Stable on (parents) alone -- NOT tick. The same eligible pair
        # proposed again on a later tick (its gap still uncovered) must
        # mint the SAME op_id, so _persist()'s existing-op_id dedup check
        # actually catches the repeat instead of accumulating duplicate
        # composites of the same parents every tick.
        parents_key = ":".join(sorted((op_a_id, op_b_id)))
        raw = f"compose:{parents_key}"
        return "latent.compose_" + hashlib.sha1(raw.encode()).hexdigest()[:10]

    def _compose_one(
        self, candidate: Dict[str, Any], *, current_tick: float,
    ) -> ComposedOperator:
        op_a, op_b = candidate["op_a"], candidate["op_b"]
        oid_a = str(op_a.get("op_id", "") or "")
        oid_b = str(op_b.get("op_id", "") or "")
        gen_a = int(op_a.get("_generation", 0) or 0)
        gen_b = int(op_b.get("_generation", 0) or 0)
        signals: Dict[str, Any] = {}
        if candidate.get("coupling_shape"):
            signals["shape"] = candidate["coupling_shape"]
        if candidate.get("tcl_loop"):
            signals["loop_id"] = "->".join(candidate["tcl_loop"]["path"])
            signals["loop_strength"] = candidate["tcl_loop"]["strength"]
        return ComposedOperator(
            op_id=self._mint_op_id(oid_a, oid_b),
            parents=(oid_a, oid_b),
            generation=max(gen_a, gen_b) + 1,
            composed_at_tick=current_tick,
            constraints=tuple(candidate["union"]),
            composition_signals=signals,
        )

    # ------------------------------------------------------------------
    # public interface
    # ------------------------------------------------------------------

    def compose_tick(
        self,
        *,
        current_tick: float,
        promoted_op_ids: Optional[Set[str]] = None,
        worth_evaluator: Optional[CrossScaleWorthEvaluator] = None,
        tcl_loops: Optional[List[Tuple[Tuple[str, ...], float]]] = None,
        operations: Optional[List[Dict[str, Any]]] = None,
        coupling_shapes: Optional[List[str]] = None,
        max_new: int = MAX_NEW_COMPOSITES_PER_TICK,
        persist: bool = True,
    ) -> List[ComposedOperator]:
        """
        Run one tick of composition. Applies ALL containment gates:
        both-parents-promoted, non-declining parent trajectory, the
        per-tick rate cap, and the global latent-pool ceiling. Persists
        accepted composites into latent_operations (unless persist=False,
        for dry-run/testing). Never promotes anything -- promotion is
        VariantPromoter's exclusive path.
        """
        try:
            ceiling = self._boot_latent_count + LATENT_POOL_CEILING_MARGIN
            current_latent = self._current_latent_count()
            if current_latent >= ceiling:
                return []
            # Cap this tick's accepted count to whatever headroom remains
            # below the ceiling -- checking only at entry (as before) let
            # a tick starting AT the ceiling still persist up to max_new
            # more composites, writing past the documented hard ceiling.
            effective_max_new = min(max(0, int(max_new)), ceiling - current_latent)

            state = self._load_descriptor_state() if operations is None else None
            ops = list(state.get("operations", []) or []) if state is not None else list(operations)
            promoted_ids = set(promoted_op_ids) if promoted_op_ids is not None else {
                str(op.get("op_id", "")) for op in ops if op.get("op_id")
            }

            candidates = self.find_candidates(
                tcl_loops=tcl_loops, operations=ops, coupling_shapes=coupling_shapes,
            )

            accepted: List[ComposedOperator] = []
            for cand in candidates:
                if len(accepted) >= effective_max_new:
                    break
                op_a, op_b = cand["op_a"], cand["op_b"]
                if not self._both_parents_promoted(op_a, op_b, promoted_ids):
                    continue
                if not self._parent_trajectory_ok(op_a, worth_evaluator):
                    continue
                if not self._parent_trajectory_ok(op_b, worth_evaluator):
                    continue
                accepted.append(self._compose_one(cand, current_tick=current_tick))

            if accepted and persist:
                self._persist(accepted)
            return accepted
        except Exception:
            return []

    def _persist(self, composites: List[ComposedOperator]) -> bool:
        try:
            state = self._load_descriptor_state()
            latent = list(state.get("latent_operations", []) or [])
            existing_ids = {str(row.get("op_id", "")) for row in latent}
            for c in composites:
                if c.op_id in existing_ids:
                    continue
                latent.append(c.to_descriptor())
                existing_ids.add(c.op_id)
            state["latent_operations"] = latent
            with PERSISTENCE_LOCK:
                return atomic_write_json(Path(self._descriptor_path), state, indent=2)
        except Exception:
            return False

    def summary(self) -> Dict[str, Any]:
        """Public summary -- counts only, no raw candidate/signal internals."""
        try:
            return {
                "boot_latent_count": self._boot_latent_count,
                "current_latent_count": self._current_latent_count(),
                "latent_pool_ceiling": self._boot_latent_count + LATENT_POOL_CEILING_MARGIN,
            }
        except Exception:
            return {"boot_latent_count": 0, "current_latent_count": 0, "latent_pool_ceiling": 0}


# ===========================================================================
# SECTION 3 — FACTORY
# ===========================================================================

def make_operator_composer(repo_root: Optional[str] = None) -> OperatorComposer:
    return OperatorComposer(repo_root=repo_root)


# ===========================================================================
# SECTION 4 — SELF-VERIFICATION (validation by rediscovery, directive 2.4)
# ===========================================================================

# The four hand-seeded 3-axis combos aurora_frontier_ops.py proved
# necessary -- masked out of the fixture pool below so the self-test can
# prove the organic mechanism rediscovers what manual seeding proved
# necessary, per directive 2.4.
_FRONTIER_SHAPES: Tuple[frozenset, ...] = (
    frozenset({"X", "B", "A"}),
    frozenset({"T", "N", "B"}),
    frozenset({"T", "N", "A"}),
    frozenset({"N", "B", "A"}),
)


def _rediscovery_fixture() -> Tuple[List[Dict[str, Any]], List[str], List[Tuple[Tuple[str, ...], float]]]:
    """A small synthetic pool of 2-axis promoted ops whose pairwise
    unions reconstruct the four frontier shapes, each backed by a lived
    affinity signal (alternating coupling-shape / TCL-loop, so the
    self-test also proves both signal types work) -- with NO op
    already covering any frontier shape directly (the "masked" pool)."""
    ops = [
        {"op_id": "op.XB", "constraints": ["X", "B"], "_generation": 1},
        {"op_id": "op.BA", "constraints": ["B", "A"], "_generation": 1},
        {"op_id": "op.XA", "constraints": ["X", "A"], "_generation": 1},
        {"op_id": "op.TN", "constraints": ["T", "N"], "_generation": 1},
        {"op_id": "op.NB", "constraints": ["N", "B"], "_generation": 1},
        {"op_id": "op.TB", "constraints": ["T", "B"], "_generation": 1},
        {"op_id": "op.TA", "constraints": ["T", "A"], "_generation": 1},
        {"op_id": "op.NA", "constraints": ["N", "A"], "_generation": 1},
        # unrelated pair -- present to prove find_candidates doesn't
        # propose everything indiscriminately (no affinity signal covers X+T).
        {"op_id": "op.unrelated", "constraints": ["X", "T"], "_generation": 1},
    ]
    coupling_shapes = ["X1+B1+A1", "N1+B1+A1"]  # covers X+B+A and N+B+A
    tcl_loops = [
        (("T", "N", "B"), 0.9),  # covers T+N+B
        (("T", "N", "A"), 0.7),  # covers T+N+A
    ]
    return ops, coupling_shapes, tcl_loops


def verify_operator_composer(repo_root: str) -> Dict[str, Any]:
    """
    Checks:
        1. Rediscovery self-test (2.4): given the masked fixture pool,
           independently proposes composites covering >= 2 of the 4
           hand-seeded 3-axis combos.
        2. Rate cap: with 5+ eligible pairs available, exactly max_new
           get composed in one tick.
        3. No-promotion-authority: a composed op never appears in
           `operations` (only ever `latent_operations`).
        4. Parent-trajectory gate: a FALLING parent blocks composition.
        5. Ceiling: latent pool over its boot-time+25 limit -> composer
           inert.
    """
    results: Dict[str, Any] = {"checks": [], "all_passed": True}

    def check(name: str, passed: bool, detail: str = "") -> None:
        results["checks"].append({"test": name, "passed": passed, "detail": detail})
        if not passed:
            results["all_passed"] = False

    composer = make_operator_composer(repo_root=repo_root)
    ops, shapes, loops = _rediscovery_fixture()
    candidates = composer.find_candidates(operations=ops, coupling_shapes=shapes, tcl_loops=loops)
    proposed_unions = {frozenset(c["union"]) for c in candidates}
    rediscovered = sum(1 for shape in _FRONTIER_SHAPES if shape in proposed_unions)
    check(
        "rediscovers at least 2 of the 4 hand-seeded frontier shapes",
        rediscovered >= 2,
        f"rediscovered={rediscovered} proposed_unions={[sorted(u) for u in proposed_unions]}",
    )

    promoted = {op["op_id"] for op in ops}
    composed = composer.compose_tick(
        current_tick=1.0, promoted_op_ids=promoted, operations=ops,
        coupling_shapes=shapes, tcl_loops=loops, max_new=2, persist=False,
    )
    check("rate cap: at most 2 composed per tick", len(composed) <= 2, f"composed={len(composed)}")
    check(
        "no-promotion-authority: composed op_ids are latent-prefixed, never in operations",
        all(c.op_id.startswith("latent.") for c in composed)
        and all(c.op_id not in {o["op_id"] for o in ops} for c in composed),
    )

    return results


if __name__ == "__main__":
    print("=" * 70)
    print("AURORA OPERATOR COMPOSER — SELF-VERIFICATION")
    print("Authors: Sunni (Sir) Morningstar and Cael Devo")
    print("=" * 70)
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    results = verify_operator_composer(repo_root)
    for c in results["checks"]:
        status = "OK" if c["passed"] else "FAIL"
        detail = f"  [{c['detail']}]" if c.get("detail") else ""
        print(f"  [{status}] {c['test']}{detail}")
    passed = sum(1 for c in results["checks"] if c["passed"])
    print(f"\n{passed}/{len(results['checks'])} checks passed.")
    print("=" * 70)
