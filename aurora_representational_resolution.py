#!/usr/bin/env python3
"""
aurora_representational_resolution.py

AURORA BUILD 714 -- NATIVE ADAPTIVE REPRESENTATIONAL RESOLUTION.

Closes the loop: "Aurora must remain at the least resolved representation
sufficient for the consequences she is presently trying to distinguish, and
autonomously acquire additional representational resolution only when
unresolved distinctions become operationally consequential."

This module is deliberately NOT a parallel learning subsystem. It is a thin
governor over machinery that already exists and is already load-bearing:

  RepresentationalRef (aurora_representational_address.py)
      A field left None IS "unresolved" -- already honest, already typed.
      This module never fabricates a field value; it only ever copies a
      value that some other real, structurally-connected representation
      already carries as ITS OWN independently-resolved field.

  ConstraintGenealogyLogger (aurora_internal/constraint_genealogy.py)
      .observe()                          the shared ~12-call-site relief
                                           convergence point (PressureVec in,
                                           PressureVec out, a trace of
                                           AbilityProfile/ConstraintLink ids).
      ._attribute_consequence()           already computes, per Ability, a
                                           confidence-weighted EMA "effect",
                                           a distinct_contexts count, and a
                                           "discrepancy" (declared axis vs
                                           measured effect) -- EXACTLY the
                                           representational-inadequacy signal
                                           directive Section 9 asks for. This
                                           module does not recompute it; it
                                           reads consequence_profile.
      .representation_collision_candidates() / .representation_gap_candidates()
                                           already search structurally-
                                           connected representations and
                                           surface "operational_discrepancy"
                                           evidence on every observe() tick.
                                           Field-candidate VALUES are pulled
                                           from these searches' real
                                           counterpart representations, never
                                           invented.
      .stage_representation_inquiry() / .complete_representation_experiment()
                                           the existing time-boxed,
                                           evidence-gated experiment harness.
                                           A candidate field value is never
                                           retained without passing through
                                           this exact machinery -- no second
                                           promotion authority.

How a RepresentationalRef participates: each distinct COARSE ref identity
(its currently-resolved fields, encoded) is registered, idempotently, as a
synthetic AbilityProfile in genealogy.abilities -- the identical pattern
aurora.py already uses a dozen times over (_ensure_pipeline_abilities,
_ensure_claim_relief_abilities, ...) for its own tracked concerns. The
ref's own encoded string and field breakdown live in that AbilityProfile's
existing `structured_state` extension point (built for exactly this kind of
opaque payload -- see its docstring in constraint_genealogy.py). No new
AbilityProfile field is added anywhere.

Governing invariant preserved throughout (directive Section 3/17):
    consequence_profile != perceptual meaning authority
This module never touches sensory routing (_effective_axis_for_node /
_dps_route_observation) and never asks "what does this perception mean" --
only "does my current representation distinguish the consequences that
actually occur." A field earns resolution solely through the ordinary
observe() -> _accumulate_pairs() -> PairStats -> _try_promote() chain that
every other genealogy consumer already uses; this module supplies no
alternate authority.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from aurora_representational_address import AXES, DIM_NAMES, RepresentationalRef, _FIELDS

# ── Tunables (this module's own, scoped config -- not a parallel currency;
#    values are gates on top of genealogy's own physics, same posture as
#    e.g. REPRESENTATION_COLLISION_CANDIDATES_PER_ITEM on genealogy's cfg) ──

MIN_DISTINCT_CONTEXTS_FOR_PRESSURE = 3       # one anomalous event never refines anything
MIN_CONFIDENCE_FOR_PRESSURE = 0.15
MIN_DISCREPANCY_FOR_PRESSURE = 0.12
MIN_DISCREPANCY_IMPROVEMENT_TO_RETAIN = 0.05  # resolution must actually help
MAX_CANDIDATE_FIELDS_PER_PASS = 4
RESOLUTION_EVENTS_MAXLEN = 2000


def _now() -> float:
    return time.time()


def _clip01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


@dataclass
class ResolutionOutcome:
    """One entry in the required Section 29 instrumentation stream."""
    event_id: str
    ref_before_encoded: str
    resolved_fields_before: Tuple[str, ...]
    unresolved_fields_before: Tuple[str, ...]
    pressure_source: str
    operational_discrepancy: float
    candidate_field: str
    candidate_values_considered: List[str]
    evidence_used: Dict[str, Any]
    inquiry_id: str
    ref_after_encoded: Optional[str]
    resolved_fields_after: Tuple[str, ...]
    discrepancy_before: float
    discrepancy_after: Optional[float]
    pressure_before: float
    pressure_after: Optional[float]
    slots_examined: int
    slots_materialized: int
    semantic_resolutions_requested: int
    computational_cost: float
    outcome: str  # "retained" | "rejected" | "unresolved" | "context_specific"
    context_scope: Optional[str]
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RepresentationalResolutionEngine:
    """The single governor. One instance shares genealogy's real state --
    it does not keep a shadow copy of anything genealogy already owns."""

    def __init__(self, genealogy: Any, *, state_dir: Optional[str] = None) -> None:
        self.genealogy = genealogy
        self.root: Optional[Path] = Path(state_dir) / "representational_resolution" if state_dir else None
        if self.root is not None:
            self.root.mkdir(parents=True, exist_ok=True)

        # Persisted ledgers. Keyed by the COARSE ref's encoded string so a
        # refined descendant is always reachable from its ancestor's key.
        self._genealogy_records: Dict[str, List[Dict[str, Any]]] = {}
        # Resolved refs actually in force right now, keyed by
        # (coarse_encoded, context_scope or "") -> refined encoded ref.
        self._active_resolutions: Dict[str, str] = {}
        self._resolution_events: List[Dict[str, Any]] = []
        self._cost_ledger: Dict[str, float] = {}
        self._load()

    # ── Registration: coarse ref <-> synthetic AbilityProfile ──────────────

    @staticmethod
    def ability_id_for_ref(ref: RepresentationalRef) -> str:
        """Deterministic id for this ref's CURRENTLY-resolved identity.
        Two refs with different resolved-field sets never collide even if
        the resolved values overlap, because encode() includes every field
        position (unresolved fields as '?')."""
        return "REFAB:" + ref.encode()[len("REF:"):]

    def ensure_registered(self, ref: RepresentationalRef, *, notes: str = "") -> str:
        """Idempotent. Creates the synthetic AbilityProfile the first time
        this exact coarse identity is seen; never mutates an existing one's
        consequence_profile (only genealogy's own _attribute_consequence
        does that, via observe())."""
        from aurora_internal.constraint_genealogy import AbilityProfile, _augment_ability_profile_with_origin

        ability_id = self.ability_id_for_ref(ref)
        if ability_id in getattr(self.genealogy, "abilities", {}):
            return ability_id

        axis = ref.nc_law_c if ref.nc_law_c in AXES else "X"
        ap = AbilityProfile(
            id=ability_id,
            axis=axis,
            requires=(axis,),
            cost={a: 0.0 for a in AXES},
            risk={a: 0.0 for a in AXES},
            effect_tags=(),
            notes=notes or "Build 714 synthetic ability for a RepresentationalRef identity.",
            structured_state={
                "kind": "representational_ref",
                "ref": ref.to_dict(),
                "level": ref.level(),
                "resolved_fields": list(ref.resolved_fields()),
                "unresolved_fields": list(ref.unresolved_fields()),
            },
        )
        ap = _augment_ability_profile_with_origin(ap)
        # _augment_ability_profile_with_origin appends its OWN derived
        # "origin_signature:<...>" tag (from ap.id/axis -- unique per ref,
        # since two refs sharing an NC identity still have different ids).
        # Genealogy's _last_tag_value() scans tags in reverse and returns
        # the first match, so appending our own family-identity signature
        # AFTER the augmenter runs makes it the one genealogy's collision/
        # gap search actually groups by -- verified empirically that
        # placing it before the augmenter call gets silently shadowed.
        ap = replace(ap, effect_tags=tuple(ap.effect_tags) + (
            f"representational_ref:{ref.encode()}",
            f"origin_signature:{self._family_signature(ref)}",
            "resolution_governed",
        ))
        self.genealogy.abilities[ability_id] = ap
        return ability_id

    @staticmethod
    def _family_signature(ref: RepresentationalRef) -> str:
        """Groups refs that share the same NC (C1) identity into one
        collision-search bucket, regardless of which deeper fields are
        resolved -- this is what lets a sibling ref's resolved col_*/sub_*
        surface as a candidate for this ref's unresolved ones.

        Genealogy's own _collision_signature_for_item() re-canonicalizes
        any "origin_signature" tag through _canonical_signature_text(),
        which round-trips ONLY the exact "AXIS^n*AXIS^n" coupling-signature
        format genealogy itself emits (anything else silently collapses to
        "0", verified empirically) -- so this must emit that same format,
        built purely from the NC identity's two axis-valued fields
        (nc_law_c, nc_target), deliberately excluding sub_*/col_* so a
        ref's family membership never shifts just because it has since
        resolved a deeper field."""
        counts: Dict[str, int] = {a: 0 for a in AXES}
        for value in (ref.nc_law_c, ref.nc_target):
            if value in counts:
                counts[value] += 1
        parts = [f"{a}^{counts[a]}" for a in AXES if counts[a] > 0]
        return "*".join(parts) if parts else "0"

    # ── The real wiring seam: a ref participates in a measured consequence ─

    def record_participation(
        self,
        ref: RepresentationalRef,
        *,
        pressure_before: Any,
        pressure_after: Any,
        source: str,
        context_tag: str = "",
        extra_trace: Optional[List[Any]] = None,
        notes: Optional[Dict[str, Any]] = None,
    ) -> Optional[Any]:
        """Call this wherever a ref genuinely participated in an experience
        whose consequence is genuinely measurable as a 5-axis pressure
        delta -- exactly the same contract every other genealogy.observe()
        call site in this codebase already honors. Returns the ReliefRecord
        genealogy.observe() returns (None on a non-qualifying tick)."""
        from aurora_internal.constraint_genealogy import PressureVec, TraceItem

        ability_id = self.ensure_registered(ref)
        trace = [TraceItem(kind="ABILITY", id=ability_id)]
        for item in (extra_trace or []):
            trace.append(item)

        p_before = pressure_before if isinstance(pressure_before, PressureVec) else PressureVec.from_dict(dict(pressure_before))
        p_after = pressure_after if isinstance(pressure_after, PressureVec) else PressureVec.from_dict(dict(pressure_after))

        merged_notes = dict(notes or {})
        merged_notes.setdefault("representational_resolution", {})
        merged_notes["representational_resolution"].update({
            "source": source,
            "ref": ref.encode(),
            "context_tag": str(context_tag or ""),
        })
        tick = int(getattr(self.genealogy, "tick_count", 0))
        return self.genealogy.observe(
            p_before, trace, p_after,
            state_sig_before=f"reprres_pre_t{tick}",
            state_sig_after=f"reprres_post_t{tick}",
            notes=merged_notes,
        )

    # ── Reading the (free) inadequacy signal ────────────────────────────────

    def consequence_profile_for(self, ref: RepresentationalRef) -> Optional[Dict[str, Any]]:
        ability = self.genealogy.abilities.get(self.ability_id_for_ref(ref))
        if ability is None:
            return None
        return getattr(ability, "consequence_profile", None)

    def inadequacy_pressure(self, ref: RepresentationalRef) -> float:
        """Zero unless there is enough independent evidence (distinct
        contexts + confidence) that the SAME coarse ref is producing
        divergent measured consequence -- i.e. read-only over genealogy's
        own consequence_profile, no recomputation of its physics."""
        profile = self.consequence_profile_for(ref)
        if not profile:
            return 0.0
        distinct_contexts = int(profile.get("distinct_contexts", 0) or 0)
        confidence = float(profile.get("confidence", 0.0) or 0.0)
        discrepancy = float(profile.get("discrepancy", 0.0) or 0.0)
        if distinct_contexts < MIN_DISTINCT_CONTEXTS_FOR_PRESSURE:
            return 0.0
        if confidence < MIN_CONFIDENCE_FOR_PRESSURE:
            return 0.0
        if discrepancy < MIN_DISCREPANCY_FOR_PRESSURE:
            return 0.0
        return _clip01(discrepancy * confidence)

    # ── Candidate generation: existing structural evidence only ────────────

    def unresolved_field_candidates(
        self, ref: RepresentationalRef, *, max_candidates: int = MAX_CANDIDATE_FIELDS_PER_PASS,
    ) -> List[Dict[str, Any]]:
        """Never invents a value. Only surfaces field values already
        independently resolved on some other structurally-connected
        representation, discovered through genealogy's own real
        collision/gap search around this ref's registered ability."""
        unresolved = ref.unresolved_fields()
        if not unresolved:
            return []
        ability_id = self.ensure_registered(ref)
        if self.inadequacy_pressure(ref) <= 0.0:
            return []

        from aurora_internal.constraint_genealogy import TraceItem

        candidates: List[Dict[str, Any]] = []
        seen_values: Dict[str, set] = {f: set() for f in unresolved}

        for finder_name, finder in (
            ("collision", self.genealogy.representation_collision_candidates),
            ("gap", self.genealogy.representation_gap_candidates),
        ):
            try:
                found = finder([TraceItem(kind="ABILITY", id=ability_id)])
            except Exception:
                found = []
            for entry in found:
                counterpart_id = str(entry.get("counterpart_representation_id", "") or "")
                counterpart_ref = self._ref_from_ability_id(counterpart_id)
                if counterpart_ref is None:
                    continue
                for field_name in unresolved:
                    value = getattr(counterpart_ref, field_name)
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
                    })
                    if len(candidates) >= max_candidates:
                        return candidates
        return candidates

    def _ref_from_ability_id(self, ability_id: str) -> Optional[RepresentationalRef]:
        ability = self.genealogy.abilities.get(ability_id)
        if ability is None:
            return None
        structured = getattr(ability, "structured_state", None) or {}
        if structured.get("kind") != "representational_ref":
            return None
        try:
            return RepresentationalRef.from_dict(structured.get("ref", {}))
        except Exception:
            return None

    # ── Inquiry / experiment integration (evidence decides, not this module) ─

    def stage_field_inquiry(
        self, ref: RepresentationalRef, candidate: Dict[str, Any], *, consumer: str,
    ) -> List[Dict[str, Any]]:
        """Routes through the existing time-boxed staged-inquiry harness.
        Staging itself is evidence-inert (genealogy's own guarantee)."""
        inquiry_id = str(candidate.get("inquiry_id", "") or "")
        return self.genealogy.stage_representation_inquiry(
            consumer, context={"resolution_candidate_field": candidate.get("field", "")},
            inquiry_id=inquiry_id, limit=1,
        )

    def complete_field_inquiry(
        self,
        ref: RepresentationalRef,
        candidate: Dict[str, Any],
        stage: Dict[str, Any],
        *,
        consumer: str,
        actual_coactivation: bool,
        pressure_before: Dict[str, float],
        pressure_after: Dict[str, float],
    ) -> Dict[str, Any]:
        """Only ever admits evidence through the SAME observe() ->
        PairStats -> _try_promote() chain every other genealogy consumer
        uses -- no alternate authority. On admission, evaluates whether
        discrepancy actually improved before deciding retain/reject."""
        ability_id = self.ensure_registered(ref)
        coactivated_ids = [ability_id, str(candidate.get("counterpart_ability_id", ""))]
        discrepancy_before = float((self.consequence_profile_for(ref) or {}).get("discrepancy", 0.0) or 0.0)

        result = self.genealogy.complete_representation_experiment(
            str(stage.get("stage_id", "")),
            consumer=consumer,
            coactivated_ids=coactivated_ids,
            pressure_before=pressure_before,
            pressure_after=pressure_after,
            outcome={"actual_coactivation": bool(actual_coactivation)},
        )

        outcome_kind = "unresolved"
        refined_ref: Optional[RepresentationalRef] = None
        discrepancy_after = discrepancy_before
        if bool(result.get("evidence_admitted", False)):
            discrepancy_after = float((self.consequence_profile_for(ref) or {}).get("discrepancy", discrepancy_before) or discrepancy_before)
            improvement = discrepancy_before - discrepancy_after
            if improvement >= MIN_DISCREPANCY_IMPROVEMENT_TO_RETAIN:
                refined_ref = self.resolve_field(
                    ref, str(candidate.get("field", "")), candidate.get("candidate_value"),
                    evidence=candidate.get("evidence", {}),
                    discrepancy_before=discrepancy_before,
                    discrepancy_after=discrepancy_after,
                    pressure_before=self.inadequacy_pressure(ref),
                    pressure_after=0.0,
                    cost=1.0,
                    inquiry_id=str(candidate.get("inquiry_id", "")),
                    source=f"stage:{stage.get('stage_id', '')}",
                )
                outcome_kind = "retained"
            else:
                outcome_kind = "rejected"
                self._record_outcome(
                    ref, candidate, discrepancy_before=discrepancy_before,
                    discrepancy_after=discrepancy_after, outcome="rejected",
                    inquiry_id=str(candidate.get("inquiry_id", "")),
                )
        else:
            self._record_outcome(
                ref, candidate, discrepancy_before=discrepancy_before,
                discrepancy_after=None, outcome="unresolved",
                inquiry_id=str(candidate.get("inquiry_id", "")),
            )

        result["representational_resolution_outcome"] = outcome_kind
        result["refined_ref"] = refined_ref.encode() if refined_ref is not None else None
        return result

    # ── The one and only field-value producer ───────────────────────────────

    def resolve_field(
        self,
        ref: RepresentationalRef,
        field_name: str,
        value: Any,
        *,
        evidence: Dict[str, Any],
        discrepancy_before: float,
        discrepancy_after: float,
        pressure_before: float,
        pressure_after: float,
        cost: float,
        inquiry_id: str = "",
        source: str = "",
        context_scope: Optional[str] = None,
    ) -> RepresentationalRef:
        """The ONLY place a new resolved field is ever produced anywhere in
        this module. Requires: field was unresolved on `ref`, `value` is a
        real candidate that arrived from unresolved_field_candidates()
        (never a literal passed from outside that pipeline), and the caller
        has already confirmed measurable discrepancy improvement. Preserves
        the coarse ancestor's own record -- ancestry does not equal
        obsolescence."""
        if getattr(ref, field_name) is not None:
            raise ValueError(f"{field_name} is already resolved on this ref; resolve_field never overwrites")
        refined = replace(ref, **{field_name: value})

        coarse_key = ref.encode()
        record = {
            "originating_representation": coarse_key,
            "unresolved_field": field_name,
            "candidate_value": value,
            "candidate_values_considered": [value],
            "evidence_source": source,
            "evidence": dict(evidence or {}),
            "inquiry_id": inquiry_id,
            "discrepancy_before": discrepancy_before,
            "discrepancy_after": discrepancy_after,
            "pressure_before": pressure_before,
            "pressure_after": pressure_after,
            "confidence": (self.consequence_profile_for(ref) or {}).get("confidence", 0.0),
            "computational_cost": cost,
            "tick": int(getattr(self.genealogy, "tick_count", 0)),
            "timestamp": _now(),
            "status": "retained",
            "context_scope": context_scope,
            "resolved_ref": refined.encode(),
        }
        self._genealogy_records.setdefault(coarse_key, []).append(record)

        scope_key = coarse_key + "|" + (context_scope or "")
        self._active_resolutions[scope_key] = refined.encode()

        self._record_outcome(
            ref, {"field": field_name, "candidate_value": value, "inquiry_id": inquiry_id, "evidence": evidence},
            discrepancy_before=discrepancy_before, discrepancy_after=discrepancy_after,
            outcome="context_specific" if context_scope else "retained",
        )
        self._save()
        return refined

    def demote_field(self, ref_encoded: str, *, context_scope: Optional[str] = None, reason: str = "") -> None:
        """Section 12: reversible-as-knowledge, not destructive-as-history.
        Removes CURRENT authority for a refinement without deleting its
        genealogy record -- the record with status flips to 'demoted', the
        active-resolution mapping is cleared, but _genealogy_records keeps
        every prior entry (contradictory evidence becomes new evidence, not
        an erasure)."""
        for coarse_key, records in self._genealogy_records.items():
            for rec in records:
                if rec.get("resolved_ref") == ref_encoded and rec.get("status") == "retained":
                    rec["status"] = "demoted"
                    rec["demoted_reason"] = reason
                    rec["demoted_at"] = _now()
                    scope_key = coarse_key + "|" + (context_scope or rec.get("context_scope") or "")
                    self._active_resolutions.pop(scope_key, None)
        self._save()

    def current_resolution(self, ref: RepresentationalRef, *, context_scope: Optional[str] = None) -> RepresentationalRef:
        """Returns the ref enriched with whatever fields have earned
        active, non-demoted authority for this context (or globally, if no
        context-specific resolution exists). Falls back to the coarse ref
        unchanged if nothing has been earned -- "minimum sufficient" is the
        default, not the exception."""
        coarse_key = ref.encode()
        scoped = self._active_resolutions.get(coarse_key + "|" + (context_scope or ""))
        if scoped:
            return RepresentationalRef.decode(scoped)
        global_scoped = self._active_resolutions.get(coarse_key + "|")
        if global_scoped:
            return RepresentationalRef.decode(global_scoped)
        return ref

    def genealogy_for(self, ref: RepresentationalRef) -> List[Dict[str, Any]]:
        return list(self._genealogy_records.get(ref.encode(), []))

    # ── Instrumentation (Section 29) ─────────────────────────────────────

    def _record_outcome(
        self, ref: RepresentationalRef, candidate: Dict[str, Any], *,
        discrepancy_before: float, discrepancy_after: Optional[float], outcome: str,
        inquiry_id: str = "",
    ) -> None:
        event = ResolutionOutcome(
            event_id=f"rre_{len(self._resolution_events)}_{int(_now() * 1000)}",
            ref_before_encoded=ref.encode(),
            resolved_fields_before=ref.resolved_fields(),
            unresolved_fields_before=ref.unresolved_fields(),
            pressure_source=candidate.get("source", ""),
            operational_discrepancy=discrepancy_before,
            candidate_field=str(candidate.get("field", "")),
            candidate_values_considered=[candidate.get("candidate_value")],
            evidence_used=dict(candidate.get("evidence", {}) or {}),
            inquiry_id=inquiry_id or str(candidate.get("inquiry_id", "")),
            ref_after_encoded=(replace(ref, **{candidate.get("field", ""): candidate.get("candidate_value")}).encode()
                                if outcome in ("retained", "context_specific") and candidate.get("field") else None),
            resolved_fields_after=(ref.resolved_fields() + (candidate.get("field"),)) if outcome in ("retained", "context_specific") else ref.resolved_fields(),
            discrepancy_before=discrepancy_before,
            discrepancy_after=discrepancy_after,
            pressure_before=self.inadequacy_pressure(ref),
            pressure_after=0.0 if outcome in ("retained", "context_specific") else self.inadequacy_pressure(ref),
            slots_examined=1,
            slots_materialized=1 if outcome in ("retained", "context_specific") else 0,
            semantic_resolutions_requested=1,
            computational_cost=1.0,
            outcome=outcome,
            context_scope=None,
        )
        self._resolution_events.append(event.to_dict())
        if len(self._resolution_events) > RESOLUTION_EVENTS_MAXLEN:
            self._resolution_events = self._resolution_events[-RESOLUTION_EVENTS_MAXLEN:]
        self._save()

    def recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        return list(self._resolution_events[-limit:])

    # ── Persistence ──────────────────────────────────────────────────────

    def _genealogy_path(self) -> Optional[Path]:
        return self.root / "resolution_genealogy.json" if self.root else None

    def _active_path(self) -> Optional[Path]:
        return self.root / "active_resolutions.json" if self.root else None

    def _events_path(self) -> Optional[Path]:
        return self.root / "resolution_events.jsonl" if self.root else None

    def _save(self) -> None:
        if self.root is None:
            return
        try:
            gpath = self._genealogy_path()
            if gpath is not None:
                gpath.write_text(json.dumps(self._genealogy_records, indent=2, sort_keys=True))
            apath = self._active_path()
            if apath is not None:
                apath.write_text(json.dumps(self._active_resolutions, indent=2, sort_keys=True))
            epath = self._events_path()
            if epath is not None:
                with open(epath, "w") as f:
                    for ev in self._resolution_events:
                        f.write(json.dumps(ev, sort_keys=True) + "\n")
        except Exception:
            pass

    def _load(self) -> None:
        if self.root is None:
            return
        try:
            gpath = self._genealogy_path()
            if gpath is not None and gpath.exists():
                self._genealogy_records = json.loads(gpath.read_text())
        except Exception:
            self._genealogy_records = {}
        try:
            apath = self._active_path()
            if apath is not None and apath.exists():
                self._active_resolutions = json.loads(apath.read_text())
        except Exception:
            self._active_resolutions = {}
        try:
            epath = self._events_path()
            if epath is not None and epath.exists():
                events = []
                with open(epath) as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            events.append(json.loads(line))
                self._resolution_events = events[-RESOLUTION_EVENTS_MAXLEN:]
        except Exception:
            self._resolution_events = []


