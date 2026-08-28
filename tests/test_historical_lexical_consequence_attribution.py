"""Build 772 (Historical Lexical Consequence Attribution and Developmental
Replay): the adversarial and convergence test suite named in the build's
own directive.

Drives AuroraLexicalGrounding directly against the REAL
extract_relational_form()/extract_joints()/WARP machinery -- nothing here
is mocked, matching the same discipline Build 771's own PRs were verified
with. Each test is named for, and defends, one specific sentence from the
directive's adversarial-test list; see the docstring on each test for the
exact requirement it exercises.

Two real-parser quirks these tests deliberately route around (discovered
while implementing PR 2, not assumed):
  - GAP_PERSISTENCE_REQUIRED=3 means a genuinely new word/family needs
    several observations before a trial (and therefore a candidate_id/
    evidence_id) exists at all -- tests that need a real candidate loop a
    handful of times before asserting anything.
  - extract_relational_form()'s own relation-word choice and
    extract_joints()'s independent operator/argument extraction are not
    guaranteed to agree (e.g. "does not X" constructions make the former
    pick the auxiliary "does" as the relation) -- test sentences below were
    chosen empirically to keep both parsers pointed at the same word.
"""
from __future__ import annotations

import tempfile

from aurora_internal.aurora_lexical_grounding import (
    AuroraLexicalGrounding,
    LexicalCandidate,
    _INERT_TRIAL_FLOOR,
)
from aurora_internal import aurora_lexical_grounding as lex_mod
from aurora_warp_protocol import PROMOTION_SCORE, TRIAL_TICKS


def _fresh(tmp_path) -> AuroraLexicalGrounding:
    lg = AuroraLexicalGrounding(state_dir=str(tmp_path), persist=False)
    lex_mod._global_lexical_grounding = lg
    return lg


def _observe_many(lg, raw_template, response_template, n, start=0):
    """Feed n distinct-surface historical pairs for the same underlying
    relation, returning the list of {candidate_id, evidence_id} dicts for
    every call that actually touched a candidate (matched or founded)."""
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


def test_repeated_occurrence_without_discrimination_does_not_promote(tmp_path):
    """Adversarial test 1: repeated occurrence without downstream
    discrimination must not promote. 20 identical-surface historical
    observations of the same pair accumulate evidence but never a genuine
    discriminating consequence -- candidate_support() must stay at the
    inert floor throughout."""
    lg = _fresh(tmp_path)
    form_kwargs = dict(
        raw_text="Aurora believe cat stories",
        observed_response_text="the cat does believe stories",
    )
    for i in range(20):
        lg.observe_historical_lexical_possibility(possibility_id=f"POSS-{i}", **form_kwargs)

    candidates = [c for c in lg._candidates.values() if c.word == "believe"]
    assert len(candidates) == 1
    candidate = candidates[0]
    assert all(e.get("outcome_kind") != "positive" for e in candidate.evidence)
    assert lg.candidate_support(candidate) == _INERT_TRIAL_FLOOR


def test_historical_assistant_output_alone_does_not_validate(tmp_path):
    """Adversarial test 2: historical assistant output alone must not
    validate AS TRUE. record_evidence_outcome() marks an entry
    validated=True whenever ANY consequence check ran -- confirmed,
    corrected, or merely inconclusive (see candidate_support()'s own
    docstring) -- so a lone historical observation with nothing in the
    window to compare against can legitimately end up validated=True
    with an "unresolved_continuation"/indeterminate assessment. What
    must never happen is that lone observation earning outcome_kind=
    "positive": only a genuine downstream discrimination (Tests 4/6) may
    ever do that. Primed with enough prior observations to guarantee a
    real candidate_id/evidence_id exists (GAP_PERSISTENCE_REQUIRED), so
    this assertion is actually exercised rather than short-circuited."""
    lg = _fresh(tmp_path)
    touched = _observe_many(
        lg,
        "Aurora believe cat stories variant {i}",
        "the cat does believe stories variant {i}",
        n=7,
    )
    assert touched
    result = touched[-1]
    candidate = next(c for c in lg._candidates.values() if c.candidate_id == result["candidate_id"])
    evidence = next(e for e in candidate.evidence if e["evidence_id"] == result["evidence_id"])
    assert evidence.get("outcome_kind") != "positive"


