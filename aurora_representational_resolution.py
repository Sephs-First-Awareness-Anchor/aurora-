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
# Five keeps a complete native axis/dimension domain (X/T/N/B/A or the five
# Noncomp dimensions) available to a bootstrap inquiry. A bound of four made
# the last lawful value unreachable in production, independent of evidence.
MAX_CANDIDATE_FIELDS_PER_PASS = 5
RESOLUTION_EVENTS_MAXLEN = 2000

# Build 714, Section 25 -- resolution economics. Each candidate search
# genuinely costs work (genealogy has to score every eligible collision/gap
# counterpart, per aurora_internal/constraint_genealogy.py's own bounded-but-
# nonzero search); MIN_BENEFIT_PER_COST_UNIT makes retention require the
# measured discrepancy improvement to actually be worth that real,
# accumulated cost, not merely clear the absolute floor above. This is what
# creates pressure toward the SMALLEST sufficient distinction rather than
# an arbitrary "coarse is good" bonus or "detail is good" bonus -- a field
# that took many searches to barely help is rejected precisely because it
# wasn't worth what it cost, using cost figures genealogy itself already
# produced (search result counts), never an invented economy.
MIN_BENEFIT_PER_COST_UNIT = 0.01


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
    candidate_evaluation: Dict[str, Any] = field(default_factory=dict)
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
        # Section 12: in-flight investigations, keyed by coarse ref encoded
        # string -> {"stage", "candidate", "consumer", "context_scope"}.
        # Deliberately in-memory only (not persisted) -- a stage is already
        # time-boxed by genealogy's own stage_representation_inquiry()
        # lifetime; surviving a restart with a stale pending stage would
        # just mean it expires normally on the far side, same as any other
        # process-restart interruption of an in-progress genealogy stage.
        self._active_stage_for_ref: Dict[str, Dict[str, Any]] = {}
        # Follow-up (item 6) -- causal-participation ledger: how many times
        # a real consumer has actually READ this ref's currently-staged
        # provisional value (via provisional_resolution() below) since it
        # was staged. Previously a domain-hypothesis candidate could be
        # retained purely from co-activation (a marker ability merely
        # appearing in the same observed trace) plus ambient discrepancy
        # trend -- neither of which required the hypothesized VALUE to
        # ever have been used for anything. Reset to 0 whenever a new
        # stage begins (investigate_if_pressured()); a stage that reaches
        # completion with zero reads was never actually tested and cannot
        # be retained regardless of ambient discrepancy.
        self._provisional_reads: Dict[str, int] = {}
        # A read is not a test.  This ledger is populated only by a consumer
        # that can show how the candidate's exact value changed relevance,
        # prediction, parameterisation, or action.  The real outcome is joined
        # later by record_participation() for the same staged ref.
        self._candidate_downstream_effects: Dict[str, Dict[str, Any]] = {}
        # Prevent one non-discriminating domain value from being restaged
        # forever merely because it is first in AXES.  Counts are reconstructed
        # from persisted resolution events on boot.
        self._candidate_attempt_counts: Dict[str, int] = {}
        # Section 15: the seal on resolve_field()'s production authority --
        # True only for the exact duration of a real complete_field_inquiry()
        # call, set/cleared by that method itself, never settable from
        # outside this class.
        self._in_complete_field_inquiry: bool = False
        self._load()

    # ── Registration: coarse ref <-> synthetic AbilityProfile ──────────────

    @staticmethod
    def ability_id_for_ref(ref: RepresentationalRef) -> str:
        """Deterministic id for this ref's CURRENTLY-resolved identity.
        Two refs with different resolved-field sets never collide even if
        the resolved values overlap, because encode() includes every field
        position (unresolved fields as '?')."""
        return "REFAB:" + ref.encode()[len("REF:"):]

    @staticmethod
    def _candidate_attempt_key(ref_encoded: str, field_name: str, value: Any) -> str:
        return f"{ref_encoded}|{field_name}={value}"

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
        consumer: str = "auto",
        candidate_evaluation: Optional[Dict[str, Any]] = None,
    ) -> Optional[Any]:
        """Call this wherever a ref genuinely participated in an experience
        whose consequence is genuinely measurable as a 5-axis pressure
        delta -- exactly the same contract every other genealogy.observe()
        call site in this codebase already honors. Returns the ReliefRecord
        genealogy.observe() returns (None on a non-qualifying tick).

        Section 12 -- closes the production resolution loop on the SAME
        real event stream this call already rides, without a second
        scheduler or privileged execution lane (Section 7): if a candidate
        is already staged for this ref (from a PRIOR pressured
        participation), this tick's genuine co-activation with the
        candidate's counterpart ability is what completes the inquiry --
        the counterpart is added to THIS tick's own trace, so "co-
        activation" means exactly what it means everywhere else in
        genealogy (two ids genuinely present in the same observed trace),
        never fabricated. If no candidate is staged yet, a pressured
        outcome from THIS tick may stage one for the next participation to
        complete. Every step here is best-effort and non-fatal: a failure
        anywhere in this optional closure must never break the primary
        participation record genealogy.observe() itself provides."""
        from aurora_internal.constraint_genealogy import PressureVec, TraceItem

        ability_id = self.ensure_registered(ref)
        coarse_key = ref.encode()
        pending = self._active_stage_for_ref.get(coarse_key)
        candidate_ready = bool(
            pending is not None
            and candidate_evaluation
            and self._candidate_downstream_effects.get(coarse_key)
        )
        # Captured BEFORE this tick's own observe() call -- see
        # complete_field_inquiry()'s _discrepancy_before_override docstring
        # for why this matters specifically for the domain_hypothesis path.
        discrepancy_before_this_tick = (
            float((self.consequence_profile_for(ref) or {}).get("discrepancy", 0.0) or 0.0)
            if candidate_ready else None
        )

        trace = [TraceItem(kind="ABILITY", id=ability_id)]
        if candidate_ready and pending is not None:
            counterpart_id = str(pending["candidate"].get("counterpart_ability_id", ""))
            if counterpart_id:
                trace.append(TraceItem(kind="ABILITY", id=counterpart_id))
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
        result = self.genealogy.observe(
            p_before, trace, p_after,
            state_sig_before=f"reprres_pre_t{tick}",
            state_sig_after=f"reprres_post_t{tick}",
            notes=merged_notes,
        )

        try:
            if candidate_ready and pending is not None:
                self._active_stage_for_ref.pop(coarse_key, None)
                completion = self.complete_field_inquiry(
                    ref, pending["candidate"], pending["stage"],
                    consumer=pending.get("consumer", consumer),
                    actual_coactivation=True,
                    pressure_before=p_before.to_dict(), pressure_after=p_after.to_dict(),
                    context_scope=pending.get("context_scope"),
                    _discrepancy_before_override=discrepancy_before_this_tick,
                    candidate_evaluation=candidate_evaluation,
                )
                # The completed candidate no longer occupies the stage. If it
                # did not earn authority and real inadequacy remains, stage the
                # least-tested alternative for a future consequence. A
                # retained/context-specific refinement stops this pass: future
                # cognition must first consume that earned structure rather
                # than immediately launching a competing value for the same
                # still-coarse key.
                if completion.get("representational_resolution_outcome") not in (
                    "retained", "context_specific",
                ):
                    self.investigate_if_pressured(
                        ref,
                        consumer=pending.get("consumer", consumer),
                        context_scope=pending.get("context_scope"),
                    )
            elif pending is None:
                # context_scope deliberately NOT auto-populated from
                # context_tag here: context_tag is a co-activation-
                # diversity marker (what distinguishes this tick from
                # others), not an explicit claim that the resulting
                # resolution is only valid in that one context. Per
                # complete_field_inquiry()'s own invariant, only a caller
                # that genuinely knows the evidence is scoped may assert
                # that -- the automatic closure has no such knowledge, so
                # it retains globally by default (the honest "this seems to
                # generalize until shown otherwise" posture) and lets
                # demote_field()/renewed discrepancy in a future context
                # correct it later if it doesn't.
                self.investigate_if_pressured(ref, consumer=consumer)
        except Exception:
            pass

        return result

    def investigate_if_pressured(
        self, ref: RepresentationalRef, *, consumer: str = "auto", context_scope: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Section 12: if this ref currently carries real inadequacy
        pressure and no investigation is already in flight for it, generate
        candidates from real structural evidence and stage the first one --
        exactly the same stage_field_inquiry() production callers would use
        directly. A no-op (returns None) when there's no pressure, no
        candidates, or an investigation is already pending -- staging is
        never forced. This is what record_participation() calls
        automatically; a caller may also call it directly (e.g. Habitat's
        own proactive affordance scan) without duplicating the logic."""
        coarse_key = ref.encode()
        if coarse_key in self._active_stage_for_ref:
            return None
        if self.inadequacy_pressure(ref) <= 0.0:
            return None
        candidates = self.unresolved_field_candidates(ref)
        if not candidates:
            return None
        # Candidate order is not authority.  Prefer the least-tested value;
        # canonical identity is only a stable neutral tie order, and the
        # selection method is recorded on the stage.  A value with no causal
        # downstream effect therefore yields to alternatives on the next pass
        # instead of becoming first-domain-value luck.
        candidate = min(
            candidates,
            key=lambda item: (
                self._candidate_attempt_counts.get(
                    self._candidate_attempt_key(
                        coarse_key, str(item.get("field", "")), item.get("candidate_value"),
                    ),
                    0,
                ),
                self._candidate_attempt_key(
                    coarse_key, str(item.get("field", "")), item.get("candidate_value"),
                ),
            ),
        )
        staged = self.stage_field_inquiry(ref, candidate, consumer=consumer)
        if not staged:
            return None
        self._active_stage_for_ref[coarse_key] = {
            "stage": staged[0], "candidate": candidate, "consumer": consumer,
            "context_scope": context_scope,
            "candidate_selection": "least_tested_then_canonical_neutral_tie",
        }
        self._provisional_reads[coarse_key] = 0
        self._candidate_downstream_effects.pop(coarse_key, None)
        return self._active_stage_for_ref[coarse_key]

    def provisional_resolution(self, ref: RepresentationalRef) -> RepresentationalRef:
        """Section 14/28 follow-up (item 6) -- lets a real consumer opt in
        to seeing a currently-staged candidate's PROVISIONAL value, never
        silently substituted for current_resolution() (which only ever
        returns EARNED, retained authority -- "candidate is not knowledge"
        still holds everywhere else). This is what makes causal
        participation real rather than a synthetic marker: a consumer that
        calls this and lets the provisional value genuinely shape a real
        decision is recorded here, and complete_field_inquiry() requires
        at least one such real read before a domain-hypothesis candidate
        may be retained. Falls back to current_resolution() when nothing
        is staged, or when the staged candidate targets a field that is
        somehow already resolved (defensive; should not happen)."""
        coarse_key = ref.encode()
        pending = self._active_stage_for_ref.get(coarse_key)
        if pending is None:
            return self.current_resolution(ref)
        candidate = pending.get("candidate") or {}
        field_name = str(candidate.get("field", ""))
        if not field_name or getattr(ref, field_name, None) is not None:
            return self.current_resolution(ref)
        self._provisional_reads[coarse_key] = self._provisional_reads.get(coarse_key, 0) + 1
        return replace(ref, **{field_name: candidate.get("candidate_value")})

    @staticmethod
    def _has_material_downstream_difference(value: Any) -> bool:
        if value is None or value is False:
            return False
        if isinstance(value, (int, float)):
            return abs(float(value)) > 1e-12
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, dict):
            return any(RepresentationalResolutionEngine._has_material_downstream_difference(v)
                       for v in value.values())
        if isinstance(value, (list, tuple, set)):
            return any(RepresentationalResolutionEngine._has_material_downstream_difference(v)
                       for v in value)
        return True

    def record_candidate_downstream_effect(
        self,
        ref: RepresentationalRef,
        *,
        consumer: str,
        downstream_difference: Any,
        action_or_prediction_affected: Any,
        baseline_expectation: Optional[Dict[str, Any]] = None,
        conditioned_expectation: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Seal a staged value to a concrete downstream counterfactual.

        Merely calling provisional_resolution() is deliberately insufficient.
        The consumer must show a material difference between cognition without
        and with this exact candidate value before any later consequence can be
        admitted as evidence for it.
        """
        coarse_key = ref.encode()
        pending = self._active_stage_for_ref.get(coarse_key)
        if pending is None:
            return None
        candidate = dict(pending.get("candidate") or {})
        field_name = str(candidate.get("field") or "")
        if not field_name or not self._has_material_downstream_difference(downstream_difference):
            return None
        without = self.current_resolution(ref)
        if getattr(without, field_name, None) is not None:
            return None
        with_candidate = replace(without, **{field_name: candidate.get("candidate_value")})
        record = {
            "candidate_field": field_name,
            "candidate_value": candidate.get("candidate_value"),
            "representation_without_candidate": without.encode(),
            "representation_with_candidate": with_candidate.encode(),
            "downstream_difference_produced": downstream_difference,
            "action_prediction_affected": action_or_prediction_affected,
            "baseline_expectation": dict(baseline_expectation or {}),
            "conditioned_expectation": dict(conditioned_expectation or {}),
            "consumer": str(consumer or ""),
            "metadata": dict(metadata or {}),
            "recorded_at": _now(),
        }
        self._candidate_downstream_effects[coarse_key] = record
        return dict(record)

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
        collision/gap search around this ref's registered ability.

        Section 25: every entry genealogy's collision/gap search actually
        returns (whether or not it yields a usable field value) is real,
        already-performed work -- accumulated per-ref in _cost_ledger so a
        later resolve_field() call can charge for what it genuinely took to
        find, rather than a flat placeholder cost."""
        unresolved = ref.unresolved_fields()
        if not unresolved:
            return []
        ability_id = self.ensure_registered(ref)
        if self.inadequacy_pressure(ref) <= 0.0:
            return []

        from aurora_internal.constraint_genealogy import TraceItem

        candidates: List[Dict[str, Any]] = []
        seen_values: Dict[str, set] = {f: set() for f in unresolved}
        coarse_key = ref.encode()

        for finder_name, finder in (
            ("collision", self.genealogy.representation_collision_candidates),
            ("gap", self.genealogy.representation_gap_candidates),
        ):
            try:
                found = finder([TraceItem(kind="ABILITY", id=ability_id)])
            except Exception:
                found = []
            self._cost_ledger[coarse_key] = self._cost_ledger.get(coarse_key, 0.0) + float(len(found))
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

        if not candidates:
            candidates = self._bootstrap_domain_hypotheses(ref, unresolved, max_candidates)
        return candidates

    def _bootstrap_domain_hypotheses(
        self, ref: RepresentationalRef, unresolved: Tuple[str, ...], max_candidates: int,
    ) -> List[Dict[str, Any]]:
        """Build 717, Sections 13-14 -- solves the first-candidate bootstrap
        problem. Aurora cannot require an already-resolved sibling to exist
        before the FIRST member of a representational family can ever be
        investigated -- that would make resolution permanently impossible
        for any family with no prior resolved member. When structural
        (sibling) evidence finds nothing, fall back to the representational
        substrate's own already-defined lawful domain (AXES for the two
        axis-valued fields, DIM_NAMES for the two dimension-valued fields --
        RepresentationalRef.__post_init__ already validates exactly this
        domain, so nothing new is invented here). Every value in that
        domain becomes a HYPOTHESIS, explicitly tagged "domain_hypothesis"
        and never treated as evidence -- "the manifold's existence of N is
        not evidence that N is correct" (directive Section 13, verbatim).
        These hypotheses are never returned when structural candidates
        already exist; they are a last resort, not a competing source."""
        candidates: List[Dict[str, Any]] = []
        coarse_key = ref.encode()
        # Section 25: enumerating the domain is itself real, if cheap, work
        # -- charge one unit per value considered, same currency as a real
        # collision/gap search result count.
        self._cost_ledger[coarse_key] = self._cost_ledger.get(coarse_key, 0.0) + 1.0
        for field_name in unresolved:
            domain = AXES if field_name in ("sub_law_c", "col_law_c") else DIM_NAMES
            for value in domain:
                hyp_id = self._hypothesis_ability_id(coarse_key, field_name, value)
                self._ensure_hypothesis_registered(hyp_id, field_name, value)
                candidates.append({
                    "field": field_name,
                    "candidate_value": value,
                    "source": f"domain_hypothesis:{field_name}={value}",
                    "inquiry_id": "",
                    "counterpart_ability_id": hyp_id,
                    "evidence": {
                        "origin": "lawful_domain",
                        "note": "unconfirmed hypothesis from the field's own valid domain -- not structural evidence, earns authority only through consequence",
                    },
                    "pressure": 0.0,
                    "origin": "domain_hypothesis",
                })
                if len(candidates) >= max_candidates:
                    return candidates
        return candidates

    @staticmethod
    def _hypothesis_ability_id(coarse_key: str, field_name: str, value: str) -> str:
        return f"REFHYP:{coarse_key[len('REF:'):]}:{field_name}={value}"

    def _ensure_hypothesis_registered(self, hyp_id: str, field_name: str, value: str) -> None:
        """A domain hypothesis gets its own tiny, idempotent marker ability
        -- just enough identity for it to genuinely co-activate (in the
        real genealogy sense: literally present together in the same
        observed trace) with the ref being investigated. It is NOT
        discoverable by collision/gap search (no origin_signature override,
        no representational_ref tag) -- it is a private test fixture for
        this one hypothesis, not a new structurally-connected
        representation other refs could mistake for real evidence."""
        if hyp_id in self.genealogy.abilities:
            return
        from aurora_internal.constraint_genealogy import AbilityProfile
        axis = value if value in AXES else "X"
        self.genealogy.abilities[hyp_id] = AbilityProfile(
            id=hyp_id, axis=axis, requires=(axis,),
            cost={a: 0.0 for a in AXES}, risk={a: 0.0 for a in AXES},
            effect_tags=("domain_hypothesis_marker", f"hypothesis_field:{field_name}", f"hypothesis_value:{value}"),
            notes=f"Build 717 bootstrap hypothesis marker for {field_name}={value} -- test fixture, not a representation.",
        )

    def _ref_from_ability_id(self, ability_id: str) -> Optional[RepresentationalRef]:
        """Section 10: candidate values may come from ANY real,
        structurally-connected representation, not only ones this module
        itself registered. Recognizes two real sources:
          1. this module's own structured_state convention (Habitat/RCEC
             refs registered via ensure_registered()).
          2. sensory citizenship's OWN, independent 'representational_ref:
             <encoded>' effect_tag -- the exact same tag prefix/format
             aurora_internal/aurora_sensory_crystal.py's
             grant_representational_citizenship() already writes (verified
             by reading that method's own source), reused verbatim rather
             than invented. Read-only: never writes to, or otherwise
             touches, a sensory-citizenship ability."""
        ability = self.genealogy.abilities.get(ability_id)
        if ability is None:
            return None
        structured = getattr(ability, "structured_state", None) or {}
        if structured.get("kind") == "representational_ref":
            try:
                return RepresentationalRef.from_dict(structured.get("ref", {}))
            except Exception:
                return None
        for tag in (getattr(ability, "effect_tags", None) or ()):
            tag = str(tag)
            if tag.startswith("representational_ref:"):
                try:
                    return RepresentationalRef.decode(tag[len("representational_ref:"):])
                except Exception:
                    return None
        return None

    # ── Inquiry / experiment integration (evidence decides, not this module) ─

    def stage_field_inquiry(
        self, ref: RepresentationalRef, candidate: Dict[str, Any], *, consumer: str,
    ) -> List[Dict[str, Any]]:
        """Routes through the existing time-boxed staged-inquiry harness.
        Staging itself is evidence-inert (genealogy's own guarantee).

        A domain_hypothesis candidate (Section 13-14 bootstrap) has no real
        genealogy collision/gap record behind it -- there is nothing for
        genealogy's own stage_representation_inquiry() to look up (passing
        an empty/unknown inquiry_id would incorrectly fall back to
        whatever ELSE happens to be pending in genealogy's own inquiry
        pool, unrelated to this specific hypothesis). Instead it returns a
        clearly-marked synthetic stage: same list-of-one shape every other
        caller of this method already expects, but stage_id=None signals
        complete_field_inquiry() to validate it through direct, real
        co-activation (Section 12's own record_participation() closure
        already puts the hypothesis marker ability into the very next
        real observed trace) rather than genealogy's pairwise experiment
        harness, which has no record of this hypothesis to consult."""
        if str(candidate.get("origin", "")) == "domain_hypothesis":
            return [{
                "stage_id": None,
                "origin": "domain_hypothesis",
                "inquiry_id": "",
                "consumer": consumer,
                "operand_ids": [self.ability_id_for_ref(ref), str(candidate.get("counterpart_ability_id", ""))],
                "status": "staged",
            }]
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
        context_scope: Optional[str] = None,
        _discrepancy_before_override: Optional[float] = None,
        candidate_evaluation: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Only ever admits evidence through the SAME observe() ->
        PairStats -> _try_promote() chain every other genealogy consumer
        uses -- no alternate authority. On admission, evaluates whether
        discrepancy actually improved before deciding retain/reject.

        context_scope (Section 13): a real caller that KNOWS the evidence
        it is completing this inquiry with is scoped to one operational
        context (e.g. Habitat's own territory tag, RCEC's own episode
        family) may pass that context here. This module never infers scope
        from ambiguous aggregate signals on its own -- consequence_profile's
        EMA blends every context together, so there is no honest way to
        decompose "this discrepancy improvement was really only true in
        context X" without a caller who actually knows X. Passing None
        (the default) retains the field universally, exactly as before;
        passing a scope retains it only for that scope (current_resolution()
        already supports per-scope + global lookup) -- the SAME canonical
        ref identity either way, never a proliferated duplicate.

        _discrepancy_before_override (Sections 13-14, bootstrap): for a
        domain_hypothesis stage, the real co-activation between this ref
        and the hypothesis marker already happened in record_participation
        ()'s OWN genealogy.observe() call, BEFORE this method runs -- so
        measuring discrepancy_before here (after that observe()) would
        already reflect the very evidence being evaluated. record_
        participation() captures the true pre-tick discrepancy and passes
        it through here instead. Internal wiring only -- production callers
        completing a real (non-hypothesis) staged inquiry never need this."""
        ability_id = self.ensure_registered(ref)
        coarse_key = ref.encode()
        coactivated_ids = [ability_id, str(candidate.get("counterpart_ability_id", ""))]
        aggregate_discrepancy_before = (
            _discrepancy_before_override if _discrepancy_before_override is not None
            else float((self.consequence_profile_for(ref) or {}).get("discrepancy", 0.0) or 0.0)
        )

        effect_record = self._candidate_downstream_effects.pop(coarse_key, None)
        supplied_outcome = dict(candidate_evaluation or {})
        causal_evaluation: Dict[str, Any] = {}
        if effect_record is not None:
            causal_evaluation.update(effect_record)
            causal_evaluation.update(supplied_outcome)
        # A caller cannot manufacture causal participation by supplying only
        # a favorable after-the-fact error comparison.  The before-
        # consequence downstream effect must already have been sealed through
        # record_candidate_downstream_effect() for this exact staged value.
        candidate_matches = bool(causal_evaluation) and (
            str(causal_evaluation.get("candidate_field") or "") == str(candidate.get("field") or "")
            and causal_evaluation.get("candidate_value") == candidate.get("candidate_value")
        )
        has_downstream_effect = candidate_matches and self._has_material_downstream_difference(
            causal_evaluation.get("downstream_difference_produced")
        )
        actual_consequence = causal_evaluation.get("actual_consequence")
        try:
            baseline_error = float(causal_evaluation.get("baseline_error"))
            conditioned_error = float(causal_evaluation.get("candidate_conditioned_error"))
            has_outcome_comparison = actual_consequence is not None
        except (TypeError, ValueError):
            baseline_error = aggregate_discrepancy_before
            conditioned_error = aggregate_discrepancy_before
            has_outcome_comparison = False
        candidate_value_discriminated = (
            has_downstream_effect
            and has_outcome_comparison
            and abs(baseline_error - conditioned_error) > 1e-12
        )
        discrepancy_before = baseline_error if has_outcome_comparison else aggregate_discrepancy_before

        if str(stage.get("origin", "")) == "domain_hypothesis":
            # No real genealogy collision/gap record exists to complete an
            # experiment against (Sections 13-14) -- the co-activation
            # itself (this ref's ability + the hypothesis marker genuinely
            # present together in the SAME already-observed trace) is
            # necessary evidence, but Section 14 follow-up (item 6) makes
            # it no longer SUFFICIENT: co-activation alone never required
            # the hypothesized VALUE to have actually influenced any real
            # decision. causally_participated is True only if a real
            # consumer called provisional_resolution() at least once while
            # this candidate was staged (see that method) -- a genuine
            # causal role, not a synthetic marker. A candidate that was
            # never actually used cannot be retained regardless of
            # ambient discrepancy trend; it remains unresolved (not
            # rejected -- it was never tested, not that it failed).
            provisional_reads = self._provisional_reads.pop(coarse_key, 0)
            causally_participated = bool(has_downstream_effect and has_outcome_comparison)
            result: Dict[str, Any] = {
                "stage_id": None,
                "evidence_admitted": bool(actual_coactivation) and candidate_value_discriminated,
                "actual_coactivation": bool(actual_coactivation),
                "causally_participated": causally_participated,
                "provisional_reads": provisional_reads,
                "candidate_value_discriminated": candidate_value_discriminated,
                "status": "hypothesis_coactivated",
            }
        else:
            result = self.genealogy.complete_representation_experiment(
                str(stage.get("stage_id", "")),
                consumer=consumer,
                coactivated_ids=coactivated_ids,
                pressure_before=pressure_before,
                pressure_after=pressure_after,
                outcome={"actual_coactivation": bool(actual_coactivation)},
            )
            result["genealogy_evidence_admitted"] = bool(result.get("evidence_admitted", False))
            result["causally_participated"] = bool(has_downstream_effect and has_outcome_comparison)
            result["candidate_value_discriminated"] = candidate_value_discriminated
            result["evidence_admitted"] = bool(result["genealogy_evidence_admitted"] and candidate_value_discriminated)
            self._provisional_reads.pop(coarse_key, None)

        attempt_key = self._candidate_attempt_key(
            coarse_key, str(candidate.get("field", "")), candidate.get("candidate_value"),
        )
        self._candidate_attempt_counts[attempt_key] = self._candidate_attempt_counts.get(attempt_key, 0) + 1

        outcome_kind = "unresolved"
        refined_ref: Optional[RepresentationalRef] = None
        discrepancy_after = conditioned_error if has_outcome_comparison else discrepancy_before
        real_cost = max(1.0, float(self._cost_ledger.get(coarse_key, 0.0)))
        if bool(result.get("evidence_admitted", False)):
            improvement = discrepancy_before - discrepancy_after
            worth_the_cost = improvement >= (real_cost * MIN_BENEFIT_PER_COST_UNIT)
            if improvement >= MIN_DISCREPANCY_IMPROVEMENT_TO_RETAIN and worth_the_cost:
                self._in_complete_field_inquiry = True
                try:
                    refined_ref = self.resolve_field(
                        ref, str(candidate.get("field", "")), candidate.get("candidate_value"),
                        evidence=candidate.get("evidence", {}),
                        discrepancy_before=discrepancy_before,
                        discrepancy_after=discrepancy_after,
                        pressure_before=self.inadequacy_pressure(ref),
                        pressure_after=0.0,
                        cost=real_cost,
                        inquiry_id=str(candidate.get("inquiry_id", "")),
                        source=f"stage:{stage.get('stage_id', '')}",
                        context_scope=context_scope,
                        candidate_evaluation=causal_evaluation,
                    )
                finally:
                    self._in_complete_field_inquiry = False
                outcome_kind = "context_specific" if context_scope else "retained"
                # Section 25: cost is "paid off" by a retained field -- the
                # next unresolved field on this same ref starts its own
                # search fresh rather than inheriting a prior success's cost.
                self._cost_ledger[coarse_key] = 0.0
            else:
                # Deliberately NOT reset here: a rejected/too-costly attempt
                # was still real spent search effort. Leaving it accumulated
                # means repeated marginal attempts on the same ref make the
                # NEXT attempt's bar higher too -- genuine economic pressure
                # against runaway low-value investigation, using only real,
                # already-measured search-result counts.
                outcome_kind = "rejected"
                self._record_outcome(
                    ref, candidate, discrepancy_before=discrepancy_before,
                    discrepancy_after=discrepancy_after, outcome="rejected",
                    inquiry_id=str(candidate.get("inquiry_id", "")), cost=real_cost,
                    candidate_evaluation=causal_evaluation,
                    context_scope=context_scope,
                )
        else:
            self._record_outcome(
                ref, candidate, discrepancy_before=discrepancy_before,
                discrepancy_after=None, outcome="unresolved",
                inquiry_id=str(candidate.get("inquiry_id", "")), cost=real_cost,
                candidate_evaluation=causal_evaluation,
                context_scope=context_scope,
            )

        result["representational_resolution_outcome"] = outcome_kind
        result["refined_ref"] = refined_ref.encode() if refined_ref is not None else None
        result["candidate_evaluation"] = causal_evaluation
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
        candidate_evaluation: Optional[Dict[str, Any]] = None,
        _allow_direct_call: bool = False,
    ) -> RepresentationalRef:
        """The ONLY place a new resolved field is ever produced anywhere in
        this module. Requires: field was unresolved on `ref`, `value` is a
        real candidate that arrived from unresolved_field_candidates()
        (never a literal passed from outside that pipeline), and the caller
        has already confirmed measurable discrepancy improvement. Preserves
        the coarse ancestor's own record -- ancestry does not equal
        obsolescence.

        Build 717, Section 15 -- sealed production authority. This
        docstring's own claim ("the ONLY place...") was previously
        aspirational, not enforced: nothing stopped an arbitrary caller
        from fabricating discrepancy/evidence and calling this directly.
        Now: any call arriving while NOT genuinely inside
        complete_field_inquiry()'s own evidence-admission logic (tracked
        via the private _in_complete_field_inquiry flag, set only for the
        duration of that method's own call) is rejected outright. Tests may
        use this as an internal fixture per the directive's own allowance,
        but must say so explicitly via _allow_direct_call=True -- the
        param's underscore and name make it unmistakable that this is a
        deliberate bypass of the sealed path, never something a production
        caller would plausibly pass by accident."""
        if not self._in_complete_field_inquiry and not _allow_direct_call:
            raise PermissionError(
                "resolve_field() may only be reached through complete_field_inquiry()'s "
                "own evidence-admission chain (source representation -> unresolved field -> "
                "candidate origin -> inquiry/experiment -> evidence -> observed consequence -> "
                "adequacy comparison -> retention decision). Direct production calls are "
                "sealed (Section 15). Tests may pass _allow_direct_call=True as an explicit, "
                "unmistakable internal-fixture bypass."
            )
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
            "candidate_evaluation": dict(candidate_evaluation or {}),
        }
        self._genealogy_records.setdefault(coarse_key, []).append(record)

        scope_key = coarse_key + "|" + (context_scope or "")
        self._active_resolutions[scope_key] = refined.encode()

        self._record_outcome(
            ref, {"field": field_name, "candidate_value": value, "inquiry_id": inquiry_id, "evidence": evidence},
            discrepancy_before=discrepancy_before, discrepancy_after=discrepancy_after,
            outcome="context_specific" if context_scope else "retained",
            candidate_evaluation=candidate_evaluation,
            context_scope=context_scope,
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
        inquiry_id: str = "", cost: Optional[float] = None,
        candidate_evaluation: Optional[Dict[str, Any]] = None,
        context_scope: Optional[str] = None,
    ) -> None:
        real_cost = cost if cost is not None else max(1.0, float(self._cost_ledger.get(ref.encode(), 0.0)))
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
            computational_cost=real_cost,
            outcome=outcome,
            context_scope=context_scope,
            candidate_evaluation=dict(candidate_evaluation or {}),
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
        self._candidate_attempt_counts = {}
        for event in self._resolution_events:
            field_name = str(event.get("candidate_field") or "")
            values = list(event.get("candidate_values_considered") or [])
            ref_encoded = str(event.get("ref_before_encoded") or "")
            if not field_name or not values or not ref_encoded:
                continue
            key = self._candidate_attempt_key(ref_encoded, field_name, values[0])
            self._candidate_attempt_counts[key] = self._candidate_attempt_counts.get(key, 0) + 1


