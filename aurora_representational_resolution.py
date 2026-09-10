#!/usr/bin/env python3
"""Perspective-before-resolution extension for Aurora Build 714.

Build 714 remains the sole authority for retained representational growth.
Before it stages a field inquiry, this layer asks whether a real structurally
connected representation already contains the needed distinction and whether a
lawful X/T/N/B/A perspective can make that distinction legible transiently.

Projection is a view, never knowledge: it does not modify current_resolution,
_active_resolutions, resolution genealogy, SediMemory, or resolve_field().
Only exhaustion of the currently available lawful structural projection
frontier permits the original Build 714 field-inquiry path to run.

Pressure observation and projection-capable consumption are intentionally
separate. A subsystem that merely reports consequence against a
RepresentationalRef may increase inadequacy pressure, but it may not stage or
complete a projection it never actually used. Real consumers opt into the
ordinary provisional-resolution/effect/evaluation chain.

Authors: Sunni (Sir) Morningstar & Ceph
"""
from __future__ import annotations

import hashlib
from dataclasses import replace
from typing import Any, Dict, List, Optional, Sequence, Tuple

import aurora_representational_resolution_base as _base
from aurora_representational_resolution_base import *  # noqa: F401,F403
from aurora_representational_resolution_base import RepresentationalResolutionEngine as _BaseEngine
from aurora_representational_address import AXES, DIM_NAMES, RepresentationalRef, _FIELDS

_DIMENSION_OWNER_AXIS = {
    "MAGNITUDE": "X", "POLARITY": "T", "COST": "N",
    "DIFFERENCE": "B", "OPERATOR": "A",
}
_AXIS_FIELDS = {"sub_law_c", "col_law_c"}
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


def _project(
    ref: RepresentationalRef,
    source: RepresentationalRef,
    perspective: Sequence[str],
) -> Tuple[RepresentationalRef, Dict[str, Any]]:
    lens = {str(a).upper() for a in perspective if str(a).upper() in AXES}
    exposed: Dict[str, Any] = {}
    for field_name in ref.unresolved_fields():
        value = getattr(source, field_name, None)
        if value is not None and perspective_owner_axis(value) in lens:
            exposed[field_name] = value
    return (replace(ref, **exposed), exposed) if exposed else (ref, {})


def _projection_id(
    ref: RepresentationalRef,
    source: RepresentationalRef,
    perspective: Sequence[str],
    projected: RepresentationalRef,
) -> str:
    payload = "|".join(
        (ref.encode(), source.encode(), ".".join(perspective), projected.encode())
    )
    return "rproj_" + hashlib.sha256(payload.encode()).hexdigest()[:20]


def _field_domain_size(field_name: str) -> int:
    """Size of this field's already-defined lawful representational domain."""
    return len(AXES) if field_name in _AXIS_FIELDS else len(DIM_NAMES)


def _complete_candidate_capacity(ref: RepresentationalRef) -> int:
    """Maximum distinct field/value hypotheses possible for this ref.

    This is not a tuning budget. It follows directly from the typed
    RepresentationalRef domains and lets the escalation path see every lawful
    value before choosing a field inquiry.
    """
    return sum(_field_domain_size(field_name) for field_name in ref.unresolved_fields())


def _projection_priority(item: Dict[str, Any]) -> Tuple[int, float, str]:
    """Cheapest dimensional lens first, then strongest native structural pressure."""
    evidence = dict(item.get("evidence") or {})
    try:
        pressure = float(evidence.get("structural_pressure", 0.0) or 0.0)
    except Exception:
        pressure = 0.0
    return (
        len(item.get("pressure_perspective") or ()),
        -pressure,
        str(item.get("projection_id") or ""),
    )


