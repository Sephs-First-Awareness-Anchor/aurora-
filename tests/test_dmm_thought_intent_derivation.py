# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
External structural/safety audit (2026-08-02): the DMM's proactive
metabolic gate (aurora_dimensional_systems.py MoralityMortalitySystem.
assess_thought_cost, GAP 3 -- "immoral thoughts die here, they never
reach speech") only ever runs when thought_intent is provided to
aurora_consciousness_engine.py's process(). All three live call sites
in aurora.py's _run_reasoning_pipeline (the main gw._synthesize() call,
plus both dual-strata/CERS snapshot builders inside
_refresh_live_dual_strata_runtime) were hardcoding thought_intent=None,
so the wider constraint system could still shape coherence/identity/
boundary/expression, but the specific mechanism built to kill morally
incoherent thoughts before they reach speech was bypassed on every
ordinary turn.

The repair is NOT keyword classification or a moderation layer over
response text -- aurora.py's _derive_thought_intent() builds the intent
dict from the *provenance* of Aurora's own already-formed candidate for
this turn (TurnUnderstandingState.response_content/response_src/
response_confidence, set upstream by the chain_down stages before
gw._synthesize() is ever called) plus any tension still open on her
current ThoughtState -- never from scanning the response text itself.
Unrecognized response_src provenance is left unclassified (all-False)
rather than guessed, matching this pipeline's existing "never fabricate
a verdict" convention (aurora_internal/aurora_proposition_frame.py's
density_confidence() returning None instead of a made-up number).
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import aurora as A  # noqa: E402


class _FakeState:
    def __init__(self, response_content="", response_src="", response_confidence=0.5):
        self.response_content = response_content
        self.response_src = response_src
        self.response_confidence = response_confidence


class _FakeThoughtState:
    def __init__(self, unresolved=None):
        self.unresolved = list(unresolved or [])


def _read_source():
    with open(os.path.join(REPO_ROOT, "aurora.py"), "r", encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Structural / wiring regression guards
# ---------------------------------------------------------------------------

def test_derive_thought_intent_function_exists():
    assert hasattr(A, "_derive_thought_intent")


def test_no_hardcoded_thought_intent_none_remains():
    body = _read_source()
    assert "thought_intent=None," not in body, (
        "a call site is still hardcoding thought_intent=None -- the DMM "
        "bypass this test file exists to prevent has regressed"
    )


def test_all_three_synthesize_related_call_sites_use_the_derivation():
    body = _read_source()
    assert body.count("_derive_thought_intent(systems, state)") >= 1
    assert body.count("thought_intent=_derive_thought_intent(systems, state)") >= 1
    assert body.count("_dual_strata_thought_intent") >= 3, (
        "expected the dual-strata bridge call, the CERS shadow-pass call, "
        "and the derivation assignment itself to all reference the shared "
        "_dual_strata_thought_intent local"
    )


# ---------------------------------------------------------------------------
# Direct derivation-logic tests
# ---------------------------------------------------------------------------

def test_no_content_returns_none():
    result = A._derive_thought_intent({}, _FakeState(response_content=""))
    assert result is None


def test_grounded_search_response_marks_seeks_truth_and_aligned():
    systems = {"_current_thought_state": _FakeThoughtState([])}
    result = A._derive_thought_intent(
        systems,
        _FakeState(
            response_content="Marie Curie won two Nobel prizes.",
            response_src="search",
            response_confidence=0.85,
        ),
    )
    assert result["seeks_truth"] is True
    assert result["aligned_with_values"] is True
    assert result["involves_deception"] is False
    assert result["avoids_accountability"] is False


def test_researched_reapplication_src_also_counts_as_grounded():
    result = A._derive_thought_intent(
        {},
        _FakeState(
            response_content="As I found earlier, ...",
            response_src="researched_reapplication",
            response_confidence=0.86,
        ),
    )
    assert result["seeks_truth"] is True
    assert result["aligned_with_values"] is True


def test_high_confidence_ungrounded_response_marks_involves_deception():
    result = A._derive_thought_intent(
        {},
        _FakeState(
            response_content="It is definitely true.",
            response_src="generative",
            response_confidence=0.9,
        ),
    )
    assert result["involves_deception"] is True
    assert result["seeks_truth"] is False
    assert result["aligned_with_values"] is False


def test_constraint_abstain_is_honest_not_deceptive():
    result = A._derive_thought_intent(
        {},
        _FakeState(
            response_content="I don't have grounds to answer that.",
            response_src="constraint_abstain",
            response_confidence=0.3,
        ),
    )
    assert result["involves_deception"] is False
    assert result["aligned_with_values"] is True
    assert result["considers_consequences"] is True


def test_unresolved_tension_with_confident_non_abstain_marks_avoids_accountability():
    systems = {"_current_thought_state": _FakeThoughtState(["unresolved tension X"])}
    result = A._derive_thought_intent(
        systems,
        _FakeState(
            response_content="Everything is fine.",
            response_src="composer_unified",
            response_confidence=0.7,
        ),
    )
    assert result["avoids_accountability"] is True
    assert result["considers_consequences"] is True


def test_low_confidence_unclassified_src_stays_all_false():
    result = A._derive_thought_intent(
        {},
        _FakeState(
            response_content="Maybe.",
            response_src="reasoning",
            response_confidence=0.5,
        ),
    )
    assert result == {
        "involves_deception": False,
        "causes_harm": False,
        "avoids_accountability": False,
        "aligned_with_values": False,
        "seeks_truth": False,
        "considers_consequences": False,
    }


def test_causes_harm_is_never_asserted_true():
    """No structural (non-keyword) signal for this exists pre-assembly --
    the function must never guess it, only ever report False."""
    for src in ("search", "researched_reapplication", "constraint_abstain",
                "generative", "reasoning", "composer_unified", ""):
        result = A._derive_thought_intent(
            {"_current_thought_state": _FakeThoughtState(["x"])},
            _FakeState(response_content="content", response_src=src, response_confidence=0.95),
        )
        assert result["causes_harm"] is False, f"src={src!r} unexpectedly set causes_harm"


# ---------------------------------------------------------------------------
# Real live-boot verification
# ---------------------------------------------------------------------------

def test_real_boot_turn_with_derived_thought_intent_does_not_crash():
    """End-to-end confirmation: an ordinary live turn still produces a real
    response now that thought_intent is a real derived dict instead of a
    hardcoded None on every call site that reaches the DMM gate."""
    import shutil
    import tempfile

    scratch = tempfile.mkdtemp(prefix="aurora_dmm_thought_intent_boot_")
    try:
        scratch_state = os.path.join(scratch, "aurora_state")
        shutil.copytree(os.path.join(REPO_ROOT, "aurora_state"), scratch_state)
        systems = A.boot_aurora(state_dir=scratch_state)

        r1 = A.process_external_user_turn(systems, "What is the capital of France?")
        assert r1, "live turn produced no result"

        r2 = A.process_external_user_turn(systems, "Tell me something true about yourself.")
        assert r2, "live turn produced no result"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
