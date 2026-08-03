# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Zip patch (generative-communication, 2026-08-02), ported as designed:
"public fact vs. private context" gap research router.

Today (pre-patch), a comprehension gap that hits gap_action == "ask"
always returns a clarification question immediately, even when the
missing information is something Aurora could honestly research
herself (e.g. "Who was Marie Curie?"). This patch classifies whether a
gap's missing information is publicly researchable vs. only the user
can supply it, auto-researches the former via the existing
_poedex_lookup_evidence, and re-applies the result as a turn-local,
non-durable semantic bridge -- durable promotion stays gated behind
receiver feedback via stage_pipeline_learning/resolve_pipeline_learning
(Communication Credit Unification), never duplicated here.

A real, load-bearing dependency gap was found and fixed while porting
this: the zip's _poedex_lookup_evidence/_broadcast_poedex_result both
take a `provisional` kwarg that live's versions did not have at all.
`provisional=True` is what makes _broadcast_poedex_result short-circuit
BEFORE any conversation_memory.learn_fact/understanding_contract.
ingest_observation call -- i.e. it is the entire mechanism that keeps
automatic research turn-local instead of immediately durable. Without
it, every call in this patch would have raised an unhandled TypeError
on any real "ask" turn. Extended both functions to match the zip.

A second, more serious real bug was found via real live-boot testing:
_try_poedex_lookup(use_researcher=True) polls a daemon queue for up to
35 SECONDS -- regardless of the timeout= argument passed in -- and did
so because its _room_likely_up heuristic (aurora.py, ~line 11122) reads
"is the poedex_results directory's own mtime under 300s old" as "a
daemon is listening". shutil.copytree (used by every real-boot test's
scratch-state setup in this whole campaign) touches the destination
directory's mtime on every write into it, so a freshly-copied
aurora_state/ ALWAYS looks like a live room for 5 minutes after copy,
even against a real repo where the daemon has been dormant for 12+
days. use_researcher=True was previously reachable only via an
EXPLICIT manual lookup (a human asked Aurora to search, consenting to
the wait); this patch's automatic gap-research paths are the first
code to reach it on every ordinary "ask"-shaped turn, including
gibberish with nothing real to research -- confirmed to actually hang
tests/test_d2_condition2_abstain_sanity.py's live gibberish-turn test
for a very long time. Fixed by keeping use_researcher=True (and its
35s ceiling) reserved for explicit manual lookups only; the automatic/
implicit paths added here use use_researcher=False with a short 2.0s
timeout, bounding the worst case even when _room_likely_up
false-positives (confirmed: against the real, uncopied aurora_state/,
where the room genuinely IS stale, the call returns in ~0.0001s).
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import aurora as A  # noqa: E402


def _read_source():
    with open(os.path.join(REPO_ROOT, "aurora.py"), "r", encoding="utf-8") as f:
        return f.read()


# ---- structural wiring ----

def test_new_functions_and_constants_exist():
    for name in (
        "_PUBLIC_FACT_QUESTION_PREFIXES", "_USER_CONTEXT_MARKERS",
        "_explicit_public_question_target", "_gap_type_value",
        "_gap_information_source", "_user_context_anchor_needed",
        "_research_target_for_gap", "_public_question_needs_research",
        "_research_summary_is_usable", "_build_research_reapplication",
        "_research_public_gap", "_detect_researchable_gap",
        "_render_user_context_clarification", "_render_research_unresolved_response",
        "_apply_research_reapplication_to_state", "_render_reapplied_research_claim",
    ):
        assert hasattr(A, name), f"missing {name}"


def test_poedex_functions_accept_provisional_kwarg():
    import inspect
    sig_evidence = inspect.signature(A._poedex_lookup_evidence)
    sig_broadcast = inspect.signature(A._broadcast_poedex_result)
    assert "provisional" in sig_evidence.parameters
    assert "provisional" in sig_broadcast.parameters
    assert sig_evidence.parameters["provisional"].default is False
    assert sig_broadcast.parameters["provisional"].default is False


def test_run_reasoning_pipeline_accepts_research_reapplication_kwarg():
    import inspect
    sig = inspect.signature(A._run_reasoning_pipeline)
    assert "research_reapplication" in sig.parameters


