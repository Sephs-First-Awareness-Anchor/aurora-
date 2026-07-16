# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
R1.9.4 Step 3 (narrow-gap branch, 3b): function-word slots in skeleton
learning.

Step 2's honest re-baseline found the gap was overwhelmingly instrument
strictness (mean stratified wellformedness jumped from ~0.03/0.0 to
0.71/0.58 just from Step 1's predicate refinement, no composer change),
comfortably clearing the >=0.35 fork threshold -- so 3a (determiner
insertion) stays shelved and only 3b runs: verify/extend the motif
schema so determiner and preposition slots actually exist to be learned.

Investigation: RoleTagger's own _SKIP_TOKENS threw away "a"/"the"/"of"/
"to"/etc. during pattern extraction entirely -- no mined or observed
motif could EVER contain a determiner or preposition slot, regardless of
how the fitness signal was grounded. Connector's category gate (L2)
already accepted "preposition" as a valid connector-slot filler, so
prepositions route to the existing CONNECTOR role once the tagger stops
skipping them. Determiners get a genuine sibling role (TokenRole.
DETERMINER) since conflating them with connector would let a preposition
fill a determiner slot or vice versa.

No forced promotion: this is eligibility-only. Whether any
determiner-inclusive skeleton is ever actually mined, reinforced, and
promoted still runs entirely through the existing should_promote() path.
"""
from aurora_grammar_engine import RoleTagger, TokenRole, is_valid_clause_shape
from aurora_expression_perception import SentenceComposer, LexicalMemory, VoiceGenome


def _tagger():
    return RoleTagger()


def test_determiners_get_their_own_role_not_skipped():
    t = _tagger()
    tagged = t.tag("I need the answer.")
    roles = {w.lower(): r for w, r in tagged}
    assert roles["the"] is TokenRole.DETERMINER


def test_true_prepositions_route_to_connector_not_skipped():
    t = _tagger()
    tagged = t.tag("I help with the project.")
    roles = {w.lower(): r for w, r in tagged}
    assert roles["with"] is TokenRole.CONNECTOR


def test_determiner_followed_by_object_not_dropped():
    """Without the DETERMINER->OBJECT positional fallback, the noun after
    a determiner fell through to UNKNOWN and got dropped from the
    pattern -- making the new role useless for mining."""
    t = _tagger()
    pattern = t.extract_pattern("I need the answer.")
    assert pattern == (TokenRole.AGENT, TokenRole.ACTION, TokenRole.DETERMINER, TokenRole.OBJECT)


def test_demonstratives_still_resolve_to_agent_unchanged():
    """This/that/these/those stay out of the new _DETERMINERS set --
    they're already handled by the pre-existing AGENT resolution and this
    change must not disturb that."""
    t = _tagger()
    tagged = t.tag("This works.")
    assert tagged[0][1] is TokenRole.AGENT


def test_determiner_object_shape_is_now_valid():
    assert is_valid_clause_shape(
        (TokenRole.AGENT, TokenRole.ACTION, TokenRole.DETERMINER, TokenRole.OBJECT))
    assert is_valid_clause_shape(
        (TokenRole.AGENT, TokenRole.ACTION, TokenRole.DETERMINER, TokenRole.OBJECT, TokenRole.DESCRIPTOR))


def test_determiner_without_object_still_invalid():
    """Widening eligibility for the reviewed shape must not accidentally
    admit a dangling determiner with nothing after it."""
    assert not is_valid_clause_shape(
        (TokenRole.AGENT, TokenRole.ACTION, TokenRole.DETERMINER))


def test_composer_can_select_a_determiner_word():
    c = SentenceComposer(LexicalMemory(), VoiceGenome())
    c._last_required_slot_attempts = 0
    c._last_floor_failures = []
    picks = set()
    for _ in range(20):
        word = c._select_constraint_word(
            "determiner", "X", (), "determiner", 0.0, [], input_text="",
        )
        if word:
            picks.add(word)
    assert picks, "no determiner word was ever selected"
    for w in picks:
        entry = c.lexicon.entries.get(w)
        assert entry is not None and entry.role == "determiner"


def test_determiner_slot_never_yields_a_non_determiner_word():
    """L2's category gate must still hold for the new role -- a noun or
    verb must never leak into a determiner slot."""
    c = SentenceComposer(LexicalMemory(), VoiceGenome())
    for entry in c.lexicon.entries.values():
        if entry.role != "determiner":
            assert not c._pos_ok(entry, "determiner"), (
                f"{entry.word!r} (role={entry.role}) wrongly accepted into a determiner slot"
            )


def test_compose_from_motif_accepts_determiner_role_in_sequence():
    """End-to-end: a motif whose role_sequence includes DETERMINER
    composes without error and the determiner word precedes its object."""
    c = SentenceComposer(LexicalMemory(), VoiceGenome())
    c._last_required_slot_attempts = 0
    c._last_floor_failures = []

    class _FakeMotif:
        role_sequence = (TokenRole.AGENT, TokenRole.ACTION, TokenRole.DETERMINER, TokenRole.OBJECT)

    sent = c._compose_from_motif(
        _FakeMotif(), {"X": 1.0, "T": 0.5, "N": 0.5, "B": 0.5, "A": 0.5},
        0.0, "i_is", 0, input_text="",
    )
    assert isinstance(sent, str)


def test_last_resort_fallback_searches_full_category_not_single_role():
    """R1.9.4: connector's last-resort search must reach preposition-
    tagged lexicon words too, not just literal role=='connector' (of
    which the lexicon currently has zero)."""
    c = SentenceComposer(LexicalMemory(), VoiceGenome())
    c._last_required_slot_attempts = 0
    c._last_floor_failures = []
    preposition_words = {w for w, e in c.lexicon.entries.items() if e.role == "preposition"}
    assert preposition_words, "fixture assumption: lexicon has >=1 preposition-tagged word"
    picks = set()
    for _ in range(30):
        word = c._select_constraint_word(
            "connector", "X", (), "connector", 0.0, [], input_text="",
        )
        if word:
            picks.add(word)
    assert picks & preposition_words, (
        f"connector slot never reached any preposition-tagged word; picks={picks}"
    )
