# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
External structural/safety audit (2026-08-02): the audit's diagnosis was
that "too many systems are permitted to rewrite the final expression."
Investigation found this is real for HALF the picture and already solved
for the other half:

  - resp_A's own formation (_chain_down3_purpose -> _chain_down2_belief ->
    _chain_down1_information) is genuinely a ~14-site cascade where each
    stage can overwrite state.response_content with no trace of who
    changed what. But it's a REFINEMENT pipeline (echo repair fixes the
    discourse-repaired text, not an independent draft), not competing
    candidates -- replacing it with a candidate/selection model would be
    a real behavior change to response generation this campaign's testing
    discipline can't fully characterize, so that was deliberately NOT
    done (see user decision, this session).

  - The resp_A-vs-resp_B reconciliation ("D2.1 voice transplant") was
    ALREADY a single, well-reasoned decision point -- just unnamed inline
    code buried in a ~2000-line function. Extracted verbatim (byte-
    identical logic) into _finalize_articulation() so the authority that
    already existed is actually nameable/callable/testable.

This test file covers both halves: _record_response_revision (the new
visibility mechanism for half one) and _finalize_articulation (the
extraction for half two, verified case-by-case against its own documented
three cases).
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import aurora as A  # noqa: E402


def _read_source():
    with open(os.path.join(REPO_ROOT, "aurora.py"), "r", encoding="utf-8") as f:
        return f.read()


class _State:
    def __init__(self, response_content="", response_confidence=0.5, response_src="", response_tone="neutral"):
        self.response_content = response_content
        self.response_confidence = response_confidence
        self.response_src = response_src
        self.response_tone = response_tone
        self.pipeline_state = {}


class _Resp:
    def __init__(self, content="", emotional_tone="neutral", confidence=0.5, src=""):
        self.content = content
        self.emotional_tone = emotional_tone
        self.confidence = confidence
        self.src = src


# ---------------------------------------------------------------------------
# Structural / wiring checks
# ---------------------------------------------------------------------------

def test_record_response_revision_function_exists():
    assert hasattr(A, "_record_response_revision")


def test_finalize_articulation_function_exists():
    assert hasattr(A, "_finalize_articulation")


def test_all_fourteen_chain_down_sites_call_record_response_revision():
    body = _read_source()
    assert body.count("_record_response_revision(state,") >= 14, (
        f"expected all 14 instrumented chain_down mutation sites, "
        f"found {body.count('_record_response_revision(state,')}"
    )


def test_run_reasoning_pipeline_calls_finalize_articulation_not_inline():
    body = _read_source()
    assert "_finalize_articulation(resp_A, resp_B, state, systems, user_text)" in body
    # The old inline marker comment should no longer appear duplicated
    # inline inside _run_reasoning_pipeline -- only inside
    # _finalize_articulation's own docstring/definition now.
    assert body.count("D2.1 (Directive D2, ratified 2026-07-17): voice transplant") == 1


# ---------------------------------------------------------------------------
# _record_response_revision
# ---------------------------------------------------------------------------

def test_records_when_content_changes():
    state = _State(response_content="new text", response_confidence=0.8)
    A._record_response_revision(state, "test_stage", "old text", 0.5)
    trace = state.pipeline_state.get("_response_revision_trace", [])
    assert len(trace) == 1
    assert trace[0]["stage"] == "test_stage"
    assert trace[0]["before"] == "old text"
    assert trace[0]["after"] == "new text"
    assert trace[0]["confidence_before"] == 0.5
    assert trace[0]["confidence_after"] == 0.8


def test_no_record_when_content_unchanged():
    state = _State(response_content="same text")
    A._record_response_revision(state, "test_stage", "same text", 0.5)
    assert "_response_revision_trace" not in state.pipeline_state


def test_multiple_stages_accumulate_in_order():
    state = _State(response_content="v1")
    A._record_response_revision(state, "stage_a", "", 0.0)
    state.response_content = "v2"
    A._record_response_revision(state, "stage_b", "v1", 0.5)
    trace = state.pipeline_state["_response_revision_trace"]
    assert [t["stage"] for t in trace] == ["stage_a", "stage_b"]


def test_missing_pipeline_state_does_not_raise():
    state = _State(response_content="new")
    state.pipeline_state = None
    A._record_response_revision(state, "stage", "old", 0.5)  # must not raise


def test_never_raises_on_malformed_state():
    class Bad:
        pass
    A._record_response_revision(Bad(), "stage", "old", 0.5)  # must not raise


# ---------------------------------------------------------------------------
# _finalize_articulation -- the 3 documented cases
# ---------------------------------------------------------------------------

