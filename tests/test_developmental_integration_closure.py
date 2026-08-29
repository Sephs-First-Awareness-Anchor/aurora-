"""Build 773 (Developmental Integration Closure and Canonical Hub
Telemetry): verification that consequence-earned lexical development can
leave lexical grounding and join Aurora's canonical genealogy/Concept-
Crystal/WARP machinery through their own native admission rules.

Drives AuroraLexicalGrounding against the REAL ConstraintGenealogyLogger
and extract_relational_form()/extract_joints()/WARP machinery -- nothing
mocked except the Concept Crystal registry (a small recording double,
since the real ConceptCrystalRegistry's own promotion physics are out of
scope here: this build only verifies evidence REACHES the registry, never
that a crystal promotes). Same discipline as Build 772's own test suite.
"""
from __future__ import annotations

from aurora_internal.aurora_lexical_grounding import (
    AuroraLexicalGrounding,
    LexicalCandidate,
)
from aurora_internal import aurora_lexical_grounding as lex_mod
from aurora_internal.constraint_genealogy import ConstraintGenealogyLogger, GenealogyConfig
from aurora_warp_protocol import PROMOTION_SCORE, TRIAL_TICKS


class _FakeCrystalRegistry:
    """Records observe_lsa() calls without touching the real DPS/crystal
    physics -- this build only needs to prove evidence reaches the
    canonical registry, never that a crystal promotes (the registry's own
    concern, deliberately not asserted here)."""

    def __init__(self):
        self.calls = []

    def observe_lsa(self, ax, path_key):
        self.calls.append({"ax": dict(ax), "path_key": path_key})


def _fresh(tmp_path, *, genealogy=True, crystal=True):
    lg = AuroraLexicalGrounding(state_dir=str(tmp_path), persist=False)
    lex_mod._global_lexical_grounding = lg
    gen = None
    if genealogy:
        gen = ConstraintGenealogyLogger("build773_test", config=GenealogyConfig(), output_dir=str(tmp_path))
    systems = {}
    if gen is not None:
        systems["genealogy"] = gen
    registry = _FakeCrystalRegistry() if crystal else None
    if registry is not None:
        systems["_concept_crystal_registry"] = registry
    lg.attach_systems(systems)
    return lg, gen, registry


def _observe_many(lg, raw_template, response_template, n, start=0):
    touched = []
    for i in range(start, start + n):
        result = lg.observe_historical_lexical_possibility(
            raw_text=raw_template.format(i=i),
            observed_response_text=response_template.format(i=i),
            possibility_id=f"POSS-{i}",
        )
        if result.get("candidate_id") and result.get("evidence_id"):
            touched.append({"candidate_id": result["candidate_id"], "evidence_id": result["evidence_id"]})
    return touched


def _promote(lg):
    for _ in range(TRIAL_TICKS + 1):
        lg.evaluate_warp_trials()


def test_historical_representation_closure_reaches_genealogy_and_resolve_promoted_role(tmp_path):
    """Historical evidence -> candidate -> consequence attribution ->
    promotion -> real genealogy ability_id -> later ordinary cognition
    can retrieve the earned representation via resolve_promoted_role()
    without touching aurora_historical_experience_environment.py at all."""
    lg, gen, _registry = _fresh(tmp_path)
    touched = _observe_many(
        lg, "Aurora believe cat stories variant {i}", "the cat does believe stories variant {i}", n=7,
    )
    for entry in touched:
        lg.record_evidence_outcome(candidate_id=entry["candidate_id"], evidence_id=entry["evidence_id"], outcome_kind="positive")
    _promote(lg)

    candidate = next(c for c in lg._candidates.values() if c.word == "believe")
    assert candidate.status == "promoted"
    assert candidate.genealogy_ability_id
    assert candidate.genealogy_ability_id in gen.abilities

    # Ordinary cognition's consumption surface -- no import of, or call
    # into, aurora_historical_experience_environment anywhere in this test.
    resolved = lg.resolve_promoted_role(
        "believe",
        {"relation": "believe", "subject": "aurora", "obj": "stories"},
    )
    assert resolved is not None
    assert resolved.candidate_id == candidate.candidate_id


