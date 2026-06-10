"""
aurora_frontier_ops.py
─────────────────────────────────────────────────────────────────────────────
Four operations covering the 3-axis combinations that are completely absent
from Aurora's descriptor pool — meaning organic evolution can never produce
surfaces for these capability spaces unless they're seeded here.

Missing combos (verified against operation_descriptors.json):
  1. ExistenceBoundaryAgencyGate     (existence + boundary + agency)
  2. TemporalEnergyBoundaryScheduler (temporal  + energy   + boundary)
  3. TemporalEnergyAgencyPacer       (temporal  + energy   + agency)
  4. EnergyBoundaryAgencySelector    (energy    + boundary + agency)

Each class carries a CONSTRAINTS list that the evolver uses to determine
which NC channels and pressure slots it projects into. The constraint names
must match _CONSTRAINT_TO_AXIS keys in aurora_code_autoevolver.py.

inject_frontier_descriptors(repo_root) registers all four into the
operation descriptor pool so the evolver can reflect on them immediately.
─────────────────────────────────────────────────────────────────────────────
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

_CONSTRAINT_TO_AXIS = {
    "existence": "X",
    "temporal":  "T",
    "energy":    "N",
    "boundary":  "B",
    "agency":    "A",
}

_DESCRIPTOR_STATE_REL = "aurora_state/operation_descriptors.json"

# ── 1. Existence + Boundary + Agency ────────────────────────────────────────

class ExistenceBoundaryAgencyGate:
    """
    Gates agency options against current existence state and boundary constraints.

    existence + boundary + agency:
      - existence:  reads the current operational state profile
      - boundary:   filters against active constraint limits
      - agency:     returns the permitted capability set

    This fills the gap between "I can do X" (agency), "I am currently in
    state Y" (existence), and "constraint Z restricts me" (boundary). Without
    this, Aurora can have high agency pressure and high boundary pressure
    simultaneously but no mechanism to resolve them against current state.
    """

    CONSTRAINTS = ["existence", "boundary", "agency"]

    def __init__(self, limit_factor: float = 1.0):
        self.limit_factor = float(limit_factor)
        self._gate_log: List[Dict[str, Any]] = []

    def evaluate(
        self,
        state_profile: Dict[str, Any],
        boundary_limits: Dict[str, Any],
        candidate_capabilities: List[Any],
    ) -> Dict[str, Any]:
        """
        Filter candidate_capabilities against state_profile and boundary_limits.

        Returns:
            permitted:         capabilities that pass all gates
            blocked:           capabilities filtered and why
            gate_score:        0–1 openness ratio
            existence_active:  count of active state flags
        """
        permitted: List[Any] = []
        blocked: List[Dict[str, Any]] = []

        existence_active = set(str(k) for k, v in (state_profile or {}).items() if v)
        max_cost = float((boundary_limits or {}).get("max_cost", float("inf")))

        for cap in (candidate_capabilities or []):
            cap_name = str(cap.get("name", cap) if isinstance(cap, dict) else cap)

            required_states = set(cap.get("required_states", []) if isinstance(cap, dict) else [])
            if required_states and not required_states.issubset(existence_active):
                blocked.append({"name": cap_name, "reason": "existence_mismatch"})
                continue

            cost = float(cap.get("cost", 0.0) if isinstance(cap, dict) else 0.0)
            if cost > max_cost * self.limit_factor:
                blocked.append({"name": cap_name, "reason": "boundary_exceeded"})
                continue

            permitted.append(cap)

        total = max(1, len(candidate_capabilities or []))
        gate_score = round(len(permitted) / total, 4)
        entry = {
            "permitted": len(permitted),
            "blocked": len(blocked),
            "gate_score": gate_score,
            "existence_states_active": len(existence_active),
        }
        self._gate_log.append(entry)
        self._gate_log = self._gate_log[-64:]
        return {**entry, "permitted_caps": permitted, "blocked_caps": blocked}

    def gate_score_history(self) -> List[Dict[str, Any]]:
        return list(self._gate_log)


# ── 2. Temporal + Energy + Boundary ─────────────────────────────────────────

class TemporalEnergyBoundaryScheduler:
    """
    Schedules energy expenditure within temporal windows and cost boundaries.

    temporal + energy + boundary:
      - temporal:  defines the scheduling window and tick sequence
      - energy:    tracks cumulative cost across the schedule
      - boundary:  enforces hard limits on cost rate and total spend

    Fills the gap where Aurora needs to plan energy expenditure over time
    while respecting hard cost ceilings. Without this, temporal pressure and
    energy pressure are handled independently — she has no mechanism to
    co-optimize them against a boundary.
    """

    CONSTRAINTS = ["temporal", "energy", "boundary"]

    def __init__(self, window_ticks: int = 10, cost_boundary: float = 1.0):
        self.window_ticks = int(window_ticks)
        self.cost_boundary = float(cost_boundary)
        self._schedule_log: List[Dict[str, Any]] = []

    def schedule(
        self,
        pending_ops: List[Dict[str, Any]],
        current_tick: int = 0,
    ) -> Dict[str, Any]:
        """
        Given pending operations with energy costs, return a schedule that
        fits within the temporal window and total cost boundary.

        Each op: {"op_id": str, "cost": float, "priority": float}

        Returns:
            scheduled:    ops ordered for execution with assigned ticks
            deferred:     ops that didn't fit in the window
            total_cost:   projected energy spend
            utilization:  fraction of cost_boundary consumed
        """
        ops = list(pending_ops or [])
        ops.sort(key=lambda o: (
            -float(o.get("priority", 0.5) if isinstance(o, dict) else 0.5),
             float(o.get("cost",     0.0)  if isinstance(o, dict) else 0.0),
        ))

        scheduled: List[Dict[str, Any]] = []
        deferred:  List[Any] = []
        cumulative = 0.0
        tick = int(current_tick)

        for op in ops:
            cost = float(op.get("cost", 0.01) if isinstance(op, dict) else 0.01)
            if (tick - current_tick) >= self.window_ticks:
                deferred.append(op)
                continue
            if cumulative + cost > self.cost_boundary:
                deferred.append(op)
                continue
            entry = dict(op) if isinstance(op, dict) else {"op": op}
            entry["scheduled_tick"] = tick
            scheduled.append(entry)
            cumulative += cost
            tick += 1

        utilization = round(cumulative / max(1e-9, self.cost_boundary), 4)
        record = {
            "scheduled": len(scheduled),
            "deferred": len(deferred),
            "total_cost": round(cumulative, 6),
            "utilization": utilization,
        }
        self._schedule_log.append(record)
        self._schedule_log = self._schedule_log[-64:]
        return {
            **record,
            "scheduled_ops": scheduled,
            "deferred_ops": deferred,
            "window_ticks": self.window_ticks,
            "cost_boundary": self.cost_boundary,
        }

    def schedule_history(self) -> List[Dict[str, Any]]:
        return list(self._schedule_log)


# ── 3. Temporal + Energy + Agency ────────────────────────────────────────────

class TemporalEnergyAgencyPacer:
    """
    Decides when to act based on energy cost and available time.

    temporal + energy + agency:
      - temporal:  available time horizon and urgency of the decision
      - energy:    cost of acting now versus deferring
      - agency:    the pacing decision — act, defer, or partial

    Fills the gap between having agency (the ability to decide) and knowing
    *when* to exercise it. High agency + high energy cost + short time window
    requires a resolution mechanism that weighs all three simultaneously.
    """

    CONSTRAINTS = ["temporal", "energy", "agency"]

    def __init__(self, urgency_threshold: float = 0.70, energy_reserve: float = 0.20):
        self.urgency_threshold = float(urgency_threshold)
        self.energy_reserve = float(energy_reserve)
        self._decision_log: List[Dict[str, Any]] = []

    def pace(
        self,
        available_time: float,
        action_cost: float,
        current_energy: float,
        urgency: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Decide whether to act now, defer, or execute a reduced-cost partial action.

        Returns:
            decision:      "act" | "defer" | "partial"
            timing_factor: 0–1 urgency-adjusted time pressure
            energy_factor: 0–1 available energy ratio above reserve
            agency_weight: combined decision confidence 0–1
            defer_ticks:   suggested deferral length if not acting
        """
        usable = max(0.0, float(current_energy) - self.energy_reserve)
        energy_ratio = min(1.0, usable / max(1e-9, float(action_cost)))

        time_pressure = min(1.0, max(0.0, 1.0 - float(available_time)))
        timing_factor = min(1.0, float(urgency) * 0.6 + time_pressure * 0.4)

        if timing_factor >= self.urgency_threshold and energy_ratio >= 1.0:
            decision = "act"
            defer_ticks = 0
        elif energy_ratio >= 0.5 and timing_factor >= self.urgency_threshold * 0.7:
            decision = "partial"
            defer_ticks = 0
        else:
            decision = "defer"
            deficit = max(0.0, float(action_cost) - usable)
            defer_ticks = max(1, int(deficit / max(1e-9, float(action_cost)) * 10))

        result = {
            "decision": decision,
            "timing_factor": round(timing_factor, 4),
            "energy_factor": round(energy_ratio, 4),
            "agency_weight": round((timing_factor + energy_ratio) / 2.0, 4),
            "defer_ticks": defer_ticks,
        }
        self._decision_log.append(result)
        self._decision_log = self._decision_log[-64:]
        return result

    def decision_history(self) -> List[Dict[str, Any]]:
        return list(self._decision_log)