def build_perspective_projections(
    ref: RepresentationalRef,
    structural_sources: Sequence[Tuple[str, RepresentationalRef, Dict[str, Any]]],
    *,
    max_projections: Optional[int] = MAX_CANDIDATE_FIELDS_PER_PASS,
) -> List[Dict[str, Any]]:
    """Return lawful transient views from real connected representations.

    ``max_projections=None`` means "do not epistemically truncate the
    projection frontier." The engine uses that form before permitting
    representational growth. A numeric limit remains available for diagnostics
    and callers that only want a bounded preview.
    """
    best_by_view: Dict[str, Dict[str, Any]] = {}
    for source_id, source_ref, evidence in sorted(
        structural_sources, key=lambda item: str(item[0])
    ):
        for perspective in _canonical_perspectives():
            projected, exposed = _project(ref, source_ref, perspective)
            encoded = projected.encode()
            if not exposed or encoded == ref.encode():
                continue
            primary = next(
                (field_name for field_name in _FIELDS if field_name in exposed),
                sorted(exposed)[0],
            )
            pid = _projection_id(ref, source_ref, perspective, projected)
            item = {
                "mode": "perspective_projection",
                "projection_id": pid,
                "field": primary,
                "candidate_value": exposed[primary],
                "projected_ref": encoded,
                "source_ref": source_ref.encode(),
                "source": f"perspective_projection:{source_id}",
                "origin": "structural_projection",
                "counterpart_ability_id": str(source_id),
                "pressure_perspective": list(perspective),
                "exposed_fields": dict(exposed),
                "evidence": {
                    "origin": "real_structurally_connected_representation",
                    "source_representation": source_ref.encode(),
                    "pressure_perspective": list(perspective),
                    "exposed_fields": dict(exposed),
                    **dict(evidence or {}),
                },
            }
            previous = best_by_view.get(encoded)
            if previous is None or _projection_priority(item) < _projection_priority(previous):
                best_by_view[encoded] = item
    results = list(best_by_view.values())
    results.sort(key=_projection_priority)
    if max_projections is None:
        return results
    return results[:max(0, int(max_projections))]