def test_genealogy_registration_does_not_silently_dead_end(tmp_path):
    """Adversarial test (reframed from the build directive's original
    'dead end' premise, which investigation found false on current
    mainline -- register_emergent_lexical_grounding() is a complete,
    working implementation). Promotion with genealogy present must
    produce a real, non-empty ability_id -- never a silent no-op. With
    genealogy genuinely unavailable, the failure must be visible on the
    candidate (empty string, queryable), never indistinguishable from
    success."""
    lg, gen, _registry = _fresh(tmp_path)
    touched = _observe_many(
        lg, "Aurora believe cat stories variant {i}", "the cat does believe stories variant {i}", n=7,
    )
    for entry in touched:
        lg.record_evidence_outcome(candidate_id=entry["candidate_id"], evidence_id=entry["evidence_id"], outcome_kind="positive")
    _promote(lg)
    candidate = next(c for c in lg._candidates.values() if c.word == "believe")
    assert candidate.status == "promoted"
    assert candidate.genealogy_ability_id != ""
    assert gen.abilities[candidate.genealogy_ability_id].origin_kind == "consequence_earned"

    # No genealogy wired at all -- registration must fail visibly (empty
    # id on the candidate), not silently pretend success.
    lg2, _gen2, _registry2 = _fresh(tmp_path, genealogy=False)
    touched2 = _observe_many(
        lg2, "Aurora believe dog stories variant {i}", "the dog does believe stories variant {i}", n=7,
    )
    for entry in touched2:
        lg2.record_evidence_outcome(candidate_id=entry["candidate_id"], evidence_id=entry["evidence_id"], outcome_kind="positive")
    _promote(lg2)
    candidate2 = next(c for c in lg2._candidates.values() if c.word == "believe")
    assert candidate2.status == "promoted"  # WARP promotion is independent of genealogy
    assert candidate2.genealogy_ability_id == ""  # visibly absent, queryable


def test_crystal_eligibility_reaches_registry_without_asserting_promotion(tmp_path):
    """Historical evidence sufficient to promote a lexical candidate must
    reach the canonical Concept Crystal registry via observe_lsa() with
    the candidate's real axis profile. Only evidence-reaches-registry is
    asserted -- never that a crystal promotes (the registry's own
    decision, out of scope for this build)."""
    lg, _gen, registry = _fresh(tmp_path)
    touched = _observe_many(
        lg, "Aurora believe cat stories variant {i}", "the cat does believe stories variant {i}", n=7,
    )
    for entry in touched:
        lg.record_evidence_outcome(candidate_id=entry["candidate_id"], evidence_id=entry["evidence_id"], outcome_kind="positive")
    _promote(lg)
    candidate = next(c for c in lg._candidates.values() if c.word == "believe")
    assert candidate.status == "promoted"

    assert len(registry.calls) == 1
    call = registry.calls[0]
    assert call["path_key"] == f"lexical_grounding:{candidate.candidate_id}"
    assert call["ax"] == dict(candidate.axis_profile)


def test_no_automatic_development_from_repetition_alone(tmp_path):
    """Extends Build 772's own no-promotion-from-frequency test: many
    repeated historical occurrences without discrimination must produce
    no promotion, no genealogy ability_id, and (new for Build 773) no
    Concept Crystal registry call at all -- the registry hook only fires
    on WARP promotion, never on mere occurrence."""
    lg, gen, registry = _fresh(tmp_path)
    # A fresh ConstraintGenealogyLogger pre-seeds its own hand-authored
    # scaffold abilities (origin_kind=None) -- the invariant under test is
    # that NOTHING NEW gets added from repetition alone, not that the
    # registry starts literally empty.
    abilities_before = dict(gen.abilities)
    _observe_many(
        lg, "Aurora believe cat stories variant {i}", "the cat does believe stories variant {i}", n=12,
    )
    candidate = next(c for c in lg._candidates.values() if c.word == "believe")
    assert candidate.status != "promoted"
    assert candidate.genealogy_ability_id == ""
    assert set(gen.abilities.keys()) == set(abilities_before.keys())
    assert registry.calls == []


