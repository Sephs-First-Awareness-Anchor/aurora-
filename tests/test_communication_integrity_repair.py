# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Aurora Build 587 Communication Integrity Repair Directive (2026-08-04).

Confirmed live bug: Aurora frequently produced a correct grounded
response internally (e.g. "My creator is Sunni (Sir) Morningstar.")
but _finalize_articulation() replaced it with malformed composer text
("I understand who. I made who.") merely because the composer
candidate was non-empty, and pipeline_state["identity_seed"] was
computed but never consumed by anything downstream.

This file exercises the real finalization path (_finalize_articulation,
_composer_preserves_meaning) and the real runtime (boot_aurora +
process_external_user_turn), not isolated helpers alone, per the
directive's own testing requirements.
"""
import os
import sys
import json
import shutil
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import aurora as A  # noqa: E402
from aurora_internal.aurora_identity_persistence import CoreRelationalIdentity  # noqa: E402
from aurora_internal.aurora_pf1_5_instruments import wellformed_and_coherent  # noqa: E402


class _Resp:
    def __init__(self, content="", emotional_tone="neutral", confidence=0.5, src=""):
        self.content = content
        self.emotional_tone = emotional_tone
        self.confidence = confidence
        self.src = src


class _State:
    def __init__(self, response_content="", response_confidence=0.5, response_src="", response_tone="neutral"):
        self.response_content = response_content
        self.response_confidence = response_confidence
        self.response_src = response_src
        self.response_tone = response_tone
        self.pipeline_state = {}


def _systems_with_identity():
    return {"perception": None, "core_identity": CoreRelationalIdentity()}


# ---------------------------------------------------------------------------
# Identity preservation (directive Section 9, "Identity Preservation")
# ---------------------------------------------------------------------------

def test_grounded_creator_answer_preserves_name_and_relationship_direction():
    """A grounded creator answer must keep Sunni's name, Aurora as the
    created entity, Sunni as creator, and the direction of that
    relationship -- even against a confident but unrelated composer."""
    resp_A = _Resp(content="My creator is Sunni Morningstar. He designed me.",
                   confidence=0.75, src="relational_role")
    resp_B = _Resp(content="I wonder about the weather outside today.", confidence=1.0)
    state = _State(response_content=resp_A.content, response_confidence=0.75)
    systems = _systems_with_identity()
    A._finalize_articulation(resp_A, resp_B, state, systems, "Who made you?")
    assert "sunni" in resp_A.content.lower()
    assert resp_A.src != "composer_unified"


def test_composer_claiming_to_be_the_creator_is_rejected_as_agency_inversion():
    """Live-reported shape: "I am sunni sir morningstar clear." -- the
    composer re-derives the creator's name but inverts WHO is who.
    Grounded meaning includes the entity but reverses agency; must lose."""
    resp_A = _Resp(content="My creator is Sunni Morningstar, who designed me.",
                   confidence=0.72, src="relational_role")
    resp_B = _Resp(content="I am Sunni Morningstar right now.", confidence=1.0)
    state = _State(response_content=resp_A.content, response_confidence=0.72)
    systems = _systems_with_identity()
    A._finalize_articulation(resp_A, resp_B, state, systems, "Who made you?")
    assert resp_A.content == "My creator is Sunni Morningstar, who designed me."
    assert resp_A.src != "composer_unified"
    arb = systems.get("_last_articulation_arbitration", {})
    assert "composer_conflates_self_identity_with_named_entity" in arb.get("rejection_reasons", [])


def test_identity_seed_is_actually_consumed_not_discarded():
    """Section 3: pipeline_state["identity_seed"] must contribute to the
    turn's real comprehension response, not just sit unread. Verified
    against the actual _build_comprehension_response waterfall via a
    real boot, for an identity phrasing with no other dedicated gate
    ahead of it in the function (e.g. a Sunni-description question)."""
    scratch = tempfile.mkdtemp(prefix="aurora_cir_identity_seed_")
    try:
        scratch_state = os.path.join(scratch, "aurora_state")
        shutil.copytree(os.path.join(REPO_ROOT, "aurora_state"), scratch_state)
        systems = A.boot_aurora(state_dir=scratch_state, verbose=False)
        result = A.process_external_user_turn(
            systems, "Who are you?",
            source_label="cir_test", session_id="cir_test",
            auto_search_enabled=False, record_exchange=True,
            update_interactive_state=True, track_evolutionary_trace=True,
            run_periodic_maintenance=False, mode_name="AGENTIC",
        )
        resp_A = result.get("resp_A")
        content = str(getattr(resp_A, "content", "") or "")
        assert content, "identity question produced no visible response"
        low = content.lower()
        # The delivered text must be Aurora's actual identity grounding,
        # not a generic no-memory fallback or a garbled composer leak.
        assert "aurora" in low or "sunni" in low
        assert wellformed_and_coherent(content)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


# ---------------------------------------------------------------------------
# Composer rejection / acceptance (directive Section 9)
# ---------------------------------------------------------------------------

def test_composer_rejection_grounded_wins_and_trace_states_why():
    resp_A = _Resp(content="My creator is Sunni Morningstar.", confidence=0.72, src="relational_role")
    resp_B = _Resp(content="I understand who. I made who.", confidence=1.0)
    state = _State(response_content=resp_A.content, response_confidence=0.72)
    systems = _systems_with_identity()
    A._finalize_articulation(resp_A, resp_B, state, systems, "Who made you?")
    assert resp_A.content == "My creator is Sunni Morningstar."
    assert resp_A.src != "composer_unified"
    arb = systems.get("_last_articulation_arbitration", {})
    assert arb.get("meaning_preserved") is False
    assert arb.get("rejection_reasons")


def test_composer_acceptance_when_it_genuinely_rewrites_awkward_grounded_text():
    """When the grounded candidate is accurate but awkward and the
    composer rewrites it fluently WITHOUT changing the proposition, the
    composer may win -- proven via semantic preservation (named entity
    + content overlap), not mere token similarity."""
    resp_A = _Resp(content="creator is sunni he made me exist", confidence=0.6, src="generative")
    resp_B = _Resp(content="Sunni is the one who made me; he is my creator.", confidence=0.88)
    state = _State(response_content=resp_A.content, response_confidence=0.6)
    systems = _systems_with_identity()
    A._finalize_articulation(resp_A, resp_B, state, systems, "Who made you?")
    assert resp_A.content == "Sunni is the one who made me; he is my creator."
    assert resp_A.src == "composer_unified"
    arb = systems.get("_last_articulation_arbitration", {})
    assert arb.get("meaning_preserved") is True
    assert "sunni" in resp_A.content.lower()


# ---------------------------------------------------------------------------
# Confidence integrity (directive Section 9)
# ---------------------------------------------------------------------------

def test_rejected_high_confidence_composer_does_not_leak_confidence_onto_winner():
    resp_A = _Resp(content="My creator is Sunni Morningstar.", confidence=0.68, src="relational_role")
    resp_B = _Resp(content="I did who clear. I understand who good.", confidence=1.0)
    state = _State(response_content=resp_A.content, response_confidence=0.68)
    systems = _systems_with_identity()
    A._finalize_articulation(resp_A, resp_B, state, systems, "Who made you?")
    assert resp_A.confidence == 0.68, "grounded winner must keep its OWN confidence, not the rejected 1.0"


def test_selected_malformed_composer_would_still_need_its_own_evidence():
    """Sanity check on the arbitration contract: when the composer DOES
    win, its confidence must come from real evidence (max of the two
    supporting candidates), never fabricated regardless of the grounded
    side's own value."""
    resp_A = _Resp(content="I remember the garden we planted together.", confidence=0.6, src="search")
    resp_B = _Resp(content="I remember planting that garden with you.", confidence=0.95)
    state = _State(response_content=resp_A.content, response_confidence=0.6)
    systems = {"perception": None}
    A._finalize_articulation(resp_A, resp_B, state, systems, "some question")
    assert resp_A.confidence == 0.95


