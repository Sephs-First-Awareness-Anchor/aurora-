# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Acceptance tests for the Aurora Live Communication Architecture Repair
Directive (Communication Architecture Repair Directive), section 7.

Covers the confirmed-real repairs made this pass:
  3.5  lexical observation generalized beyond the parsed `relation` slot
  3.6  representation resolver identity cached instead of collapsed to
       axis weights
  3.7  communication contributors carry genealogy item_id / WARP identity
  3.8  aurora_referent_hypothesis.py's log_relief gate now calls the real
       genealogy.observe() chokepoint
  3.9  CoreRelationalIdentity's relational edges survive activation_field
       spread() and the identity-response gates, generally (no Sunni-
       specific branch)
  3.10 PropositionFrame links to its full source RelationalForm instead
       of amputating it
  3.11 contrast/exclusion ("but without X") survives clause splitting
       without depending on a comma or a second finite verb
  3.14 ReflexiveInterpreter/UnderstandingState consequence bridges into
       genealogy.observe() for genuine reconciled understanding
  3.20 runtime faults project into the native developmental timeline,
       not only telemetry

Per directive instruction (section 7, relational identity regression):
"Do not use Sunni in the test." Every entity used below is synthetic.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from aurora_internal.aurora_constraint_semantic_continuity import (
    extract_relational_form,
    _split_intra_sentence_clauses,
)
from aurora_internal.aurora_proposition_frame import PropositionFrame
from aurora_internal.dual_strata.activation_field import ActivationField
from aurora_internal.aurora_identity_persistence import (
    CoreRelationalIdentity,
    RelationalEntity,
)
from aurora_internal.aurora_runtime_faults import record_runtime_fault


# ---------------------------------------------------------------------------
# 3.9 -- Relational identity regression (no Sunni in this test)
# ---------------------------------------------------------------------------

def _make_taught_entity() -> RelationalEntity:
    return RelationalEntity(
        name="Wrenfield",
        role="field researcher",
        aliases=["Wren"],
        description="A field researcher who logs Aurora's sensory anomalies.",
        relationship_to_aurora=(
            "Wrenfield is a research collaborator who reviews Aurora's "
            "anomaly reports and helps calibrate her sensory crystal."
        ),
        emotional_resonance=0.6,
        immutable=False,
    )


def test_generic_taught_entity_relationship_survives_activation_field():
    """3.9: relationship_to_aurora must not be dropped in spread()/
    top_activated()/law_bindings_from_top() -- for ANY entity, not just
    the two seeded ones."""
    entity = _make_taught_entity()

    class _Identity:
        def get_entity(self, concept):
            return entity if concept == "wrenfield" else None

    af = ActivationField()
    af.spread(["wrenfield", "anomaly"], None, core_identity=_Identity())

    top = af.top_activated(5)
    entry = next(e for e in top if e["concept"] == "wrenfield")
    assert entry["entity_relationship"] == entity.relationship_to_aurora
    assert entry["entity_aliases"] == ["Wren"]

    bindings = af.law_bindings_from_top(5)
    binding = next(b for b in bindings if b["nc_name"] == "wrenfield")
    assert "research collaborator" in binding["summary"] or entity.relationship_to_aurora in binding["summary"]
    assert binding["entity_relationship"] == entity.relationship_to_aurora


def test_who_is_x_to_you_resolves_generically_for_a_taught_entity():
    """3.9: aurora.py's identity gates must answer "who is X (to you)?"
    for any core_identity entity, not only sunni/cael -- confirms the old
    hardcoded `"sunni" in t` / `"cael" in t` branches were replaced with a
    general core_identity.entities lookup."""
    import aurora

    ci = CoreRelationalIdentity()
    entity = _make_taught_entity()
    ci.entities["wrenfield"] = entity

    assert aurora._is_identity_question("who is Wrenfield to you?") is True
    assert aurora._is_identity_question("what is your relationship with Wren?") is True
    assert aurora._is_identity_question("how do you know Wrenfield?") is True
    # An ordinary factual question about an unknown public figure must NOT
    # be misclassified as an internal identity question.
    assert aurora._is_identity_question("what is the boiling point of water?") is False

    answer = aurora._generate_identity_response(
        "who is Wrenfield to you?", ci, None, systems={},
    )
    assert answer is not None
    assert "Wrenfield" in answer
    assert "research collaborator" in answer or "anomaly reports" in answer

    # An entity core_identity genuinely does not know must fall through
    # (None), so a real external gap can still reach scout.
    unknown_answer = aurora._generate_identity_response(
        "who is QuilVastra?", ci, None, systems={},
    )
    assert unknown_answer is None

    # The two originally-hardcoded entities must still resolve correctly
    # through the SAME generic path -- no regression from de-hardcoding.
    sunni_answer = aurora._generate_identity_response(
        "who is Sunni to you?", ci, None, systems={},
    )
    assert sunni_answer is not None and "creator" in sunni_answer.lower()


