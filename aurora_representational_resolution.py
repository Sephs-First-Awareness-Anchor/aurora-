#!/usr/bin/env python3
"""Perspective-before-resolution extension for Aurora Build 714.

Build 714 remains the sole authority for retained representational growth.
Before it stages a field inquiry, this layer asks whether a real structurally
connected representation already contains the needed distinction and whether a
lawful X/T/N/B/A perspective can make that distinction legible transiently.

Projection is a view, never knowledge: it does not modify current_resolution,
_active_resolutions, resolution genealogy, SediMemory, or resolve_field().
Only failure of available causal projections permits the original Build 714
field-inquiry path to run.

Authors: Sunni (Sir) Morningstar & Ceph
"""
from __future__ import annotations

import hashlib
from dataclasses import replace
from typing import Any, Dict, List, Optional, Sequence, Tuple

import aurora_representational_resolution_base as _base
from aurora_representational_resolution_base import *  # noqa: F401,F403
from aurora_representational_resolution_base import RepresentationalResolutionEngine as _BaseEngine
from aurora_representational_address import AXES, RepresentationalRef, _FIELDS

_DIMENSION_OWNER_AXIS = {
    "MAGNITUDE": "X", "POLARITY": "T", "COST": "N",
    "DIFFERENCE": "B", "OPERATOR": "A",
}
_EPS = 1e-12


def perspective_owner_axis(value: Any) -> Optional[str]:
    token = str(value or "").upper()
    return token if token in AXES else _DIMENSION_OWNER_AXIS.get(token)


def _canonical_perspectives() -> Tuple[Tuple[str, ...], ...]:
    try:
        from aurora_internal.dual_strata.predictive_stager import PRESSURE_PERSPECTIVES
        return tuple(tuple(str(a).upper() for a in p) for p in PRESSURE_PERSPECTIVES)
    except Exception:
        from itertools import combinations
        axes = tuple(AXES)
        return tuple(c for n in range(1, len(axes) + 1) for c in combinations(axes, n))


def _project(ref: RepresentationalRef, source: RepresentationalRef,
             perspective: Sequence[str]) -> Tuple[RepresentationalRef, Dict[str, Any]]:
    lens = {str(a).upper() for a in perspective if str(a).upper() in AXES}
    exposed = {}
    for field_name in ref.unresolved_fields():
        value = getattr(source, field_name, None)
        if value is not None and perspective_owner_axis(value) in lens:
            exposed[field_name] = value
    return (replace(ref, **exposed), exposed) if exposed else (ref, {})


def _projection_id(ref: RepresentationalRef, source: RepresentationalRef,
                   perspective: Sequence[str], projected: RepresentationalRef) -> str:
    payload = "|".join((ref.encode(), source.encode(), ".".join(perspective), projected.encode()))
    return "rproj_" + hashlib.sha256(payload.encode()).hexdigest()[:20]


def build_perspective_projections(
    ref: RepresentationalRef,
    structural_sources: Sequence[Tuple[str, RepresentationalRef, Dict[str, Any]]],
    *, max_projections: Optional[int] = MAX_CANDIDATE_FIELDS_PER_PASS,
) -> List[Dict[str, Any]]:
    """Return lawful transient views from real connected sources.

    ``max_projections`` is only a caller-side compute budget. Passing ``None``
    exposes the complete currently-relevant projection frontier. The engine
    uses that complete frontier before it is allowed to conclude that
    perspective failed and escalate to retained representational refinement.
    """
    results, seen = [], set()
    for source_id, source_ref, evidence in sorted(structural_sources, key=lambda x: str(x[0])):
        for perspective in _canonical_perspectives():
            projected, exposed = _project(ref, source_ref, perspective)
            encoded = projected.encode()
            if not exposed or encoded == ref.encode() or encoded in seen:
                continue
            seen.add(encoded)
            primary = next((f for f in _FIELDS if f in exposed), sorted(exposed)[0])
            pid = _projection_id(ref, source_ref, perspective, projected)
            results.append({
                "mode": "perspective_projection", "projection_id": pid,
                "field": primary, "candidate_value": exposed[primary],
                "projected_ref": encoded, "source_ref": source_ref.encode(),
                "source": f"perspective_projection:{source_id}",
                "origin": "structural_projection",
                "counterpart_ability_id": str(source_id),
                "pressure_perspective": list(perspective),
                "exposed_fields": dict(exposed),
                "evidence": {
                    "origin": "real_structurally_connected_representation",
                    "source_representation": source_ref.encode(),
                    "pressure_perspective": list(perspective),
                    "exposed_fields": dict(exposed), **dict(evidence or {}),
                },
            })
    results.sort(key=lambda p: (len(p["pressure_perspective"]), p["projection_id"]))
    if max_projections is None:
        return results
    return results[:max(0, int(max_projections))]


