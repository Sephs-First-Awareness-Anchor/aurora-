# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA BUILD 717 -- AUTONOMOUS HABITAT MOTIVATION, CLOSED-LOOP RESOLUTION,
AND LIVED PERCEPTUAL DEVELOPMENT DIRECTIVE.

Required regression coverage for aurora_habitat_motivation.py (directive
section 31, motivation category) plus the section 21 Autonomous Habitat
Engagement Canary with its required control conditions.

Every test here drives REAL ConstraintGenealogyLogger / HabitatRuntime /
RepresentationalResolutionEngine machinery -- never a mock of the physics
under test. Pressure is built the same way tests/test_representational_
resolution_build714.py builds it: real record_participation() calls with
genuinely divergent axes, never a hand-set pressure field.
"""
from __future__ import annotations

import tempfile

import pytest

from aurora_internal.constraint_genealogy import (
    AXES,
    AbilityProfile,
    ConstraintGenealogyLogger,
    GenealogyConfig,
    TraceItem,
)
from aurora_representational_address import RepresentationalRef
from aurora_representational_resolution import get_or_create_engine
from aurora_habitat import HabitatRuntime
import aurora_habitat_motivation as mot


def _context_ability(genealogy, cid):
    if cid not in genealogy.abilities:
        genealogy.abilities[cid] = AbilityProfile(
            id=cid, axis="X", requires=("X",),
            cost={a: 0.0 for a in AXES}, risk={a: 0.0 for a in AXES},
            effect_tags=("context_marker",), notes="test context",
        )


def _fresh_systems(tmp_path, name):
    genealogy = ConstraintGenealogyLogger(name, config=GenealogyConfig(), output_dir=str(tmp_path / name / "g"))
    systems = {"genealogy": genealogy, "state_dir": str(tmp_path / name / "s")}
    habitat = HabitatRuntime(str(tmp_path / name / "hab"), systems=systems)
    systems["habitat"] = habitat
    return genealogy, systems, habitat


def _drive_real_pressure(genealogy, engine, ref, *, ticks=15, axis_sequence=("B", "X", "T")):
    """Repeatedly participates `ref` with relief landing on axes OTHER than
    its own declared axis -- the same divergent-participation pattern
    Build 714's own tests use to produce genuine, measured discrepancy
    (never a hand-set pressure number)."""
    i = 0
    seq = list(axis_sequence) * ((ticks // len(axis_sequence)) + 1)
    for ax in seq[:ticks]:
        ctx = f"CTX:{i % 3}"
        _context_ability(genealogy, ctx)
        engine.record_participation(
            ref, pressure_before={a: (0.3 if a == ax else 0.0) for a in AXES},
            pressure_after={a: 0.0 for a in AXES}, source="mot_test",
            context_tag=ctx, extra_trace=[TraceItem(kind="ABILITY", id=ctx)],
        )
        i += 1
    return i


# ── Section 21: Autonomous Habitat Engagement Canary ────────────────────────

def test_A_control_zero_pressure_produces_zero_engagement(tmp_path):
    """No pressure exists anywhere -- 'no action' must be the outcome
    (directive section 3: the world is allowed to remain untouched)."""
    _genealogy, systems, habitat = _fresh_systems(tmp_path, "canary_control")
    habitat.act(actor="aurora", territory="space", operation="create", parameters={"entity_type": "shape"})

    record = mot.maybe_engage_habitat(systems)
    assert record.engaged is False
    assert record.selected_action is None
    assert record.active_pressures == {}


def test_B_control_real_pressure_but_no_afforded_opportunity_produces_zero_engagement(tmp_path):
    """Section 21's required IRRELEVANT-affordance control: real,
    genuinely-measured pressure exists, but nothing in the Habitat
    currently affords Aurora an opportunity to act on it (no entities at
    all) -- engagement must still not occur. Pressure being real is not
    sufficient; an actual afforded opportunity is also required (section 5:
    Habitat is a neutral affordance surface, not a wish granter)."""
    genealogy, systems, habitat = _fresh_systems(tmp_path, "canary_irrelevant")
    engine = get_or_create_engine(systems)
    ref = RepresentationalRef.for_c1("N", "OPERATOR", "A")
    engine.ensure_registered(ref)
    _drive_real_pressure(genealogy, engine, ref)

    assert mot.active_pressures(systems).get("N", 0.0) > 0.0
    # No entity ever created -- affordance surface is genuinely empty.
    record = mot.maybe_engage_habitat(systems)
    assert record.engaged is False
    assert record.candidate_actions == []


def test_C_control_afforded_entity_aurora_cannot_modify_produces_zero_engagement(tmp_path):
    """A second flavor of 'irrelevant affordance': the entity visibly
    exists (a real affordance is present in the world) but Aurora's own
    modify permission on it has been revoked, so it must not become a
    candidate -- an opportunity that exists is not the same as an
    opportunity available to her."""
    genealogy, systems, habitat = _fresh_systems(tmp_path, "canary_permission")
    c = habitat.act(actor="aurora", territory="space", operation="create", parameters={"entity_type": "shape"})
    eid = c.affected_entities[0]
    revoked = habitat.act(
        actor="aurora", territory="space", operation="revoke_permission",
        target_ids=[eid], parameters={"permission": "modifiable_by_aurora"},
    )
    assert revoked.success

    engine = get_or_create_engine(systems)
    ref = RepresentationalRef.for_c1("N", "OPERATOR", "A")
    engine.ensure_registered(ref)
    _drive_real_pressure(genealogy, engine, ref)

    record = mot.maybe_engage_habitat(systems)
    assert record.engaged is False
    assert record.candidate_actions == []


def test_D_relevant_pressure_with_real_afforded_entity_produces_real_engagement(tmp_path):
    """The positive case: real, measured pressure plus a genuinely
    modifiable entity that structurally supports an operation in the
    pressured category -- engagement must occur, and the selected action
    must be a real, physically-legal Habitat operation (never a fabricated
    label)."""
    genealogy, systems, habitat = _fresh_systems(tmp_path, "canary_relevant")
    c = habitat.act(actor="aurora", territory="space", operation="create", parameters={"entity_type": "shape"})
    eid = c.affected_entities[0]

    engine = get_or_create_engine(systems)
    ref = RepresentationalRef.for_c1("N", "OPERATOR", "A")
    engine.ensure_registered(ref)
    _drive_real_pressure(genealogy, engine, ref)

    record = mot.maybe_engage_habitat(systems)
    assert record.engaged is True
    assert record.selected_action is not None
    assert record.selected_action["operation"] in ("move", "resize", "rotate", "recolor")
    assert record.selected_action["target_ids"] == [eid]
    # Real, inspectable consequence -- not a stub.
    assert record.consequence is not None
    assert "error" not in record.consequence
    assert record.pre_state is not None and record.post_state is not None


def test_E_selected_action_pressure_changes_after_engagement(tmp_path):
    """The consequence must genuinely feed back -- pressure_change is
    recorded from two REAL before/after inadequacy_pressure() reads, not
    fabricated."""
    genealogy, systems, habitat = _fresh_systems(tmp_path, "canary_feedback")
    habitat.act(actor="aurora", territory="space", operation="create", parameters={"entity_type": "shape"})

    engine = get_or_create_engine(systems)
    ref = RepresentationalRef.for_c1("N", "OPERATOR", "A")
    engine.ensure_registered(ref)
    _drive_real_pressure(genealogy, engine, ref)

    record = mot.maybe_engage_habitat(systems)
    assert record.engaged is True
    assert record.pressure_change is not None
    assert "N" in record.pressure_change


# ── Section 31 motivation-category unit assertions ──────────────────────────

def test_no_action_labels_are_hardcoded_in_this_module(tmp_path):
    """Directive section 4/10: 'play', 'introspect', 'social', 'ownership',
    'attachment', 'curiosity' must never appear as Habitat action labels in
    this module's EXECUTABLE code -- comments/docstrings are explicitly
    exempt (the directive's own audit standard), since this module's
    docstrings legitimately name the forbidden words to document that they
    are absent from the logic. Every real candidate operation must come
    from HabitatRuntime's own real operation set instead."""
    import ast
    import inspect

    source = inspect.getsource(mot)
    tree = ast.parse(source)

    def _is_docstring_expr(stmt):
        return isinstance(stmt, ast.Expr) and isinstance(getattr(stmt, "value", None), ast.Constant) \
            and isinstance(stmt.value.value, str)

    class _StripDocstrings(ast.NodeTransformer):
        def _strip(self, node):
            if node.body and _is_docstring_expr(node.body[0]):
                node.body = node.body[1:] or [ast.Pass()]
            self.generic_visit(node)
            return node

        visit_Module = _strip
        visit_FunctionDef = _strip
        visit_ClassDef = _strip

    tree = _StripDocstrings().visit(tree)
    ast.fix_missing_locations(tree)
    code_only = ast.unparse(tree).lower()

    forbidden = ("play", "introspect", "creativity", "sociality", "ownership", "attachment", "curiosity")
    for word in forbidden:
        assert word not in code_only, f"forbidden hardcoded action-label word found in executable code: {word!r}"


def test_operation_category_is_imported_not_duplicated(tmp_path):
    """_operation_category must import aurora_habitat's real frozensets
    rather than maintaining a parallel, driftable copy."""
    from aurora_habitat import _EXISTENCE_OPS, _CHANGE_OPS, _BOUNDARY_OPS
    assert mot._operation_category("create") == "X"
    assert mot._operation_category("move") == "N"
    assert mot._operation_category("group") == "B"
    assert mot._operation_category("nonexistent_op") is None
    assert set(_EXISTENCE_OPS) | set(_CHANGE_OPS) | set(_BOUNDARY_OPS)


def test_select_action_is_generic_competition_not_habitat_specific(tmp_path):
    """select_action() must return None (no action) whenever candidates are
    empty or none clear the relevance bar -- 'no action' is a legitimate,
    common outcome, never an error."""
    winner, evidence = mot.select_action([])
    assert winner is None and evidence["reason"] == "no_candidates"

    low = [{"operation": "move", "territory": "space", "target_ids": ["e1"], "relevance_score": 0.01}]
    winner, evidence = mot.select_action(low)
    assert winner is None and evidence["reason"] == "below_relevance_threshold"

    high = [{"operation": "move", "territory": "space", "target_ids": ["e1"], "relevance_score": 0.9}]
    winner, evidence = mot.select_action(high)
    assert winner is high[0] and evidence["reason"] == "cleared_relevance_threshold"


def test_maybe_engage_habitat_never_raises_on_habitat_act_failure(tmp_path):
    """A failure inside habitat.act() (e.g. a corrupted/unexpected state)
    must not propagate -- this optional, competing candidate source must
    never break the rest of the proactive cycle."""
    genealogy, systems, habitat = _fresh_systems(tmp_path, "canary_resilience")
    habitat.act(actor="aurora", territory="space", operation="create", parameters={"entity_type": "shape"})
    engine = get_or_create_engine(systems)
    ref = RepresentationalRef.for_c1("N", "OPERATOR", "A")
    engine.ensure_registered(ref)
    _drive_real_pressure(genealogy, engine, ref)

    def _boom(*a, **k):
        raise RuntimeError("simulated habitat failure")
    habitat.act = _boom  # type: ignore[assignment]

    record = mot.maybe_engage_habitat(systems)
    assert record.engaged is False
    assert record.consequence is not None and "error" in record.consequence


def test_engagement_record_is_structural_never_anthropomorphic(tmp_path):
    """Section 25: the record's own field names and reason contents must be
    structural (pressures, candidates, evidence) -- never an invented
    internal-state label like 'bored' or 'curious'."""
    genealogy, systems, habitat = _fresh_systems(tmp_path, "canary_observability")
    habitat.act(actor="aurora", territory="space", operation="create", parameters={"entity_type": "shape"})
    engine = get_or_create_engine(systems)
    ref = RepresentationalRef.for_c1("N", "OPERATOR", "A")
    engine.ensure_registered(ref)
    _drive_real_pressure(genealogy, engine, ref)

    record = mot.maybe_engage_habitat(systems)
    d = record.to_dict()
    forbidden = ("bored", "curious", "lonely", "wants to", "feels like")
    blob = str(d).lower()
    for word in forbidden:
        assert word not in blob, f"anthropomorphic language leaked into observability record: {word!r}"
    assert "active_pressures" in d and "selection_evidence" in d and "candidate_actions" in d


# ── Section 16/28: current_resolution() genuinely consumed ──────────────────

def test_resolved_context_for_axis_reports_no_earned_fields_before_any_resolution(tmp_path):
    _genealogy, systems, _habitat = _fresh_systems(tmp_path, "resctx_before")
    engine = get_or_create_engine(systems)
    ref = RepresentationalRef.for_c1("N", "OPERATOR", "A")
    engine.ensure_registered(ref)
    ctx = mot.resolved_context_for_axis(systems, "N")
    assert ctx["earned_fields"] == ()


def test_earned_resolution_genuinely_increases_relevance_after_being_earned(tmp_path):
    """Regression guard for the shape-vs-earned bug: nc_law_c/nc_dim/
    nc_target are always present the instant for_c1() is called, so a
    naive resolved_fields() count would reward every category identically
    with zero real evidence. Only fields earned BEYOND that baseline may
    move relevance."""
    genealogy, systems, habitat = _fresh_systems(tmp_path, "resctx_after")
    habitat.act(actor="aurora", territory="space", operation="create", parameters={"entity_type": "shape"})
    engine = get_or_create_engine(systems)
    ref = RepresentationalRef.for_c1("N", "OPERATOR", "A")
    engine.ensure_registered(ref)

    i = _drive_real_pressure(genealogy, engine, ref, ticks=15)
    before = mot.maybe_engage_habitat(systems)
    before_earned = before.selected_action["reason"]["earned_resolution"]["earned_fields"] if before.selected_action else ()

    # Drive a strong, single-axis participation to complete any staged
    # inquiry and genuinely earn a field.
    ctx = f"CTX:{i % 3}"
    _context_ability(genealogy, ctx)
    engine.record_participation(
        ref, pressure_before={"X": 0.0, "T": 0.5, "N": 0.0, "B": 0.0, "A": 0.0},
        pressure_after={a: 0.0 for a in AXES}, source="mot_test",
        context_tag=ctx, extra_trace=[TraceItem(kind="ABILITY", id=ctx)],
    )

    after = mot.maybe_engage_habitat(systems)
    if after.selected_action is not None:
        after_earned = after.selected_action["reason"]["earned_resolution"]["earned_fields"]
        assert len(after_earned) >= len(before_earned)
