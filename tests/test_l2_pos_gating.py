# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
R1.9.3 L2: hard POS gate on _select_constraint_word's candidate pools,
applied BEFORE relevance ranking. Grammar diagnosis found the "action"
slot (expects a verb) filled with nouns like "energy"/"cost" because the
primary concept-axis candidate collection (find_by_noncomp) never checked
entry.role against the slot's required category. These tests hold that
gate to the directive's category map and its unknown-POS handling.
"""
import json
import os

from aurora_expression_perception import SentenceComposer, LexicalMemory, VoiceGenome


def _make_composer():
    return SentenceComposer(LexicalMemory(), VoiceGenome())


def test_pos_ok_matches_directive_category_map():
    c = _make_composer()
    cases = [
        ("agent", "pronoun", True), ("agent", "noun", True), ("agent", "verb", False),
        ("object", "noun", True), ("object", "pronoun", True), ("object", "verb", False),
        ("action", "verb", True), ("action", "noun", False), ("action", "adjective", False),
        ("descriptor", "adjective", True), ("descriptor", "adverb", True), ("descriptor", "verb", False),
        ("connector", "preposition", True), ("connector", "conjunction", True), ("connector", "noun", False),
    ]
    for role, pos, expected in cases:
        entry = c.lexicon.add_word(f"__test_{role}_{pos}", "test", pos)
        assert c._pos_ok(entry, role) is expected, f"role={role} pos={pos} expected={expected}"


def test_unknown_pos_excluded_from_role_strict_slots_but_allowed_in_descriptor():
    c = _make_composer()
    entry = c.lexicon.add_word("__test_unknown_word", "test", "training_gap")
    for role in ("agent", "object", "action", "connector"):
        assert c._pos_ok(entry, role) is False
    assert c._pos_ok(entry, "descriptor") is True


def test_missing_pos_treated_as_unknown():
    c = _make_composer()

    class _Blank:
        word = "__test_blank"
        role = None

    assert c._pos_ok(_Blank(), "action") is False
    assert c._pos_ok(_Blank(), "descriptor") is True


def test_unknown_pos_is_logged():
    c = _make_composer()
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                             "aurora_state", "pos_unknown_log.jsonl")
    log_path = os.path.normpath(log_path)
    before = 0
    if os.path.exists(log_path):
        with open(log_path) as f:
            before = sum(1 for _ in f)
    entry = c.lexicon.add_word("__test_logged_unknown", "test", "training_gap")
    c._pos_ok(entry, "action")
    assert os.path.exists(log_path)
    with open(log_path) as f:
        lines = f.readlines()
    assert len(lines) > before
    last = json.loads(lines[-1])
    assert last["word"] == "__test_logged_unknown"
    assert last["slot_role"] == "action"
    assert last["lexicon_pos"] == "training_gap"


def test_action_slot_can_never_select_a_noun_end_to_end():
    """The mini-gate's literal regression case: 'I energy.' / 'I cost.'
    must be impossible by construction now, even when a noun is
    crystallized onto exactly the axis/character an action slot searches."""
    c = _make_composer()
    c._last_required_slot_attempts = 0
    c._last_floor_failures = []
    c.lexicon.add_word("energy", "test-noun-on-action-axis", "noun",
                        valence=0.0, lineage="")
    c.lexicon.entries["energy"].noncomp_id = "X:OPERATOR"
    picks = set()
    for _ in range(30):
        word = c._select_constraint_word(
            "action", "X", ("OPERATOR", "COST"), "verb", 0.0, [],
            input_text="",
        )
        if word:
            picks.add(word)
    assert "energy" not in picks
    for w in picks:
        entry = c.lexicon.entries.get(w)
        assert entry is not None and entry.role == "verb", (
            f"non-verb {w!r} (role={entry.role if entry else None}) selected for an action slot"
        )


def test_object_slot_accepts_noun_and_pronoun_not_verb():
    c = _make_composer()
    c._last_required_slot_attempts = 0
    c._last_floor_failures = []
    c.lexicon.add_word("__test_obj_verb", "test", "verb")
    c.lexicon.entries["__test_obj_verb"].noncomp_id = "N:MAGNITUDE"
    for _ in range(15):
        word = c._select_constraint_word(
            "object", "N", ("MAGNITUDE",), "noun", 0.0, [], input_text="",
        )
        if word:
            entry = c.lexicon.entries.get(word)
            assert entry is not None and entry.role in ("noun", "pronoun")
