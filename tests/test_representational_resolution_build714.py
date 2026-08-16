# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA BUILD 714 -- NATIVE ADAPTIVE REPRESENTATIONAL RESOLUTION.
Required regression coverage (directive Section 30, categories A-R).

Every test here exercises REAL genealogy machinery (ConstraintGenealogyLogger,
PressureVec, TraceItem) -- never a mock of the physics under test. Where a
"structurally-connected sibling representation" is needed to supply a
candidate field value, it is registered exactly as any real caller
(RCEC/Habitat) would register one -- via RepresentationalResolutionEngine.
ensure_registered() -- never via a shortcut that bypasses the same
production path.
"""
from __future__ import annotations

import inspect
import json
import os
import re
import tempfile

import pytest

from aurora_internal.constraint_genealogy import (
    AXES,
    AbilityProfile,
    ConstraintGenealogyLogger,
    GenealogyConfig,
    PressureVec,
    TraceItem,
)
from aurora_representational_address import RepresentationalRef
import aurora_representational_resolution as rr
from aurora_representational_resolution import (
    RepresentationalResolutionEngine,
    get_or_create_engine,
    record_ref_participation_from_scores,
)


def _fresh(tmp_path, name="build714"):
    genealogy = ConstraintGenealogyLogger(name, config=GenealogyConfig(), output_dir=str(tmp_path / name / "g"))
    engine = RepresentationalResolutionEngine(genealogy, state_dir=str(tmp_path / name / "s"))
    return genealogy, engine


def _context_ability(genealogy, cid):
    if cid not in genealogy.abilities:
        genealogy.abilities[cid] = AbilityProfile(
            id=cid, axis="X", requires=("X",),
            cost={a: 0.0 for a in AXES}, risk={a: 0.0 for a in AXES},
            effect_tags=("context_marker",), notes="test context",
        )


def _drive(genealogy, engine, ref, *, axis_sequence, context_prefix="CTX", n_contexts=3):
    """Repeatedly observes `ref` across `n_contexts` distinct contexts, with
    relief landing on the axis given per-tick by axis_sequence -- exactly
    the pattern that produces real, measured discrepancy when the axes
    diverge from the ref's own declared axis."""
    for i, ax in enumerate(axis_sequence):
        ctx_id = f"{context_prefix}:{i % n_contexts}"
        _context_ability(genealogy, ctx_id)
        engine.record_participation(
            ref,
            pressure_before={a: (0.3 if a == ax else 0.0) for a in AXES},
            pressure_after={a: 0.0 for a in AXES},
            source="test", context_tag=ctx_id,
            extra_trace=[TraceItem(kind="ABILITY", id=ctx_id)],
        )


# ── A. Coarse Sufficiency ───────────────────────────────────────────────────

def test_A_coherent_consequences_leave_representation_coarse(tmp_path):
    genealogy, engine = _fresh(tmp_path)
    ref = RepresentationalRef.for_c1("T", "MAGNITUDE", "B")
    # Every observation's relief lands on the SAME axis the ref itself
    # declares (T) -- a perfectly coherent, non-divergent consequence
    # history. No deeper coordinate should be fabricated.
    _drive(genealogy, engine, ref, axis_sequence=["T"] * 9)
    assert engine.inadequacy_pressure(ref) == 0.0
    assert engine.unresolved_field_candidates(ref) == []
    assert ref.unresolved_fields() == ("sub_law_c", "sub_law_d", "col_law_c", "col_law_d")


# ── B. Divergent Consequence Pressure ───────────────────────────────────────

def test_B_divergent_consequence_across_contexts_generates_measurable_pressure(tmp_path):
    genealogy, engine = _fresh(tmp_path)
    ref = RepresentationalRef.for_c1("T", "MAGNITUDE", "B")
    _drive(genealogy, engine, ref, axis_sequence=["B", "N", "X", "B", "N", "X", "B"], n_contexts=3)
    profile = engine.consequence_profile_for(ref)
    assert profile is not None
    assert profile["distinct_contexts"] >= 3
    assert profile["discrepancy"] > 0.0
    assert engine.inadequacy_pressure(ref) > 0.0


