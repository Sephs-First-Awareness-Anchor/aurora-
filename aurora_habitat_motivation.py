#!/usr/bin/env python3
"""
aurora_habitat_motivation.py

AURORA BUILD 717 -- AUTONOMOUS HABITAT MOTIVATION, CLOSED-LOOP RESOLUTION,
AND LIVED PERCEPTUAL DEVELOPMENT DIRECTIVE.

Answers the directive's Primary Question with a real bridge rather than a
script. Audited first (read-only, no edits) before writing this file:
_proactive_loop() in flutter_app/android/app/src/main/python/aurora_bridge.py
chains several real pressure sources into one observation string, but that
string only ever reaches process_external_user_turn() -- whose output
becomes spoken text (_proactive_expression). There is no branch anywhere
that turns pressure into an executed action. The only other autonomous-
action precedent anywhere in this codebase (aurora_daemon.py's code-
mutation trigger) is purely timer-based ("every ~10 min"), not pressure-
arbitrated -- so there was no existing arbitration primitive to reuse
either. This module is that primitive, built to the directive's own
constraints:

  Section 3 -- Governing Motivation Principle: this module manufactures NO
  motive. It reads Aurora's OWN already-real pressure (representational
  inadequacy pressure from aurora_representational_resolution.py, computed
  from genealogy's own consequence_profile, no new physics) and asks only
  "does Habitat afford an opportunity to act on THIS specific pressure."
  Habitat opportunities are exposed as neutral facts (Section 5); nothing
  here decides they are motivationally relevant except by genuinely
  intersecting a real pressure source.

  Section 4 -- no fixed schedule, no hardcoded action label ("play",
  "introspect", "create"). Every candidate is a physically-legal Habitat
  operation on a physically-eligible entity, generated from
  HabitatRuntime.get_affordances()/get_state(), never a label chosen in
  advance.

  Section 7 -- competition, not command. select_action() is a generic
  candidate-competition primitive (name and logic are not Habitat-specific)
  that returns the winner among whatever candidates it is given, or None.
  "No action" is the return value whenever nothing clears the bar --
  expected to be the common case, exactly like the existing proactive
  loop's own speech decision, which also produces nothing most cycles.

  Section 11 -- Aurora-native arbitration, inspectable. select_action()
  IS the arbitration; nothing upstream (Habitat, Flutter, the bridge) picks
  the action for her. Every step is captured in the returned engagement
  record (Section 25).

  Section 16/28 -- Habitat cognition consumes current_resolution() and
  inadequacy_pressure() (real, already-computed by Build 714's engine) as
  its relevance signal -- the resolution loop and Habitat motivation share
  one physics, not two.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Section 6's neutral affordance categories map onto the SAME three
# operation-category axes aurora_habitat.py's own _emit_resolution_pressure
# already established (X=existence, N=change, B=boundary) -- reused
# verbatim, not reinvented, so a pressure signal and a Habitat affordance
# are talking about the same identity.
_CATEGORY_AXES: Tuple[str, ...] = ("X", "N", "B")

MIN_RELEVANCE_TO_ENGAGE = 0.20
STAGE_PENDING_BONUS = 0.35


@dataclass
class HabitatEngagementRecord:
    """Section 25 -- motivation observability. Structural causes only, no
    anthropomorphic explanation invented on Aurora's behalf."""
    timestamp: float
    active_pressures: Dict[str, float]
    active_inquiries: List[str]
    environmental_affordances_considered: int
    candidate_actions: List[Dict[str, Any]]
    selected_action: Optional[Dict[str, Any]]
    selection_evidence: Dict[str, Any]
    competing_candidates: List[Dict[str, Any]]
    pre_state: Optional[Dict[str, Any]] = None
    post_state: Optional[Dict[str, Any]] = None
    consequence: Optional[Dict[str, Any]] = None
    pressure_change: Optional[Dict[str, float]] = None
    engaged: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "active_pressures": self.active_pressures,
            "active_inquiries": self.active_inquiries,
            "environmental_affordances_considered": self.environmental_affordances_considered,
            "candidate_actions": self.candidate_actions,
            "selected_action": self.selected_action,
            "selection_evidence": self.selection_evidence,
            "competing_candidates": self.competing_candidates,
            "pre_state": self.pre_state,
            "post_state": self.post_state,
            "consequence": self.consequence,
            "pressure_change": self.pressure_change,
            "engaged": self.engaged,
        }


