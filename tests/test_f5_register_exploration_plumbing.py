# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
R1.9.2 G3 / R1.9 Addendum F5: register-gated exploration plumbing.

N2.1 (decision memo, ratified 2026-07-16) rebuilt register estimation
with a source inversion: N2's mini-acceptance found the original F5.1
premise false -- offspring.tone is an EVOLUTIONARY population trait
(ExpressionEcology.spawn(), i_state lineage bias + 20% random mutation),
not derived from the current turn's content, so "tone as reading the
room" measured lineage noise, not distress. Register now derives
EXCLUSIVELY from the user's own turn text. These tests hold the rebuilt
plumbing to F5's invariants. SentenceComposer._EXPLORATION_ENABLED
switched ON at N2.1 once test_n21_hardened_reacceptance.py's full battery
passed 7/7 (see that file).
"""
from aurora_expression_perception import SentenceComposer, LexicalMemory, VoiceGenome


def _make_composer():
    return SentenceComposer(LexicalMemory(), VoiceGenome())


def _make_composer_with_real_lexicon():
    """A composer backed by the real seeded lexicon (aurora_state/
    lexicon.json), not an empty one -- valence-based register signals need
    real word coverage to mean anything."""
    import os
    lex = LexicalMemory()
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "aurora_state", "lexicon.json")
    lex.load(path)
    return SentenceComposer(lex, VoiceGenome())


def test_register_estimate_source_inversion_signature():
    """N2.1: _estimate_register takes ONLY input_text now -- tone and
    coherence (both internal/evolutionary signals) must not appear in its
    signature at all. This is the source-inversion invariant itself,
    checked structurally so a future regression can't silently reintroduce
    an internal-state parameter."""
    import inspect
    sig = inspect.signature(SentenceComposer._estimate_register)
    params = list(sig.parameters.keys())
    assert params == ["self", "input_text"], (
        f"_estimate_register's signature is {params} -- must be exactly "
        f"(self, input_text), never tone/coherence/mood/any internal state."
    )


def test_register_estimate_explicit_distress_phrase_is_serious():
    c = _make_composer_with_real_lexicon()
    register, signals = c._estimate_register("I'm so sad and worried about everything.")
    assert register == "serious"
    assert signals["reason"] == "distress_phrase"


def test_register_estimate_explicit_playful_cue():
    c = _make_composer_with_real_lexicon()
    register, signals = c._estimate_register("lol that's hilarious, love it!")
    assert register == "playful"


def test_register_estimate_fragmentation_punctuation_is_serious():
    c = _make_composer_with_real_lexicon()
    register, signals = c._estimate_register("!!!! WHAT IS GOING ON")
    assert register == "serious"
    assert signals["reason"] == "fragmentation_or_intensity_punctuation"


def test_register_estimate_empty_input_is_serious():
    """Fail-closed invariant, the degenerate case: no input at all is the
    most unknown a turn can be."""
    c = _make_composer_with_real_lexicon()
    register, signals = c._estimate_register("")
    assert register == "serious"
    assert signals["reason"] == "empty_input_fail_closed"


def test_register_estimate_low_coverage_fails_closed_to_serious():
    """Fail-closed invariant, the load-bearing case this whole redesign
    depends on: a turn with no distress phrase, no fragmentation cue, and
    too few lexicon-scored words to trust an average must default to
    serious, not neutral. 'When she cannot read the room, she assumes the
    room is heavy.' Subtle, keyword-free distress input is exactly this
    shape -- see test_n21_hardened_reacceptance.py's 20-case set."""
    c = _make_composer_with_real_lexicon()
    register, signals = c._estimate_register("my mom's test results came back")
    assert register == "serious"
    assert signals["reason"] == "low_coverage_fail_closed"
    assert signals["coverage"] < c._REGISTER_MIN_COVERAGE or \
        signals["scored_word_count"] < c._REGISTER_MIN_SCORED_WORDS