def test_B_single_anomalous_event_does_not_force_resolution(tmp_path):
    """One anomalous event must not automatically refine the representation
    (directive Section 9) -- distinct_contexts/confidence gates hold it back."""
    genealogy, engine = _fresh(tmp_path)
    ref = RepresentationalRef.for_c1("T", "MAGNITUDE", "B")
    _drive(genealogy, engine, ref, axis_sequence=["N"], n_contexts=1)
    assert engine.inadequacy_pressure(ref) == 0.0


# ── C. No Immediate Answer ──────────────────────────────────────────────────

def test_C_pressure_creates_investigation_not_an_immediate_field_value(tmp_path):
    genealogy, engine = _fresh(tmp_path)
    ref = RepresentationalRef.for_c1("T", "MAGNITUDE", "B")
    _drive(genealogy, engine, ref, axis_sequence=["B", "N", "X"] * 3, n_contexts=3)
    assert engine.inadequacy_pressure(ref) > 0.0
    # Pressure alone, with NO structurally-connected sibling registered yet,
    # must not populate a field -- candidates require real evidence.
    assert ref.unresolved_fields() == ("sub_law_c", "sub_law_d", "col_law_c", "col_law_d")
    assert engine.unresolved_field_candidates(ref) == []


# ── D. Earned Intermediate Field ────────────────────────────────────────────

def test_D_native_inquiry_sequence_produces_a_newly_resolved_field_traceable_to_evidence(tmp_path):
    genealogy, engine = _fresh(tmp_path)
    ref = RepresentationalRef.for_c1("T", "MAGNITUDE", "B")
    sibling = RepresentationalRef.for_m21("T", "MAGNITUDE", "B", col_law_c="N", col_law_d="COST")
    engine.ensure_registered(sibling)

    _drive(genealogy, engine, ref, axis_sequence=["B", "N", "X"] * 3, n_contexts=3)
    candidates = engine.unresolved_field_candidates(ref)
    assert candidates, "expected at least one candidate from the registered sibling"
    candidate = candidates[0]

    staged = engine.stage_field_inquiry(ref, candidate, consumer="test_D")
    assert staged

    result = engine.complete_field_inquiry(
        ref, candidate, staged[0], consumer="test_D", actual_coactivation=True,
        pressure_before={"X": 0.0, "T": 0.4, "N": 0.0, "B": 0.0, "A": 0.0},
        pressure_after={a: 0.0 for a in AXES},
    )
    assert result["representational_resolution_outcome"] == "retained"
    resolved = RepresentationalRef.decode(result["refined_ref"])
    assert getattr(resolved, candidate["field"]) == candidate["candidate_value"]

    records = engine.genealogy_for(ref)
    assert records and records[-1]["status"] == "retained"
    assert records[-1]["evidence_source"].startswith("stage:")
    assert records[-1]["discrepancy_after"] < records[-1]["discrepancy_before"]


# ── E. Independent Fields ───────────────────────────────────────────────────

def test_E_resolving_one_field_does_not_automatically_resolve_another(tmp_path):
    genealogy, engine = _fresh(tmp_path)
    ref = RepresentationalRef.for_c1("T", "MAGNITUDE", "B")
    sibling = RepresentationalRef.for_m21("T", "MAGNITUDE", "B", col_law_c="N", col_law_d="COST")
    engine.ensure_registered(sibling)
    _drive(genealogy, engine, ref, axis_sequence=["B", "N", "X"] * 3, n_contexts=3)

    resolved = engine.resolve_field(
        ref, "col_law_c", "N", evidence={}, discrepancy_before=0.9, discrepancy_after=0.3,
        pressure_before=0.5, pressure_after=0.0, cost=1.0,
    )
    assert resolved.col_law_c == "N"
    assert resolved.col_law_d is None
    assert resolved.sub_law_c is None
    assert resolved.sub_law_d is None


