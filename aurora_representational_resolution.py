#!/usr/bin/env python3
"""Perspective-before-resolution extension for Aurora Build 714.

Build 714 remains the sole authority for retained representational growth.
Before it stages a field inquiry, this layer asks whether a real structurally
connected representation already contains the needed distinction and whether a
lawful X/T/N/B/A perspective can make that distinction legible transiently.

Projection is a view, never knowledge: it does not modify current_resolution,
_active_resolutions, resolution genealogy, SediMemory, or resolve_field().
Only failure of the complete currently-relevant structural projection frontier
permits the original Build 714 field-inquiry path to run.

Pressure observation and projection-capable consumption are intentionally
separate. A subsystem that merely reports consequence against a
RepresentationalRef may increase inadequacy pressure, but it may not stage or
complete a projection it never actually used. Real consumers opt into the
ordinary provisional-resolution/effect/evaluation chain, so an inquiry opens
from her own provisional read of something, not from raw traffic.

The structural mirror search is intentionally amortized. One inadequacy episode
builds a transient projection frontier once, consumes it one lens at a time,
and performs at most one structural refresh when that frontier is exhausted.
A hypothetical peek reads that cached frontier when one exists and otherwise
scans without charging cost or caching.

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
_SURFACE_EVIDENCE_PER_REF = 16

# On a device running as her surface, the shared inquiry's other end is home
# (aurora_internal.dual_strata.inquiry_tiers.SurfaceInquiryTier).  A whole-mind
# device and home itself never set it, so nothing changes for them.
_HOME_TIER: Any = None


def set_home_tier(tier: Any) -> None:
    """Join this device's inquiry to home's; ``None`` makes it whole again."""
    global _HOME_TIER
    _HOME_TIER = tier


def home_tier() -> Any:
    return _HOME_TIER


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


def _projection_view_key(candidate: Dict[str, Any]) -> str:
    """Identity of what the consumer can actually see, independent of lens/source."""
    payload = str(candidate.get("projected_ref") or "")
    return "rview_" + hashlib.sha256(payload.encode()).hexdigest()[:20]


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
    """Return lawful transient views from real connected sources.

    ``max_projections`` is only a caller-side work budget. ``None`` exposes the
    complete currently-relevant projection frontier. The engine uses that
    complete frontier before it may conclude that perspective is exhausted.
    """
    # Distinct lenses/sources that yield the same projected RepresentationalRef
    # are one consumable view; the least-dimensional lens wins, then the
    # strongest structural pressure, with projection identity a neutral tie.
    best_by_view: Dict[str, Dict[str, Any]] = {}
    for source_id, source_ref, evidence in sorted(structural_sources, key=lambda x: str(x[0])):
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
            item["projection_view_key"] = _projection_view_key(item)
            previous = best_by_view.get(item["projection_view_key"])
            if previous is None or _projection_priority(item) < _projection_priority(previous):
                best_by_view[item["projection_view_key"]] = item
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
        # One cached projection frontier per inadequacy episode, keyed by ref.
        # Cleared when the episode ends (pressure resolved or a field inquiry
        # completed).
        if not hasattr(self, "_projection_frontiers"):
            self._projection_frontiers = {}
        # The surface's end of a shared inquiry (only used while a home tier is
        # set).  _passed_home marks what was carried up and with how much lived
        # evidence; _surface_evidence keeps the recent lived consequences per
        # ref so home can feel what she lived; _home_waiting holds an
        # experiment home handed down while one of her own lenses was mid-test.
        if not hasattr(self, "_passed_home"):
            self._passed_home = {}
        if not hasattr(self, "_surface_evidence"):
            self._surface_evidence = {}
        if not hasattr(self, "_surface_evidence_count"):
            self._surface_evidence_count = {}
        if not hasattr(self, "_home_waiting"):
            self._home_waiting = {}

    def _projection_event(self, ref, pending, outcome, evaluation=None):
        self._projection_state()
        candidate = dict(pending.get("candidate") or {})
        self._projection_events.append({
            "ref": ref.encode(),
            "projection_id": candidate.get("projection_id"),
            "projection_view_key": candidate.get("projection_view_key"),
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
            "projection_view_key": None,
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

    def _structural_projection_candidates(self, ref, *, charge_cost: bool) -> List[Dict[str, Any]]:
        """Search every real structural counterpart without domain hypotheses.

        Build 714's normal candidate generator intentionally caps itself at
        ``MAX_CANDIDATE_FIELDS_PER_PASS`` and may register lawful-domain
        hypotheses when no sibling exists. Neither behavior is appropriate for
        deciding whether the *structural projection frontier* is exhausted.

        This scan reuses genealogy's collision/gap finders and the same field
        extraction rule, but has no candidate-count cutoff. ``charge_cost`` is
        True only for lived investigation. A hypothetical possibility peek uses
        False, so rejected futures cannot alter Build 714's cost ledger.
        """
        unresolved = ref.unresolved_fields()
        if not unresolved:
            return []
        ability_id = self.ability_id_for_ref(ref)
        if ability_id not in getattr(self.genealogy, "abilities", {}):
            return []

        from aurora_internal.constraint_genealogy import TraceItem

        candidates: List[Dict[str, Any]] = []
        seen_values = {field_name: set() for field_name in unresolved}
        coarse_key = ref.encode()
        for finder_name, finder in (
            ("collision", self.genealogy.representation_collision_candidates),
            ("gap", self.genealogy.representation_gap_candidates),
        ):
            try:
                found = finder([TraceItem(kind="ABILITY", id=ability_id)])
            except Exception:
                found = []
            if charge_cost:
                self._cost_ledger[coarse_key] = (
                    self._cost_ledger.get(coarse_key, 0.0) + float(len(found))
                )
            for entry in found:
                counterpart_id = str(entry.get("counterpart_representation_id", "") or "")
                counterpart_ref = self._ref_from_ability_id(counterpart_id)
                if counterpart_ref is None:
                    continue
                for field_name in unresolved:
                    value = getattr(counterpart_ref, field_name, None)
                    if value is None or value in seen_values[field_name]:
                        continue
                    seen_values[field_name].add(value)
                    candidates.append({
                        "field": field_name,
                        "candidate_value": value,
                        "source": f"{finder_name}:{entry.get('collision_id') or entry.get('gap_id') or counterpart_id}",
                        "inquiry_id": str(entry.get("collision_id") or entry.get("gap_id") or ""),
                        "counterpart_ability_id": counterpart_id,
                        "evidence": dict(entry.get("evidence", {}) or {}),
                        "pressure": float(entry.get("pressure", 0.0) or 0.0),
                        "origin": finder_name,
                    })
        return candidates

    def _projection_sources(self, candidates):
        sources = {}
        for c in candidates:
            if str(c.get("origin") or "") == "domain_hypothesis":
                continue
            sid = str(c.get("counterpart_ability_id") or "")
            if not sid or sid in sources:
                continue
            src = self._ref_from_ability_id(sid)
            if src is not None:
                sources[sid] = (sid, src, dict(c.get("evidence") or {}))
        return list(sources.values())

    def _projection_frontier(self, ref, candidates):
        return build_perspective_projections(
            ref, self._projection_sources(candidates), max_projections=None,
        )

    def _candidate_pool(self, ref: RepresentationalRef) -> List[Dict[str, Any]]:
        """Ask Build 714 for the full typed candidate capacity when supported."""
        capacity = max(1, _complete_candidate_capacity(ref))
        try:
            return list(
                self.unresolved_field_candidates(ref, max_candidates=capacity) or []
            )
        except TypeError:
            return list(self.unresolved_field_candidates(ref) or [])

    def _projection_sources_from_candidates(
        self, candidates: Sequence[Dict[str, Any]]
    ) -> List[Tuple[str, RepresentationalRef, Dict[str, Any]]]:
        sources: Dict[str, Tuple[str, RepresentationalRef, Dict[str, Any]]] = {}
        for candidate in candidates:
            if str(candidate.get("origin") or "") == "domain_hypothesis":
                continue
            source_id = str(candidate.get("counterpart_ability_id") or "")
            if not source_id or source_id in sources:
                continue
            source_ref = self._ref_from_ability_id(source_id)
            if source_ref is None:
                continue
            evidence = dict(candidate.get("evidence") or {})
            evidence.setdefault(
                "structural_pressure", float(candidate.get("pressure", 0.0) or 0.0)
            )
            evidence.setdefault("candidate_source", str(candidate.get("source") or ""))
            sources[source_id] = (source_id, source_ref, evidence)
        return list(sources.values())

    @staticmethod
    def _field_candidates_from_structural_sources(
        ref: RepresentationalRef,
        sources: Sequence[Tuple[str, RepresentationalRef, Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        """Reuse the mirror scan as Build 714 field-candidate evidence.

        After every structural perspective has genuinely failed, there is no
        reason to rescan genealogy merely to recover the same counterpart
        field/value pairs. This reconstructs the ordinary Build 714 candidate
        shape from the already-returned real source refs and their native
        inquiry provenance. It grants no authority; the normal staged inquiry
        and consequence test still decide retention.
        """
        best: Dict[Tuple[str, Any], Dict[str, Any]] = {}
        for source_id, source_ref, evidence in sources:
            evidence = dict(evidence or {})
            finder = str(evidence.get("structural_finder") or "structural")
            inquiry_id = str(evidence.get("structural_inquiry_id") or "")
            try:
                pressure = float(evidence.get("structural_pressure", 0.0) or 0.0)
            except Exception:
                pressure = 0.0
            for field_name in ref.unresolved_fields():
                value = getattr(source_ref, field_name, None)
                if value is None:
                    continue
                key = (field_name, value)
                candidate = {
                    "field": field_name,
                    "candidate_value": value,
                    "source": f"{finder}:{inquiry_id or source_id}",
                    "inquiry_id": inquiry_id,
                    "counterpart_ability_id": str(source_id),
                    "evidence": dict(evidence),
                    "pressure": pressure,
                }
                previous = best.get(key)
                if previous is None or (
                    -pressure,
                    str(source_id),
                ) < (
                    -float(previous.get("pressure", 0.0) or 0.0),
                    str(previous.get("counterpart_ability_id") or ""),
                ):
                    best[key] = candidate
        return [best[key] for key in sorted(best, key=lambda item: (item[0], str(item[1])))]

    def _native_structural_finders_available(self) -> bool:
        return any(
            callable(getattr(self.genealogy, name, None))
            for name in (
                "representation_collision_candidates",
                "representation_gap_candidates",
            )
        )

    def _projection_sources_for_ref(
        self, ref: RepresentationalRef
    ) -> List[Tuple[str, RepresentationalRef, Dict[str, Any]]]:
        """Read the currently available real structural mirror sources.

        Production prefers genealogy's native collision/gap search so a whole
        counterpart representation remains visible even when several of its
        fields duplicate values found elsewhere. Alternate/test genealogies
        without those finder methods fall back to Build 714's candidate
        surface. Domain hypotheses are never accepted as mirrors.
        """
        unresolved = ref.unresolved_fields()
        if not unresolved or self.inadequacy_pressure(ref) <= 0.0:
            return []

        finder_specs = (
            ("collision", getattr(self.genealogy, "representation_collision_candidates", None)),
            ("gap", getattr(self.genealogy, "representation_gap_candidates", None)),
        )
        if not self._native_structural_finders_available():
            return self._projection_sources_from_candidates(self._candidate_pool(ref))

        ability_id = self.ensure_registered(ref)
        coarse_key = ref.encode()
        from aurora_internal.constraint_genealogy import TraceItem

        sources: Dict[str, Tuple[str, RepresentationalRef, Dict[str, Any]]] = {}
        for finder_name, finder in finder_specs:
            if not callable(finder):
                continue
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

    def _discover_projection_frontier(self, ref: RepresentationalRef) -> Dict[str, Any]:
        sources = self._projection_sources_for_ref(ref)
        projections = build_perspective_projections(
            ref, sources, max_projections=None
        )
        return {
            "projections": projections,
            "sources": list(sources),
            "structural_candidates": self._field_candidates_from_structural_sources(
                ref, sources
            ),
            "source_count": len(sources),
            "refresh_used": False,
        }

    def _frontier_for_ref(self, ref: RepresentationalRef) -> Dict[str, Any]:
        self._projection_state()
        key = ref.encode()
        frontier = self._projection_frontiers.get(key)
        if not isinstance(frontier, dict):
            frontier = self._discover_projection_frontier(ref)
            self._projection_frontiers[key] = frontier
        return frontier

    def _projection_was_attempted(self, projection: Dict[str, Any]) -> bool:
        pid = str(projection.get("projection_id") or "")
        view_key = str(projection.get("projection_view_key") or "")
        return bool(
            (pid and self._projection_attempt_counts.get(pid, 0) > 0)
            or (view_key and self._projection_attempt_counts.get(view_key, 0) > 0)
        )

    def _refresh_frontier_once(
        self, ref: RepresentationalRef, frontier: Dict[str, Any]
    ) -> Dict[str, Any]:
        if frontier.get("refresh_used"):
            return frontier
        refreshed = self._discover_projection_frontier(ref)
        refreshed["refresh_used"] = True
        self._projection_frontiers[ref.encode()] = refreshed
        return refreshed

    def _stage_projection(
        self,
        ref: RepresentationalRef,
        candidate: Dict[str, Any],
        *,
        consumer: str,
        context_scope: Optional[str],
        available_projection_count: int,
    ) -> Dict[str, Any]:
        key = ref.encode()
        self._active_stage_for_ref[key] = {
            "mode": "perspective_projection",
            "stage": None,
            "candidate": candidate,
            "consumer": consumer,
            "context_scope": context_scope,
            "candidate_selection": "progressive_least_dimensional_then_structural_pressure",
            "available_projection_count": int(available_projection_count),
        }
        self._provisional_reads[key] = 0
        self._candidate_downstream_effects.pop(key, None)
        self._projection_event(ref, self._active_stage_for_ref[key], "staged")
        return self._active_stage_for_ref[key]

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

    def _field_candidates_after_frontier(
        self, ref: RepresentationalRef, frontier: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        if not self._native_structural_finders_available():
            # The frontier came from Build 714's candidate surface, not a
            # native scan, so ask that surface again at full typed capacity.
            return self._candidate_pool(ref)
        structural = list(frontier.get("structural_candidates") or [])
        if structural:
            return structural
        # We already performed the native structural scan and found no real
        # mirror. Go directly to Build 714's lawful-domain bootstrap rather
        # than paying for the same empty search again, with Build 714's own
        # per-pass bound.  Domain hypotheses are not evidence, and the bound is
        # what walks them one field at a time: at full capacity every
        # unresolved field is offered at once, and a finer field (sub_law_d,
        # col_law_d) can be staged before the field it refines, where its
        # provisional view changes nothing downstream and is never evaluated.
        return list(self._bootstrap_domain_hypotheses(
            ref,
            ref.unresolved_fields(),
            _base.MAX_CANDIDATE_FIELDS_PER_PASS,
        ) or [])

    # ── The surface's end of a shared inquiry ──────────────────────────────

    def _tier(self) -> Any:
        """The home end of this engine's inquiry, or None when this engine is
        the whole mind or is home itself."""
        if getattr(self, "_is_home", False):
            return None
        return _HOME_TIER

    def _note_surface_evidence(self, ref, *, pressure_before, pressure_after, source,
                               context_tag="", consumer=""):
        """Keep what she lived against this ref, so home can feel it too."""
        if self._tier() is None:
            return
        from aurora_internal.dual_strata.inquiry_tiers import pressure_dict
        self._projection_state()
        key = ref.encode()
        items = self._surface_evidence.setdefault(key, [])
        items.append({
            "pressure_before": pressure_dict(pressure_before),
            "pressure_after": pressure_dict(pressure_after),
            "source": str(source or ""), "context_tag": str(context_tag or ""),
            "consumer": str(consumer or ""), "at": _base._now(),
        })
        del items[:-_SURFACE_EVIDENCE_PER_REF]
        self._surface_evidence_count[key] = int(self._surface_evidence_count.get(key, 0)) + 1

    def _adopt_home_stage(self, key, record):
        self._active_stage_for_ref[key] = {
            "mode": "home_inquiry",
            "stage": None,
            "candidate": dict(record.get("candidate") or {}),
            "view": str(record.get("view") or ""),
            "stage_mode": str(record.get("stage_mode") or ""),
            "inquiry_id": str(record.get("inquiry_id") or ""),
            "consumer": record.get("consumer"),
            "context_scope": record.get("context_scope"),
            "candidate_selection": "staged_at_home",
        }
        self._provisional_reads[key] = 0
        self._candidate_downstream_effects.pop(key, None)
        try:
            self._projection_event(RepresentationalRef.decode(key),
                                   self._active_stage_for_ref[key], "home_inquiry_adopted")
        except Exception:
            pass

    def _take_home_inquiries(self) -> None:
        """Adopt what home handed down; drop what home has closed."""
        tier = self._tier()
        if tier is None:
            return
        self._projection_state()
        try:
            records = list(tier.inbox() or [])
        except Exception:
            records = []
        for record in records:
            key = str(record.get("ref") or "")
            kind = str(record.get("kind") or "")
            if not key:
                continue
            pending = self._active_stage_for_ref.get(key)
            if kind == "stage":
                if pending is not None and pending.get("mode") == "perspective_projection":
                    self._home_waiting[key] = dict(record)   # her own lens finishes first
                else:
                    self._adopt_home_stage(key, record)
            elif kind == "closed":
                inquiry_id = str(record.get("inquiry_id") or "")
                if (pending is not None and pending.get("mode") == "home_inquiry"
                        and (not inquiry_id or pending.get("inquiry_id") == inquiry_id)):
                    self._active_stage_for_ref.pop(key, None)
                    self._provisional_reads[key] = 0
                    self._candidate_downstream_effects.pop(key, None)
                waiting = self._home_waiting.get(key)
                if waiting is not None and (not inquiry_id or waiting.get("inquiry_id") == inquiry_id):
                    self._home_waiting.pop(key, None)
                mark = self._passed_home.get(key)
                if mark is not None:
                    mark["home_outcome"] = str(record.get("outcome") or "closed")
                try:
                    self._projection_frontier_event(RepresentationalRef.decode(key),
                                                    outcome="home_inquiry_closed",
                                                    projection_count=0, attempted_count=0)
                except Exception:
                    pass
        for key, record in list(self._home_waiting.items()):
            if key not in self._active_stage_for_ref:
                self._home_waiting.pop(key, None)
                self._adopt_home_stage(key, record)

    def _pass_inquiry_home(self, ref, frontier, consumer, context_scope):
        """Her lenses here are spent and the pressure remains: what is left is
        retained growth, which lives at home.  Carry the question up with what
        she lived, once per new piece of lived evidence."""
        key = ref.encode()
        count = int(self._surface_evidence_count.get(key, 0))
        mark = self._passed_home.get(key)
        if mark is not None and count <= int(mark.get("evidence_count", -1)):
            return None
        projections = list((frontier or {}).get("projections") or [])
        sent_before = int((mark or {}).get("evidence_count", 0))
        evidence = list(self._surface_evidence.get(key) or [])
        new = evidence[-max(0, count - sent_before):] if mark is not None else evidence
        payload = {
            "ref": key,
            "pressure": float(self.inadequacy_pressure(ref)),
            "frontier": {
                "projection_count": len(projections),
                "attempted_count": sum(1 for p in projections if self._projection_was_attempted(p)),
            },
            "consumer": str(consumer or ""),
            "context_scope": context_scope,
            "evidence": new,
        }
        try:
            sent = bool(self._tier().pass_up(payload))
        except Exception:
            sent = False
        if not sent:
            return None
        self._passed_home[key] = {"at": _base._now(), "evidence_count": count,
                                  "consumer": consumer, "context_scope": context_scope}
        self._projection_frontier_event(ref, outcome="passed_home",
                                        projection_count=payload["frontier"]["projection_count"],
                                        attempted_count=payload["frontier"]["attempted_count"])
        return {"mode": "passed_home", "ref": key, "evidence_sent": len(new)}

    def investigate_if_pressured(self, ref, *, consumer="auto", context_scope=None):
        self._projection_state()
        if self._projection_resolution_hold:
            return None
        self._take_home_inquiries()
        key = ref.encode()
        if key in self._active_stage_for_ref or self.inadequacy_pressure(ref) <= 0.0:
            return None

        # Discover mirrors once, then progressively spend only one projected
        # view at a time. Failed lenses do not trigger another genealogy scan.
        frontier = self._frontier_for_ref(ref)
        projections = list(frontier.get("projections") or [])
        untried = [
            projection for projection in projections
            if not self._projection_was_attempted(projection)
        ]
        if untried:
            return self._stage_projection(
                ref,
                untried[0],
                consumer=consumer,
                context_scope=context_scope,
                available_projection_count=len(projections),
            )

        # At the apparent end of the cached frontier, permit exactly one fresh
        # structural scan. If a newly available view appears, consume it before
        # resolution. Otherwise this inadequacy episode has genuinely exhausted
        # every structural perspective currently available to Aurora.
        if projections and not frontier.get("refresh_used"):
            frontier = self._refresh_frontier_once(ref, frontier)
            projections = list(frontier.get("projections") or [])
            untried = [
                projection for projection in projections
                if not self._projection_was_attempted(projection)
            ]
            if untried:
                return self._stage_projection(
                    ref,
                    untried[0],
                    consumer=consumer,
                    context_scope=context_scope,
                    available_projection_count=len(projections),
                )

        if projections:
            self._projection_frontier_event(
                ref,
                outcome="frontier_exhausted",
                projection_count=len(projections),
                attempted_count=sum(
                    1 for projection in projections
                    if self._projection_was_attempted(projection)
                ),
            )

        if self._tier() is not None:
            return self._pass_inquiry_home(ref, frontier, consumer, context_scope)
        candidates = self._field_candidates_after_frontier(ref, frontier)
        if not candidates:
            return None
        return self._stage_field_after_projection(ref, candidates, consumer, context_scope)

    def _projection_view_record(self, ref, candidate, *, consumer, context_scope, observed):
        try:
            view = RepresentationalRef.decode(str(candidate.get("projected_ref") or ""))
        except Exception:
            return None
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
            "observed": bool(observed),
        }

    def peek_projection(self, ref, *, consumer="hypothetical", context_scope=None):
        """Pure projection lookup for an uncommitted hypothetical branch.

        It never stages an inquiry, increments a read counter, writes a
        projection event, changes attempt state, charges search cost, or creates
        a domain-hypothesis registration. Rejected possibility branches can
        inspect the mirror without entering lived representational development.
        """
        self._projection_state()
        key = ref.encode()
        pending = self._active_stage_for_ref.get(key)
        if pending is not None:
            if pending.get("mode") != "perspective_projection":
                return None
            return self._projection_view_record(
                ref,
                dict(pending.get("candidate") or {}),
                consumer=consumer,
                context_scope=context_scope,
                observed=False,
            )

        ability_id = self.ability_id_for_ref(ref)
        if ability_id not in getattr(self.genealogy, "abilities", {}):
            return None
        if self.inadequacy_pressure(ref) <= 0.0:
            return None

        frontier = self._projection_frontiers.get(key)
        if isinstance(frontier, dict):
            projections = list(frontier.get("projections") or [])
        else:
            structural = self._structural_projection_candidates(ref, charge_cost=False)
            if not structural:
                return None
            projections = self._projection_frontier(ref, structural)
        untried = [p for p in projections if not self._projection_was_attempted(p)]
        if not untried:
            return None
        candidate = dict(untried[0])
        candidate["projection_frontier_size"] = len(projections)
        candidate["projection_frontier_remaining"] = len(untried)
        return self._projection_view_record(
            ref, candidate, consumer=consumer, context_scope=context_scope, observed=False,
        )

    def provisional_resolution(
        self,
        ref,
        *,
        consumer="provisional_reader",
        context_scope=None,
    ):
        """Return the current earned/provisional view and make demand causal.

        A pressure observer never stages an optic. The first real subsystem
        that actually asks to *use* a provisional representation is therefore
        the lawful demand edge: if inadequacy exists and no experiment is
        active, this read opens the perspective frontier (or, only after its
        exhaustion/unavailability, Build 714's ordinary field inquiry) before
        returning the view. Existing one-argument callers remain compatible.
        """
        self._projection_state()
        self._take_home_inquiries()
        key = ref.encode()
        pending = self._active_stage_for_ref.get(key)
        if pending is None and self.inadequacy_pressure(ref) > 0.0:
            self.investigate_if_pressured(
                ref,
                consumer=str(consumer or "provisional_reader"),
                context_scope=context_scope,
            )
            pending = self._active_stage_for_ref.get(key)
        if pending is not None and pending.get("mode") == "home_inquiry":
            # The experiment is home's; she reads its view here, where its
            # consequence will arrive.
            try:
                view = RepresentationalRef.decode(str(pending.get("view") or ""))
            except Exception:
                return self.current_resolution(ref)
            self._provisional_reads[key] = self._provisional_reads.get(key, 0) + 1
            return view
        if pending is None or pending.get("mode") != "perspective_projection":
            return super().provisional_resolution(ref)
        try:
            view = RepresentationalRef.decode(str(pending["candidate"]["projected_ref"]))
        except Exception:
            return self.current_resolution(ref)
        self._provisional_reads[key] = self._provisional_reads.get(key, 0) + 1
        return view

    def consume_projection(self, ref, *, consumer="cognition", context_scope=None):
        """Common causal doorway for an actual representational consumer."""
        self._projection_state()
        key = ref.encode()
        if key not in self._active_stage_for_ref:
            self.investigate_if_pressured(ref, consumer=consumer, context_scope=context_scope)
        pending = self._active_stage_for_ref.get(key)
        if pending is None or pending.get("mode") != "perspective_projection":
            return None
        view = self.provisional_resolution(ref)
        candidate = dict(pending.get("candidate") or {})
        record = self._projection_view_record(
            ref, candidate, consumer=consumer, context_scope=context_scope, observed=True,
        )
        if record is not None:
            record["projected_ref"] = view.encode()
        return record

    def actualize_projection_use(self, ref, peeked_view, *, consumer,
                                 downstream_difference=None,
                                 action_or_prediction_affected="cognition"):
        """Commit projection participation only for an actualized branch."""
        self._projection_state()
        expected_id = str((peeked_view or {}).get("projection_id") or "")
        observed = self.consume_projection(
            ref,
            consumer=consumer,
            context_scope=(peeked_view or {}).get("context_scope"),
        )
        if not observed or str(observed.get("projection_id") or "") != expected_id:
            return {"status": "projection_mismatch", "projection_id": expected_id}

        key = ref.encode()
        pending = self._active_stage_for_ref.get(key)
        if pending is None or pending.get("mode") != "perspective_projection":
            return {"status": "projection_unavailable", "projection_id": expected_id}

        difference = dict(downstream_difference or {})
        if self._has_material_downstream_difference(difference):
            self.record_candidate_downstream_effect(
                ref,
                consumer=consumer,
                downstream_difference=difference,
                action_or_prediction_affected=action_or_prediction_affected,
                baseline_expectation={"projection": False},
                conditioned_expectation={"projection": True},
                metadata={"projection_id": expected_id, "actualized_branch": True},
            )
            return {
                "status": "awaiting_consequence",
                "projection_id": expected_id,
                "downstream_difference": difference,
            }

        # The chosen branch used this view and it changed nothing downstream.
        # That lens is non-discriminating for the current inadequacy, so release
        # it and progressively widen to the next lawful perspective.
        self._active_stage_for_ref.pop(key, None)
        self._provisional_reads[key] = 0
        self._candidate_downstream_effects.pop(key, None)
        if expected_id:
            self._projection_attempt_counts[expected_id] = (
                self._projection_attempt_counts.get(expected_id, 0) + 1
            )
        self._projection_event(
            ref,
            pending,
            "non_discriminating",
            {"actualized_branch": True, "consumer": consumer},
        )
        self.investigate_if_pressured(
            ref,
            consumer=consumer,
            context_scope=(peeked_view or {}).get("context_scope"),
        )
        return {"status": "non_discriminating", "projection_id": expected_id}

    def record_candidate_downstream_effect(self, ref, *, consumer, downstream_difference,
                                           action_or_prediction_affected,
                                           baseline_expectation=None,
                                           conditioned_expectation=None, metadata=None):
        self._projection_state()
        key = ref.encode()
        pending = self._active_stage_for_ref.get(key)
        if pending is not None and pending.get("mode") == "home_inquiry":
            # Kept to travel home with the consequence; home seals it against
            # its own staged candidate.
            if not self._has_material_downstream_difference(downstream_difference):
                return None
            record = {
                "mode": "home_inquiry",
                "inquiry_id": pending.get("inquiry_id"),
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
        c = dict(pending.get("candidate") or {})
        try:
            projected = RepresentationalRef.decode(str(c.get("projected_ref") or ""))
        except Exception:
            return None
        record = {
            "mode": "perspective_projection",
            "candidate_field": c.get("field"),
            "candidate_value": c.get("candidate_value"),
            "projection_id": c.get("projection_id"),
            "pressure_perspective": list(c.get("pressure_perspective") or ()),
            "exposed_fields": dict(c.get("exposed_fields") or {}),
            "source_ref": c.get("source_ref"),
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
        effect = dict(self._candidate_downstream_effects.get(key, None) or {})
        evaluation = dict(effect)
        evaluation.update(dict(candidate_evaluation or {}))
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

        # A real consumer may have used the projection before reality supplies
        # the consequence needed to judge the lens. Missing evidence is not
        # failed perspective and cannot escalate retained resolution.
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
        if pid:
            self._projection_attempt_counts[pid] = self._projection_attempt_counts.get(pid, 0) + 1
        self._projection_event(ref, pending, "failed", evaluation)
        return "failed"

    def _clear_frontier_if_pressure_resolved(self, ref: RepresentationalRef) -> None:
        self._projection_state()
        if self.inadequacy_pressure(ref) <= 0.0:
            key = ref.encode()
            self._projection_frontiers.pop(key, None)
            # This episode is over here; a new one passes up afresh.
            self._passed_home.pop(key, None)
            self._surface_evidence.pop(key, None)

    def complete_field_inquiry(self, ref, candidate, stage, **kwargs):
        """A completed real refinement experiment ends this optic episode."""
        try:
            return super().complete_field_inquiry(ref, candidate, stage, **kwargs)
        finally:
            self._projection_state()
            self._projection_frontiers.pop(ref.encode(), None)

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

        An observation is not a read: a real consumer's pending projection and
        its provisional read count stay exactly as that consumer left them.
        """
        self._projection_state()
        self._note_surface_evidence(ref, pressure_before=pressure_before,
                                    pressure_after=pressure_after, source=source,
                                    context_tag=context_tag, consumer=consumer)
        key = ref.encode()
        pending = self._active_stage_for_ref.get(key)
        reads_before = int(self._provisional_reads.get(key, 0) or 0)
        previous_hold = self._projection_resolution_hold
        self._projection_resolution_hold = True
        try:
            result = _BaseEngine.record_participation(
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
        if pending is not None and pending.get("mode") == "perspective_projection":
            self._active_stage_for_ref[key] = pending
            self._provisional_reads[key] = reads_before
        self._clear_frontier_if_pressure_resolved(ref)
        return result

    def record_participation(self, ref, *, pressure_before, pressure_after, source,
                             context_tag="", extra_trace=None, notes=None,
                             consumer="auto", candidate_evaluation=None):
        """A real consumer's participation: closes a staged projection's test."""
        self._projection_state()
        self._take_home_inquiries()
        key = ref.encode()
        pending = self._active_stage_for_ref.get(key)
        if pending is not None and pending.get("mode") == "home_inquiry":
            return self._participate_in_home_inquiry(
                ref, pending, pressure_before=pressure_before, pressure_after=pressure_after,
                source=source, context_tag=context_tag, extra_trace=extra_trace, notes=notes,
                consumer=consumer, candidate_evaluation=candidate_evaluation)
        self._note_surface_evidence(ref, pressure_before=pressure_before,
                                    pressure_after=pressure_after, source=source,
                                    context_tag=context_tag, consumer=consumer)
        if pending is None or pending.get("mode") != "perspective_projection":
            result = super().record_participation(
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
            self._clear_frontier_if_pressure_resolved(ref)
            return result

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
            self._projection_frontiers.pop(key, None)
        elif outcome in ("adequate", "untested", "pending_evidence"):
            self._active_stage_for_ref[key] = pending
        else:
            self.investigate_if_pressured(
                ref,
                consumer=str(pending.get("consumer") or consumer),
                context_scope=pending.get("context_scope"),
            )
        return result

    def _participate_in_home_inquiry(self, ref, pending, *, pressure_before, pressure_after,
                                     source, context_tag, extra_trace, notes, consumer,
                                     candidate_evaluation):
        """She lived a consequence of home's experiment here.  It is felt here
        as observation and goes home as evidence; only home completes it."""
        from aurora_internal.dual_strata.inquiry_tiers import pressure_dict
        key = ref.encode()
        self._active_stage_for_ref.pop(key, None)
        previous_hold = self._projection_resolution_hold
        self._projection_resolution_hold = True
        try:
            result = _BaseEngine.record_participation(
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
            self._active_stage_for_ref[key] = pending
        evidence = {
            "ref": key,
            "inquiry_id": pending.get("inquiry_id"),
            "pressure_before": pressure_dict(pressure_before),
            "pressure_after": pressure_dict(pressure_after),
            "source": str(source or ""),
            "context_tag": str(context_tag or ""),
            "consumer": str(consumer or ""),
            "provisional_reads": int(self._provisional_reads.get(key, 0) or 0),
            "downstream_effect": self._candidate_downstream_effects.get(key),
            "candidate_evaluation": dict(candidate_evaluation) if candidate_evaluation else None,
        }
        try:
            tier = self._tier()
            sent = bool(tier is not None and tier.send_evidence(evidence))
        except Exception:
            sent = False
        if sent:
            # Delivered reads and effects belong to home's ledger now.
            self._provisional_reads[key] = 0
            self._candidate_downstream_effects.pop(key, None)
        self._projection_event(ref, pending, "evidence_sent_home" if sent else "evidence_waiting",
                               {"consumer": consumer})
        return result


def get_or_create_engine(systems: Optional[Dict[str, Any]]) -> Optional[RepresentationalResolutionEngine]:
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
    engine = RepresentationalResolutionEngine(genealogy, state_dir=systems.get("state_dir"))
    systems["representational_resolution_engine"] = engine
    return engine


def peek_projection_for_ref(systems, ref_encoded, *, consumer="hypothetical", context_scope=None):
    """Pure bridge for uncommitted branches holding a real encoded ref."""
    if not ref_encoded:
        return None
    engine = get_or_create_engine(systems)
    if engine is None:
        return None
    try:
        ref = RepresentationalRef.decode(str(ref_encoded))
        return engine.peek_projection(ref, consumer=consumer, context_scope=context_scope)
    except Exception:
        return None


def consume_projection_for_ref(systems, ref_encoded, *, consumer="cognition", context_scope=None):
    """Observed-consumer bridge for an already-real encoded RepresentationalRef."""
    if not ref_encoded:
        return None
    engine = get_or_create_engine(systems)
    if engine is None:
        return None
    try:
        ref = RepresentationalRef.decode(str(ref_encoded))
        return engine.consume_projection(ref, consumer=consumer, context_scope=context_scope)
    except Exception:
        return None


def actualize_projection_for_ref(systems, peeked_view, *, consumer="cognition",
                                 downstream_difference=None,
                                 action_or_prediction_affected="cognition"):
    """Commit only projection use belonging to an actualized branch."""
    if not isinstance(peeked_view, dict) or not peeked_view.get("base_ref"):
        return None
    engine = get_or_create_engine(systems)
    if engine is None:
        return None
    try:
        ref = RepresentationalRef.decode(str(peeked_view.get("base_ref")))
        return engine.actualize_projection_use(
            ref,
            peeked_view,
            consumer=consumer,
            downstream_difference=downstream_difference,
            action_or_prediction_affected=action_or_prediction_affected,
        )
    except Exception:
        return None


def record_ref_participation_from_scores(systems, ref_encoded, dimension_scores, *, source,
                                         context_tag="", extra_trace_ids=None,
                                         candidate_evaluation=None):
    """Bridge real evaluation scores into resolution pressure.

    With ``candidate_evaluation`` the caller already supplies the causal
    before/after record that tests a provisional view, so the full
    projection/refinement path runs.  Without it the caller is an
    observational pressure source: its scores update the genealogy
    consequence profile, and the next real ``provisional_resolution()``
    reader opens the perspective frontier.
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
        # Scores with no candidate evaluation are observation: they build
        # inadequacy pressure but cannot stage or complete an inquiry.  Her
        # next real provisional read of this ref is the demand edge that opens
        # one.  Scores that carry a candidate evaluation come from a consumer
        # that used the provisional view, so they take the full path.
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