class RepresentationalResolutionEngine(_BaseEngine):
    """Build 714 with causal perspective projection as its precursor."""

    def _projection_state(self) -> None:
        if not hasattr(self, "_projection_attempt_counts"): self._projection_attempt_counts = {}
        if not hasattr(self, "_projection_events"): self._projection_events = []
        if not hasattr(self, "_projection_resolution_hold"): self._projection_resolution_hold = False

    def _projection_event(self, ref, pending, outcome, evaluation=None):
        self._projection_state()
        c = dict(pending.get("candidate") or {})
        self._projection_events.append({
            "ref": ref.encode(), "projection_id": c.get("projection_id"),
            "projected_ref": c.get("projected_ref"),
            "pressure_perspective": list(c.get("pressure_perspective") or ()),
            "exposed_fields": dict(c.get("exposed_fields") or {}),
            "source_ref": c.get("source_ref"), "outcome": outcome,
            "evaluation": dict(evaluation or {}),
        })
        self._projection_events = self._projection_events[-200:]

    def recent_projection_events(self, limit=50):
        self._projection_state()
        return list(self._projection_events[-max(0, int(limit)):])

    def _projection_sources(self, candidates):
        sources = {}
        for c in candidates:
            if str(c.get("origin") or "") == "domain_hypothesis":
                continue
            sid = str(c.get("counterpart_ability_id") or "")
            if not sid or sid in sources: continue
            src = self._ref_from_ability_id(sid)
            if src is not None: sources[sid] = (sid, src, dict(c.get("evidence") or {}))
        return list(sources.values())

    def _stage_field_after_projection(self, ref, candidates, consumer, context_scope):
        if not candidates: return None
        key = ref.encode()
        candidate = min(candidates, key=lambda c: (
            self._candidate_attempt_counts.get(self._candidate_attempt_key(
                key, str(c.get("field", "")), c.get("candidate_value")), 0),
            self._candidate_attempt_key(key, str(c.get("field", "")), c.get("candidate_value")),
        ))
        staged = self.stage_field_inquiry(ref, candidate, consumer=consumer)
        if not staged: return None
        self._active_stage_for_ref[key] = {
            "mode": "field_inquiry", "stage": staged[0], "candidate": candidate,
            "consumer": consumer, "context_scope": context_scope,
            "candidate_selection": "least_tested_then_canonical_neutral_tie",
        }
        self._provisional_reads[key] = 0
        self._candidate_downstream_effects.pop(key, None)
        return self._active_stage_for_ref[key]

    def investigate_if_pressured(self, ref, *, consumer="auto", context_scope=None):
        self._projection_state()
        if self._projection_resolution_hold: return None
        key = ref.encode()
        if key in self._active_stage_for_ref or self.inadequacy_pressure(ref) <= 0.0: return None
        candidates = self.unresolved_field_candidates(ref)
        if not candidates: return None

        # Projection is a precursor to refinement, so the old per-pass field
        # candidate budget must not become an epistemic cutoff. Materializing
        # these views is cheap: they are only encoded overlays over already
        # resolved structural counterparts. We expose the complete relevant
        # frontier here, then stage ONE cheapest untried view at a time.
        projections = build_perspective_projections(
            ref, self._projection_sources(candidates), max_projections=None,
        )
        untried = [p for p in projections if self._projection_attempt_counts.get(p["projection_id"], 0) == 0]
        if untried:
            candidate = dict(untried[0])
            candidate["projection_frontier_size"] = len(projections)
            candidate["projection_frontier_remaining"] = len(untried)
            self._active_stage_for_ref[key] = {
                "mode": "perspective_projection", "stage": None, "candidate": candidate,
                "consumer": consumer, "context_scope": context_scope,
                "candidate_selection": "progressive_least_dimensional_lawful_projection",
            }
            self._provisional_reads[key] = 0
            self._candidate_downstream_effects.pop(key, None)
            self._projection_event(ref, self._active_stage_for_ref[key], "staged")
            return self._active_stage_for_ref[key]

        # Only a genuinely exhausted relevant projection frontier allows the
        # original Build 714 retained-resolution inquiry to begin.
        return self._stage_field_after_projection(ref, candidates, consumer, context_scope)

    def provisional_resolution(self, ref):
        self._projection_state()
        key = ref.encode(); pending = self._active_stage_for_ref.get(key)
        if pending is None or pending.get("mode") != "perspective_projection":
            return super().provisional_resolution(ref)
        try: view = RepresentationalRef.decode(str(pending["candidate"]["projected_ref"]))
        except Exception: return self.current_resolution(ref)
        self._provisional_reads[key] = self._provisional_reads.get(key, 0) + 1
        return view

    def consume_projection(self, ref, *, consumer="cognition", context_scope=None):
        """Common causal doorway for any real representational consumer.

        If pressure has staged a lawful perspective view, return that transient
        view and record that the consumer actually looked through it. Nothing
        here can promote or retain a field. Consumers may separately report a
        downstream difference and later consequence evidence through the
        existing Build 714 path.
        """
        self._projection_state()
        key = ref.encode()
        if key not in self._active_stage_for_ref:
            self.investigate_if_pressured(ref, consumer=consumer, context_scope=context_scope)
        pending = self._active_stage_for_ref.get(key)
        if pending is None or pending.get("mode") != "perspective_projection":
            return None
        view = self.provisional_resolution(ref)
        candidate = dict(pending.get("candidate") or {})
        return {
            "mode": "perspective_projection",
            "consumer": str(consumer or "cognition"),
            "context_scope": context_scope,
            "base_ref": ref.encode(),
            "current_ref": self.current_resolution(ref).encode(),
            "projected_ref": view.encode(),
            "projection_id": candidate.get("projection_id"),
            "pressure_perspective": list(candidate.get("pressure_perspective") or ()),
            "exposed_fields": dict(candidate.get("exposed_fields") or {}),
            "source_ref": candidate.get("source_ref"),
            "projection_frontier_size": candidate.get("projection_frontier_size"),
            "projection_frontier_remaining": candidate.get("projection_frontier_remaining"),
        }

    def record_candidate_downstream_effect(self, ref, *, consumer, downstream_difference,
                                           action_or_prediction_affected,
                                           baseline_expectation=None,
                                           conditioned_expectation=None, metadata=None):
        self._projection_state()
        key = ref.encode(); pending = self._active_stage_for_ref.get(key)
        if pending is None or pending.get("mode") != "perspective_projection":
            return super().record_candidate_downstream_effect(
                ref, consumer=consumer, downstream_difference=downstream_difference,
                action_or_prediction_affected=action_or_prediction_affected,
                baseline_expectation=baseline_expectation,
                conditioned_expectation=conditioned_expectation, metadata=metadata,
            )
        if not self._has_material_downstream_difference(downstream_difference): return None
        c = dict(pending.get("candidate") or {})
        try: projected = RepresentationalRef.decode(str(c.get("projected_ref") or ""))
        except Exception: return None
        record = {
            "mode": "perspective_projection", "candidate_field": c.get("field"),
            "candidate_value": c.get("candidate_value"), "projection_id": c.get("projection_id"),
            "pressure_perspective": list(c.get("pressure_perspective") or ()),
            "exposed_fields": dict(c.get("exposed_fields") or {}), "source_ref": c.get("source_ref"),
            "representation_without_candidate": self.current_resolution(ref).encode(),
            "representation_with_candidate": projected.encode(),
            "downstream_difference_produced": downstream_difference,
            "action_prediction_affected": action_or_prediction_affected,
            "baseline_expectation": dict(baseline_expectation or {}),
            "conditioned_expectation": dict(conditioned_expectation or {}),
            "consumer": str(consumer or ""), "metadata": dict(metadata or {}),
            "recorded_at": _base._now(),
        }
        self._candidate_downstream_effects[key] = record
        return dict(record)

    def _projection_consequence(self, ref, pending, candidate_evaluation):
        key = ref.encode(); reads = int(self._provisional_reads.get(key, 0) or 0)
        effect = dict(self._candidate_downstream_effects.get(key, None) or {})
        evaluation = dict(effect); evaluation.update(dict(candidate_evaluation or {}))
        if reads <= 0:
            return "untested"

        has_effect = bool(effect) and self._has_material_downstream_difference(
            effect.get("downstream_difference_produced"))
        has_actual = evaluation.get("actual_consequence") is not None
        try:
            baseline_error = float(evaluation.get("baseline_error"))
            candidate_error = float(evaluation.get("candidate_conditioned_error"))
            has_errors = True
        except (TypeError, ValueError):
            baseline_error = candidate_error = 0.0
            has_errors = False

        # A live cognitive consumer may have genuinely used the projection and
        # changed its downstream thought before reality has supplied the
        # consequence needed to judge that lens. Do not misclassify absence of
        # evidence as failed perspective and escalate to resolution.
        if not (has_effect and has_actual and has_errors):
            self._projection_event(ref, pending, "pending_evidence", evaluation)
            return "pending_evidence"

        better = candidate_error + _EPS < baseline_error
        self._provisional_reads[key] = 0
        self._candidate_downstream_effects.pop(key, None)
        if better:
            self._projection_event(ref, pending, "adequate", evaluation)
            return "adequate"
        pid = str((pending.get("candidate") or {}).get("projection_id") or "")
        if pid: self._projection_attempt_counts[pid] = self._projection_attempt_counts.get(pid, 0) + 1
        self._projection_event(ref, pending, "failed", evaluation)
        return "failed"

    def record_participation(self, ref, *, pressure_before, pressure_after, source,
                             context_tag="", extra_trace=None, notes=None,
                             consumer="auto", candidate_evaluation=None):
        self._projection_state()
        key = ref.encode(); pending = self._active_stage_for_ref.get(key)
        if pending is None or pending.get("mode") != "perspective_projection":
            return super().record_participation(
                ref, pressure_before=pressure_before, pressure_after=pressure_after,
                source=source, context_tag=context_tag, extra_trace=extra_trace,
                notes=notes, consumer=consumer, candidate_evaluation=candidate_evaluation,
            )
        self._active_stage_for_ref.pop(key, None)
        self._projection_resolution_hold = True
        try:
            result = super().record_participation(
                ref, pressure_before=pressure_before, pressure_after=pressure_after,
                source=source, context_tag=context_tag, extra_trace=extra_trace,
                notes=notes, consumer=consumer, candidate_evaluation=None,
            )
        finally:
            self._projection_resolution_hold = False
        outcome = self._projection_consequence(ref, pending, candidate_evaluation)
        if outcome == "adequate" and self.inadequacy_pressure(ref) <= 0.0:
            self._projection_event(ref, pending, "released_pressure_resolved")
        elif outcome in ("adequate", "untested", "pending_evidence"):
            self._active_stage_for_ref[key] = pending
        else:
            self.investigate_if_pressured(
                ref, consumer=str(pending.get("consumer") or consumer),
                context_scope=pending.get("context_scope"),
            )
        return result