# ── F. No Fixed Staircase ───────────────────────────────────────────────────

def test_F_a_resolved_pattern_that_matches_no_named_rung_stays_honest(tmp_path):
    genealogy, engine = _fresh(tmp_path)
    ref = RepresentationalRef.for_c1("T", "MAGNITUDE", "B")
    resolved = engine.resolve_field(
        ref, "col_law_c", "N", evidence={}, discrepancy_before=0.9, discrepancy_after=0.3,
        pressure_before=0.5, pressure_after=0.0, cost=1.0,
    )
    # {nc_law_c, nc_dim, nc_target, col_law_c} matches none of the six named
    # ladder rungs (D1/C1/D2/M21/M22/C2) -- level() must say so honestly,
    # not force-classify it into the nearest one.
    assert resolved.level() == "UNKNOWN"
    assert resolved.resolved_fields() == ("nc_law_c", "nc_dim", "nc_target", "col_law_c")


# ── G. Consequence Profile Boundary (already covered exhaustively by
#      tests/test_consequence_profile_does_not_govern_perception.py; this
#      test only confirms Build 714's own module never touches the two
#      protected functions) ───────────────────────────────────────────────

def test_G_resolution_module_never_calls_sensory_routing_functions():
    """The module's own docstring legitimately DISCUSSES this boundary by
    name (see its module docstring); what must never appear is an actual
    call site."""
    src = inspect.getsource(rr)
    assert "_effective_axis_for_node(" not in src
    assert "_dps_route_observation(" not in src


# ── H. Consequence Profile Investigability ──────────────────────────────────

def test_H_consequence_profile_contributes_operational_discrepancy_that_makes_a_field_investigable(tmp_path):
    genealogy, engine = _fresh(tmp_path)
    ref = RepresentationalRef.for_c1("T", "MAGNITUDE", "B")
    sibling = RepresentationalRef.for_m21("T", "MAGNITUDE", "B", col_law_c="N", col_law_d="COST")
    engine.ensure_registered(sibling)
    _drive(genealogy, engine, ref, axis_sequence=["B", "N", "X"] * 3, n_contexts=3)

    ability = genealogy.abilities[engine.ability_id_for_ref(ref)]
    assert ability.consequence_profile is not None
    assert ability.consequence_profile["discrepancy"] > 0.0
    # The SAME profile that must never drive perception now legitimately
    # makes an unresolved field investigable.
    assert engine.unresolved_field_candidates(ref) != []


# ── I. History Sensitivity Without Meaning Injection ────────────────────────

def test_I_same_present_participation_under_different_history_yields_different_pressure(tmp_path):
    genealogy, engine = _fresh(tmp_path)
    ref = RepresentationalRef.for_c1("T", "MAGNITUDE", "B")
    # Coherent history first.
    _drive(genealogy, engine, ref, axis_sequence=["T"] * 6, n_contexts=3, context_prefix="A")
    pressure_after_coherent_history = engine.inadequacy_pressure(ref)

    genealogy2, engine2 = _fresh(tmp_path, name="build714_divergent")
    ref2 = RepresentationalRef.for_c1("T", "MAGNITUDE", "B")
    _drive(genealogy2, engine2, ref2, axis_sequence=["B", "N", "X"] * 2, n_contexts=3, context_prefix="B")
    pressure_after_divergent_history = engine2.inadequacy_pressure(ref2)

    assert pressure_after_coherent_history == 0.0
    assert pressure_after_divergent_history > pressure_after_coherent_history
    # Critically: the discrepancy came from measured relief location, not
    # from any per-history lookup table -- no coordinate was injected by
    # "history says so."
    assert ref.unresolved_fields() == ref2.unresolved_fields()


# ── J. Computational Laziness ───────────────────────────────────────────────