def test_chain_down3_purpose_renders_reapplied_claim_before_generic_extraction():
    source = _read_source()
    start = source.index("def _chain_down3_purpose(")
    end = source.index("\ndef ", start + 10)
    body = source[start:end]
    reapply_idx = body.index("_render_reapplied_research_claim")
    generic_idx = body.index("Narrow factual extraction using salient concepts")
    assert reapply_idx < generic_idx


def test_dual_question_pipeline_gap_ask_routes_before_immediate_clarification():
    source = _read_source()
    start = source.index("def dual_question_pipeline(")
    end = source.index("\ndef _run_live_response_turn(")
    body = source[start:end]
    for marker in (
        "_user_context_anchor_needed(user_text)",
        "_public_question_needs_research(",
        "_detect_researchable_gap(user_text, systems)",
        "_research_public_gap(",
        'route == "reapplied"',
        'route == "user_context"',
        'route == "unresolved"',
        "research_reapplication=research_reapplication or None",
    ):
        assert marker in body, f"missing {marker!r} in dual_question_pipeline"


def test_automatic_research_paths_never_use_researcher_true_unconditionally():
    """Regression guard for the 35s-hang finding: _research_public_gap's
    own _poedex_lookup_evidence call must use use_researcher=False (not
    True), and dual_question_pipeline's shared evidence-fetch call must
    gate use_researcher on manual_lookup rather than passing True
    unconditionally."""
    source = _read_source()

    start = source.index("def _research_public_gap(")
    end = source.index("\ndef ", start + 10)
    body = source[start:end]
    call_start = body.index("_poedex_lookup_evidence(")
    call_body = body[call_start:call_start + 300]
    assert "use_researcher=False" in call_body
    assert "use_researcher=True" not in call_body


def test_unresolved_route_never_returns_a_canned_response():
    """Regression guard for the second real bug found via live-boot
    testing: all three route == "unresolved" sites in dual_question_
    pipeline must NOT return _MiniResp(..., src="research_unresolved")
    early -- doing so overrode this codebase's existing, specifically-
    tested constraint_abstain honest-failure path (D2 Condition 2) for
    genuinely ungroundable input like pure gibberish. An unresolved
    research attempt must fall through to whatever the pipeline would
    already do without it."""
    source = _read_source()
    start = source.index("def dual_question_pipeline(")
    end = source.index("\ndef _run_live_response_turn(")
    body = source[start:end]
    assert 'resp_gap.src = "research_unresolved"' not in body
    assert 'elif route == "unresolved":' not in body, (
        "no live branch should still test for the unresolved route -- "
        "only explanatory comments may mention it"
    )

    start = source.index("def dual_question_pipeline(")
    end = source.index("\ndef _run_live_response_turn(")
    body = source[start:end]
    assert "use_researcher=manual_lookup" in body


def test_room_likely_up_false_positive_returns_fast_with_use_researcher_false():
    """The actual bug: against the real, uncopied aurora_state/ (where
    the poedex room has genuinely been dormant for a long time),
    _try_poedex_lookup must return near-instantly regardless of
    use_researcher, proving the automatic path's own bounded timeout is
    what protects it -- not luck about room staleness."""
    import time

    systems = {"state_dir": os.path.join(REPO_ROOT, "aurora_state")}
    t0 = time.time()
    result = A._try_poedex_lookup("a nonexistent gibberish concept xyzzy", systems, timeout=2.0, use_researcher=False)
    elapsed = time.time() - t0

    assert elapsed < 1.0, f"expected a fast return against a dormant room, took {elapsed:.3f}s"
    assert result == ""


# ---- direct unit tests: classifier functions (no systems mocking needed) ----

def test_explicit_public_question_target_keeps_multiword_subject():
    assert A._explicit_public_question_target("Who was Marie Curie?") == "marie curie"


def test_explicit_public_question_target_empty_for_non_public_prefix():
    assert A._explicit_public_question_target("why did that matter to me?") == ""


def test_gap_information_source_public_for_plain_factual_question():
    assert A._gap_information_source("What is photosynthesis?") == "public"


def test_gap_information_source_user_context_for_personal_reference():
    assert A._gap_information_source("what did I say about that yesterday?") == "user_context"


def test_gap_information_source_vocabulary_gap_is_public_by_default():
    import types
    gap = types.SimpleNamespace(gap_type=types.SimpleNamespace(value="vocabulary"), unclear_element="bussin")
    assert A._gap_information_source("that meal was bussin", gap=gap) == "public"