def get_or_create_engine(systems: Optional[Dict[str, Any]]) -> Optional[RepresentationalResolutionEngine]:
    if not systems: return None
    existing = systems.get("representational_resolution_engine")
    if isinstance(existing, RepresentationalResolutionEngine):
        existing._projection_state(); return existing
    if isinstance(existing, _BaseEngine):
        upgraded = RepresentationalResolutionEngine.__new__(RepresentationalResolutionEngine)
        upgraded.__dict__.update(existing.__dict__); upgraded._projection_state()
        systems["representational_resolution_engine"] = upgraded; return upgraded
    if existing is not None: return existing
    genealogy = systems.get("genealogy")
    if genealogy is None: return None
    engine = RepresentationalResolutionEngine(genealogy, state_dir=systems.get("state_dir"))
    systems["representational_resolution_engine"] = engine
    return engine


def consume_projection_for_ref(systems, ref_encoded, *, consumer="cognition", context_scope=None):
    """Public consumer bridge for an already-real encoded RepresentationalRef."""
    if not ref_encoded:
        return None
    engine = get_or_create_engine(systems)
    if engine is None:
        return None
    try:
        ref = RepresentationalRef.decode(str(ref_encoded))
    except Exception:
        return None
    try:
        return engine.consume_projection(ref, consumer=consumer, context_scope=context_scope)
    except Exception:
        return None