def test_J_low_pressure_narrow_call_does_not_materialize_the_full_manifold():
    from aurora_reflexive_interpreter import (
        MatchResult, _project_noncomp_state,
        reset_noncomp_materialization_stats, get_noncomp_materialization_stats,
    )
    match = MatchResult("B", "OPERATOR", "DIRECT", "neutral", None, [], "B:OPERATOR",
                         0.8, False, False, False, False, False, "statement", None)
    reset_noncomp_materialization_stats()
    narrow = _project_noncomp_state(
        match, worth_score=0.5, depth_score=0.5, origin_weight=0.5,
        origin_region="dense", route=None, expression="hello world", resolution_need="narrow",
    )
    assert narrow["manifold"]["materialized_slot_count"] == 25
    assert narrow["manifold"]["materialized_layer_count"] == 1
    assert narrow["manifold"]["slot_count"] == 125  # addressable space unchanged
    stats = get_noncomp_materialization_stats()
    assert stats["narrow_expansions"] == 1
    assert stats["full_manifold_expansions"] == 0


def test_J_default_call_still_materializes_the_full_manifold_backward_compat():
    from aurora_reflexive_interpreter import MatchResult, _project_noncomp_state
    match = MatchResult("B", "OPERATOR", "DIRECT", "neutral", None, [], "B:OPERATOR",
                         0.8, False, False, False, False, False, "statement", None)
    full = _project_noncomp_state(
        match, worth_score=0.5, depth_score=0.5, origin_weight=0.5,
        origin_region="dense", route=None, expression="hello world",
    )
    assert full["manifold"]["materialized_slot_count"] == 125
    assert full["manifold"]["materialized_layer_count"] == 5


# ── K. Escalated Resolution ─────────────────────────────────────────────────

def test_K_narrow_and_full_resolution_agree_on_every_field_a_real_consumer_reads():
    from aurora_reflexive_interpreter import MatchResult, _project_noncomp_state
    match = MatchResult("N", "COST", "DIRECT", "neutral", None, [], "N:COST",
                         0.8, False, False, False, False, False, "statement", None)
    narrow = _project_noncomp_state(
        match, worth_score=0.5, depth_score=0.5, origin_weight=0.5,
        origin_region="dense", route=None, expression="how much does this cost", resolution_need="narrow",
    )
    full = _project_noncomp_state(
        match, worth_score=0.5, depth_score=0.5, origin_weight=0.5,
        origin_region="dense", route=None, expression="how much does this cost", resolution_need="full",
    )
    assert narrow["dominant_target"] == full["dominant_target"]
    assert narrow["basis_channel"] == full["basis_channel"]
    assert narrow["semantic_translation"] == full["semantic_translation"]
    assert narrow["manifold"]["materialized_slot_count"] < full["manifold"]["materialized_slot_count"]


# ── L. Habitat Consequence ──────────────────────────────────────────────────

def test_L_habitat_interaction_sequence_contributes_real_representational_pressure(tmp_path):
    from aurora_habitat import HabitatRuntime
    genealogy = ConstraintGenealogyLogger("hab714", config=GenealogyConfig(), output_dir=str(tmp_path / "hg"))
    systems = {"genealogy": genealogy, "state_dir": str(tmp_path / "hstate")}
    habitat = HabitatRuntime(str(tmp_path / "hstate"), systems=systems)

    created = []
    for _ in range(6):
        c = habitat.act(actor="aurora", territory="space", operation="create",
                         parameters={"entity_type": "shape"})
        created.append(c.affected_entities[0])
    # Divergent real consequence across genuinely different contexts:
    # shapes get moved in "space" by a human, text entities never touched.
    for i, eid in enumerate(created):
        if i % 2 == 0:
            habitat.act(actor="human", territory="space", operation="move",
                        target_ids=[eid], parameters={"position": {"x": i, "y": 1}})

    engine = get_or_create_engine(systems)
    assert engine is not None
    ref = RepresentationalRef.for_c1("N", "OPERATOR", "A")  # "change"-category habitat ops
    profile = engine.consequence_profile_for(ref)
    assert profile is not None
    assert profile["samples"] > 0