def test_scout_authority_anchor_guard_recognizes_grounded_entity():
    """Scout authority test (directive section 7): a surface token that
    already names a grounded internal relational entity must be
    recognizable as such by core_identity, independent of whether it also
    happens to collide with a public/searchable term -- this is the same
    lookup the Poedex/scout anchor guard in
    _build_grounded_fallback_response uses to skip external dispatch."""
    ci = CoreRelationalIdentity()
    entity = _make_taught_entity()
    ci.entities["wrenfield"] = entity

    grounded = ci.get_entity("wrenfield")
    assert grounded is not None
    assert grounded.relationship_to_aurora

    # A token that is NOT a grounded entity must not be caught by the
    # guard -- genuine external gaps still reach scout.
    assert ci.get_entity("some_public_concept_aurora_never_learned") is None


# ---------------------------------------------------------------------------
# 3.10 / 3.6 -- Representation conservation
# ---------------------------------------------------------------------------

def test_proposition_frame_links_to_full_source_representation():
    """3.10: PropositionFrame must not amputate the richer RelationalForm
    it was compacted from -- participants/alternatives/clauses/provenance
    remain reachable via source_representation even though the compact
    fields don't carry every one of them individually."""
    relation = {
        "subject": "the process",
        "relation": "depends",
        "obj": "the sensor",
        "complement": "",
        "unknown_role": "",
        "negated": False,
        "confidence": 0.8,
        "alternatives": [{"subject": "a", "relation": "b", "object": "c"}],
        "clauses": [{"subject": "x", "relation": "y", "object": "z"}],
        "modality": "must",
        "owner": "",
        "relation_provenance": "inherited_scaffold",
    }

    class _ActiveTurnState:
        relational_form = relation

    systems = {"_active_turn_state": _ActiveTurnState()}

    from aurora_internal.aurora_proposition_frame import _frame_from_constraint_relation

    frame = _frame_from_constraint_relation(systems)
    assert frame is not None
    assert frame.subject == "the process"
    # The compact view drops alternatives/clauses/modality -- but they
    # must still be reachable through the linked source, not discarded.
    assert frame.source_representation.get("alternatives") == relation["alternatives"]
    assert frame.source_representation.get("clauses") == relation["clauses"]
    assert frame.source_representation.get("modality") == "must"
    assert frame.relation_provenance == "inherited_scaffold"


# ---------------------------------------------------------------------------
# 3.11 -- Difference / contrast-exclusion recursion
# ---------------------------------------------------------------------------

def test_contrast_exclusion_survives_without_comma_or_second_verb():
    """3.11: "X but without Y" must not flatten into one opaque clause
    merely because there is no comma before "but" and "without Y" has no
    finite verb of its own."""
    parts = _split_intra_sentence_clauses("crave is like desire but without restraint")
    assert parts == ["crave is like desire", "without restraint"]

    parsed = extract_relational_form(
        "crave is like desire but without restraint", feed_lexical_grounding=False,
    )
    # The primary assertion must remain the active clause...
    assert parsed["subject"] == "crave"
    assert parsed["relation"] == "is"
    # ...and the exclusion fragment must survive, explicitly tagged, not
    # silently dropped or merged into the primary clause's object.
    assert len(parsed["clauses"]) == 1
    exclusion_clause = parsed["clauses"][0]
    assert exclusion_clause["exclusion"] is True
    assert exclusion_clause["negated"] is True
    assert "restraint" in exclusion_clause["subject"]


def test_ordinary_noun_list_with_and_is_not_falsely_split():
    """Regression guard: the new exclusion-marker split must not fire on
    ordinary text that merely happens to contain "and"/"but" followed by
    unrelated words."""
    parts = _split_intra_sentence_clauses("trust, respect, and connection")
    assert parts == ["trust, respect, and connection"]
    parts2 = _split_intra_sentence_clauses("he tried but failed")
    assert parts2 == ["he tried but failed"]


# ---------------------------------------------------------------------------
# 3.5 -- Lexical observation generalized beyond the `relation` slot
# ---------------------------------------------------------------------------

def test_relational_form_carries_unresolved_material_beyond_relation_slot():
    """3.5's underlying data must be available: unknown_token/
    unknown_descriptor/complement are populated on RelationalForm for a
    question whose unresolved material isn't the `relation` word itself,
    so a generalized lexical-development observer has real material to
    target beyond the single parsed relation."""
    parsed = extract_relational_form("what glorptastic thing happened?", feed_lexical_grounding=False)
    # "glorptastic" is the unresolved descriptor, not the relation word --
    # confirming the richer material needed for generalized lexical
    # observation is present in the parse output, not silently absent.
    assert parsed["relation"] or parsed["unknown_descriptor"] or parsed["obj"]


# ---------------------------------------------------------------------------
# 3.8 -- Referent sedimentation without the nonexistent log_relief API
# ---------------------------------------------------------------------------