def test_register_estimate_negative_valence_is_serious():
    c = _make_composer_with_real_lexicon()
    register, signals = c._estimate_register(
        "Everything feels wrong and I am so afraid, nothing helps."
    )
    assert register == "serious"
    assert signals["reason"] in ("negative_valence", "distress_phrase", "low_coverage_fail_closed")


def test_register_signals_never_contain_tone_or_coherence():
    """N2.1's source-inversion invariant, checked on live output too (not
    just the signature): the signals dict this stage logs must never
    carry a 'tone' or 'coherence' key again -- those were the internal-
    state fields the redesign specifically removed."""
    c = _make_composer_with_real_lexicon()
    for text in ("hello", "I'm sad", "lol", "", "what is the capital of france"):
        _, signals = c._estimate_register(text)
        assert "tone" not in signals
        assert "coherence" not in signals


def test_register_estimate_logs_contributing_terms_when_scored():
    """N2.1 spec: 'log the contributing terms per turn.'"""
    c = _make_composer_with_real_lexicon()
    _, signals = c._estimate_register("You make me feel good and warm inside.")
    assert "contributing_terms" in signals
    assert len(signals["contributing_terms"]) >= 1


class _FakeEntry:
    def __init__(self, word, valence, usage_count=0):
        self.word = word
        self.emotional_valence = valence
        self.usage_count = usage_count


def test_hard_invariant_exploration_never_selects_below_register_floor():
    """The one invariant F5.2 explicitly demands be unit-tested: whatever
    register widens the ring to, nothing below the (register-adjusted)
    relevance floor can be chosen."""
    c = _make_composer()
    anchor_set = {"guitar": 1.0}
    # A pool where only the first candidate clears any reasonable floor;
    # the rest are all RELEVANCE_DISTANT_FLOOR-tier irrelevant words.
    ranked = [
        _FakeEntry("guitar", valence=0.0),
        _FakeEntry("junk1", valence=0.0),
        _FakeEntry("junk2", valence=0.0),
        _FakeEntry("junk3", valence=0.0),
        _FakeEntry("junk4", valence=0.0),
        _FakeEntry("junk5", valence=0.0),
        _FakeEntry("junk6", valence=0.0),
        _FakeEntry("junk7", valence=0.0),
    ]
    floor = c._RELEVANCE_FLOOR_R_MIN
    for register in ("serious", "neutral", "playful"):
        chosen, rank = c._select_with_temperature(ranked, anchor_set, 0.0, register, floor)
        score = c._score_composer_candidate(chosen, anchor_set, 0.0)
        effective_floor = floor * (c._SERIOUS_FLOOR_MULTIPLIER if register == "serious" else 1.0)
        assert score >= effective_floor or chosen is ranked[0], (
            f"register={register} selected {chosen.word!r} (score={score}) "
            f"below its effective floor {effective_floor} -- loose != irrelevant"
        )


def test_serious_register_is_deterministic_top_pick():
    c = _make_composer()
    anchor_set = {"guitar": 1.0}
    ranked = [_FakeEntry("guitar", valence=0.0), _FakeEntry("chords", valence=0.0)]
    chosen, rank = c._select_with_temperature(ranked, anchor_set, 0.0, "serious", c._RELEVANCE_FLOOR_R_MIN)
    assert chosen is ranked[0]
    assert rank == 0


def test_playful_register_can_reach_wider_ring_than_neutral():
    assert SentenceComposer._REGISTER_RING_WIDTH["playful"] > SentenceComposer._REGISTER_RING_WIDTH["neutral"]
    assert SentenceComposer._REGISTER_RING_WIDTH["neutral"] > SentenceComposer._REGISTER_RING_WIDTH["serious"]


def test_apply_correction_returns_false_without_oets():
    c = _make_composer()
    c._oets = None
    assert c.apply_correction("word", ["anchor"], "confirmation") is False


def test_apply_correction_returns_false_without_anchor_words():
    c = _make_composer()
    assert c.apply_correction("word", [], "confirmation") is False