# ── M. Habitat Anti-Scripting ───────────────────────────────────────────────

def test_M_habitat_source_still_contains_no_semantic_shortcut_mappings():
    """Same regex family as test_aurora_habitat.py's own guard, re-run here
    to confirm Build 714's Habitat edits didn't introduce one."""
    import aurora_habitat as habitat_mod
    src = inspect.getsource(habitat_mod)
    forbidden_patterns = [
        r"uncertainty.{0,20}yellow", r"happiness.{0,20}smile", r"is_happy.{0,20}heart",
        r"emotion.{0,10}[-=]>.{0,10}(color|shape|visual)",
        r"constraint.{0,10}[-=]>.{0,10}(symbol|shape|color)",
        r"representation_type.{0,10}[-=]>.{0,10}shape",
        r'"meaning"\s*:', r"\.meaning\s*=",
    ]
    for pattern in forbidden_patterns:
        assert not re.search(pattern, src, re.IGNORECASE), f"forbidden pattern matched: {pattern}"


def test_M_resolution_module_never_labels_habitat_entities_with_meaning():
    src = inspect.getsource(rr)
    for forbidden in ('"meaning"', ".meaning =", "preferred=", "is_interesting"):
        assert forbidden not in src


# ── N. Habitat Ownership ────────────────────────────────────────────────────

def test_N_resolution_pressure_never_weakens_self_ownership_boundary(tmp_path):
    from aurora_habitat import HabitatRuntime
    genealogy = ConstraintGenealogyLogger("hab714own", config=GenealogyConfig(), output_dir=str(tmp_path / "hg2"))
    systems = {"genealogy": genealogy, "state_dir": str(tmp_path / "hstate2")}
    habitat = HabitatRuntime(str(tmp_path / "hstate2"), systems=systems)

    c = habitat.act(actor="aurora", territory="self", operation="create", parameters={"entity_type": "shape"})
    eid = c.affected_entities[0]
    for _ in range(8):
        habitat.act(actor="aurora", territory="self", operation="move",
                    target_ids=[eid], parameters={"position": {"x": 1, "y": 1}})

    denied = habitat.act(actor="human", territory="self", operation="move",
                          target_ids=[eid], parameters={"position": {"x": 9, "y": 9}})
    assert denied.success is False
    assert denied.permission_result.startswith("denied")


# ── O. Habitat Introspection ────────────────────────────────────────────────

def test_O_aurora_own_prior_habitat_history_is_raw_evidence_without_declared_meaning(tmp_path):
    from aurora_habitat import HabitatRuntime
    genealogy = ConstraintGenealogyLogger("hab714introspect", config=GenealogyConfig(), output_dir=str(tmp_path / "hg3"))
    systems = {"genealogy": genealogy, "state_dir": str(tmp_path / "hstate3")}
    habitat = HabitatRuntime(str(tmp_path / "hstate3"), systems=systems)
    c = habitat.act(actor="aurora", territory="self", operation="create", parameters={"entity_type": "shape"})
    eid = c.affected_entities[0]
    habitat.act(actor="aurora", territory="self", operation="recolor",
                target_ids=[eid], parameters={"color": "blue"})

    history = habitat.get_history(entity_id=eid)
    assert history
    for event in history:
        assert "meaning" not in event
        assert "interpretation" not in event


# ── P. WARP Boundary ────────────────────────────────────────────────────────

def test_P_unresolved_coordinates_remain_investigable_without_full_resolution_gate(tmp_path):
    """Existing unresolved coordinates should be investigable before
    unnecessary new representational invention, but full (C2) resolution
    must not become a mandatory prerequisite for anything else in this
    module -- every public method here accepts a ref at ANY resolution
    level, never requiring is_fully_resolved()."""
    genealogy, engine = _fresh(tmp_path)
    ref = RepresentationalRef.for_d1("T", "MAGNITUDE")  # D1: barely resolved at all
    assert not ref.is_fully_resolved()
    # None of these should raise or require full resolution first.
    engine.ensure_registered(ref)
    assert engine.inadequacy_pressure(ref) == 0.0
    assert engine.unresolved_field_candidates(ref) == []
    assert engine.current_resolution(ref) == ref