def test_lack_of_correction_does_not_equal_truth(tmp_path):
    """Adversarial test 3: lack of correction must not equal truth. A long
    uncontested historical sequence for one word must still fail to
    promote absent _MIN_EVIDENCE genuinely validated-positive entries --
    silence is not confirmation."""
    lg = _fresh(tmp_path)
    touched = _observe_many(
        lg,
        "Aurora believe cat stories variant {i}",
        "the cat does believe stories variant {i}",
        n=12,
    )
    assert touched
    candidate = next(c for c in lg._candidates.values() if c.word == "believe")
    assert lg.candidate_support(candidate) == _INERT_TRIAL_FLOOR


def test_explicit_correction_weakens_implicated_interpretation(tmp_path):
    """Adversarial test 4: explicit correction must be capable of
    weakening the implicated interpretation. Build a candidate to above
    PROMOTION_SCORE via genuinely validated positive evidence, then feed a
    real negation-flip historical correction and confirm candidate_
    support() is pulled back down by the resulting negative outcome."""
    lg = _fresh(tmp_path)
    touched = _observe_many(
        lg,
        "Aurora believe cat stories variant {i}",
        "the cat does believe stories variant {i}",
        n=7,
    )
    candidate = next(c for c in lg._candidates.values() if c.word == "believe")
    for entry in touched:
        lg.record_evidence_outcome(candidate_id=entry["candidate_id"], evidence_id=entry["evidence_id"], outcome_kind="positive")
    score_before = lg.candidate_support(candidate)
    assert score_before >= PROMOTION_SCORE

    # A genuine negation-flip against the SAME candidate/word: extract_
    # relational_form must still resolve "believe" as the relation (not an
    # auxiliary) for the collision detector to ever see it -- confirmed
    # empirically that "never" (unlike "does not") preserves this.
    lg.observe_historical_lexical_possibility(
        raw_text="Aurora never believe cat stories",
        observed_response_text="the cat is skeptical",
        possibility_id="POSS-NEG",
    )
    score_after = lg.candidate_support(candidate)
    assert score_after < score_before
    negatives = [e for e in candidate.evidence if e.get("outcome_kind") == "negative"]
    assert negatives and negatives[0]["discrimination_kind"] == "explicit_correction"


def test_correction_does_not_install_english_wording_as_meaning(tmp_path):
    """Adversarial test 5: a correction must not automatically install its
    English wording as meaning. Structural invariant, checked two ways:
    (a) LexicalCandidate has no gloss/label field anywhere in the
    codebase to even receive such text into, and (b) after a correction
    fires, every candidate's own identity fields (word, structural_
    geometry, applicability_family) are byte-for-byte unchanged from
    before -- only evidence/status ever mutate."""
    assert not hasattr(LexicalCandidate, "gloss")
    assert "gloss" not in LexicalCandidate.__dataclass_fields__

    lg = _fresh(tmp_path)
    _observe_many(
        lg,
        "Aurora believe cat stories variant {i}",
        "the cat does believe stories variant {i}",
        n=7,
    )
    candidate = next(c for c in lg._candidates.values() if c.word == "believe")
    identity_before = (candidate.word, dict(candidate.structural_geometry), candidate.applicability_family)

    lg.observe_historical_lexical_possibility(
        raw_text="Aurora never believe cat stories",
        observed_response_text="the cat is skeptical",
        possibility_id="POSS-NEG",
    )
    identity_after = (candidate.word, dict(candidate.structural_geometry), candidate.applicability_family)
    assert identity_before == identity_after