def _operation_category(operation: str) -> Optional[str]:
    """Mirrors aurora_habitat.py's own _EXISTENCE_OPS/_CHANGE_OPS/
    _BOUNDARY_OPS category membership -- imported directly rather than
    duplicated, so this module can never silently drift from Habitat's own
    physical-operation categories."""
    from aurora_habitat import _EXISTENCE_OPS, _CHANGE_OPS, _BOUNDARY_OPS
    if operation in _EXISTENCE_OPS:
        return "X"
    if operation in _CHANGE_OPS:
        return "N"
    if operation in _BOUNDARY_OPS:
        return "B"
    return None


def active_pressures(systems: Optional[Dict[str, Any]]) -> Dict[str, float]:
    """The real, already-computed inadequacy_pressure() for each Habitat
    operation-category ref that has ever actually been registered (i.e.
    genuinely participated in at least one real consequence -- see
    aurora_representational_resolution.RepresentationalResolutionEngine.
    ensure_registered()). A category with no prior participation simply
    has no pressure to report -- never fabricated as zero-with-meaning,
    just genuinely absent."""
    from aurora_representational_address import RepresentationalRef
    from aurora_representational_resolution import get_or_create_engine

    engine = get_or_create_engine(systems)
    if engine is None:
        return {}
    pressures: Dict[str, float] = {}
    for axis in _CATEGORY_AXES:
        ref = RepresentationalRef.for_c1(axis, "OPERATOR", "A")
        ability_id = engine.ability_id_for_ref(ref)
        if ability_id not in getattr(engine.genealogy, "abilities", {}):
            continue
        p = engine.inadequacy_pressure(ref)
        if p > 0.0:
            pressures[axis] = p
    return pressures


def resolved_context_for_axis(systems: Optional[Dict[str, Any]], axis: str) -> Dict[str, Any]:
    """Section 16/28 -- Habitat cognition must consume current_resolution()
    itself, not merely inadequacy_pressure(): a category whose pressure ref
    has already earned real refinement (via the SAME record_participation()
    closure Section 12 wires into every genuine consequence) is evidence
    about how well-understood this pressure already is. Requests only the
    GLOBAL, unscoped resolution -- 'least-sufficient' (Section 16): this
    module has no per-context scope of its own to assert, so it asks for
    exactly what it needs and nothing more, the same restraint
    complete_field_inquiry()'s docstring requires of every caller."""
    from aurora_representational_address import RepresentationalRef
    from aurora_representational_resolution import get_or_create_engine

    engine = get_or_create_engine(systems)
    if engine is None:
        return {"resolved_fields": (), "earned_fields": (), "level": "UNKNOWN"}
    ref = RepresentationalRef.for_c1(axis, "OPERATOR", "A")
    refined = engine.current_resolution(ref)
    base_resolved = set(ref.resolved_fields())
    # Only fields NOT already given by the C1 ref's own construction count
    # as "earned" -- nc_law_c/nc_dim/nc_target are always present the
    # instant for_c1() is called, so counting them would reward every
    # category identically regardless of any real genealogy evidence.
    earned = tuple(f for f in refined.resolved_fields() if f not in base_resolved)
    return {
        "resolved_fields": refined.resolved_fields(),
        "earned_fields": earned,
        "level": refined.level(),
    }