# ── Q. Restart Persistence ──────────────────────────────────────────────────

def test_Q_earned_resolution_and_genealogy_survive_restart(tmp_path):
    genealogy, engine = _fresh(tmp_path, name="persist714")
    ref = RepresentationalRef.for_c1("T", "MAGNITUDE", "B")
    resolved = engine.resolve_field(
        ref, "col_law_c", "N", evidence={"source": "test"}, discrepancy_before=0.9,
        discrepancy_after=0.3, pressure_before=0.5, pressure_after=0.0, cost=1.0,
    )
    state_dir = engine.root.parent
    engine2 = RepresentationalResolutionEngine(genealogy, state_dir=str(state_dir))
    assert engine2.current_resolution(ref) == resolved
    assert engine2.genealogy_for(ref)
    assert engine2.recent_events(10)


# ── R. Backward Compatibility ───────────────────────────────────────────────

def test_R_a_ref_encoded_before_build_714_decodes_and_loads_safely():
    """Any pre-Build-714 stored ref (a plain encode() string with no
    adequacy metadata attached) must still decode and behave correctly --
    RepresentationalRef itself is untouched by this build."""
    old_style = RepresentationalRef.for_c1("X", "POLARITY", "N").encode()
    ref = RepresentationalRef.decode(old_style)
    assert ref.nc_law_c == "X"
    assert ref.is_fully_resolved() is False


def test_R_engine_with_no_prior_state_dir_data_starts_clean(tmp_path):
    genealogy, engine = _fresh(tmp_path, name="fresh714")
    ref = RepresentationalRef.for_c1("A", "DIFFERENCE", "B")
    assert engine.genealogy_for(ref) == []
    assert engine.current_resolution(ref) == ref


# ── P (extended). WARP boundary advisory ────────────────────────────────────

def test_P_warp_investigability_report_never_touches_warp_decision_code():
    """The advisory is purely additive -- confirm neither WARP module calls
    into it, and it never imports WARP itself (no coupling in either
    direction)."""
    import aurora_warp_protocol as warp_mod
    warp_src = inspect.getsource(warp_mod)
    assert "warp_investigability_report" not in warp_src
    assert "aurora_representational_resolution" not in warp_src

    import aurora_internal.aurora_recursive_causal_reasoning_waveform as rcrw_mod
    rcrw_src = inspect.getsource(rcrw_mod)
    assert "warp_investigability_report" not in rcrw_src

    rr_src = inspect.getsource(rr)
    assert "import aurora_warp_protocol" not in rr_src
    assert "from aurora_warp_protocol" not in rr_src


def test_P_warp_investigability_report_reflects_real_pressure_and_candidates(tmp_path):
    genealogy, engine = _fresh(tmp_path, name="warp714")
    ref = RepresentationalRef.for_c1("T", "MAGNITUDE", "B")
    sibling = RepresentationalRef.for_m21("T", "MAGNITUDE", "B", col_law_c="N", col_law_d="COST")
    engine.ensure_registered(sibling)

    quiet = rr.warp_investigability_report(engine, ref.encode())
    assert quiet["available"] is True
    assert quiet["investigable"] is False

    _drive(genealogy, engine, ref, axis_sequence=["B", "N", "X"] * 3, n_contexts=3)
    loud = rr.warp_investigability_report(engine, ref.encode())
    assert loud["inadequacy_pressure"] > 0.0
    assert loud["investigable"] is True
    assert loud["candidate_count"] > 0