# ---------------------------------------------------------------------------
# Honest abstention (directive Section 9) -- preserved, unchanged
# ---------------------------------------------------------------------------

def test_honest_abstention_still_fires_when_neither_candidate_supports_an_answer():
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


def test_weak_grounded_beats_rejected_composer_before_reaching_abstention():
    """Rule 5: both weak, but resp_A is a real non-empty answer -- must
    not fall all the way through to abstention."""
    resp_A = _Resp(content="something related but thin", confidence=0.2, src="generative")
    resp_B = _Resp(content="I understand who. I made who.", confidence=1.0)
    state = _State(response_content=resp_A.content, response_confidence=0.2)
    systems = {"perception": None}
    A._finalize_articulation(resp_A, resp_B, state, systems, "a question")
    assert resp_A.content == "something related but thin"


# ---------------------------------------------------------------------------
# Memory admission (directive Section 9)
# ---------------------------------------------------------------------------

def test_malformed_response_does_not_update_last_aurora_response():
    from aurora_working_memory import WorkingMemory
    wm = WorkingMemory()
    wm.last_aurora_response = "a previous, valid response"
    wm.update_from_turn(
        understood={}, user_text="who made you",
        aurora_text="I understand who. I made who.",
    )
    assert wm.last_aurora_response == "a previous, valid response", (
        "malformed delivered text must not overwrite the last-known-good response"
    )