def test_case1_composer_grounded_content_becomes_resp_a_words():
    """Communication Integrity Repair (2026-08-04): case 1 now requires
    the composer to demonstrably preserve resp_A's meaning, not just be
    non-empty -- this fixture is a genuine fluent paraphrase (shared
    content words "remember"/"garden", no named entity to drop) so it
    legitimately wins under the new arbitration, same as it always did
    under the old "any non-empty composer wins" rule."""
    resp_A = _Resp(content="I remember the garden we planted together.", confidence=0.6, src="search")
    resp_B = _Resp(content="I remember planting that garden with you.", emotional_tone="engaged", confidence=0.9)
    state = _State(response_content="I remember the garden we planted together.", response_confidence=0.6)
    systems = {"perception": None}
    A._finalize_articulation(resp_A, resp_B, state, systems, "some question")
    assert resp_A.content == "I remember planting that garden with you."
    assert resp_A.src == "composer_unified"
    assert resp_A.confidence == 0.9  # max(0.6, 0.9)
    assert state.response_content == "I remember planting that garden with you."
    assert state.response_src == "composer_unified"


def test_composer_that_does_not_preserve_meaning_does_not_overwrite_grounded_answer():
    """Communication Integrity Repair (2026-08-04): the confirmed live
    bug -- a well-grounded resp_A must not be replaced by a non-empty
    composer candidate that shares none of its content and drops it
    entirely, even at high composer confidence. Live-reported shape:
    grounded creator fact overwritten by unrelated composer prose."""
    resp_A = _Resp(content="My creator is Sunni Morningstar.", confidence=0.72, src="relational_role")
    resp_B = _Resp(content="I wonder about the weather outside today.", confidence=1.0)
    state = _State(response_content="My creator is Sunni Morningstar.", response_confidence=0.72)
    systems = {"perception": None}
    A._finalize_articulation(resp_A, resp_B, state, systems, "Who made you?")
    assert resp_A.content == "My creator is Sunni Morningstar."
    assert resp_A.src != "composer_unified"
    assert resp_A.confidence == 0.72, "rejected composer's confidence must not leak onto the winner"
    assert state.response_content == "My creator is Sunni Morningstar."


def test_case2_both_empty_triggers_honest_abstain():
    resp_A = _Resp(content="", confidence=0.0, src="")
    resp_B = _Resp(content="", confidence=0.0)
    state = _State(response_content="", response_confidence=0.0)
    systems = {"perception": None}

    called = {}
    def _fake_abstain(user_text, systems, state, trigger=""):
        called["trigger"] = trigger
        state.response_content = "I don't have grounds to answer that."
        state.response_tone = "honest"
        state.response_confidence = 0.3
        state.response_src = "constraint_abstain"

    orig = A._emit_honest_abstain_and_seek
    A._emit_honest_abstain_and_seek = _fake_abstain
    try:
        A._finalize_articulation(resp_A, resp_B, state, systems, "unanswerable question")
    finally:
        A._emit_honest_abstain_and_seek = orig

    assert called.get("trigger") == "emission_chokepoint"
    assert resp_A.content == "I don't have grounds to answer that."
    assert resp_A.src == "constraint_abstain"


def test_case3_composer_empty_but_chain_has_content_keeps_chain():
    resp_A = _Resp(content="a direct fact from my own chain", confidence=0.85, src="search")
    resp_B = _Resp(content="", confidence=0.0)
    state = _State(response_content="a direct fact from my own chain", response_confidence=0.85, response_src="search")
    systems = {"perception": None}
    A._finalize_articulation(resp_A, resp_B, state, systems, "a question")
    # Unchanged -- graceful degradation, not abstain, not composer_unified.
    assert resp_A.content == "a direct fact from my own chain"
    assert resp_A.src == "search"
    assert state.response_src == "search"


def test_composer_abstain_template_recognized_as_silence_not_content():
    """D2 Acceptance Condition 2: a composer-level abstain string (from
    SentenceComposer._ABSTAIN_TEMPLATES) must fall through to case 2/3,
    not be mistaken for grounded case-1 content."""
    class _FakeComposer:
        _ABSTAIN_TEMPLATES = ("I'm not sure.", "I don't know.")

    resp_A = _Resp(content="my own chain answer", confidence=0.6, src="search")
    resp_B = _Resp(content="I'm not sure.", confidence=0.5)
    state = _State(response_content="my own chain answer", response_confidence=0.6, response_src="search")
    systems = {"perception": type("P", (), {"composer": _FakeComposer()})()}

    A._finalize_articulation(resp_A, resp_B, state, systems, "a question")
    # Falls to case 3 (chain has content) -- composer's abstain string
    # must never become the delivered content.
    assert resp_A.content == "my own chain answer"
    assert resp_A.src != "composer_unified"


def test_resp_b_none_falls_through_to_chain_content():
    resp_A = _Resp(content="chain content", confidence=0.7, src="search")
    resp_B = None
    state = _State(response_content="chain content", response_confidence=0.7, response_src="search")
    systems = {"perception": None}
    A._finalize_articulation(resp_A, resp_B, state, systems, "a question")
    assert resp_A.content == "chain content"