def active_inquiries(systems: Optional[Dict[str, Any]]) -> List[str]:
    """Which operation-category refs currently have a live staged
    investigation (Section 12's closure) -- performing a real Habitat
    action in that category is what could complete it (Section 28: an
    unresolved distinction increases a relevant action's informational
    value). Reads existing state; stages nothing itself."""
    from aurora_representational_address import RepresentationalRef
    from aurora_representational_resolution import get_or_create_engine

    engine = get_or_create_engine(systems)
    if engine is None:
        return []
    live: List[str] = []
    for axis in _CATEGORY_AXES:
        ref = RepresentationalRef.for_c1(axis, "OPERATOR", "A")
        if ref.encode() in getattr(engine, "_active_stage_for_ref", {}):
            live.append(axis)
    return live


def candidate_actions(systems: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Section 5/6/10 -- neutral affordance surface intersected with real
    pressure. Returns [] whenever nothing is genuinely pressured, which is
    expected to be the common case (Section 3: 'no action' is legitimate).

    Never attaches an intended developmental outcome to a candidate (no
    "move object to learn agency") -- each candidate is exactly:
    {operation, territory, target_ids, relevance_score, reason}, where
    relevance_score is built ONLY from real pressure/stage signals already
    computed elsewhere, and reason records which real signal produced it
    (Section 25) rather than an invented motive."""
    habitat = (systems or {}).get("habitat")
    if habitat is None:
        return []
    pressures = active_pressures(systems)
    inquiries = set(active_inquiries(systems))
    if not pressures and not inquiries:
        return []

    try:
        state = habitat.get_state(actor="aurora")
    except Exception:
        return []
    entities = (state or {}).get("entities", []) or []

    # Section 16/28 -- fetch each pressured/inquiring axis's earned
    # resolution ONCE per call (least-sufficient: only the axes actually in
    # play here, never every axis that exists), not per candidate.
    resolved_context: Dict[str, Dict[str, Any]] = {}
    for axis in pressures.keys() | inquiries:
        resolved_context[axis] = resolved_context_for_axis(systems, axis)

    candidates: List[Dict[str, Any]] = []
    for entity in entities:
        entity_id = entity.get("id")
        if not entity_id:
            continue
        territory = entity.get("territory")
        entity_type = entity.get("entity_type")
        perms = entity.get("interaction_permissions", {}) or {}
        if not perms.get("modifiable_by_aurora", False):
            continue
        for operation in _real_operations_for_entity(habitat, territory, entity):
            axis = _operation_category(operation)
            if axis is None:
                continue
            has_pressure = axis in pressures
            has_inquiry = axis in inquiries
            if not has_pressure and not has_inquiry:
                continue
            relevance = float(pressures.get(axis, 0.0))
            if has_inquiry:
                relevance += STAGE_PENDING_BONUS
            earned = resolved_context.get(
                axis, {"resolved_fields": (), "earned_fields": (), "level": "UNKNOWN"},
            )
            # A pressure whose ref carries more earned, non-demoted
            # resolution is less speculative -- Aurora already knows more
            # about what specifically is unresolved here, not just that
            # something is. Small and capped: earned resolution informs
            # competition, it does not override real pressure (Section 3).
            relevance += 0.05 * len(earned["earned_fields"])
            candidates.append({
                "operation": operation,
                "territory": territory,
                "target_ids": [entity_id],
                "entity_type": entity_type,
                "relevance_score": relevance,
                "reason": {
                    "axis": axis,
                    "inadequacy_pressure": pressures.get(axis, 0.0),
                    "active_inquiry_pending": has_inquiry,
                    "earned_resolution": earned,
                },
            })
    candidates.sort(key=lambda c: -c["relevance_score"])
    return candidates


def _real_operations_for_entity(habitat: Any, territory: Optional[str], entity: Dict[str, Any]) -> List[str]:
    """Only physically/legally available operations -- Section 10's
    explicit "Bad: move object to learn agency / Good: entity X can be
    moved" distinction. Sourced from HabitatRuntime.get_affordances()'s own
    OPERATIONS list, filtered to what this specific entity structurally
    supports (groups can't be resized/recolored/rotated as a unit the same
    way a shape can; existence ops always apply to a live entity)."""
    try:
        affordances = habitat.get_affordances()
    except Exception:
        return []
    all_ops = list(affordances.get("operations", []))
    entity_type = entity.get("entity_type")
    ops: List[str] = []
    for op in all_ops:
        if op in ("create", "duplicate", "grant_permission", "revoke_permission"):
            continue  # not a per-entity affordance on an existing entity
        if op in ("resize", "rotate", "recolor") and entity_type == "group":
            continue  # groups don't carry these properties directly
        if op == "ungroup" and entity_type != "group":
            continue
        if op == "group" and entity_type == "group":
            continue
        ops.append(op)
    return ops


def select_action(
    candidates: List[Dict[str, Any]], *, min_relevance: float = MIN_RELEVANCE_TO_ENGAGE,
) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """Section 7/11 -- generic candidate competition, not Habitat-specific
    in name or logic. Returns (winner_or_None, selection_evidence).
    "No action" (winner is None) whenever nothing clears the bar, or the
    candidate list is empty -- the default, expected outcome."""
    if not candidates:
        return None, {"reason": "no_candidates"}
    winner = candidates[0]
    if winner["relevance_score"] < min_relevance:
        return None, {
            "reason": "below_relevance_threshold",
            "top_candidate": winner, "threshold": min_relevance,
        }
    return winner, {
        "reason": "cleared_relevance_threshold",
        "threshold": min_relevance, "margin": winner["relevance_score"] - min_relevance,
    }


def maybe_engage_habitat(systems: Optional[Dict[str, Any]]) -> HabitatEngagementRecord:
    """The single entry point Section 32's end-to-end chain runs through.
    Always returns a record (Section 25) -- engaged=False is the common,
    legitimate outcome, not a failure. Never raises: a failure anywhere in
    this optional, competing candidate source must not affect anything
    else the proactive cycle is doing."""
    habitat = (systems or {}).get("habitat")
    pressures = active_pressures(systems)
    inquiries = active_inquiries(systems)
    try:
        candidates = candidate_actions(systems)
    except Exception:
        candidates = []

    record = HabitatEngagementRecord(
        timestamp=time.time(),
        active_pressures=pressures,
        active_inquiries=inquiries,
        environmental_affordances_considered=len(candidates),
        candidate_actions=candidates,
        selected_action=None,
        selection_evidence={},
        competing_candidates=candidates,
    )
    if habitat is None:
        record.selection_evidence = {"reason": "no_habitat"}
        return record

    try:
        winner, evidence = select_action(candidates)
    except Exception:
        winner, evidence = None, {"reason": "selection_error"}
    record.selection_evidence = evidence
    if winner is None:
        return record

    try:
        pre_state = habitat.get_state()
    except Exception:
        pre_state = None
    record.pre_state = pre_state
    record.selected_action = winner

    try:
        consequence = habitat.act(
            actor="aurora", territory=winner["territory"], operation=winner["operation"],
            target_ids=winner["target_ids"], parameters={},
            intention_context="autonomous_engagement",
        )
        record.consequence = consequence.to_dict() if hasattr(consequence, "to_dict") else dict(consequence or {})
        record.engaged = bool(getattr(consequence, "success", False))
    except Exception as exc:
        record.consequence = {"error": str(exc)}
        record.engaged = False

    try:
        record.post_state = habitat.get_state()
    except Exception:
        record.post_state = None

    try:
        after_pressures = active_pressures(systems)
        record.pressure_change = {
            axis: round(after_pressures.get(axis, 0.0) - pressures.get(axis, 0.0), 6)
            for axis in set(pressures) | set(after_pressures)
        }
    except Exception:
        record.pressure_change = None

    return record
