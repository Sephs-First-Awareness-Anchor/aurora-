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

import random
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

# Follow-up (broadened motivational inputs, item 1): aurora_language_field.py's
# identity-field axis_pressures default to ~0.30 when no data is present
# (its own _tensor_state() fallback) -- only elevation genuinely ABOVE that
# resting baseline counts as a real motivational signal, never the resting
# value itself (which would manufacture motive out of nothing, violating
# section 3).
IDENTITY_FIELD_BASELINE = 0.30
IDENTITY_FIELD_ELEVATION_WEIGHT = 0.5

# Follow-up (item 2, real Self/Space relevance): both bonuses are read from
# REAL structural facts already sitting on the entity/action -- never a
# hardcoded "Self means X" label. An entity Aurora exclusively owns carries
# a real, technically-enforced boundary (aurora_habitat.py's own
# _default_permissions: Self defaults modifiable_by_human=False) that a
# shared Space entity never has -- OWNERSHIP_ALIGNED_BONUS reflects that
# real fact, and SELF_EXCLUSIVE_BONUS is the additional real weight of the
# territory itself defaulting new entities to exclusive Aurora ownership
# (aurora_habitat.py::_op_create's own owner default). Both are small and
# additive, exactly like the earned-resolution bonus below -- they inform
# competition among already-pressured candidates, never manufacture one.
OWNERSHIP_ALIGNED_BONUS = 0.05
SELF_EXCLUSIVE_BONUS = 0.05

# Follow-up (item 3, fully instantiated actions): a small, real, neutral
# vocabulary for parameter values that are neither fabricated meaning nor
# derived from Aurora's own internal axis state (Rule 3) -- a genuine
# environmental dice roll, exactly as "which exact pixel a hand lands on"
# is not itself a developmental claim.
_RECOLOR_PALETTE: Tuple[str, ...] = ("red", "blue", "green", "yellow", "purple", "orange", "teal", "gray")
_CREATABLE_ENTITY_TYPES: Tuple[str, ...] = ("shape", "text", "mark_path", "connector")


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


def _identity_field_axis_elevation(systems: Optional[Dict[str, Any]]) -> Dict[str, float]:
    """Follow-up, item 1 -- broadens motivational input beyond
    representational inadequacy: Aurora's own identity field already
    computes real X/T/N/B/A axis pressure every tick (aurora_language_
    field.py, consumed identically by _proactive_loop()'s own salience
    prefix and by aurora_possibility_selves.py/aurora_quantum_dream_
    substrate.py elsewhere in this codebase -- an established, widely-read
    real signal, not invented for this module). Only genuine elevation
    above the field's own resting baseline counts; the baseline itself
    carries no motivational content (section 3 -- no motive manufactured
    from nothing)."""
    identity_field = (systems or {}).get("identity_field")
    if identity_field is None or not hasattr(identity_field, "status"):
        return {}
    try:
        status = identity_field.status() or {}
    except Exception:
        return {}
    axis_pressures = status.get("axis_pressures") or {}
    elevation: Dict[str, float] = {}
    for axis in _CATEGORY_AXES:
        v = axis_pressures.get(axis)
        if v is None:
            continue
        above_baseline = float(v) - IDENTITY_FIELD_BASELINE
        if above_baseline > 0.0:
            elevation[axis] = above_baseline * IDENTITY_FIELD_ELEVATION_WEIGHT
    return elevation