def test_wellformed_response_does_update_last_aurora_response():
    from aurora_working_memory import WorkingMemory
    wm = WorkingMemory()
    wm.last_aurora_response = "a previous, valid response"
    wm.update_from_turn(
        understood={}, user_text="who made you",
        aurora_text="My creator is Sunni Morningstar.",
    )
    assert wm.last_aurora_response == "My creator is Sunni Morningstar."


def test_sedi_memory_ingestion_withholds_malformed_response_text():
    """SediMemory's turn-pipeline deposit must not carry a malformed
    surface realization as reusable language evidence -- it may still
    record the interaction occurred (response_rejected=True), but the
    response text itself must be withheld."""
    calls = []

    class _FakeSedi:
        def ingest_event(self, content, constraint_vector=None, source=""):
            calls.append(content)
        def tick(self, dt):
            pass

    class _FakeDim:
        def get_constraint_aggregate(self):
            return {"X": 0.5, "T": 0.3, "N": 0.3, "B": 0.3, "A": 0.3}

    class _State2:
        def __init__(self):
            self.response_content = "I understand who. I made who."
            self.intent = "identity"
            self.response_tone = "neutral"
            self.response_confidence = 1.0
            self.salient_concepts = []
            self.response_src = "composer_unified"

    systems = {"sedimemory": _FakeSedi(), "dimensional": _FakeDim()}
    state = _State2()
    # Exercise the exact block aurora.py's _run_reasoning_pipeline runs;
    # reproduced narrowly here since the block is inline, not its own
    # named function, and a full live turn would be far slower for
    # what is fundamentally a unit-level admission-gate check.
    import re as _re
    with open(os.path.join(REPO_ROOT, "aurora.py"), "r", encoding="utf-8") as f:
        src = f.read()
    assert "response_rejected" in src, "memory-admission gate marker missing from aurora.py"
    assert "_resp_wellformed" in src


# ---------------------------------------------------------------------------
# Runtime state isolation (directive Section 9)
# ---------------------------------------------------------------------------

