# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
R1.9.2 G3 / R1.9 Addendum F5: register-gated exploration plumbing.

"Build the plumbing WITH R1.9; ship temperature-FLAT (exploration
disabled) until all F3 gates pass." SentenceComposer._EXPLORATION_ENABLED
must stay False -- G4 found the stratified-wellformedness gate failing and
two gates not yet run this session, so exploration behavior must not be
live. These tests hold the PLUMBING to F5's invariants without switching
anything on.
"""
from aurora_expression_perception import SentenceComposer, LexicalMemory, VoiceGenome


def _make_composer():
    return SentenceComposer(LexicalMemory(), VoiceGenome())


def test_exploration_is_shipped_disabled():
    assert SentenceComposer._EXPLORATION_ENABLED is False, (
        "F5 exploration must stay temperature-flat until all F3 gates pass -- "
        "gate 2 (stratified wellformedness) failed and two gates were not run "
        "this session, so this must not flip to True yet."
    )


def test_register_estimate_serious_tones():
    c = _make_composer()
    for tone in ("focused", "precise", "determined"):
        register, signals = c._estimate_register(tone, coherence=0.8)
        assert register == "serious"
        assert signals["reason"] == "serious_tone"


def test_register_estimate_playful_tone():
    c = _make_composer()
    register, signals = c._estimate_register("playful", coherence=0.8)
    assert register == "playful"
    assert signals["reason"] == "playful_tone"


def test_register_estimate_low_coherence_overrides_to_serious():
    """She is never loose about grief, distress, or weight -- low internal
    coherence is the closest available proxy for that and always wins,
    even over a playful tone."""
    c = _make_composer()
    register, signals = c._estimate_register("playful", coherence=0.1)
    assert register == "serious"
    assert signals["reason"] == "low_coherence_override"


def test_register_estimate_default_neutral():
    c = _make_composer()
    register, signals = c._estimate_register("warm", coherence=0.8)
    assert register == "neutral"
    assert signals["reason"] == "default"


def test_register_signals_are_logged_and_honest():
    """F5.1: 'report what IS available rather than faking one' -- signals
    dict must only contain the two real fields this stage actually has
    (tone, coherence), never an invented attention-path signal."""
    c = _make_composer()
    _, signals = c._estimate_register("neutral", coherence=0.6)
    assert set(signals.keys()) == {"tone", "coherence", "reason"}


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