def test_gap_information_source_vocabulary_gap_with_personal_marker_is_private():
    import types
    gap = types.SimpleNamespace(gap_type=types.SimpleNamespace(value="vocabulary"), unclear_element="term")
    assert A._gap_information_source("we call it our term in my project", gap=gap) == "user_context"


def test_gap_information_source_referent_gap_is_user_context():
    import types
    gap = types.SimpleNamespace(gap_type=types.SimpleNamespace(value="referent"), unclear_element="that")
    assert A._gap_information_source("why did that matter to me?", gap=gap) == "user_context"


def test_user_context_anchor_needed_detects_personal_referent_question():
    anchor = A._user_context_anchor_needed("why did that matter to me?")
    assert anchor


def test_user_context_anchor_needed_empty_for_ordinary_statement():
    assert A._user_context_anchor_needed("the sky is blue today") == ""


def test_render_user_context_clarification_falls_back_to_template_when_composer_fails():
    """Live user report (2026-08-03): when working_memory._render_from_
    comprehension_intent()'s own composer candidate is rejected (or
    never produced), its fallback is the raw, unprocessed core_claim --
    internal-reasoning phrasing never meant to be spoken verbatim ("the
    missing anchor is X; it belongs to your own context rather than
    public evidence; what should I use as the right reference"). Since
    target is a substring of that claim by construction, the old check
    (`target.lower() in rendered.lower()`) could not tell a real
    composed rendering apart from this raw leak. Must fall through to
    the clean template instead."""
    import types

    class _LeakyWorkingMemory:
        def _render_from_comprehension_intent(self, systems, *, core_claim, **kwargs):
            return core_claim  # simulates the composer failing and clean leaking back out

    systems = {"working_memory": _LeakyWorkingMemory()}
    gap = types.SimpleNamespace(gap_type=types.SimpleNamespace(value="referent"), unclear_element="it")
    result = A._render_user_context_clarification(systems, user_text="Did that upset you?", gap=gap)
    assert result == "What should I use as the right reference for it?"
    assert "missing anchor is" not in result
    assert "public evidence" not in result


def test_render_user_context_clarification_accepts_a_real_composed_rendering():
    """A genuine field-composed rendering (not the raw claim leaking
    back out) that legitimately contains the target must still be used
    as-is -- the new check only rejects an EXACT match against the raw
    internal claim, not any rendering that happens to reuse some of its
    words."""
    import types

    class _RealWorkingMemory:
        def _render_from_comprehension_intent(self, systems, *, core_claim, **kwargs):
            return "I'm not sure what you mean by it -- can you tell me more?"

    systems = {"working_memory": _RealWorkingMemory()}
    gap = types.SimpleNamespace(gap_type=types.SimpleNamespace(value="referent"), unclear_element="it")
    result = A._render_user_context_clarification(systems, user_text="Did that upset you?", gap=gap)
    assert result == "I'm not sure what you mean by it -- can you tell me more?"


def test_real_boot_user_context_clarification_never_leaks_raw_claim():
    """Real end-to-end confirmation against the live composer/working_
    memory stack, not a mock -- the exact scenario the user's report
    surfaced."""
    import shutil
    import tempfile
    import types

    scratch = tempfile.mkdtemp(prefix="aurora_uc_clarification_boot_")
    try:
        scratch_state = os.path.join(scratch, "aurora_state")
        shutil.copytree(os.path.join(REPO_ROOT, "aurora_state"), scratch_state)
        systems = A.boot_aurora(state_dir=scratch_state)

        gap = types.SimpleNamespace(gap_type=types.SimpleNamespace(value="referent"), unclear_element="it")
        result = A._render_user_context_clarification(systems, user_text="Did that upset you?", gap=gap)
        assert result, "clarification produced no result"
        assert "missing anchor is" not in result.lower()
        assert "public evidence" not in result.lower()
        assert "it" in result.lower()
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_research_summary_is_usable_rejects_parser_artifact_prefixes():
    assert A._research_summary_is_usable("from_definition: something", target="something") is False


def test_research_summary_is_usable_accepts_real_content():
    assert A._research_summary_is_usable(
        "a physicist and chemist known for research on radioactivity", target="marie curie"
    ) is True


def test_research_summary_is_usable_rejects_too_few_content_words():
    assert A._research_summary_is_usable("a person", target="marie curie") is False