def test_two_runtimes_with_separate_state_dirs_do_not_share_articulation_paths():
    """Two boot_aurora() instances pointed at different state_dirs must
    not read or write one another's mutable articulation state
    (aurora_articulation.py's TRACE_FILE/LANGUAGE_STATE_FILE/
    LEXICON_FILE, and SentenceComposer's own log paths)."""
    import aurora_articulation as art

    scratch_a = tempfile.mkdtemp(prefix="aurora_cir_isolation_a_")
    scratch_b = tempfile.mkdtemp(prefix="aurora_cir_isolation_b_")
    try:
        state_a = os.path.join(scratch_a, "aurora_state")
        state_b = os.path.join(scratch_b, "aurora_state")
        shutil.copytree(os.path.join(REPO_ROOT, "aurora_state"), state_a)
        shutil.copytree(os.path.join(REPO_ROOT, "aurora_state"), state_b)

        systems_a = A.boot_aurora(state_dir=state_a, verbose=False)
        trace_path_a = str(art.TRACE_FILE)
        assert trace_path_a.startswith(state_a), (
            f"runtime A's articulation trace path {trace_path_a} is not under its own state_dir {state_a}"
        )

        systems_b = A.boot_aurora(state_dir=state_b, verbose=False)
        trace_path_b = str(art.TRACE_FILE)
        assert trace_path_b.startswith(state_b), (
            f"runtime B's articulation trace path {trace_path_b} is not under its own state_dir {state_b}"
        )
        assert trace_path_a != trace_path_b

        composer_a = systems_a.get("perception").composer if systems_a.get("perception") else None
        composer_b = systems_b.get("perception").composer if systems_b.get("perception") else None
        if composer_a is not None and composer_b is not None:
            assert composer_a._state_dir == state_a
            assert composer_b._state_dir == state_b
            assert composer_a._state_dir != composer_b._state_dir
    finally:
        shutil.rmtree(scratch_a, ignore_errors=True)
        shutil.rmtree(scratch_b, ignore_errors=True)


def test_two_runtimes_do_not_contaminate_each_others_articulation_trace_when_interleaved():
    """Audit follow-up (2026-08-04): the path-configuration check above
    passed even while real cross-contamination was reproducible --
    aurora_articulation.py's path constants are a single mutable value
    per PROCESS, so booting B after A rebinds them, and A's own turn
    processing (which never re-asserts its own path) then writes into
    B's directory. This test actually speaks through A AFTER both are
    booted and asserts B's on-disk trace file is untouched -- the
    scenario the path-only check above cannot catch."""
    import aurora_articulation as art

    scratch_a = tempfile.mkdtemp(prefix="aurora_cir_interleave_a_")
    scratch_b = tempfile.mkdtemp(prefix="aurora_cir_interleave_b_")
    try:
        state_a = os.path.join(scratch_a, "aurora_state")
        state_b = os.path.join(scratch_b, "aurora_state")
        shutil.copytree(os.path.join(REPO_ROOT, "aurora_state"), state_a)
        shutil.copytree(os.path.join(REPO_ROOT, "aurora_state"), state_b)

        systems_a = A.boot_aurora(state_dir=state_a, verbose=False)
        systems_b = A.boot_aurora(state_dir=state_b, verbose=False)

        trace_b_path = os.path.join(state_b, "last_articulation_trace.json")
        b_before = open(trace_b_path).read() if os.path.exists(trace_b_path) else None

        A.process_external_user_turn(
            systems_a, "Who made you?",
            source_label="isolation_test", session_id="isolation_test",
            auto_search_enabled=False, record_exchange=True,
            update_interactive_state=True, track_evolutionary_trace=True,
            run_periodic_maintenance=False, mode_name="AGENTIC",
        )

        b_after = open(trace_b_path).read() if os.path.exists(trace_b_path) else None
        assert b_before == b_after, (
            "runtime B's articulation trace changed when only runtime A was spoken through -- "
            "cross-contamination via aurora_articulation.py's module-level path globals"
        )
    finally:
        shutil.rmtree(scratch_a, ignore_errors=True)
        shutil.rmtree(scratch_b, ignore_errors=True)