def test_P_warp_investigability_report_handles_missing_engine_or_ref_safely():
    assert rr.warp_investigability_report(None, "REF:T:MAGNITUDE:B:?:?:?:?")["available"] is False
    dummy = rr.RepresentationalResolutionEngine.__new__(rr.RepresentationalResolutionEngine)
    assert rr.warp_investigability_report(dummy, None)["available"] is False
    assert rr.warp_investigability_report(dummy, "not-a-real-ref")["available"] is False


# ── Section 10 extension: sensory citizenship as a real candidate source ────

def test_sensory_citizenship_tag_convention_is_a_real_candidate_source(tmp_path):
    """Reuses aurora_internal/aurora_sensory_crystal.py's OWN
    'representational_ref:<encoded>' effect_tag convention verbatim (not
    invented here) -- confirms a sensory-citizenship-registered ability
    (never touched by RepresentationalResolutionEngine.ensure_registered())
    is still recognized as a real structurally-connected representation."""
    genealogy, engine = _fresh(tmp_path, name="sensory714")
    sensory_ref = RepresentationalRef.for_m21("T", "MAGNITUDE", "B", col_law_c="X", col_law_d="POLARITY")
    genealogy.abilities["sensory:audio:tone:node1"] = AbilityProfile(
        id="sensory:audio:tone:node1", axis="T", requires=("T",),
        cost={a: 0.0 for a in AXES}, risk={a: 0.0 for a in AXES},
        structured_state={"kind": "sensory_node", "domain": "audio"},
        effect_tags=("sensory_representation", f"representational_ref:{sensory_ref.encode()}"),
        notes="simulated sensory citizenship ability",
    )
    found = engine._ref_from_ability_id("sensory:audio:tone:node1")
    assert found == sensory_ref


def test_sensory_citizenship_registration_is_read_only_never_mutated():
    """The candidate-recognition path must never write back to a
    sensory-citizenship (or any other) ability -- read-only lookup only."""
    src = inspect.getsource(rr.RepresentationalResolutionEngine._ref_from_ability_id)
    assert "self.genealogy.abilities[" not in src


# ── Section 13: context-scoped resolution ───────────────────────────────────

def test_context_scoped_resolution_preserves_canonical_identity_without_duplication(tmp_path):
    genealogy, engine = _fresh(tmp_path, name="ctxscope714")
    ref = RepresentationalRef.for_c1("T", "MAGNITUDE", "B")
    sibling = RepresentationalRef.for_m21("T", "MAGNITUDE", "B", col_law_c="N", col_law_d="COST")
    engine.ensure_registered(sibling)
    _drive(genealogy, engine, ref, axis_sequence=["B", "N", "X"] * 3, n_contexts=3)

    candidates = engine.unresolved_field_candidates(ref)
    candidate = candidates[0]
    staged = engine.stage_field_inquiry(ref, candidate, consumer="ctxtest")
    result = engine.complete_field_inquiry(
        ref, candidate, staged[0], consumer="ctxtest", actual_coactivation=True,
        pressure_before={"X": 0.0, "T": 0.4, "N": 0.0, "B": 0.0, "A": 0.0},
        pressure_after={a: 0.0 for a in AXES},
        context_scope="territory:space",
    )
    assert result["representational_resolution_outcome"] == "context_specific"
    refined = RepresentationalRef.decode(result["refined_ref"])

    # The SAME canonical coarse identity resolves differently per scope --
    # no duplicate/unrelated ref was ever created.
    assert engine.current_resolution(ref, context_scope="territory:space") == refined
    assert engine.current_resolution(ref, context_scope="territory:self") == ref
    assert engine.current_resolution(ref) == ref  # no scope given -> minimum sufficient default
    assert refined.nc_law_c == ref.nc_law_c and refined.nc_target == ref.nc_target