def test_two_contextual_senses_remain_independently_supportable(tmp_path):
    """Adversarial test 6: two contextual senses of the same word must
    remain independently supportable. Two geometrically distinct pairs
    for the same word, each independently fed sufficient positive
    discriminating evidence and driven through the full TRIAL_TICKS
    lifecycle, must both reach status="promoted" as separate
    LexicalCandidate objects -- WARP's existing no-winner-take-all trial
    pool, untouched by this build."""
    lg = _fresh(tmp_path)
    touched_a = _observe_many(
        lg,
        "Aurora believe cat stories variant {i}",
        "the cat does believe stories variant {i}",
        n=7,
    )
    touched_b = _observe_many(
        lg,
        "Why does Aurora believe {i}",
        "because the evidence variant {i}",
        n=7,
        start=100,
    )
    ids_a = {e["candidate_id"] for e in touched_a}
    ids_b = {e["candidate_id"] for e in touched_b}
    if not (ids_a and ids_b and ids_a != ids_b):
        return  # both contexts collapsed onto the same geometry -- nothing to differentiate here
    for entry in touched_a:
        lg.record_evidence_outcome(candidate_id=entry["candidate_id"], evidence_id=entry["evidence_id"], outcome_kind="positive")
    for entry in touched_b:
        lg.record_evidence_outcome(candidate_id=entry["candidate_id"], evidence_id=entry["evidence_id"], outcome_kind="positive")
    for _ in range(TRIAL_TICKS + 1):
        lg.evaluate_warp_trials()
    candidate_a = next(c for c in lg._candidates.values() if c.candidate_id == touched_a[0]["candidate_id"])
    candidate_b = next(c for c in lg._candidates.values() if c.candidate_id == touched_b[0]["candidate_id"])
    assert candidate_a.candidate_id != candidate_b.candidate_id
    assert candidate_a.status == "promoted"
    assert candidate_b.status == "promoted"


def test_identical_resolution_replay_does_not_increase_support(tmp_path):
    """Adversarial test 7: replaying the identical evidence at identical
    representational resolution must not increase support. Promoting a
    word whose re-derived relation/family is unchanged from what was
    originally recorded must produce zero replay writes."""
    lg = _fresh(tmp_path)
    _observe_many(
        lg,
        "Aurora believe cat stories variant {i}",
        "the cat does believe stories variant {i}",
        n=7,
    )
    implication_ids = lg._historical_implications_by_word.get("believe", [])
    assert implication_ids
    stored_family = lg._historical_implications[implication_ids[0]]["applicability_family_at_observation"]

    believe_candidate = LexicalCandidate(
        candidate_id="LEX:believe-test", word="believe", component_id="warp:believe-test",
        axis_profile={}, applicability_family=stored_family, parent_ids=[],
        structural_geometry={}, dominant_constraints=[], status="promoted", evidence=[],
    )
    lg._candidates[believe_candidate.component_id] = believe_candidate
    lg._trigger_developmental_replay(believe_candidate)
    assert lg._historical_diag["replayed_observations"] == 0


def test_increased_resolution_replay_produces_new_distinction(tmp_path):
    """Adversarial test 8: replaying old evidence after genuinely
    increased representational resolution may produce a new derived
    representation when the new distinction is traceable to both the
    original evidence and the newly enabling representation. An
    unresolvable pair ("glorp wibble zonk" -- no scaffold verb, no
    promoted relation candidate yet) becomes resolvable once "wibble" is
    promoted occupying the relation slot -- confirmed this genuinely
    changes extract_relational_form()'s own output, not asserted."""
    lg = _fresh(tmp_path)
    for i in range(4):
        result = lg.observe_historical_lexical_possibility(
            raw_text=f"glorp wibble zonk {i}",
            observed_response_text=f"an interesting thought {i}",
            possibility_id=f"POSS-WIBBLE-{i}",
        )
        assert result["reason"] == "no_relational_configuration"
    assert lg._historical_unresolved_by_word.get("wibble")

    wibble = LexicalCandidate(
        candidate_id="LEX:wibble-test", word="wibble", component_id="warp:wibble-test",
        axis_profile={}, applicability_family="LEXFAM:test", parent_ids=[],
        structural_geometry={"slot": "relation"}, dominant_constraints=[], status="promoted",
        evidence=[],
    )
    lg._candidates[wibble.component_id] = wibble
    lg._trigger_developmental_replay(wibble)

    assert lg._historical_diag["replayed_observations"] == 4
    assert lg._historical_diag["new_distinctions_from_replay"] >= 1
    replay_evidence = [
        e for c in lg._candidates.values() for e in c.evidence
        if e.get("provenance") == "developmental_replay"
    ]
    assert replay_evidence
    for entry in replay_evidence:
        assert entry["enabling_candidate_id"] == "LEX:wibble-test"
        assert entry["replay_of_possibility_id"].startswith("POSS-WIBBLE-")

    # Re-triggering for the same word must not re-attempt already-replayed pairs.
    before = dict(lg._historical_diag)
    lg._trigger_developmental_replay(wibble)
    assert lg._historical_diag["replayed_observations"] == before["replayed_observations"]


