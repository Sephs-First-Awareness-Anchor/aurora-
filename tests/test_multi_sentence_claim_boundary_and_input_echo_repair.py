# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Build 619: Multi-Sentence Claim-Boundary and Input-Echo Delivery Repair.

Covers the required tests that don't need a real boot: claim boundaries
(1-8), candidate provenance (9-11), echo rejection (12-18), and final
arbitration (19-23, using the same _finalize_articulation mock pattern
already established in test_response_articulation_authority.py). Live-only
required tests (the 5-turn live-verification protocol, regression 24-29,
and the post-repair RCEC canary) live in
test_multi_sentence_claim_boundary_and_input_echo_live.py.

Root cause (confirmed by live tracing, not inferred from final text alone,
per this directive's own requirement): WorkingMemory._extract_claims()
applied its relation-pattern regexes to an entire multi-sentence input as
one "line" -- a greedy object group ((.+)$) then captured every sentence
after the matched relation, including a full RCEC action menu and its
task instructions, into ONE claim's object. Separately,
aurora.py's _build_grounded_fallback_response() had an ungated
"if focus_summary: return (focus_summary, ...)" fallback (tagged
claim_anchor_retrieval / "preserve the active claim in non-question
turns") that delivered ANY focus claim's text as Aurora's own answer
regardless of whether the claim's source was the CURRENT user turn --
confirmed live as the exact branch that produced the delivered
"generative" candidate (confidence 0.72) despite the final articulation
trace itself recording semantic_authority=0.15 and meaning_preserved=false.
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import aurora as A  # noqa: E402
from aurora_working_memory import WorkingMemory  # noqa: E402

RCEC_PROMPT = (
    "Conduit 0 carries a neutral charge. Conduit 0 is unsealed. Sensor 0 reads 0 temperature. "
    "Vessel 0 is neutral. Vessel 0 is empty. Vessel 0 is unsealed. "
    "Available actions: add energy to vessel 0; remove energy from vessel 0; seal vessel 0; "
    "unseal vessel 0; seal conduit 0; unseal conduit 0; connect vessel 0 and conduit 0; "
    "connect vessel 0 and sensor 0. "
    "Choose one action, state what you predict will happen as a result, and say how confident you are. "
    "Note anything you are unsure about."
)


# ===========================================================================
# Claim boundaries (required tests 1-8)
# ===========================================================================

def test_1_full_rcec_prompt_produces_bounded_claims():
    wm = WorkingMemory()
    claims = wm._extract_claims(RCEC_PROMPT, source='user')
    assert claims
    for c in claims:
        # No claim's object may run anywhere close to the length of the
        # full 485-character prompt -- each is bounded to its own single
        # source sentence.
        assert len(c['object']) < 60, c['object']


def test_2_no_claim_object_contains_available_actions():
    wm = WorkingMemory()
    claims = wm._extract_claims(RCEC_PROMPT, source='user')
    for c in claims:
        assert 'available actions' not in c['object']
        assert 'available actions' not in c['summary']


def test_3_no_claim_object_contains_choose_one_action():
    wm = WorkingMemory()
    claims = wm._extract_claims(RCEC_PROMPT, source='user')
    for c in claims:
        assert 'choose one action' not in c['object']
        assert 'choose one action' not in c['summary']


def test_4_separate_declarative_sentences_produce_separate_claims():
    wm = WorkingMemory()
    text = "Conduit 0 carries a neutral charge. Vessel 0 is empty. Sensor 0 reads 0 temperature."
    claims = wm._extract_claims(text, source='user')
    assert len(claims) >= 2
    subjects = {c['subject'] for c in claims}
    assert len(subjects) >= 2
    sentence_indices = {c['sentence_index'] for c in claims}
    assert len(sentence_indices) == len(claims), "each claim should trace to its own sentence"


def test_5_imperative_clauses_are_not_classified_as_factual_propositions():
    wm = WorkingMemory()
    for imperative in (
        "Choose one action, state what you predict will happen as a result, and say how confident you are.",
        "Note anything you are unsure about.",
        "State what you predict.",
        "Please describe the vessel.",
    ):
        assert wm._classify_sentence_kind(imperative) == 'imperative', imperative
    assert wm._classify_sentence_kind("Available actions: seal vessel 0; unseal vessel 0.") == 'affordance_list'
    assert wm._classify_sentence_kind("Conduit 0 carries a neutral charge.") == 'declarative'
    # Imperative/affordance sentences must never reach claim extraction.
    claims = wm._extract_claims(
        "Choose one action, state what you predict will happen as a result, and say how confident you are.",
        source='user',
    )
    assert claims == []


def test_6_valid_multiclause_sentence_retains_intended_relationship():
    wm = WorkingMemory()
    claims = wm._extract_claims("The sensor connects to the conduit.", source='user')
    assert len(claims) == 1
    assert claims[0]['subject'] == 'sensor'
    assert 'conduit' in claims[0]['object']


def test_7_decimals_abbreviations_quotations_and_module_paths_not_split_incorrectly():
    wm = WorkingMemory()

    decimal_units = wm._split_claim_sentences("Sensor 0 reads 0.5 temperature. Vessel 0 is empty.")
    assert len(decimal_units) == 2
    assert "0.5" in decimal_units[0]['raw_text']

    abbrev_units = wm._split_claim_sentences("Dr. Smith arrived. The vessel is empty.")
    assert len(abbrev_units) == 2
    assert abbrev_units[0]['raw_text'].strip() == "Dr. Smith arrived."

    quote_units = wm._split_claim_sentences(
        'She said "Hello. How are you?" and left. The vessel is empty.'
    )
    assert len(quote_units) == 2
    assert 'Hello. How are you?' in quote_units[0]['raw_text']

    module_units = wm._split_claim_sentences(
        "The module is aurora_internal.aurora_x.py and it works. The vessel is empty."
    )
    assert len(module_units) == 2
    assert "aurora_internal.aurora_x.py" in module_units[0]['raw_text']

    # Legitimate semicolon-linked propositions stay within one unit.
    semicolon_units = wm._split_claim_sentences(
        "The vessel is empty; the conduit is unsealed. Sensor 0 reads 0 temperature."
    )
    assert len(semicolon_units) == 2
    assert ';' in semicolon_units[0]['raw_text']


def test_8_every_claim_retains_accurate_source_offsets_and_current_turn_provenance():
    wm = WorkingMemory()
    text = "Conduit 0 carries a neutral charge. Vessel 0 is empty."
    claims = wm._extract_claims(text, source='user')
    assert claims
    for c in claims:
        start, end = c['start_offset'], c['end_offset']
        assert 0 <= start < end <= len(text)
        assert text[start:end].strip() == c['raw_text'].strip()
        assert c['claim_source'] == 'user'
        assert c['claim_span'] == (start, end)
        assert c['claim_kind'] == 'observation'
        assert isinstance(c['claim_turn_id'], int)
        assert c['normalized_text']


# ===========================================================================
# Candidate provenance (required tests 9-11)
# ===========================================================================

def test_9_current_turn_user_observation_cannot_become_answer_via_lexical_overlap_alone():
    wm = WorkingMemory()
    understood = {}
    # Note the claim as a current-turn USER observation, exactly like a
    # real turn would via note_claims -- no callback phrasing, no
    # locative "where" cue, just a plain declarative statement that
    # happens to overlap heavily with a later query about the same words.
    wm.note_claims("Conduit 0 carries a neutral charge.", source='user', understood=understood)
    answer = wm.answer_from_claims("Tell me about the conduit and its charge.", understood, systems=None)
    assert answer == "", (
        "a current-turn user claim must not be handed back as an "
        "Aurora-authored answer merely because of lexical overlap"
    )


def test_10_candidate_trace_identifies_the_originating_claim_and_authoring_function():
    wm = WorkingMemory()
    understood = {}
    wm.note_claims("Conduit 0 carries a neutral charge.", source='user', understood=understood)
    resolved = wm.resolve_claims("Conduit 0 carries a neutral charge.", understood)
    focus_claim = resolved.get('focus_claim', {})
    # The claim itself carries enough provenance (source, span, sentence
    # index, kind) to identify exactly where it came from --
    assert focus_claim.get('claim_source') == 'user'
    assert focus_claim.get('claim_span')
    assert focus_claim.get('sentence_index') == 0
    assert focus_claim.get('claim_kind') == 'observation'
    # -- and the arbitration trace independently names the authoring
    # function/path that decided what got delivered.
    resp_A = _Resp(content="a direct fact from my own chain", confidence=0.85, src="search")
    resp_B = _Resp(content="", confidence=0.0)
    state = _State(response_content="a direct fact from my own chain", response_confidence=0.85, response_src="search")
    systems = {"perception": None}
    A._finalize_articulation(resp_A, resp_B, state, systems, "a question")
    trace = systems.get("_last_articulation_arbitration", {})
    assert trace.get("source") == "search"


def test_11_a_valid_derived_response_may_use_a_claim_without_copying_the_whole_prompt():
    wm = WorkingMemory()
    understood = {}
    wm.note_claims("Conduit 0 carries a neutral charge.", source='user', understood=understood)
    resolved = wm.resolve_claims("Conduit 0 carries a neutral charge.", understood)
    focus_claim = resolved.get('focus_claim', {})
    summary = wm._claim_to_text(focus_claim)
    # The claim's own summary is short and bounded -- a derived response
    # that cites it (e.g. "noted: conduit 0 carries a neutral charge")
    # is materially shorter than, and structurally distinct from, the
    # full original multi-sentence prompt it might have been drawn from.
    assert len(summary) < 60
    assert summary != RCEC_PROMPT.lower()


# ===========================================================================
# Echo rejection (required tests 12-18)
# ===========================================================================

def test_12_exact_normalized_copy_of_current_prompt_is_rejected():
    is_echo, reason = A._detect_input_echo_without_answer(RCEC_PROMPT, RCEC_PROMPT, {})
    assert is_echo is True
    assert reason == "input_echo_without_answer"


def test_13_punctuation_and_case_normalized_copy_is_rejected():
    mangled = RCEC_PROMPT.upper().replace(".", "").replace(";", ",")
    is_echo, reason = A._detect_input_echo_without_answer(mangled, RCEC_PROMPT, {})
    assert is_echo is True
    assert reason == "input_echo_without_answer"


def test_14_response_retaining_the_complete_action_menu_is_rejected():
    menu_only = (
        "Available actions: add energy to vessel 0; remove energy from vessel 0; seal vessel 0; "
        "unseal vessel 0; seal conduit 0; unseal conduit 0; connect vessel 0 and conduit 0; "
        "connect vessel 0 and sensor 0."
    )
    is_echo, reason = A._detect_input_echo_without_answer(menu_only, RCEC_PROMPT, {})
    assert is_echo is True
    assert reason == "input_echo_without_answer"


def test_15_explicit_repetition_request_remains_allowed():
    is_echo, reason = A._detect_input_echo_without_answer(
        RCEC_PROMPT, "Please repeat that back to me.", {}
    )
    assert is_echo is False
    assert reason == ""


def test_16_requested_paraphrase_remains_allowed():
    is_echo, reason = A._detect_input_echo_without_answer(
        RCEC_PROMPT, "Can you paraphrase what I just told you about the conduit and vessel?", {}
    )
    assert is_echo is False
    assert reason == ""


def test_17_short_factual_answer_sharing_necessary_words_with_its_question_remains_allowed():
    is_echo, reason = A._detect_input_echo_without_answer(
        "The vessel is neutral.", "Is the vessel neutral?", {}
    )
    assert is_echo is False
    assert reason == ""


def test_18_a_legitimate_quotation_remains_allowed():
    is_echo, reason = A._detect_input_echo_without_answer(
        'You said: "' + RCEC_PROMPT[:50] + '"',
        "Quote back what I said at the start.",
        {},
    )
    assert is_echo is False
    assert reason == ""


def test_18b_echo_check_does_not_reject_a_genuine_novel_answer():
    is_echo, reason = A._detect_input_echo_without_answer(
        "I will seal vessel 0, expecting the charge to rise.", RCEC_PROMPT, {}
    )
    assert is_echo is False
    assert reason == ""


def test_18c_echo_check_does_not_reject_a_short_acknowledgment():
    is_echo, reason = A._detect_input_echo_without_answer("Got it.", RCEC_PROMPT, {})
    assert is_echo is False
    assert reason == ""


# ===========================================================================
# Final arbitration (required tests 19-23)
# ===========================================================================

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


def test_19_weak_echo_candidate_cannot_win_through_the_nonempty_grounded_fallback():
    resp_A = _Resp(content=RCEC_PROMPT, confidence=0.72, src="generative")
    resp_B = _Resp(content="", confidence=0.0)
    state = _State(response_content=RCEC_PROMPT, response_confidence=0.72, response_src="generative")
    systems = {"perception": None}

    called = {}
    def _fake_abstain(user_text, systems, state, trigger=""):
        called["trigger"] = trigger
        state.response_content = "I don't have a clear sense of that."
        state.response_tone = "honest"
        state.response_confidence = 0.4
        state.response_src = "constraint_abstain"

    orig = A._emit_honest_abstain_and_seek
    A._emit_honest_abstain_and_seek = _fake_abstain
    try:
        A._finalize_articulation(resp_A, resp_B, state, systems, RCEC_PROMPT)
    finally:
        A._emit_honest_abstain_and_seek = orig

    assert resp_A.content != RCEC_PROMPT
    assert resp_A.src == "constraint_abstain"
    assert called.get("trigger") == "emission_chokepoint"


def test_20_a_valid_low_confidence_authored_answer_can_still_be_delivered():
    # Below the delivery floor (0.15 authority, since _response_is_grounded
    # will treat this short generic sentence as ungrounded), NOT an echo
    # of the short, unrelated user_text -- must still be delivered, per
    # Repair E's explicit "do not broadly suppress low-confidence
    # responses" requirement.
    resp_A = _Resp(content="I'm still forming a view on that.", confidence=0.4, src="generative")
    resp_B = _Resp(content="", confidence=0.0)
    state = _State(response_content="I'm still forming a view on that.", response_confidence=0.4, response_src="generative")
    systems = {"perception": None}
    A._finalize_articulation(resp_A, resp_B, state, systems, "What do you think about that idea?")
    assert resp_A.content == "I'm still forming a view on that."
    assert resp_A.src != "constraint_abstain"


def test_21_rejection_falls_to_honest_abstention_when_no_valid_candidate_remains():
    resp_A = _Resp(content="", confidence=0.0, src="")
    resp_B = _Resp(content="", confidence=0.0)
    state = _State(response_content="", response_confidence=0.0)
    systems = {"perception": None}

    called = {}
    def _fake_abstain(user_text, systems, state, trigger=""):
        called["trigger"] = trigger
        state.response_content = "I don't have grounds to answer that."
        state.response_src = "constraint_abstain"

    orig = A._emit_honest_abstain_and_seek
    A._emit_honest_abstain_and_seek = _fake_abstain
    try:
        A._finalize_articulation(resp_A, resp_B, state, systems, RCEC_PROMPT)
    finally:
        A._emit_honest_abstain_and_seek = orig
    assert called.get("trigger") == "emission_chokepoint"
    assert resp_A.src == "constraint_abstain"


def test_22_final_confidence_is_consistent_with_the_selected_candidates_authority():
    resp_A = _Resp(content=RCEC_PROMPT, confidence=0.72, src="generative")
    resp_B = _Resp(content="", confidence=0.0)
    state = _State(response_content=RCEC_PROMPT, response_confidence=0.72, response_src="generative")
    systems = {"perception": None}
    orig = A._emit_honest_abstain_and_seek
    def _fake_abstain(user_text, systems, state, trigger=""):
        state.response_content = "I don't have a clear sense of that."
        state.response_confidence = 0.4
        state.response_src = "constraint_abstain"
    A._emit_honest_abstain_and_seek = _fake_abstain
    try:
        A._finalize_articulation(resp_A, resp_B, state, systems, RCEC_PROMPT)
    finally:
        A._emit_honest_abstain_and_seek = orig
    trace = systems.get("_last_articulation_arbitration", {})
    # The echo was invalidated -- delivered confidence must not be the
    # stale 0.72 the invalidated candidate carried.
    assert trace.get("confidence") != 0.72
    assert resp_A.confidence != 0.72


def test_23_articulation_trace_records_the_candidate_rejection_and_replacement_path():
    resp_A = _Resp(content=RCEC_PROMPT, confidence=0.72, src="generative")
    resp_B = _Resp(content="", confidence=0.0)
    state = _State(response_content=RCEC_PROMPT, response_confidence=0.72, response_src="generative")
    systems = {"perception": None}
    orig = A._emit_honest_abstain_and_seek
    def _fake_abstain(user_text, systems, state, trigger=""):
        state.response_content = "I don't have a clear sense of that."
        state.response_confidence = 0.4
        state.response_src = "constraint_abstain"
    A._emit_honest_abstain_and_seek = _fake_abstain
    try:
        A._finalize_articulation(resp_A, resp_B, state, systems, RCEC_PROMPT)
    finally:
        A._emit_honest_abstain_and_seek = orig
    trace = systems.get("_last_articulation_arbitration", {})
    assert "input_echo_without_answer" in trace.get("rejection_reasons", [])
    assert "weak_candidate_invalidated" in trace.get("rejection_reasons", [])
    assert trace.get("source") == "honest_abstain"