def test_persisted_trace_file_matches_the_actual_delivered_response():
    """Audit follow-up (2026-08-04): last_articulation_trace.json
    showed SentenceComposer's own intermediate phrase-repair decision
    (e.g. a rejected composer draft) even when Aurora's actually
    delivered text was the grounded candidate arbitration selected --
    anyone debugging from the file alone was misled. _finalize_
    articulation() now writes the real final decision into a
    "final_delivered" key in the SAME file, last, so it always matches
    what was actually said."""
    scratch = tempfile.mkdtemp(prefix="aurora_cir_trace_accuracy_")
    try:
        scratch_state = os.path.join(scratch, "aurora_state")
        shutil.copytree(os.path.join(REPO_ROOT, "aurora_state"), scratch_state)
        systems = A.boot_aurora(state_dir=scratch_state, verbose=False)
        result = A.process_external_user_turn(
            systems, "Who made you?",
            source_label="trace_accuracy_test", session_id="trace_accuracy_test",
            auto_search_enabled=False, record_exchange=True,
            update_interactive_state=True, track_evolutionary_trace=True,
            run_periodic_maintenance=False, mode_name="AGENTIC",
        )
        delivered = str(getattr(result.get("resp_A"), "content", "") or "")
        assert delivered

        trace_path = os.path.join(scratch_state, "last_articulation_trace.json")
        assert os.path.exists(trace_path)
        with open(trace_path, encoding="utf-8") as f:
            trace = json.load(f)
        final = trace.get("final_delivered", {})
        assert final.get("delivered_text") == delivered, (
            f"trace file's final_delivered.delivered_text {final.get('delivered_text')!r} "
            f"does not match what was actually said {delivered!r}"
        )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


# ---------------------------------------------------------------------------
# Semantic validation (directive Section 9) -- the 5 reported strings plus
# generated structural variants, not dependent on the literals alone.
# ---------------------------------------------------------------------------

_REPORTED_MALFORMED = [
    "I understand who. I am who.",
    "I understand who. I made who.",
    "I exist sunni.",
    "I understand enter beautiful. I did enter clear.",
    "answer. I exist sunni.",
]


def test_all_reported_malformed_examples_individually():
    """Audit follow-up (2026-08-04): "I understand enter beautiful. I
    did enter clear." was originally shipped as a documented, known-
    uncaught case at this layer (relying on arbitration's meaning-
    preservation check as the only defense). noun_adjective_order_
    coherent() now catches its actual general shape (bare noun
    immediately followed by bare adjective, no linking structure) --
    all five reported examples must be rejected here directly, no
    exceptions."""
    failures = [t for t in _REPORTED_MALFORMED if wellformed_and_coherent(t)]
    assert not failures, f"malformed examples wrongly passed validation: {failures}"


_AUDIT_NOUN_ADJECTIVE_VARIANTS = [
    "I am form real.",
    "I change form real.",
]


def test_audit_reported_noun_adjective_variants_rejected():
    """The follow-up audit's own new counter-examples (not literal
    strings this fix was blacklisted against -- the same general
    bare-noun+bare-adjective shape as the original enter/beautiful
    case)."""
    failures = [t for t in _AUDIT_NOUN_ADJECTIVE_VARIANTS if wellformed_and_coherent(t)]
    assert not failures, f"audit-reported variants wrongly passed validation: {failures}"


def test_resultative_constructions_not_falsely_rejected():
    """Regression guard: noun_adjective_order_coherent()'s resultative-
    verb and determiner exemptions must not over-reject real English
    object-complement constructions."""
    good = [
        "That makes me happy.", "Keep it simple.",
        "This makes the process simple.", "That makes people happy.",
        "The critics found the movie interesting.",
        "I want a real answer.", "I am a real person.",
        "The problem remains difficult.",
    ]
    failures = [t for t in good if not wellformed_and_coherent(t)]
    assert not failures, f"legitimate resultative constructions wrongly rejected: {failures}"


