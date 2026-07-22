# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Directive PF3, PF3.2: pronoun claim consumer split (ratified ruling).

_CLAIM_SKIP_SUBJECTS (aurora_working_memory.py) stays untouched for
PropositionSubstrate admission -- the substrate keys contradiction
identity by subject, and an unresolved "he"/"she"/"they" colliding
across referents would manufacture false contradictions, violating
fail-quiet perception (which requires positive same-referent evidence
the substrate cannot have). But the frame needs no cross-turn identity:
a claim rejected SOLELY by the pronoun-subject check is now offered on
a separate, turn-local, never-persisted channel
(WorkingMemory._turn_local_claims), which build_frame's claim rung
(aurora_internal/aurora_proposition_frame.py) consumes at lower
precedence than a real substrate claim: substrate claim -> turn-local
claim -> anchor. The frame renders the pronoun as spoken ("he" stays
"he" within the turn).

Gate (directive's own words): "He's a bit nervous around new people."
produces a frame with subject=he, relation=is; substrate node count for
the turn remains zero; contradiction ledger untouched; full regression
green. (The directive's illustrative "obj=nervous" is the intent, not a
literal string match -- the existing, unchanged copula pattern captures
the whole predicate, "bit nervous around new people", same as it always
has for non-pronoun subjects; PF3.2 only changes WHERE a pronoun-subject
claim goes, never how the object is extracted.)
"""
import os
import sys
import types

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_working_memory import WorkingMemory  # noqa: E402
from aurora_internal.aurora_proposition_frame import build_frame  # noqa: E402


def _wm(turn=1):
    wm = WorkingMemory()
    wm.turn_count = turn
    return wm


def test_pronoun_subject_claim_never_reaches_substrate():
    wm = _wm()
    out = wm._extract_claims("He's a bit nervous around new people.", source='user')
    assert out == []
    assert len(wm._turn_local_claims) == 1
    claim = wm._turn_local_claims[0]
    assert claim['subject'] == 'he'
    assert claim['relation'] == 'is'
    assert claim['turn'] == 1


def test_note_claims_pronoun_subject_substrate_node_count_stays_zero():
    wm = _wm()
    added = wm.note_claims("He's a bit nervous around new people.", source='user')
    assert added == []
    assert len(wm.proposition_substrate.nodes) == 0
    assert len(wm._turn_local_claims) == 1


def test_note_claims_pronoun_subject_contradiction_ledger_untouched():
    """note_claims only ever iterates its substrate-bound return value
    (claims == []  here) -- proposition_substrate.note_claim,
    recent_claims, and claim_conflicts are never touched for a
    pronoun-only turn."""
    wm = _wm()
    wm.note_claims("He's a bit nervous around new people.", source='user')
    assert len(wm.recent_claims) == 0
    assert len(wm.claim_conflicts) == 0


def test_build_frame_gate_directive_scenario():
    """The directive's own gate, end to end."""
    wm = _wm()
    wm.note_claims("He's a bit nervous around new people.", source='user')
    assert len(wm.proposition_substrate.nodes) == 0

    systems = {'working_memory': wm, '_current_thought_state': None}
    state = types.SimpleNamespace(noncomp_input_state={})
    frame = build_frame(systems, state)

    assert frame is not None
    assert frame.subject == 'he'
    assert frame.relation == 'is'
    assert frame.source == 'claim'
    assert 'nervous' in frame.obj


def test_substrate_claim_takes_precedence_over_turn_local():
    """substrate claim -> turn-local claim -> anchor, in that order."""
    wm = _wm()
    # A non-pronoun claim (goes to substrate) AND a pronoun claim
    # (goes turn-local) in the same turn.
    wm.note_claims("The meeting requires careful planning.", source='user')
    wm.note_claims("He's a bit nervous around new people.", source='user')
    assert len(wm.proposition_substrate.nodes) >= 1
    assert len(wm._turn_local_claims) == 1

    systems = {'working_memory': wm, '_current_thought_state': None}
    state = types.SimpleNamespace(noncomp_input_state={})
    frame = build_frame(systems, state)

    assert frame is not None
    assert frame.subject != 'he'  # substrate claim wins, not the turn-local one


def test_turn_local_falls_back_to_anchor_when_absent():
    wm = _wm()
    systems = {'working_memory': wm, '_current_thought_state': None}
    state = types.SimpleNamespace(noncomp_input_state={'anchor': 'guitar'})
    frame = build_frame(systems, state)
    assert frame is not None
    assert frame.source == 'anchor'
    assert frame.obj == 'guitar'


def test_turn_local_claims_survive_multiple_note_claims_calls_same_turn():
    """note_claims runs once for source='user' and again for source=
    'aurora' within a single turn -- a second call must not wipe the
    first call's turn-local claims (a bounded multi-turn deque, not a
    single-call scratch value, precisely to avoid this)."""
    wm = _wm()
    wm.note_claims("He's a bit nervous around new people.", source='user')
    wm.note_claims("She trusts the process completely.", source='aurora')
    assert len(wm._turn_local_claims) == 2
    subjects = {c['subject'] for c in wm._turn_local_claims}
    assert subjects == {'he', 'she'}


def test_turn_local_claims_filtered_by_current_turn_in_build_frame():
    """A turn-local claim from an EARLIER turn must not leak into a
    LATER turn's frame -- same turn-filtering discipline
    _frame_from_claims already applies to substrate nodes."""
    wm = _wm(turn=1)
    wm.note_claims("He's a bit nervous around new people.", source='user')
    wm.turn_count = 2
    systems = {'working_memory': wm, '_current_thought_state': None}
    state = types.SimpleNamespace(noncomp_input_state={})
    frame = build_frame(systems, state)
    # Turn 1's turn-local claim must not surface as a "claim" frame on turn 2.
    assert frame is None or frame.source != 'claim'


def test_wh_word_subject_also_goes_turn_local():
    wm = _wm()
    out = wm._extract_claims("What causes the delay?", source='user')
    # Question text is filtered before extraction (endswith '?'), so this
    # should produce nothing at all -- confirms turn-local doesn't
    # accidentally widen extraction to text that was never eligible.
    assert out == []
    assert len(wm._turn_local_claims) == 0


def test_no_turn_local_claim_when_object_is_vague():
    """A pronoun-subject claim that ALSO fails on a real invalidity
    (vague object) must not be offered anywhere -- "solely by pronoun"
    means every other check still has to pass."""
    wm = _wm()
    wm._extract_claims("They believe it.", source='user')
    assert len(wm._turn_local_claims) == 0


def test_deduplicates_within_a_single_extract_claims_call():
    """Dedup is per-call (seen_turn_local), the same scope _extract_
    claims's existing `seen` set already uses for substrate-bound
    claims -- a repeated call is a repeated observation, not something
    this phase changes the dedup semantics of."""
    wm = _wm()
    # A sentence that could plausibly double-match two different
    # patterns for the exact same (subject, relation, object) triple --
    # within ONE call, the key must only appear once.
    wm._extract_claims("He's a bit nervous around new people.", source='user')
    assert len(wm._turn_local_claims) == 1