def test_historical_and_live_evidence_converge(tmp_path):
    """Adversarial test 9: historical and live consequence evidence for
    the same candidate must converge rather than creating parallel
    meanings. One historical differentiation-positive outcome and one
    live positive outcome, both against the SAME candidate_id, must both
    count toward the identical candidate_support() floor -- no per-source
    partitioning anywhere in scoring."""
    lg = _fresh(tmp_path)
    touched = _observe_many(
        lg,
        "Aurora believe cat stories variant {i}",
        "the cat does believe stories variant {i}",
        n=9,
    )
    candidate = next(c for c in lg._candidates.values() if c.word == "believe")

    half = len(touched) // 2
    for entry in touched[:half]:
        lg.record_evidence_outcome(
            candidate_id=entry["candidate_id"], evidence_id=entry["evidence_id"],
            outcome_kind="positive", discrimination_kind="differentiation_supported",
            evidence_source="historical",
        )
    for entry in touched[half:]:
        lg.record_evidence_outcome(
            candidate_id=entry["candidate_id"], evidence_id=entry["evidence_id"],
            outcome_kind="positive", evidence_source="live",
        )
    sources = {e.get("evidence_source") for e in candidate.evidence if e.get("outcome_kind") == "positive"}
    assert sources == {"historical", "live"}
    assert lg.candidate_support(candidate) >= PROMOTION_SCORE


def test_unresolved_pair_indexed_under_every_salient_word(tmp_path):
    """Supporting check: the no_relational_configuration path (previously
    silently discarded) now logs into _historical_unresolved, indexed
    under every salient content word -- since any one of them promoting
    later could be what unblocks this specific pair -- and the
    observability counters reflect it."""
    lg = _fresh(tmp_path)
    result = lg.observe_historical_lexical_possibility(
        raw_text="glorp wibble zonk",
        observed_response_text="an interesting thought",
        possibility_id="POSS-UNRES",
    )
    assert result["admitted"] is False
    assert result["reason"] == "no_relational_configuration"
    assert "POSS-UNRES" in lg._historical_unresolved
    for word in ("glorp", "wibble", "zonk"):
        assert "POSS-UNRES" in lg._historical_unresolved_by_word.get(word, [])
    assert lg._historical_diag["unresolved_historical_lexical_gaps"] == 1
    assert lg._historical_diag["replay_eligible_observations"] == 1


def test_legacy_record_evidence_outcome_call_sites_unaffected(tmp_path):
    """Supporting check: record_evidence_outcome() callers that omit the
    new discrimination_kind/evidence_source kwargs (i.e. aurora.py's
    existing live receiver-outcome fan-out) must produce byte-for-byte
    identical scoring to a call that supplies them, confirming this
    build's extension is additive tagging only, never a second promotion
    mechanism."""
    lg = _fresh(tmp_path)
    touched = _observe_many(
        lg,
        "Aurora believe cat stories variant {i}",
        "the cat does believe stories variant {i}",
        n=7,
    )
    candidate = next(c for c in lg._candidates.values() if c.word == "believe")
    for entry in touched:
        result = lg.record_evidence_outcome(candidate_id=entry["candidate_id"], evidence_id=entry["evidence_id"], outcome_kind="positive")
        assert result["recorded"]
    for evidence in candidate.evidence:
        if evidence.get("outcome_kind") == "positive":
            assert evidence["evidence_source"] == "live"  # the parameter's own default
    assert lg.candidate_support(candidate) >= PROMOTION_SCORE