class RepresentationalResolutionEngine(_BaseEngine):
    """Build 714 with causal perspective projection as its precursor."""

    def _projection_state(self) -> None:
        if not hasattr(self, "_projection_attempt_counts"):
            self._projection_attempt_counts = {}
        if not hasattr(self, "_projection_events"):
            self._projection_events = []
        if not hasattr(self, "_projection_resolution_hold"):
            self._projection_resolution_hold = False

    def _projection_event(self, ref, pending, outcome, evaluation=None):
        self._projection_state()
        candidate = dict(pending.get("candidate") or {})
        self._projection_events.append({
            "ref": ref.encode(),
            "projection_id": candidate.get("projection_id"),
            "projected_ref": candidate.get("projected_ref"),
            "pressure_perspective": list(candidate.get("pressure_perspective") or ()),
            "exposed_fields": dict(candidate.get("exposed_fields") or {}),
            "source_ref": candidate.get("source_ref"),
            "outcome": outcome,
            "evaluation": dict(evaluation or {}),
        })
        self._projection_events = self._projection_events[-200:]

    def _projection_frontier_event(
        self,
        ref: RepresentationalRef,
        *,
        outcome: str,
        projection_count: int,
        attempted_count: int,
    ) -> None:
        self._projection_state()
        self._projection_events.append({
            "ref": ref.encode(),
            "projection_id": None,
            "projected_ref": None,
            "pressure_perspective": [],
            "exposed_fields": {},
            "source_ref": None,
            "outcome": outcome,
            "evaluation": {
                "projection_count": int(projection_count),
                "attempted_count": int(attempted_count),
            },
        })
        self._projection_events = self._projection_events[-200:]

    def recent_projection_events(self, limit=50):
        self._projection_state()
        return list(self._projection_events[-max(0, int(limit)):])

    def _projection_sources_for_ref(
        self, ref: RepresentationalRef
    ) -> List[Tuple[str, RepresentationalRef, Dict[str, Any]]]:
        """Read the complete currently available structural frontier once.

        Projection should be able to use a whole real sibling representation,
        including combinations of fields that field-by-field candidate
        deduplication could otherwise hide. We therefore query genealogy's
        existing collision/gap search directly and preserve every distinct
        counterpart ref it returns. The search itself is still bounded by
        genealogy's native machinery; this layer adds no new exhaustive scan.
        """
        unresolved = ref.unresolved_fields()
        if not unresolved or self.inadequacy_pressure(ref) <= 0.0:
            return []

        ability_id = self.ensure_registered(ref)
        coarse_key = ref.encode()
        from aurora_internal.constraint_genealogy import TraceItem

        sources: Dict[str, Tuple[str, RepresentationalRef, Dict[str, Any]]] = {}
        for finder_name, finder in (
            ("collision", self.genealogy.representation_collision_candidates),
            ("gap", self.genealogy.representation_gap_candidates),
        ):
            try:
                found = finder([TraceItem(kind="ABILITY", id=ability_id)])
            except Exception:
                found = []
            self._cost_ledger[coarse_key] = (
                self._cost_ledger.get(coarse_key, 0.0) + float(len(found))
            )
            for entry in found:
                counterpart_id = str(entry.get("counterpart_representation_id", "") or "")
                if not counterpart_id or counterpart_id in sources:
                    continue
                counterpart_ref = self._ref_from_ability_id(counterpart_id)
                if counterpart_ref is None:
                    continue
                sources[counterpart_id] = (
                    counterpart_id,
                    counterpart_ref,
                    {
                        "structural_finder": finder_name,
                        "structural_inquiry_id": str(
                            entry.get("collision_id") or entry.get("gap_id") or ""
                        ),
                        "structural_pressure": float(entry.get("pressure", 0.0) or 0.0),
                        **dict(entry.get("evidence", {}) or {}),
                    },
                )
        return list(sources.values())

    def _stage_field_after_projection(self, ref, candidates, consumer, context_scope):
        if not candidates:
            return None
        key = ref.encode()
        candidate = min(
            candidates,
            key=lambda item: (
                self._candidate_attempt_counts.get(
                    self._candidate_attempt_key(
                        key, str(item.get("field", "")), item.get("candidate_value")
                    ),
                    0,
                ),
                self._candidate_attempt_key(
                    key, str(item.get("field", "")), item.get("candidate_value")
                ),
            ),
        )
        staged = self.stage_field_inquiry(ref, candidate, consumer=consumer)
        if not staged:
            return None
        self._active_stage_for_ref[key] = {
            "mode": "field_inquiry",
            "stage": staged[0],
            "candidate": candidate,
            "consumer": consumer,
            "context_scope": context_scope,
            "candidate_selection": "least_tested_then_canonical_neutral_tie",
        }
        self._provisional_reads[key] = 0
        self._candidate_downstream_effects.pop(key, None)
        return self._active_stage_for_ref[key]

    def investigate_if_pressured(self, ref, *, consumer="auto", context_scope=None):
        self._projection_state()
        if self._projection_resolution_hold:
            return None
        key = ref.encode()
        if key in self._active_stage_for_ref or self.inadequacy_pressure(ref) <= 0.0:
            return None

        # First look through every currently available *real structural*
        # mirror. Only one view is staged at a time, so representational cost
        # remains progressive even though the epistemic frontier is complete.
        structural_sources = self._projection_sources_for_ref(ref)
        projections = build_perspective_projections(
            ref, structural_sources, max_projections=None
        )
        untried = [
            projection
            for projection in projections
            if self._projection_attempt_counts.get(projection["projection_id"], 0) == 0
        ]
        if untried:
            candidate = untried[0]
            self._active_stage_for_ref[key] = {
                "mode": "perspective_projection",
                "stage": None,
                "candidate": candidate,
                "consumer": consumer,
                "context_scope": context_scope,
                "candidate_selection": "progressive_least_dimensional_then_structural_pressure",
                "available_projection_count": len(projections),
            }
            self._provisional_reads[key] = 0
            self._candidate_downstream_effects.pop(key, None)
            self._projection_event(ref, self._active_stage_for_ref[key], "staged")
            return self._active_stage_for_ref[key]

        # A real structural frontier existed and every distinct view currently
        # available from it has failed. This explicit barrier is what permits
        # Build 714 to buy new representational resolution.
        if projections:
            self._projection_frontier_event(
                ref,
                outcome="frontier_exhausted",
                projection_count=len(projections),
                attempted_count=sum(
                    1
                    for projection in projections
                    if self._projection_attempt_counts.get(projection["projection_id"], 0) > 0
                ),
            )

        capacity = _complete_candidate_capacity(ref)
        candidates = self.unresolved_field_candidates(
            ref, max_candidates=max(1, capacity)
        )
        if not candidates:
            return None
        return self._stage_field_after_projection(ref, candidates, consumer, context_scope)

    def provisional_resolution(self, ref):
        self._projection_state()
        key = ref.encode()
        pending = self._active_stage_for_ref.get(key)
        if pending is None or pending.get("mode") != "perspective_projection":
            return super().provisional_resolution(ref)
        try:
            view = RepresentationalRef.decode(str(pending["candidate"]["projected_ref"]))
        except Exception:
            return self.current_resolution(ref)
        self._provisional_reads[key] = self._provisional_reads.get(key, 0) + 1
        return view

    def record_candidate_downstream_effect(
        self,
        ref,
        *,
        consumer,
        downstream_difference,
        action_or_prediction_affected,
        baseline_expectation=None,
        conditioned_expectation=None,
        metadata=None,
    ):
        self._projection_state()
        key = ref.encode()
        pending = self._active_stage_for_ref.get(key)
        if pending is None or pending.get("mode") != "perspective_projection":
            return super().record_candidate_downstream_effect(
                ref,
                consumer=consumer,
                downstream_difference=downstream_difference,
                action_or_prediction_affected=action_or_prediction_affected,
                baseline_expectation=baseline_expectation,
                conditioned_expectation=conditioned_expectation,
                metadata=metadata,
            )
        if not self._has_material_downstream_difference(downstream_difference):
            return None
        candidate = dict(pending.get("candidate") or {})
        try:
            projected = RepresentationalRef.decode(str(candidate.get("projected_ref") or ""))
        except Exception:
            return None
        record = {
            "mode": "perspective_projection",
            "candidate_field": candidate.get("field"),
            "candidate_value": candidate.get("candidate_value"),
            "projection_id": candidate.get("projection_id"),
            "pressure_perspective": list(candidate.get("pressure_perspective") or ()),
            "exposed_fields": dict(candidate.get("exposed_fields") or {}),
            "source_ref": candidate.get("source_ref"),
            "representation_without_candidate": self.current_resolution(ref).encode(),
            "representation_with_candidate": projected.encode(),
            "downstream_difference_produced": downstream_difference,
            "action_prediction_affected": action_or_prediction_affected,
            "baseline_expectation": dict(baseline_expectation or {}),
            "conditioned_expectation": dict(conditioned_expectation or {}),
            "consumer": str(consumer or ""),
            "metadata": dict(metadata or {}),
            "recorded_at": _base._now(),
        }
        self._candidate_downstream_effects[key] = record
        return dict(record)

    def _projection_consequence(self, ref, pending, candidate_evaluation):
        key = ref.encode()
        reads = int(self._provisional_reads.get(key, 0) or 0)
        effect = dict(self._candidate_downstream_effects.pop(key, None) or {})
        evaluation = dict(effect)
        evaluation.update(dict(candidate_evaluation or {}))
        if reads <= 0:
            return "untested"
        has_effect = bool(effect) and self._has_material_downstream_difference(
            effect.get("downstream_difference_produced")
        )
        try:
            better = (
                evaluation.get("actual_consequence") is not None
                and float(evaluation.get("candidate_conditioned_error")) + _EPS
                < float(evaluation.get("baseline_error"))
            )
        except (TypeError, ValueError):
            better = False
        self._provisional_reads[key] = 0
        if has_effect and better:
            self._projection_event(ref, pending, "adequate", evaluation)
            return "adequate"
        pid = str((pending.get("candidate") or {}).get("projection_id") or "")
        if pid:
            self._projection_attempt_counts[pid] = (
                self._projection_attempt_counts.get(pid, 0) + 1
            )
        self._projection_event(ref, pending, "failed", evaluation)
        return "failed"

    def record_pressure_observation(
        self,
        ref,
        *,
        pressure_before,
        pressure_after,
        source,
        context_tag="",
        extra_trace=None,
        notes=None,
        consumer="observer",
    ):
        """Record consequence pressure without claiming projection consumption.

        Some systems carry a RepresentationalRef only as provenance while
        evaluating their own world-state evidence. Their observation is valid
        evidence that the current representation may be inadequate, but it is
        not evidence that a staged projected/refined value participated in the
        calculation. Such observers therefore may update genealogy pressure
        while neither staging nor completing a resolution experiment.
        """
        self._projection_state()
        previous_hold = self._projection_resolution_hold
        self._projection_resolution_hold = True
        try:
            return _BaseEngine.record_participation(
                self,
                ref,
                pressure_before=pressure_before,
                pressure_after=pressure_after,
                source=source,
                context_tag=context_tag,
                extra_trace=extra_trace,
                notes=notes,
                consumer=consumer,
                candidate_evaluation=None,
            )
        finally:
            self._projection_resolution_hold = previous_hold

    def record_participation(
        self,
        ref,
        *,
        pressure_before,
        pressure_after,
        source,
        context_tag="",
        extra_trace=None,
        notes=None,
        consumer="auto",
        candidate_evaluation=None,
    ):
        self._projection_state()
        key = ref.encode()
        pending = self._active_stage_for_ref.get(key)
        if pending is None or pending.get("mode") != "perspective_projection":
            return super().record_participation(
                ref,
                pressure_before=pressure_before,
                pressure_after=pressure_after,
                source=source,
                context_tag=context_tag,
                extra_trace=extra_trace,
                notes=notes,
                consumer=consumer,
                candidate_evaluation=candidate_evaluation,
            )
        self._active_stage_for_ref.pop(key, None)
        previous_hold = self._projection_resolution_hold
        self._projection_resolution_hold = True
        try:
            result = super().record_participation(
                ref,
                pressure_before=pressure_before,
                pressure_after=pressure_after,
                source=source,
                context_tag=context_tag,
                extra_trace=extra_trace,
                notes=notes,
                consumer=consumer,
                candidate_evaluation=None,
            )
        finally:
            self._projection_resolution_hold = previous_hold
        outcome = self._projection_consequence(ref, pending, candidate_evaluation)
        if outcome == "adequate" and self.inadequacy_pressure(ref) <= 0.0:
            self._projection_event(ref, pending, "released_pressure_resolved")
        elif outcome in ("adequate", "untested"):
            self._active_stage_for_ref[key] = pending
        else:
            self.investigate_if_pressured(
                ref,
                consumer=str(pending.get("consumer") or consumer),
                context_scope=pending.get("context_scope"),
            )
        return result


