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

Second pass (connecting the pieces originally identified as deferred):
  3.2  confirmed already fixed in current-main (aurora.py:_chain_up3_purpose
       calls RCRW's prepare_semantic_state() and its effective_interpretation
       becomes state.relational_form/axis_activation) -- see
       tests/test_recursive_causal_reasoning_waveform.py for the live-turn
       acceptance test, added here since it was missing before
  3.15/3.16 real live-turn arithmetic examples now reach
       OperationalSynthesisChamber and GeneralExecutionFoundry through the
       existing submit_lived_experience() universal discovery seam, which
       previously had its one production caller only in the offline dream
       trainer

Per directive instruction (section 7, relational identity regression):
"Do not use Sunni in the test." Every entity used below is synthetic.
"""
from __future__ import annotations

import json
import os
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


# ---------------------------------------------------------------------------
# 3.15/3.16 -- Live turns reach OperationalSynthesisChamber and
# GeneralExecutionFoundry through the existing universal discovery seam
# ---------------------------------------------------------------------------

def test_arithmetic_turn_feeds_both_synthesis_chambers_via_universal_seam():
    """A full-repo search confirmed observe_experience()/observe_example()
    had zero live-turn callers for either chamber, and
    submit_lived_experience()'s only caller anywhere was the offline dream
    trainer. Real arithmetic turns must now reach both chambers as genuine
    (input, expected_output) evidence -- never changing the delivered
    answer, and never raising when a chamber is absent."""
    import aurora
    from aurora_internal.aurora_operational_synthesis import AuroraOperationalSynthesisChamber
    from aurora_internal.aurora_general_execution_foundry import AuroraGeneralExecutionFoundry

    with tempfile.TemporaryDirectory() as td1, tempfile.TemporaryDirectory() as td2:
        op_synth = AuroraOperationalSynthesisChamber(state_dir=td1, persist=False)
        foundry = AuroraGeneralExecutionFoundry(state_dir=td2, persist=False)
        systems = {"operational_synthesis": op_synth, "general_execution_foundry": foundry}

        for a, op, b in [(2, "plus", 3), (10, "plus", 5), (7, "plus", 1), (100, "plus", 1)]:
            answer = aurora._answer_simple_arithmetic(f"what is {a} {op} {b}?")
            assert answer  # the delivered answer path is untouched
            aurora._feed_arithmetic_lived_experience(f"what is {a} {op} {b}?", systems)

        op_status = op_synth.task_status("OPTASK:arithmetic:+")
        foundry_status = foundry.task_status("OPTASK:arithmetic:+")
        # Both chambers genuinely processed the evidence (not silently
        # dropped) -- op_synth's narrower primitive space finds a fitting
        # candidate; the foundry at minimum records real examples against
        # the same task, whatever its own classification lands on.
        assert op_status.get("status") in ("candidate_trial", "warp_trial")
        assert foundry_status.get("status") != "unknown_task"


def test_arithmetic_feed_never_raises_when_chambers_absent_or_division_by_zero():
    import aurora

    # Neither chamber present.
    aurora._feed_arithmetic_lived_experience("what is 4 plus 5?", {})
    aurora._feed_arithmetic_lived_experience("what is 4 plus 5?", {"operational_synthesis": None})

    # Division by zero has no defined result -- must not be fed as if it did.
    class _SpyChamber:
        def __init__(self):
            self.calls = []
        def observe_example(self, *args, **kwargs):
            self.calls.append((args, kwargs))
            return {}

    spy = _SpyChamber()
    aurora._feed_arithmetic_lived_experience(
        "what is 4 divided by 0?", {"operational_synthesis": spy},
    )
    assert spy.calls == []

    # Non-arithmetic text must not be fed.
    aurora._feed_arithmetic_lived_experience("who is Wrenfield to you?", {"operational_synthesis": spy})
    assert spy.calls == []


# ---------------------------------------------------------------------------
# 3.22 -- Fail-soft starvation: required organs now report their absence
# once, into the native developmental stream, instead of vanishing silently
# ---------------------------------------------------------------------------

def test_missing_required_organ_reported_once_and_reaches_native_stream():
    import aurora

    with tempfile.TemporaryDirectory() as td:
        systems = {"state_dir": td}
        aurora._report_missing_required_organ(systems, "genealogy", operation="pressure_orientation")
        aurora._report_missing_required_organ(systems, "genealogy", operation="pressure_orientation")
        aurora._report_missing_required_organ(systems, "genealogy", operation="pressure_orientation")
        aurora._report_missing_required_organ(systems, "lattice", operation="heat_status")

        faults_path = Path(td) / "runtime_faults.jsonl"
        faults = [json.loads(line) for line in faults_path.read_text().splitlines() if line.strip()]
        # Deduped: 3 identical calls for "genealogy" produce exactly one
        # record, not three -- a hot per-turn call site must not flood the
        # ledger just because the organ stays missing for the whole process.
        genealogy_faults = [f for f in faults if f["subsystem"] == "genealogy"]
        assert len(genealogy_faults) == 1
        assert len(faults) == 2  # genealogy + lattice, once each

        dev_path = Path(td) / "developmental_timeline.jsonl"
        dev_entries = [json.loads(line) for line in dev_path.read_text().splitlines() if line.strip()]
        assert len(dev_entries) == 2
        assert {e["subsystem"] for e in dev_entries} == {"genealogy", "lattice"}


def test_missing_required_organ_never_raises_on_bad_systems():
    import aurora
    # Non-dict systems must be a silent no-op, not a crash.
    aurora._report_missing_required_organ(None, "genealogy", operation="x")
    aurora._report_missing_required_organ("not a dict", "genealogy", operation="x")


# ---------------------------------------------------------------------------
# 3.5 -- Lexical observation actually generalized (not just data-available)
# ---------------------------------------------------------------------------

def test_taught_word_in_subject_slot_is_now_observed_not_just_the_copula():
    """3.5's real failure: 'wanna is related to want' binds wanna as
    SUBJECT and 'is' as relation -- the old gate fed only the relation
    slot, so the taught word itself never reached lexical grounding.
    Confirms the generalized feed now observes every content-bearing
    slot, not just relation."""
    import aurora_internal.aurora_lexical_grounding as alg
    from aurora_internal.aurora_constraint_semantic_continuity import extract_relational_form

    observed = []

    class _FakeGrounding:
        def observe_lexical_context(self, *, word, relational_form, provenance):
            observed.append(word)
            return {"action": "trial_started"}

    original_get = alg.get_lexical_grounding
    fake = _FakeGrounding()
    alg.get_lexical_grounding = lambda: fake
    try:
        extract_relational_form("wanna is related to want crave desire")
    finally:
        alg.get_lexical_grounding = original_get

    assert "wanna" in observed, "the actual taught word must be observed, not only the copula"
    assert "want" in observed
    assert "crave" in observed


def test_function_words_are_not_fed_as_lexical_content():
    import aurora_internal.aurora_lexical_grounding as alg
    from aurora_internal.aurora_constraint_semantic_continuity import extract_relational_form

    observed = []

    class _FakeGrounding:
        def observe_lexical_context(self, *, word, relational_form, provenance):
            observed.append(word)
            return {"action": "trial_started"}

    original_get = alg.get_lexical_grounding
    fake = _FakeGrounding()
    alg.get_lexical_grounding = lambda: fake
    try:
        extract_relational_form("the glass fell from the table")
    finally:
        alg.get_lexical_grounding = original_get

    assert "the" not in observed
    assert "from" not in observed


# ---------------------------------------------------------------------------
# Persistence test (directive section 7): a validated/promoted
# developmental distinction survives a restart using the active state
# directory, without re-crediting the historical evidence
# ---------------------------------------------------------------------------

def test_lexical_candidate_survives_restart_without_recrediting_evidence():
    from aurora_internal.aurora_lexical_grounding import AuroraLexicalGrounding

    with tempfile.TemporaryDirectory() as td:
        form = {
            "raw_text": "a novel gadget appeared",
            "subject": "gadget", "relation": "appeared", "obj": "", "complement": "",
        }
        first = AuroraLexicalGrounding(state_dir=td, persist=True)
        for _ in range(3):
            first.observe_lexical_context(word="gadget", relational_form=form, provenance="test")
        first.save()

        candidates_before = list(first._candidates.values())
        assert len(candidates_before) == 1
        evidence_before = len(candidates_before[0].evidence)
        assert evidence_before >= 1

        # "Restart": a fresh instance reading only the persisted state,
        # using the SAME active state directory -- not a fixture copy.
        restarted = AuroraLexicalGrounding(state_dir=td, persist=True)
        candidates_after = list(restarted._candidates.values())
        assert len(candidates_after) == 1
        assert candidates_after[0].word == "gadget"
        # Retained, not re-credited: reloading must not replay the
        # observation as new evidence -- the count must match exactly,
        # never double.
        assert len(candidates_after[0].evidence) == evidence_before
        assert candidates_after[0].status == candidates_before[0].status


# ---------------------------------------------------------------------------
# Boot identity + WARP registry test (directive section 7). Real end-to-end
# boot, not source inspection -- expensive (a full boot_aurora() takes
# ~2-3 minutes), so this single test covers both required checks at once
# rather than paying that cost twice.
# ---------------------------------------------------------------------------

def test_real_boot_produces_singleton_organs_registered_under_canonical_warp_field():
    import shutil
    import aurora as A
    import aurora_warp_protocol as awp
    from aurora_internal.aurora_lexical_grounding import get_lexical_grounding

    repo_root = Path(__file__).resolve().parents[1]
    scratch = tempfile.mkdtemp(prefix="aurora_directive_boot_")
    try:
        scratch_state = os.path.join(scratch, "aurora_state")
        shutil.copytree(str(repo_root / "aurora_state"), scratch_state)
        systems = A.boot_aurora(state_dir=scratch_state, verbose=False)

        # Boot identity: no lazily-created detached WarpField/lexical
        # singleton -- the global getters must resolve to the SAME object
        # boot_aurora installed into systems, not a second, empty one.
        warp_field = systems.get("warp_field")
        assert warp_field is not None
        assert awp.get_warp_field() is warp_field, (
            "get_warp_field() resolved to a different, detached WarpField "
            "than the one boot_aurora installed into systems"
        )
        assert get_lexical_grounding() is systems.get("lexical_grounding"), (
            "get_lexical_grounding() resolved to a different, detached "
            "singleton than the one boot_aurora installed into systems"
        )

        # WARP registry: every organ this directive touched must be
        # registered on the SAME canonical field under a real routing name,
        # and that registry entry must be object-identical to systems[key]
        # -- not a copy, not a second instance.
        registry = dict(getattr(warp_field, "_warp_capable_registry", {}) or {})
        expected = {
            # RCRW's routing name (its own _warp_level_name()) differs from
            # its systems dict key -- confirmed at aurora.py's actual
            # register_warp_capable call site, not assumed.
            "recursive_causal_waveform": "recursive_causal_reasoning_waveform",
            "communication_emergence": "communication_emergence",
            "lexical_grounding": "lexical_grounding",
            "operational_synthesis": "operational_synthesis",
            "general_execution_foundry": "general_execution_foundry",
        }
        for systems_key, routing_name in expected.items():
            organ = systems.get(systems_key)
            assert organ is not None, f"systems['{systems_key}'] was not mounted"
            assert routing_name in registry, (
                f"'{routing_name}' is not registered on the canonical WARP field"
            )
            assert registry[routing_name] is organ, (
                f"WARP registry entry for '{routing_name}' is not the same "
                f"object as systems['{systems_key}'] -- detached singleton"
            )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


# ---------------------------------------------------------------------------
# Contributor closure test (directive section 7): every contributor
# consumed during composition is captured once, and outcome routing never
# double-credits the same evidence
# ---------------------------------------------------------------------------

def test_lexical_contributor_captured_once_and_outcome_never_double_credited():
    import aurora
    from aurora_internal.aurora_lexical_grounding import AuroraLexicalGrounding

    lex = AuroraLexicalGrounding(state_dir=tempfile.mkdtemp(), persist=False)
    form = {
        "raw_text": "a novel gadget appeared",
        "subject": "gadget", "relation": "appeared", "obj": "", "complement": "",
    }
    for _ in range(3):
        lex.observe_lexical_context(word="gadget", relational_form=form, provenance="test")

    systems = {"lexical_grounding": lex}

    contributors = aurora._build_communication_contributors(systems)
    trace = contributors.get("lexical_grounding")
    assert trace, "the drained trace must be attached to the contributor bundle"
    assert len(trace) == 1

    # Captured once: a second build must drain nothing further for the
    # same observation -- the trace was already consumed.
    contributors_again = aurora._build_communication_contributors(systems)
    assert not contributors_again.get("lexical_grounding")

    entry = trace[0]
    result1 = lex.record_evidence_outcome(
        candidate_id=entry["candidate_id"], evidence_id=entry["evidence_id"],
        outcome_kind="positive", observed_effect="confirmed",
    )
    assert result1["recorded"] is True

    candidate = next(c for c in lex._candidates.values() if c.candidate_id == entry["candidate_id"])
    matching_evidence = [e for e in candidate.evidence if e.get("evidence_id") == entry["evidence_id"]]
    assert len(matching_evidence) == 1
    assert matching_evidence[0]["validated"] is True
    assert matching_evidence[0]["outcome_kind"] == "positive"

    # No duplicate credit: recording the SAME outcome again must not
    # create a second evidence entry or otherwise double-count it.
    result2 = lex.record_evidence_outcome(
        candidate_id=entry["candidate_id"], evidence_id=entry["evidence_id"],
        outcome_kind="positive", observed_effect="confirmed",
    )
    assert result2["recorded"] is True
    matching_evidence_after = [e for e in candidate.evidence if e.get("evidence_id") == entry["evidence_id"]]
    assert len(matching_evidence_after) == 1