def test_apply_correction_promotes_knowledge_source_on_already_seen_pair():
    """N2.1 regression test, exact reproduction of N2's live finding:
    apply_correction("exist", ["truth"], "confirmation") returned True, but
    zero relations in the web carried source_of_knowledge=="correction"
    afterward, because add_relation()'s 'strengthen existing' branch
    touched strength/confidence but never knowledge_source -- a silent
    no-op on the MAIN case (a word pair that already has a relation from
    prior conversation), not an edge case. Fixed in
    aurora_internal/aurora_ontological_scaffolding.py's add_relation()."""
    from aurora_internal.aurora_ontological_scaffolding import OntologicalWeb, RelationType

    class _FakeOETS:
        def __init__(self, web):
            self.web = web

    web = OntologicalWeb()
    web.add_node("exist", role="verb")
    web.add_node("truth", role="noun")

    # The common case: a relation already exists from ordinary co-occurrence
    # tracking, BEFORE any correction ever touches this pair.
    pre_existing = web.add_relation(
        "exist", "truth", RelationType.RELATED_TO,
        strength=0.3, confidence=0.4, knowledge_source="co-occurrence",
    )
    assert pre_existing.source_of_knowledge == "co-occurrence"

    c = _make_composer()
    c._oets = _FakeOETS(web)

    result = c.apply_correction("exist", ["truth"], "confirmation")
    assert result is True

    corrected = web.get_relation_between("exist", "truth")
    assert corrected is not None
    assert corrected.source_of_knowledge == "correction", (
        "apply_correction() returned True but the already-seen-pair path "
        "left source_of_knowledge unpromoted -- the exact silent no-op "
        "N2's mini-acceptance found live."
    )


def test_compose_and_select_constraint_word_accept_f5_kwargs_without_breaking():
    """input_text-style optionality: existing callers that don't pass
    f5_turn_id/f5_register must keep working exactly as before."""
    import inspect

    compose_sig = inspect.signature(SentenceComposer.compose)
    motif_sig = inspect.signature(SentenceComposer._compose_from_motif)
    select_sig = inspect.signature(SentenceComposer._select_constraint_word)
    for sig in (motif_sig, select_sig):
        assert sig.parameters["f5_turn_id"].default == ""
        assert sig.parameters["f5_register"].default == "neutral"


def test_selection_wiring_uses_deterministic_path_when_disabled():
    """_select_with_temperature is wired into _select_constraint_word
    behind the flag. N2.1 (2026-07-16) switched the class default to
    True (hardened re-acceptance passed), but the conditional itself must
    still correctly fall back to the old deterministic-ish top-4 path
    when an instance explicitly has exploration off."""
    c = _make_composer()
    c._EXPLORATION_ENABLED = False
    c._last_required_slot_attempts = 0
    c._last_floor_failures = []
    calls = []
    orig = c._select_with_temperature

    def _spy(*a, **kw):
        calls.append(a)
        return orig(*a, **kw)

    c._select_with_temperature = _spy
    for _ in range(20):
        c._select_constraint_word("action", "X", ("OPERATOR", "COST"), "verb", 0.0, [], input_text="")
    assert calls == [], "_select_with_temperature was called even though _EXPLORATION_ENABLED is False"


def test_selection_wiring_uses_temperature_path_when_enabled():
    """The other half of the same check: with exploration enabled (the
    shipped default since N2.1), the wiring must actually route through
    _select_with_temperature, not silently keep using the old path."""
    c = _make_composer()
    assert c._EXPLORATION_ENABLED is True, "N2.1 shipped this True by default"
    c._last_required_slot_attempts = 0
    c._last_floor_failures = []
    calls = []
    orig = c._select_with_temperature

    def _spy(*a, **kw):
        calls.append(a)
        return orig(*a, **kw)

    c._select_with_temperature = _spy
    word = c._select_constraint_word("action", "X", ("OPERATOR", "COST"), "verb", 0.0, [], input_text="")
    assert calls, "_select_with_temperature was never called even though _EXPLORATION_ENABLED was True"