# ---- _broadcast_poedex_result: the critical provisional short-circuit ----

class _FakeMemory:
    def __init__(self):
        self.facts = []

    def learn_fact(self, fact, source="", confidence=0.5):
        self.facts.append(fact)


def test_broadcast_provisional_true_does_not_commit_to_memory():
    memory = _FakeMemory()
    systems = {"conversation_memory": memory}

    packet = A._broadcast_poedex_result(
        systems,
        concept="marie curie",
        request_text="who was marie curie",
        result_text="a physicist and chemist known for radioactivity research",
        provisional=True,
    )

    assert packet.get("result")
    assert memory.facts == [], "provisional=True must not commit to conversation_memory"
    assert systems.get("_last_research_observation", {}).get("provisional") is True


def test_broadcast_provisional_false_commits_to_memory_as_before():
    memory = _FakeMemory()
    systems = {"conversation_memory": memory}

    A._broadcast_poedex_result(
        systems,
        concept="marie curie",
        request_text="who was marie curie",
        result_text="a physicist and chemist known for radioactivity research",
        provisional=False,
    )

    assert len(memory.facts) == 1, "provisional=False (default) must keep the established immediate commit"


# ---- research reapplication build/apply/render ----

def test_build_research_reapplication_produces_recontextualized_text():
    evidence = [{
        "title": "Aurora grounding: marie curie",
        "url": "",
        "snippet": "a physicist and chemist known for pioneering research on radioactivity",
        "source": "local_grounding",
    }]
    context = A._build_research_reapplication(
        user_text="Who was Marie Curie?",
        target="marie curie",
        evidence=evidence,
    )
    assert context.get("target") == "marie curie"
    assert context.get("provisional") is True
    assert "marie curie" in context.get("recontextualized_text", "").lower()


def test_apply_research_reapplication_to_state_merges_topic_words():
    import types
    state = types.SimpleNamespace(
        parsed={"topic_words": ["marie"], "entities": []},
        pipeline_state={},
    )
    context = {
        "target": "marie curie",
        "summary": "a physicist and chemist known for pioneering research on radioactivity",
        "evidence": [],
        "source": "poedex",
        "gap_type": "factual",
        "recontextualized_text": "Who was Marie Curie? marie curie means a physicist and chemist",
    }
    systems = {}
    A._apply_research_reapplication_to_state("Who was Marie Curie?", systems, state, context)

    assert "marie curie" in state.parsed["topic_words"]
    assert state.parsed["research_reapplied"] is True
    assert state.pipeline_state["research_reapplication"]["target"] == "marie curie"
    assert systems["_last_research_reapplication"]["provisional"] is True


def test_render_reapplied_research_claim_for_a_question_uses_summary_directly():
    import types
    state = types.SimpleNamespace(
        parsed={"topic_words": ["marie", "curie"]},
        pipeline_state={
            "research_reapplication": {
                "target": "marie curie",
                "summary": "a physicist and chemist known for pioneering research on radioactivity",
            }
        },
    )
    claim = A._render_reapplied_research_claim("Who was Marie Curie?", {}, state)
    assert "radioactivity" in claim.lower() or "physicist" in claim.lower()


def test_render_reapplied_research_claim_empty_without_usable_summary():
    import types
    state = types.SimpleNamespace(parsed={}, pipeline_state={"research_reapplication": {}})
    assert A._render_reapplied_research_claim("Who was Marie Curie?", {}, state) == ""


# ---- real live-boot verification ----

def test_real_boot_public_question_and_private_question_do_not_crash():
    """Real end-to-end confirmation: a public-fact question and a
    private-context question must both produce real responses without
    crashing the live pipeline now that the gap research router and its
    provisional-evidence dependency are wired in."""
    import shutil
    import tempfile

    scratch = tempfile.mkdtemp(prefix="aurora_gap_research_router_boot_")
    try:
        scratch_state = os.path.join(scratch, "aurora_state")
        shutil.copytree(os.path.join(REPO_ROOT, "aurora_state"), scratch_state)
        systems = A.boot_aurora(state_dir=scratch_state)

        r1 = A.process_external_user_turn(systems, "Who was Marie Curie?")
        assert r1, "live turn produced no result for a public factual question"

        r2 = A.process_external_user_turn(systems, "why did that matter to me?")
        assert r2, "live turn produced no result for a private-context question"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