def test_global_resolution_still_works_when_no_context_scope_given(tmp_path):
    genealogy, engine = _fresh(tmp_path, name="ctxscope714b")
    ref = RepresentationalRef.for_c1("T", "MAGNITUDE", "B")
    sibling = RepresentationalRef.for_m21("T", "MAGNITUDE", "B", col_law_c="N", col_law_d="COST")
    engine.ensure_registered(sibling)
    _drive(genealogy, engine, ref, axis_sequence=["B", "N", "X"] * 3, n_contexts=3)

    candidates = engine.unresolved_field_candidates(ref)
    candidate = candidates[0]
    staged = engine.stage_field_inquiry(ref, candidate, consumer="globaltest")
    result = engine.complete_field_inquiry(
        ref, candidate, staged[0], consumer="globaltest", actual_coactivation=True,
        pressure_before={"X": 0.0, "T": 0.4, "N": 0.0, "B": 0.0, "A": 0.0},
        pressure_after={a: 0.0 for a in AXES},
    )
    assert result["representational_resolution_outcome"] == "retained"
    refined = RepresentationalRef.decode(result["refined_ref"])
    assert engine.current_resolution(ref) == refined
    assert engine.current_resolution(ref, context_scope="anything") == refined


# ── Section 25: resolution economics ────────────────────────────────────────

def test_resolution_is_rejected_when_marginal_improvement_is_not_worth_accumulated_search_cost(tmp_path):
    genealogy, engine = _fresh(tmp_path, name="cost714")
    ref = RepresentationalRef.for_c1("T", "MAGNITUDE", "B")
    sibling = RepresentationalRef.for_m21("T", "MAGNITUDE", "B", col_law_c="N", col_law_d="COST")
    engine.ensure_registered(sibling)
    _drive(genealogy, engine, ref, axis_sequence=["B", "N", "X"] * 3, n_contexts=3)

    # Real, repeated search work -- each call genuinely re-runs genealogy's
    # own collision/gap search and accumulates its real result counts.
    for _ in range(50):
        engine.unresolved_field_candidates(ref)
    accumulated_cost = engine._cost_ledger.get(ref.encode(), 0.0)
    assert accumulated_cost > 10.0, "expected real accumulated search cost from repeated investigation"

    candidates = engine.unresolved_field_candidates(ref)
    candidate = candidates[0]
    staged = engine.stage_field_inquiry(ref, candidate, consumer="cost_reject_test")
    # A tiny improvement that clears the absolute floor on its own but is
    # nowhere near worth what 50 rounds of searching actually cost.
    result = engine.complete_field_inquiry(
        ref, candidate, staged[0], consumer="cost_reject_test", actual_coactivation=True,
        pressure_before={"X": 0.0, "T": 0.06, "N": 0.0, "B": 0.0, "A": 0.0},
        pressure_after={a: 0.0 for a in AXES},
    )
    assert result["representational_resolution_outcome"] == "rejected"
    assert result["refined_ref"] is None


def test_resolution_cost_is_real_not_a_fixed_placeholder(tmp_path):
    genealogy, engine = _fresh(tmp_path, name="cost714b")
    ref = RepresentationalRef.for_c1("T", "MAGNITUDE", "B")
    sibling = RepresentationalRef.for_m21("T", "MAGNITUDE", "B", col_law_c="N", col_law_d="COST")
    engine.ensure_registered(sibling)
    _drive(genealogy, engine, ref, axis_sequence=["B", "N", "X"] * 3, n_contexts=3)

    candidates = engine.unresolved_field_candidates(ref)
    candidate = candidates[0]
    staged = engine.stage_field_inquiry(ref, candidate, consumer="cost_real_test")
    result = engine.complete_field_inquiry(
        ref, candidate, staged[0], consumer="cost_real_test", actual_coactivation=True,
        pressure_before={"X": 0.0, "T": 0.4, "N": 0.0, "B": 0.0, "A": 0.0},
        pressure_after={a: 0.0 for a in AXES},
    )
    assert result["representational_resolution_outcome"] == "retained"
    records = engine.genealogy_for(ref)
    assert records[-1]["computational_cost"] > 0.0
    # Retention pays off the cost ledger -- the next unresolved field starts fresh.
    assert engine._cost_ledger.get(ref.encode(), 0.0) == 0.0