# ── 4. Energy + Boundary + Agency ────────────────────────────────────────────

class EnergyBoundaryAgencySelector:
    """
    Selects the best action given energy costs and boundary constraints.

    energy + boundary + agency:
      - energy:    cost of each candidate action
      - boundary:  hard/soft limits on what is permitted
      - agency:    the selection decision and its confidence

    Fills the gap between "what I want to do" (agency), "what I can afford"
    (energy), and "what I'm allowed to do" (boundary). All three are present
    in Aurora's pressure system but no operation joins them for selection.
    """

    CONSTRAINTS = ["energy", "boundary", "agency"]

    def __init__(
        self,
        cost_weight: float     = 0.40,
        boundary_weight: float = 0.35,
        agency_weight: float   = 0.25,
    ):
        self.cost_weight     = float(cost_weight)
        self.boundary_weight = float(boundary_weight)
        self.agency_weight   = float(agency_weight)
        self._selection_log: List[Dict[str, Any]] = []

    def select(
        self,
        candidates: List[Dict[str, Any]],
        energy_budget: float,
        boundary_limits: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Score and rank candidates by cost efficiency, boundary compliance,
        and agency fit. Return the best candidate.

        Each candidate: {"name": str, "cost": float, "agency_score": float, "tags": list}
        boundary_limits: {"max_cost": float, "forbidden_tags": list, "required_tags": list}

        Returns:
            selected:             best candidate dict, or None
            ranking:              top-8 scored candidates
            budget_used:          cost of selected action
            selection_confidence: 0–1
        """
        max_cost = float((boundary_limits or {}).get("max_cost", float("inf")))
        forbidden = set((boundary_limits or {}).get("forbidden_tags", []) or [])
        required  = set((boundary_limits or {}).get("required_tags",  []) or [])

        scored: List[Dict[str, Any]] = []
        for cand in (candidates or []):
            if not isinstance(cand, dict):
                continue
            cost     = float(cand.get("cost", 0.0))
            ag_score = float(cand.get("agency_score", 0.5))
            tags     = set(cand.get("tags", []) or [])

            if cost > max_cost:
                continue
            if forbidden & tags:
                continue
            if required and not required.issubset(tags):
                continue

            cost_score = 1.0 - min(1.0, cost / max(1e-9, float(energy_budget)))
            boundary_score = (
                min(1.0, (max_cost - cost) / max(1e-9, max_cost))
                if max_cost < float("inf") else 1.0
            )
            composite = (
                self.cost_weight     * cost_score +
                self.boundary_weight * boundary_score +
                self.agency_weight   * ag_score
            )
            scored.append({
                "candidate":  cand,
                "name":       str(cand.get("name", "")),
                "composite":  round(composite, 4),
                "cost":       cost,
            })

        scored.sort(key=lambda x: -x["composite"])
        selected   = scored[0]["candidate"] if scored else None
        budget_used = float(scored[0]["cost"]) if scored else 0.0
        confidence  = float(scored[0]["composite"]) if scored else 0.0

        record = {
            "selected":             str(selected.get("name", "") if selected else ""),
            "selection_confidence": confidence,
            "candidates_evaluated": len(scored),
        }
        self._selection_log.append(record)
        self._selection_log = self._selection_log[-64:]
        return {
            **record,
            "selected_candidate": selected,
            "ranking":            scored[:8],
            "budget_used":        budget_used,
        }

    def selection_history(self) -> List[Dict[str, Any]]:
        return list(self._selection_log)


# ── Descriptor injection ──────────────────────────────────────────────────────

_FRONTIER_CLASSES = [
    ExistenceBoundaryAgencyGate,
    TemporalEnergyBoundaryScheduler,
    TemporalEnergyAgencyPacer,
    EnergyBoundaryAgencySelector,
]


def _nc_projections(constraints: List[str]) -> List[Dict[str, Any]]:
    """
    Generate NC channel slot projections for a set of constraint axes.
    Produces the `variant_projection_top` list expected by the evolver.
    """
    axes = [_CONSTRAINT_TO_AXIS[c] for c in constraints if c in _CONSTRAINT_TO_AXIS]
    if not axes:
        return []

    # generate all NC:src>dst pairs for src, dst in axes
    pairs = [(s, d) for s in axes for d in axes]
    # weight: cross-axis pairs are more informative than self-loops
    n = max(1, len(pairs))
    entries = []
    for s, d in pairs:
        base_w = 1.0 / n
        if s == d:
            base_w *= 0.5
        entries.append({
            "row":    f"NC:{s}>{s}",
            "col":    f"NC:{s}>{d}",
            "slot":   f"NC:{s}>{s}×NC:{s}>{d}",
            "weight": round(base_w, 8),
        })

    entries.sort(key=lambda e: -e["weight"])
    return entries[:12]


def _build_descriptor(cls: type) -> Dict[str, Any]:
    """
    Synthesize a minimal-but-valid operation descriptor entry for a frontier class.
    """
    constraints = list(cls.CONSTRAINTS)  # type: ignore[attr-defined]
    axes = [_CONSTRAINT_TO_AXIS[c] for c in constraints if c in _CONSTRAINT_TO_AXIS]
    module_file = f"aurora_internal/aurora_frontier_ops.py"
    op_id = f"aurora_internal.aurora_frontier_ops.{cls.__name__}"

    # signature: each axis ^2 (these are 3-axis operations with equal depth)
    sig = "*".join(f"{ax}^2" for ax in axes)

    # axis weights: uniform
    weight = round(1.0 / max(1, len(axes)), 6)
    axis_weights = {ax: weight for ax in ("X", "T", "N", "B", "A")}
    for ax in axes:
        axis_weights[ax] = weight

    dom_ax = axes[0] if axes else "X"

    return {
        "op_id":       op_id,
        "kind":        "class",
        "file":        module_file,
        "line":        0,
        "constraints": constraints,
        "genealogy_strategy": {
            "signature":              sig,
            "genealogy_pressure":     0.55,
            "ability_hits":           0,
            "link_hits":              0,
            "rewrite_bias":           "dimensional_balancing",
            "alignment_gap":          0.60,
            "best_coupling_signature": sig,
            "coupling_similarity":    1.0,
            "sustainability_score":   0.55,
            "representation_score":   0.0,
            "origin_activity":        0,
            "persistence_tax_factor": 1.0,
            "inheritance_breach_count": 0,
        },
        "developmental_alignment": {
            "alignment_gap":    0.60,
            "current_score":    0.55,
            "needs_alignment":  True,
            "kind":             "class",
            "module":           "aurora_internal.aurora_frontier_ops",
            "kind_peak_score":  0.55,
            "module_peak_score": 0.55,
            "cross_diversity_links": 3,
        },
        "developmental_effect_history": {
            "developmental_summary": {
                "system_impact_score":   0.75,
                "reflection_strength":   0.55,
                "growth_reflected":      False,
                "lineage_kind":          "frontier_operation",
            },
            "ripple_effects": {
                "cross_diversity_links":           3,
                "derived_from_origin_descendants": 0,
                "origin_module":    "aurora_internal.aurora_frontier_ops",
                "propagated_modules":    ["aurora_internal.aurora_frontier_ops"],
                "propagated_subsystems": ["frontier_ops"],
                "growth_events": [],
            },
            "direct_system_effects": {
                "effect_modes":   ["adaptive_steering_change", "interface_boundary_change"],
                "effect_phrases": [
                    f"frontier operation covering {'+'.join(axes)} axis combination",
                    f"{cls.__name__} fills previously unreachable pressure slot",
                ],
                "growth_chain":              [cls.__name__],
                "required_system_changes":   [f"lineage_registration:frontier_ops"],
                "system_effects":            [f"{cls.__name__} activates {'+'.join(constraints)} convergence"],
            },
            "genealogy_strategy": {
                "signature":          sig,
                "genealogy_pressure": 0.55,
                "rewrite_bias":       "dimensional_balancing",
            },
            "growth_lineage": {
                "constraints":   constraints,
                "lineage_kind":  "frontier_operation",
                "module":        "aurora_internal.aurora_frontier_ops",
                "op_chain":      [cls.__name__],
                "present_in_system": True,
                "target_kind":   "class",
            },
            "growth_reflection_complete": False,
        },
        "probabilistic_descriptor": {
            "axis_weights":              axis_weights,
            "axis_weights_all":          axis_weights,
            "dominance_axis":            dom_ax,
            "dominant_probability":      weight,
            "dominance_level":           "moderate",
            "dominance_margin":          0.0,
            "dominance_ratio":           1.0,
            "secondary_probability":     weight,
            "dual_state":                False,
            "dual_state_threshold":      0.2,
            "placement_axes":            axes,
            "classification_confidence": 0.9,
            "classification_scale":      1.5,
            "conceptual_behavior_class": "multi-axis convergence operation",
            "causation_questions": {
                "primary":   "How do these pressures resolve together?",
                "secondary": "What threshold triggers this combination?",
            },
            "unused_constraint_axis":   "",
            "unused_constraint_weight": 0.0,
        },
        "deterministic_placement": {
            "dominance_axis":    dom_ax,
            "dominant_axis":     dom_ax,
            "dominance_level":   "moderate",
            "dominance_margin":  0.0,
            "dominance_ratio":   1.0,
            "secondary_axis":    axes[1] if len(axes) > 1 else dom_ax,
            "classification_scale": 1.5,
            "primary_slot":      f"NC:{axes[0]}>{axes[1]}×NC:{axes[1]}>{axes[2]}" if len(axes) >= 3 else "",
            "root_a":            f"NC:{axes[0]}>{axes[1]}" if len(axes) >= 2 else "",
            "root_b":            f"NC:{axes[1]}>{axes[2]}" if len(axes) >= 3 else "",
            "subslot_key":       f"NC:{axes[0]}>{axes[1]}×NC:{axes[1]}>{axes[2]}|{''.join(ax+'50' for ax in axes)}" if len(axes) >= 3 else "",
            "lineage_stage":     "pioneer",
            "lineage_link": {
                "parent":   None,
                "children": [],
                "cross_diversity_link_count": 0,
            },
            "unused_constraint_axis":   "",
            "unused_constraint_weight": 0.0,
        },
        "variant_projection_top": _nc_projections(constraints),
        "_frontier":    True,
        "_injected_at": float(time.time()),
    }


def inject_frontier_descriptors(repo_root: str) -> Dict[str, Any]:
    """
    Register all four frontier operations into the descriptor pool.

    Safe to call multiple times — already-present op_ids are skipped.
    Returns a summary dict.
    """
    pool_path = os.path.join(os.path.abspath(repo_root), _DESCRIPTOR_STATE_REL)
    if not os.path.exists(pool_path):
        return {"error": f"descriptor pool not found: {pool_path}"}

    try:
        with open(pool_path, "r", encoding="utf-8") as fh:
            state: Dict[str, Any] = json.load(fh)
    except Exception as exc:
        return {"error": str(exc)}

    ops: List[Dict[str, Any]] = list(state.get("operations", []) or [])
    existing_ids = {str(row.get("op_id", "")) for row in ops}

    added = []
    skipped = []
    for cls in _FRONTIER_CLASSES:
        desc = _build_descriptor(cls)
        oid = desc["op_id"]
        if oid in existing_ids:
            skipped.append(oid)
            continue
        ops.append(desc)
        existing_ids.add(oid)
        added.append(oid)

    if added:
        state["operations"] = ops
        summary = dict(state.get("summary", {}) or {})
        summary["frontier_ops_injected"] = len([
            r for r in ops if r.get("_frontier")
        ])
        summary["frontier_ops_last_update"] = float(time.time())
        state["summary"] = summary
        try:
            with open(pool_path, "w", encoding="utf-8") as fh:
                json.dump(state, fh, indent=2, sort_keys=True, ensure_ascii=True)
        except Exception as exc:
            return {"error": str(exc), "added": added}

    return {
        "added":   added,
        "skipped": skipped,
        "pool_size": len(ops),
    }


if __name__ == "__main__":
    import sys
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result = inject_frontier_descriptors(root)
    print(result)