def record_ref_participation_from_scores(systems, ref_encoded, dimension_scores, *, source,
                                         context_tag="", extra_trace_ids=None,
                                         candidate_evaluation=None):
    """Original Build 714 bridge, routed through the perspective-aware factory."""
    if not ref_encoded or not dimension_scores: return
    engine = get_or_create_engine(systems)
    if engine is None: return
    try: ref = RepresentationalRef.decode(ref_encoded)
    except Exception: return
    axis = ref.nc_law_c if ref.nc_law_c in AXES else "X"
    others = [a for a in AXES if a != axis]
    avg = _base._clip01(sum(dimension_scores.values()) / max(1, len(dimension_scores)))
    unexplained = max(0.0, 1.0 - avg)
    before = {a: (1.0 if a == axis else 0.0) for a in AXES}
    after = {a: (unexplained if a == axis else unexplained / len(others)) for a in AXES}
    from aurora_internal.constraint_genealogy import TraceItem
    trace = [TraceItem(kind="ABILITY", id=str(t)) for t in (extra_trace_ids or [])]
    try:
        engine.record_participation(
            ref, pressure_before=before, pressure_after=after, source=source,
            context_tag=context_tag, extra_trace=trace,
            candidate_evaluation=candidate_evaluation,
        )
    except Exception:
        pass