def active_pressures(systems: Optional[Dict[str, Any]]) -> Dict[str, float]:
    """The real, already-computed inadequacy_pressure() for each Habitat
    operation-category ref that has ever actually been registered (i.e.
    genuinely participated in at least one real consequence -- see
    aurora_representational_resolution.RepresentationalResolutionEngine.
    ensure_registered()), COMBINED with Aurora's own broader identity-field
    axis elevation (item 1 -- motivational input is no longer limited to
    this one narrow representational-inadequacy signal). A category with
    neither source active simply has no pressure to report -- never
    fabricated as zero-with-meaning, just genuinely absent."""
    from aurora_representational_address import RepresentationalRef
    from aurora_representational_resolution import get_or_create_engine

    pressures: Dict[str, float] = {}
    engine = get_or_create_engine(systems)
    if engine is not None:
        for axis in _CATEGORY_AXES:
            ref = RepresentationalRef.for_c1(axis, "OPERATOR", "A")
            ability_id = engine.ability_id_for_ref(ref)
            if ability_id not in getattr(engine.genealogy, "abilities", {}):
                continue
            p = engine.inadequacy_pressure(ref)
            if p > 0.0:
                pressures[axis] = p

    for axis, elevation in _identity_field_axis_elevation(systems).items():
        pressures[axis] = pressures.get(axis, 0.0) + elevation

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
        return {"resolved_fields": (), "earned_fields": (), "provisional_fields": (), "level": "UNKNOWN"}
    ref = RepresentationalRef.for_c1(axis, "OPERATOR", "A")
    refined = engine.current_resolution(ref)
    base_resolved = set(ref.resolved_fields())
    # Only fields NOT already given by the C1 ref's own construction count
    # as "earned" -- nc_law_c/nc_dim/nc_target are always present the
    # instant for_c1() is called, so counting them would reward every
    # category identically regardless of any real genealogy evidence.
    earned = tuple(f for f in refined.resolved_fields() if f not in base_resolved)

    # Follow-up, item 6 -- causal participation: if a domain-hypothesis
    # candidate is currently staged for this ref, this call to
    # provisional_resolution() IS a real causal read (recorded by the
    # engine itself) that complete_field_inquiry() will require before the
    # candidate may ever be retained. Never conflated with earned_fields
    # (current_resolution() alone still governs what counts as knowledge,
    # Section 14) -- kept in its own key so a caller can tell "this
    # already earned authority" from "this is only being tried right now".
    provisional = engine.provisional_resolution(ref)
    provisional_fields = tuple(
        f for f in provisional.resolved_fields() if f not in base_resolved and f not in earned
    )
    return {
        "resolved_fields": refined.resolved_fields(),
        "earned_fields": earned,
        "provisional_fields": provisional_fields,
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


def _ownership_relevance_bonus(territory: Optional[str], owner: Optional[str]) -> float:
    """Follow-up, item 2 -- Self and Space genuinely differ because their
    REAL ownership/permission facts differ, never because of a hardcoded
    label. An entity Aurora exclusively owns carries more real, technically
    -enforced significance than a jointly-owned one; Self territory is the
    only place that exclusivity is the DEFAULT (aurora_habitat.py's own
    _default_permissions: Self's modifiable_by_human starts False unless
    the owner is human)."""
    bonus = 0.0
    if owner == "aurora":
        bonus += OWNERSHIP_ALIGNED_BONUS
        if territory == "self":
            bonus += SELF_EXCLUSIVE_BONUS
    return bonus


def _real_parameters_for_operation(
    operation: str, entity: Dict[str, Any], all_entities: List[Dict[str, Any]],
) -> Optional[Tuple[Dict[str, Any], List[str]]]:
    """Follow-up, item 3 -- returns (parameters, extra_target_ids) for a
    genuinely enactable, non-vacuous instance of `operation`, or None when
    no real instantiation is currently possible (e.g. connect with no
    eligible partner -- a genuinely absent affordance, never fabricated).
    Every value is either a real environmental dice roll (never derived
    from Aurora's own internal axis state -- Rule 3) or read from real
    existing entity data; nothing here invents meaning or an intended
    developmental outcome (Section 10)."""
    entity_id = entity.get("id")
    if operation == "move":
        return {"x": round(random.uniform(0.0, 1.0), 4), "y": round(random.uniform(0.0, 1.0), 4)}, []
    if operation == "resize":
        return {"width": round(random.uniform(0.05, 1.0), 4), "height": round(random.uniform(0.05, 1.0), 4)}, []
    if operation == "rotate":
        return {"degrees": round(random.uniform(0.0, 360.0), 2)}, []
    if operation == "recolor":
        current = (entity.get("visual_properties") or {}).get("color")
        choices = [c for c in _RECOLOR_PALETTE if c != current] or list(_RECOLOR_PALETTE)
        return {"color": random.choice(choices)}, []
    if operation in ("connect", "disconnect"):
        territory = entity.get("territory")
        links = set(entity.get("links") or [])
        eligible: List[str] = []
        for other in all_entities:
            other_id = other.get("id")
            if not other_id or other_id == entity_id:
                continue
            if other.get("territory") != territory:
                continue
            if not (other.get("interaction_permissions") or {}).get("modifiable_by_aurora", False):
                continue
            already_linked = other_id in links
            if operation == "connect" and already_linked:
                continue
            if operation == "disconnect" and not already_linked:
                continue
            eligible.append(other_id)
        if not eligible:
            return None  # no real second party -- multi-target requirement genuinely unmet
        return {}, [random.choice(eligible)]
    if operation == "transfer":
        from aurora_habitat import OWNERS
        current_owner = entity.get("owner")
        choices = [o for o in OWNERS if o != current_owner] or list(OWNERS)
        return {"owner": random.choice(choices), "territory": entity.get("territory")}, []
    return {}, []


def _real_creation_parameters(territory: str) -> Dict[str, Any]:
    """Follow-up, item 4 -- autonomous creation. A real, neutral
    entity_type/position/dimensions dice roll; ownership/permissions are
    left to aurora_habitat.py's own _op_create defaults (Self exclusive,
    Space shared) rather than duplicated here."""
    return {
        "entity_type": random.choice(_CREATABLE_ENTITY_TYPES),
        "position": [round(random.uniform(0.0, 1.0), 4), round(random.uniform(0.0, 1.0), 4)],
        "dimensions": [round(random.uniform(0.05, 0.3), 4), round(random.uniform(0.05, 0.3), 4)],
    }


def candidate_actions(systems: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Section 5/6/10 -- neutral affordance surface intersected with real
    pressure. Returns [] whenever nothing is genuinely pressured, which is
    expected to be the common case (Section 3: 'no action' is legitimate).

    Never attaches an intended developmental outcome to a candidate (no
    "move object to learn agency") -- each candidate is exactly:
    {operation, territory, target_ids, parameters, relevance_score, reason},
    where relevance_score is built ONLY from real pressure/stage/ownership
    signals already computed elsewhere, and reason records which real
    signal produced it (Section 25) rather than an invented motive.
    parameters are always concrete and non-vacuous when present (item 3);
    target_ids includes every entity the operation structurally requires
    (item 3's multi-target requirement, e.g. connect/disconnect)."""
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

    def _earned_bonus(axis: str) -> Tuple[float, Dict[str, Any]]:
        earned = resolved_context.get(
            axis, {"resolved_fields": (), "earned_fields": (), "provisional_fields": (), "level": "UNKNOWN"},
        )
        # A pressure whose ref carries more earned, non-demoted resolution
        # is less speculative -- Aurora already knows more about what
        # specifically is unresolved here, not just that something is.
        # Small and capped: earned resolution informs competition, it does
        # not override real pressure (Section 3).
        bonus = 0.05 * len(earned["earned_fields"])
        # Item 6 -- a currently-staged (unconfirmed) candidate contributes
        # too, but at a fraction of earned's weight: this is what makes
        # reading it a genuine causal act (it measurably moves competition)
        # rather than an inert lookup, while still keeping "candidate is
        # not knowledge" real -- an unproven hypothesis can never outweigh
        # actual earned authority.
        bonus += 0.02 * len(earned.get("provisional_fields") or ())
        return bonus, earned

    candidates: List[Dict[str, Any]] = []
    for entity in entities:
        entity_id = entity.get("id")
        if not entity_id:
            continue
        territory = entity.get("territory")
        entity_type = entity.get("entity_type")
        owner = entity.get("owner")
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
            instantiation = _real_parameters_for_operation(operation, entity, entities)
            if instantiation is None:
                continue  # no real, non-fabricated way to instantiate this right now
            parameters, extra_targets = instantiation
            relevance = float(pressures.get(axis, 0.0))
            if has_inquiry:
                relevance += STAGE_PENDING_BONUS
            earned_bonus, earned = _earned_bonus(axis)
            relevance += earned_bonus
            relevance += _ownership_relevance_bonus(territory, owner)
            candidates.append({
                "operation": operation,
                "territory": territory,
                "target_ids": [entity_id] + extra_targets,
                "entity_type": entity_type,
                "parameters": parameters,
                "relevance_score": relevance,
                "reason": {
                    "axis": axis,
                    "inadequacy_pressure": pressures.get(axis, 0.0),
                    "active_inquiry_pending": has_inquiry,
                    "earned_resolution": earned,
                    "ownership_bonus": _ownership_relevance_bonus(territory, owner),
                },
            })

    # Item 4 -- autonomous creation, not tied to any existing entity.
    # Existence-axis pressure/inquiry is what makes creating something new
    # (rather than modifying something that already exists) relevant.
    if "X" in pressures or "X" in inquiries:
        earned_bonus, earned = _earned_bonus("X")
        for territory in ("self", "space"):
            relevance = float(pressures.get("X", 0.0))
            if "X" in inquiries:
                relevance += STAGE_PENDING_BONUS
            relevance += earned_bonus
            # No existing entity to read ownership from yet -- the real
            # structural fact is the territory's own default (Self
            # defaults new entities to exclusive Aurora ownership; Space
            # defaults to shared), so this is exactly the SELF_EXCLUSIVE
            # half of the same bonus above, not a separate rule.
            ownership_bonus = SELF_EXCLUSIVE_BONUS if territory == "self" else 0.0
            relevance += ownership_bonus
            candidates.append({
                "operation": "create",
                "territory": territory,
                "target_ids": [],
                "entity_type": None,
                "parameters": _real_creation_parameters(territory),
                "relevance_score": relevance,
                "reason": {
                    "axis": "X",
                    "inadequacy_pressure": pressures.get("X", 0.0),
                    "active_inquiry_pending": "X" in inquiries,
                    "earned_resolution": earned,
                    "ownership_bonus": ownership_bonus,
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
        if op == "restore":
            continue  # get_state() never returns deleted entities -- restore-on-a-live-entity is a structural no-op
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
            target_ids=winner["target_ids"], parameters=dict(winner.get("parameters") or {}),
            intention_context="autonomous_engagement",
        )
        record.consequence = consequence.to_dict() if hasattr(consequence, "to_dict") else dict(consequence or {})
        # A legally-granted but vacuous action (state_changed=False) is not
        # a genuine engagement -- Aurora didn't actually do anything to the
        # world, whatever the permission boundary said. Defaults to True
        # for any Habitat build predating the state_changed field so this
        # module degrades gracefully rather than under-reporting.
        record.engaged = bool(getattr(consequence, "success", False)) and bool(
            getattr(consequence, "state_changed", True)
        )
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