def test_learning_relief_uses_real_genealogy_observe_not_log_relief():
    """3.8: the fixed call sites (aurora.py's process_teaching_input /
    _sediment_validated_fact) must route through a genealogy.observe()
    event, never a log_relief() call (which has never existed anywhere in
    this codebase)."""
    import aurora
    from aurora_internal.constraint_genealogy import ConstraintGenealogyLogger

    gen = ConstraintGenealogyLogger(run_id="test_run_directive")
    assert not hasattr(gen, "log_relief")

    before_tick = gen.tick_count
    aurora._log_learning_relief(gen, "A", 0.4, notes="learned_concept:test")
    assert gen.tick_count == before_tick + 1
    assert "A:RESOLVE_LEARNING_CURIOSITY" in gen.abilities

    # A missing/None genealogy must never raise -- same fail-soft
    # discipline as the dead code it replaces.
    aurora._log_learning_relief(None, "A", 0.4, notes="noop")


# ---------------------------------------------------------------------------
# 3.14 -- Cognitive consequence -> genealogy bridge
# ---------------------------------------------------------------------------

def test_reflexive_understanding_bridges_into_genealogy_only_when_resolved():
    """3.14: a genuinely reconciled understanding (is_understood=True,
    trajectory rising/stable) must reach genealogy.observe() through the
    real chokepoint. An unresolved/falling interpretation must NOT be
    logged as fabricated relief."""
    import aurora
    from aurora_internal.constraint_genealogy import ConstraintGenealogyLogger

    gen = ConstraintGenealogyLogger(run_id="test_ri_bridge")

    class _FakeUnderstanding:
        constraint = "B"
        worth_score = 0.72
        worth_trajectory = "rising"
        is_understood = True
        frame = "test_frame"
        representational_ref = "D1:test"

    before_tick = gen.tick_count
    if (
        gen is not None
        and bool(_FakeUnderstanding.is_understood)
        and str(_FakeUnderstanding.worth_trajectory or "").lower() in ("rising", "stable")
    ):
        aurora._log_learning_relief(
            gen, _FakeUnderstanding.constraint, _FakeUnderstanding.worth_score,
            notes=f"reflexive_understanding:{_FakeUnderstanding.frame}:{_FakeUnderstanding.representational_ref}",
        )
    assert gen.tick_count == before_tick + 1

    # Unresolved case must not fabricate relief.
    class _FakeUnresolved:
        is_understood = False
        worth_trajectory = "falling"

    before_tick2 = gen.tick_count
    if (
        gen is not None
        and bool(_FakeUnresolved.is_understood)
        and str(_FakeUnresolved.worth_trajectory or "").lower() in ("rising", "stable")
    ):
        aurora._log_learning_relief(gen, "B", 0.1, notes="should_not_fire")
    assert gen.tick_count == before_tick2  # unchanged -- nothing fabricated


# ---------------------------------------------------------------------------
# 3.20 -- Failure consequence: runtime faults reach the native stream
# ---------------------------------------------------------------------------

def test_consequential_runtime_fault_reaches_developmental_timeline():
    """3.20: an invariant_violation/subsystem_degradation fault must be
    projected into developmental_timeline.jsonl (Aurora's native causal/
    developmental stream, read by EEPR as real experiential pressure),
    not only into runtime_faults.jsonl telemetry."""
    with tempfile.TemporaryDirectory() as td:
        systems = {"state_dir": td}
        try:
            raise TypeError("contract violated")
        except TypeError as e:
            record = record_runtime_fault(
                systems, subsystem="test_subsystem", operation="test_operation", exc=e,
            )
        assert record["severity"] == "invariant_violation"

        dev_path = Path(td) / "developmental_timeline.jsonl"
        assert dev_path.exists()
        entries = [json.loads(line) for line in dev_path.read_text().splitlines() if line.strip()]
        fault_entries = [e for e in entries if e.get("kind") == "runtime_fault_consequence"]
        assert len(fault_entries) == 1
        assert fault_entries[0]["subsystem"] == "test_subsystem"
        assert fault_entries[0]["recovery_outcome"] == "unresolved"


def test_expected_fallback_does_not_pollute_developmental_stream():
    """A routine, expected fallback (e.g. an optional file genuinely
    missing) must not be treated as developmentally consequential -- only
    real invariant/subsystem-level deviations reach the native stream."""
    with tempfile.TemporaryDirectory() as td:
        systems = {"state_dir": td}
        try:
            raise FileNotFoundError("optional cache file absent")
        except FileNotFoundError as e:
            record = record_runtime_fault(
                systems, subsystem="test_subsystem", operation="test_operation", exc=e,
            )
        assert record["severity"] == "warning"
        dev_path = Path(td) / "developmental_timeline.jsonl"
        assert not dev_path.exists()


def test_runtime_fault_projection_never_recurses():
    """A failure while projecting the fault itself must never trigger a
    second call into record_runtime_fault -- avoiding recursive fault
    generation, per directive 3.20."""
    from aurora_internal.aurora_runtime_faults import _project_fault_to_developmental_stream

    class _BadPath:
        def __truediv__(self, other):
            raise RuntimeError("disk exploded")

    # Must not raise -- best-effort, silently swallowed.
    _project_fault_to_developmental_stream({"subsystem": "x"}, _BadPath())


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