# ── systems-dict convenience wiring (the same "systems.get(...)" convention
#    every other subsystem in this codebase already shares) ────────────────

def warp_investigability_report(
    engine: Optional["RepresentationalResolutionEngine"], ref_encoded: Optional[str],
) -> Dict[str, Any]:
    """Build 714, Section 26 -- WARP boundary.

    Audited: aurora_warp_protocol.py's coverage-gap/anomaly-detection
    machinery (CoverageGap, WarpComponent, WarpGenerator, ConstraintAnomaly
    Record, evaluate_warp_trials) operates entirely on a disjoint 5D/15D
    axis-profile vocabulary with NO representational_ref field anywhere.
    The one WARP type that DOES carry a ref -- WarpDemand.representational_
    ref -- is an existing, directive-protected invariant from an earlier
    phase of this session, explicitly documented as "contextual provenance
    only, never read by _classify()/_route() or any numeric pathway logic."
    This function does not touch that boundary and is never called from
    anywhere inside aurora_warp_protocol.py or aurora_internal/aurora_
    recursive_causal_reasoning_waveform.py -- verified by
    tests/test_representational_resolution_build714.py's own source scan.

    Building a real (non-fabricated) bridge between "coverage gap in an
    axis-profile space" and "unresolved RepresentationalRef field" is not
    possible today without inventing a mapping between two vocabularies
    that share no genuine structural correlation -- exactly what this
    directive's own Section 34 forbids ("no hardcoded input pattern... as
    authority"). So rather than wire a decision-affecting coupling into
    WARP's promotion pipeline (which several existing tests protect in
    exact-behavior detail), this is a standalone, read-only advisory a
    caller MAY consult before treating a coverage gap as evidence for new
    representational structure -- satisfying "existing unresolved
    coordinates should be investigable before unnecessary new
    representational invention" as a capability, while leaving "full
    resolution must not become a mandatory WARP prerequisite" untouched:
    nothing calls this, nothing gates on it, and a caller ignoring it
    entirely is exactly as valid as one that doesn't.
    """
    if engine is None or not ref_encoded:
        return {"available": False, "reason": "no_engine_or_ref"}
    try:
        ref = RepresentationalRef.decode(ref_encoded)
    except Exception:
        return {"available": False, "reason": "undecodable_ref"}

    unresolved = ref.unresolved_fields()
    if not unresolved:
        return {"available": True, "ref": ref_encoded, "unresolved_fields": (), "investigable": False,
                "reason": "already_fully_resolved"}

    pressure = engine.inadequacy_pressure(ref)
    candidates = engine.unresolved_field_candidates(ref) if pressure > 0.0 else []
    records = engine.genealogy_for(ref)
    recently_explained = any(
        r.get("status") == "retained" and r.get("discrepancy_after", 1.0) < r.get("discrepancy_before", 0.0)
        for r in records
    )
    return {
        "available": True,
        "ref": ref_encoded,
        "unresolved_fields": unresolved,
        "inadequacy_pressure": pressure,
        "candidate_count": len(candidates),
        "investigable": bool(candidates),
        "already_explained_by_existing_structure": recently_explained,
    }


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
    candidate_evaluation: Optional[Dict[str, Any]] = None,
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
            candidate_evaluation=candidate_evaluation,
        )
    except Exception:
        pass