def get_or_create_engine(
    systems: Optional[Dict[str, Any]]
) -> Optional[RepresentationalResolutionEngine]:
    if not systems:
        return None
    existing = systems.get("representational_resolution_engine")
    if isinstance(existing, RepresentationalResolutionEngine):
        existing._projection_state()
        return existing
    if isinstance(existing, _BaseEngine):
        upgraded = RepresentationalResolutionEngine.__new__(RepresentationalResolutionEngine)
        upgraded.__dict__.update(existing.__dict__)
        upgraded._projection_state()
        systems["representational_resolution_engine"] = upgraded
        return upgraded
    if existing is not None:
        return existing
    genealogy = systems.get("genealogy")
    if genealogy is None:
        return None
    engine = RepresentationalResolutionEngine(
        genealogy, state_dir=systems.get("state_dir")
    )
    systems["representational_resolution_engine"] = engine
    return engine


def record_ref_participation_from_scores(
    systems,
    ref_encoded,
    dimension_scores,
    *,
    source,
    context_tag="",
    extra_trace_ids=None,
    candidate_evaluation=None,
):
    """Bridge real evaluation scores into resolution pressure.

    When ``candidate_evaluation`` is present, the caller has already supplied
    the causal before/after record required to test a provisional view, so the
    full projection/refinement participation path is allowed.

    Without ``candidate_evaluation`` the caller is an observational pressure
    source only. Its scores still update the canonical genealogy consequence
    profile, but it cannot stage or complete a representation experiment it
    did not actually consume.
    """
    if not ref_encoded or not dimension_scores:
        return
    engine = get_or_create_engine(systems)
    if engine is None:
        return
    try:
        ref = RepresentationalRef.decode(ref_encoded)
    except Exception:
        return
    axis = ref.nc_law_c if ref.nc_law_c in AXES else "X"
    others = [a for a in AXES if a != axis]
    avg = _base._clip01(
        sum(dimension_scores.values()) / max(1, len(dimension_scores))
    )
    unexplained = max(0.0, 1.0 - avg)
    before = {a: (1.0 if a == axis else 0.0) for a in AXES}
    after = {
        a: (
            unexplained
            if a == axis
            else unexplained / max(1, len(others))
        )
        for a in AXES
    }
    from aurora_internal.constraint_genealogy import TraceItem
    trace = [
        TraceItem(kind="ABILITY", id=str(trace_id))
        for trace_id in (extra_trace_ids or [])
    ]
    try:
        if candidate_evaluation is None:
            engine.record_pressure_observation(
                ref,
                pressure_before=before,
                pressure_after=after,
                source=source,
                context_tag=context_tag,
                extra_trace=trace,
            )
        else:
            engine.record_participation(
                ref,
                pressure_before=before,
                pressure_after=after,
                source=source,
                context_tag=context_tag,
                extra_trace=trace,
                candidate_evaluation=candidate_evaluation,
            )
    except Exception:
        pass