# ── systems-dict convenience wiring (the same "systems.get(...)" convention
#    every other subsystem in this codebase already shares) ────────────────

def get_or_create_engine(systems: Optional[Dict[str, Any]]) -> Optional["RepresentationalResolutionEngine"]:
    """Lazily builds (once) and caches a RepresentationalResolutionEngine on
    systems['representational_resolution_engine'], bound to systems['genealogy'].
    Returns None if systems or its genealogy is unavailable -- callers must
    treat that as "resolution tracking not available this call", never as an
    error, exactly like every other optional systems.get(...) lookup in this
    codebase."""
    if not systems:
        return None
    existing = systems.get("representational_resolution_engine")
    if existing is not None:
        return existing
    genealogy = systems.get("genealogy")
    if genealogy is None:
        return None
    state_dir = systems.get("state_dir")
    engine = RepresentationalResolutionEngine(genealogy, state_dir=state_dir)
    systems["representational_resolution_engine"] = engine
    return engine


def record_ref_participation_from_scores(
    systems: Optional[Dict[str, Any]],
    ref_encoded: Optional[str],
    dimension_scores: Dict[str, float],
    *,
    source: str,
    context_tag: str = "",
    extra_trace_ids: Optional[List[str]] = None,
) -> None:
    """Generic bridge from an existing real 0..1 evaluation-score dict (any
    subsystem's own already-computed, already-meaningful scores -- causal
    accuracy, evidence discipline, whatever it is) into resolution pressure,
    without inventing a new pressure currency and without any per-word/
    per-domain mapping.

    Deliberately does NOT put all relief on the ref's own declared axis --
    doing so would make the measured effect concentrate there by
    construction every single time, so genealogy's discrepancy computation
    (declared axis vs. where relief actually landed) would compute exactly
    0 regardless of how accurate the scores actually were, permanently
    silencing this signal (caught empirically before this was wired up).
    Instead: pressure starts fully on the declared axis (the prior -- "this
    axis alone should explain the outcome"); a GOOD score clears it there;
    whatever a score fails to explain surfaces as pressure on the OTHER
    axes too, split evenly (the same fixed, non-semantic split every time --
    no domain/word mapping), so a representation that keeps failing to
    predict its own outcomes accumulates real, measured divergence from its
    declared axis, while one that predicts well accumulates none.

    Silently a no-op if no ref, no engine, or no scores -- this is ambient
    instrumentation, never a required step in any caller's own logic."""
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
    other_axes = [a for a in AXES if a != axis]
    avg_score = _clip01(sum(dimension_scores.values()) / max(1, len(dimension_scores)))
    unexplained = max(0.0, 1.0 - avg_score)
    pressure_before = {a: (1.0 if a == axis else 0.0) for a in AXES}
    pressure_after = {a: (unexplained if a == axis else (unexplained / len(other_axes))) for a in AXES}

    from aurora_internal.constraint_genealogy import TraceItem
    extra_trace = [TraceItem(kind="ABILITY", id=str(tid)) for tid in (extra_trace_ids or [])]
    try:
        engine.record_participation(
            ref, pressure_before=pressure_before, pressure_after=pressure_after,
            source=source, context_tag=context_tag, extra_trace=extra_trace,
        )
    except Exception:
        pass