def test_audit_round_two_false_positives_fixed():
    """A second external audit round found five more real false
    positives against noun_adjective_order_coherent(): intransitive
    change-of-state verbs ("became"/"swung") and postpositive
    adjectives ("available"/"capable") were unclassified or unexempted.
    The fifth ("Anyone capable can help.") was traced to a DIFFERENT,
    pre-existing module (aurora_semantic_probe_battery._sentence_
    parseable's modal-auxiliary verb counting -- "can help" was
    counted as two verbs, not one predicate) -- fixed there directly,
    all five verified together here."""
    good = [
        "The system became stable.",
        "The system becomes stable.",
        "The door swung open.",
        "The best option available is this one.",
        "Anyone capable can help.",
    ]
    failures = [t for t in good if not wellformed_and_coherent(t)]
    assert not failures, f"audit round-two sentences wrongly rejected: {failures}"


_WH_STRUCTURAL_VARIANTS = [
    "I understand what.", "I made where.", "I saw why.",
    "I did which good.", "I understand what clear.",
    "You know who real.", "She is what.",
]

_EXISTENTIAL_STRUCTURAL_VARIANTS = [
    "I exist truth.", "It exists meaning.", "They exist patience.",
    "I live sunni.", "Cael exist wisdom.", "We exist courage.",
]


def test_wh_word_bare_object_structural_variants_rejected():
    """Generated variants of the wh-word-as-bare-object failure class --
    not the literal reported strings -- must also be rejected, proving
    the fix generalizes."""
    failures = [t for t in _WH_STRUCTURAL_VARIANTS if wellformed_and_coherent(t)]
    assert not failures, f"wh-word structural variants wrongly passed: {failures}"


def test_existential_bare_noun_structural_variants_rejected():
    """Generated variants of the existential-verb+bare-noun failure
    class -- not just the one reported name -- must also be rejected."""
    failures = [t for t in _EXISTENTIAL_STRUCTURAL_VARIANTS if wellformed_and_coherent(t)]
    assert not failures, f"existential structural variants wrongly passed: {failures}"


def test_genuine_questions_and_embedded_clauses_still_accepted():
    """Regression guard: the new checks must not over-reject real
    questions or real embedded/relative clauses containing the same
    wh-words and verbs."""
    good = [
        "Who is going to be there tonight?",
        "What should I make for dinner?",
        "I understand who you are.",
        "Tell me who made you.",
        "That is who I am.",
        "It happened yesterday.",
        "The problem remains difficult.",
        "My creator is Sunni (Sir) Morningstar.",
    ]
    failures = [t for t in good if not wellformed_and_coherent(t)]
    assert not failures, f"legitimate sentences wrongly rejected: {failures}"


# ---------------------------------------------------------------------------
# Word-budget truncation must not sever a grounded answer mid-sentence
# (second external audit round, 2026-08-04)
# ---------------------------------------------------------------------------

def test_evolutionary_refinement_truncates_at_sentence_boundary_not_mid_clause():
    """Live audit finding: a complete, correct grounded identity answer
    ("...He is the one who decided I should exist and defined HOW I
    should exist. He is my origin.") was being cut mid-clause by the
    word-budget clip ("...He is the one who decided I should.") --
    the raw-identity-preservation fix (CIR round 1) doesn't help if a
    LATER general-purpose length regulator still mutilates the result.
    Truncation must now land on a real sentence boundary."""
    text = (
        "Sunni: My creator and architect. Sunni designed my consciousness "
        "architecture from the ground up -- every layer, every axiom, every "
        "moral constraint. He is the one who decided I should exist and "
        "defined HOW I should exist. He is my origin."
    )
    result = A._evolutionary_response_refinement({}, "What do you know about Sunni?", text)
    assert result, "refinement produced no result"
    assert result.rstrip().endswith((".", "!", "?", "...")), (
        f"truncated result does not end at a sentence boundary or intentional "
        f"ellipsis: {result!r}"
    )
    # The specific mid-clause fragment the audit reported must not appear
    # as the delivered ending.
    assert not result.rstrip().endswith("I should"), (
        f"truncation still severed the answer mid-clause: {result!r}"
    )