def test_developmental_replay_ancestry_reaches_genealogy_and_warp_demand(tmp_path):
    """Unresolved historical evidence (no relational configuration) must
    submit a real WARP demand (Build 773 PR 2). A later promotion that
    enables replay must produce a new distinction whose genealogy tags
    (Build 773 PR 1) carry both the original evidence and the enabling
    representation. Re-triggering with no further resolution increase
    must produce zero new writes (Build 772's own invariant, still
    holding after this build's additions)."""
    lg, gen, registry = _fresh(tmp_path)
    for i in range(4):
        r = lg.observe_historical_lexical_possibility(
            raw_text=f"glorp wibble zonk {i}",
            observed_response_text=f"an interesting thought {i}",
            possibility_id=f"POSS-WIBBLE-{i}",
        )
        assert r["reason"] == "no_relational_configuration"

    # Every unresolved entry got a real WARP demand_id.
    for entry in lg._historical_unresolved.values():
        assert entry.get("warp_demand_id")

    wibble = LexicalCandidate(
        candidate_id="LEX:wibble-enabler", word="wibble", component_id="warp:wibble-enabler",
        axis_profile={}, applicability_family="LEXFAM:test", parent_ids=[],
        structural_geometry={"slot": "relation"}, dominant_constraints=[], status="promoted",
        evidence=[], genealogy_ability_id="B:FAKE_ENABLER",
    )
    lg._candidates[wibble.component_id] = wibble
    lg._trigger_developmental_replay(wibble)

    replay_evidence = [
        e for c in lg._candidates.values() for e in c.evidence
        if e.get("provenance") == "developmental_replay"
    ]
    assert replay_evidence
    for e in replay_evidence:
        assert e["enabling_candidate_id"] == "LEX:wibble-enabler"
        assert e["enabling_genealogy_ability_id"] == "B:FAKE_ENABLER"
        assert e["replay_of_possibility_id"].startswith("POSS-WIBBLE-")
        assert e.get("warp_demand_id")  # threaded through from the original demand

    # Re-triggering for the same word with no further resolution increase
    # must not re-attempt already-replayed pairs.
    before = dict(lg._historical_diag)
    lg._trigger_developmental_replay(wibble)
    assert lg._historical_diag["replayed_observations"] == before["replayed_observations"]


def test_live_and_historical_evidence_converge_with_distinct_provenance(tmp_path):
    """Equivalent consequence-supported distinctions built once live, once
    historical, must converge on the same candidate_support() floor and
    the same genealogy/crystal reach, while evidence_source stays
    distinguishable per-entry -- historical provenance must not create a
    separate ontology."""
    lg, gen, registry = _fresh(tmp_path)
    touched = _observe_many(
        lg, "Aurora believe cat stories variant {i}", "the cat does believe stories variant {i}", n=9,
    )
    candidate = next(c for c in lg._candidates.values() if c.word == "believe")
    half = len(touched) // 2
    for entry in touched[:half]:
        lg.record_evidence_outcome(
            candidate_id=entry["candidate_id"], evidence_id=entry["evidence_id"],
            outcome_kind="positive", evidence_source="historical",
        )
    for entry in touched[half:]:
        lg.record_evidence_outcome(
            candidate_id=entry["candidate_id"], evidence_id=entry["evidence_id"],
            outcome_kind="positive", evidence_source="live",
        )
    sources = {e.get("evidence_source") for e in candidate.evidence if e.get("outcome_kind") == "positive"}
    assert sources == {"historical", "live"}
    assert lg.candidate_support(candidate) >= PROMOTION_SCORE

    _promote(lg)
    assert candidate.status == "promoted"
    ability = gen.abilities[candidate.genealogy_ability_id]
    tags = ability.effect_tags
    assert any(t.startswith("historical_evidence:") and not t.endswith(":0") for t in tags)
    assert any(t.startswith("live_evidence:") and not t.endswith(":0") for t in tags)
    # One registry call regardless of how many distinct evidence sources
    # contributed -- convergence, not a per-source split.
    assert len(registry.calls) == 1
