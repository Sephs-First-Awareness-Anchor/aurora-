# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Four breaks in the path by which language is meant to fall out of her constraint
genealogy, each found by measurement on a live full-profile session.

1. Context collapse: every absorbed structure was filed under md5("") so promotion
   (>= 3 contexts) was unreachable -- 0 of 3,616 motifs ever promoted.
2. Granularity: whole messages were observed as ONE pattern (99% unique), so nothing
   could recur; per sentence the same text yields reusable clause shapes.
3. Severed pressure: belief_tension read a "cost_signal" key nothing produces, so
   conversation never recorded a pressure experience.
4. Words that could not compete: OETS-bridged topical words got no channel, and the
   candidate pool was gated by the dominant axis so relevance only ranked it.
"""
import hashlib

from aurora_expression_perception import (
    LexicalMemory,
    SentenceComposer,
    VoiceGenome,
    assign_bridged_channels,
    split_absorb_sentences,
)

EMPTY_CTX = hashlib.md5(b"").hexdigest()[:8]  # "d41d8cd9"


# ---- 1. context ---------------------------------------------------------------

def _all_contexts(engine):
    out = set()
    for m in engine._lineage._motifs.values():
        out |= set(m.contexts_seen)
    return out


def test_absorbed_structure_is_not_filed_under_the_empty_string_context(tmp_path):
    from aurora_grammar_engine import GrammarEngine

    eng = GrammarEngine(str(tmp_path))
    eng.observe_exchange("", "The dog runs very fast today.", success=True)
    eng.observe_exchange("", "A bird sings quite loudly outside.", success=True)
    ctxs = _all_contexts(eng)
    assert EMPTY_CTX not in ctxs, "absorbed text must not collapse onto md5('')"
    assert len(ctxs) >= 2, "different heard sentences must be different contexts"


def test_a_real_user_turn_still_defines_the_context(tmp_path):
    from aurora_grammar_engine import GrammarEngine

    eng = GrammarEngine(str(tmp_path))
    eng.observe_exchange("what is the dog doing", "The dog runs very fast today.", success=True)
    assert GrammarEngine._context_hash("what is the dog doing") in _all_contexts(eng)


# ---- 2. granularity -----------------------------------------------------------

def test_split_absorb_sentences_keeps_only_real_sentences():
    text = "The sky is blue today. Photosynthesis makes energy from light.\nOk. Yes."
    assert split_absorb_sentences(text) == [
        "The sky is blue today.",
        "Photosynthesis makes energy from light.",
    ]
    assert split_absorb_sentences("") == []


def test_absorb_observes_each_sentence_as_its_own_exchange():
    c = SentenceComposer(LexicalMemory(), VoiceGenome())
    calls = []

    class _Engine:
        def observe_exchange(self, user_text, aurora_text, **kw):
            calls.append((user_text, aurora_text))

    c.grammar_engine = _Engine()
    c.absorb("The sky is blue today. Photosynthesis makes energy from light.")
    assert calls == [
        ("", "The sky is blue today."),
        ("", "Photosynthesis makes energy from light."),
    ]


def test_absorb_of_a_short_text_without_a_full_sentence_still_observes_it_whole():
    c = SentenceComposer(LexicalMemory(), VoiceGenome())
    calls = []

    class _Engine:
        def observe_exchange(self, user_text, aurora_text, **kw):
            calls.append(aurora_text)

    c.grammar_engine = _Engine()
    c.absorb("hello there")
    assert calls == ["hello there"]


# ---- 3. belief tension --------------------------------------------------------

def test_belief_tension_reads_the_contract_total_when_no_cost_signal():
    import aurora

    n = {"coherence_cost": 0.328, "contradiction_cost": 0.0, "boundary_cost": 0.295, "total": 0.1519}
    assert aurora._belief_tension_from_n_cost(n) == 0.1519
    assert aurora._belief_tension_from_n_cost(n) >= 0.05, "must clear _record_pressure_experience's gate"


def test_belief_tension_still_honours_an_explicit_cost_signal():
    import aurora

    assert aurora._belief_tension_from_n_cost({"cost_signal": 0.4, "total": 0.1}) == 0.4


def test_belief_tension_is_zero_for_missing_or_malformed_cost():
    import aurora

    assert aurora._belief_tension_from_n_cost(None) == 0.0
    assert aurora._belief_tension_from_n_cost({}) == 0.0
    assert aurora._belief_tension_from_n_cost({"total": "not-a-number"}) == 0.0


# ---- 4a. bridged words get a channel -------------------------------------------

def test_bridged_content_words_receive_a_concept_channel():
    lex = LexicalMemory()
    # words absent from the seed vocabulary, so they arrive exactly as bridged words do:
    # present in the lexicon, no channel
    words = (("chloroplast", "noun"), ("photolyze", "verb"), ("glaucous", "adjective"))
    for w, r in words:
        assert w not in lex.entries, f"{w!r} is in the seed lexicon; pick another test word"
        lex.add_word(w, "oets:test", r, lineage="oets")
    assert not any(lex.entries[w].noncomp_id for w, _ in words)
    out = assign_bridged_channels(lex, [(w, r, 0.0) for w, r in words], "i_is")
    assert out, "assign_batch must have returned assignments"
    assert lex.entries["chloroplast"].noncomp_id, "a bridged noun must land in a channel"
    assert all(lex.entries[w].noncomp_id for w in out)


def test_bridged_non_content_roles_are_not_given_channels():
    lex = LexicalMemory()
    lex.add_word("zzz", "oets:test", "training_gap", lineage="oets")
    out = assign_bridged_channels(lex, [("zzz", "training_gap", 0.0)], "i_is")
    assert out == {}
    assert not lex.entries["zzz"].noncomp_id


def test_assign_bridged_channels_with_nothing_to_do_is_a_noop():
    assert assign_bridged_channels(LexicalMemory(), [], "i_is") == {}
    assert assign_bridged_channels(LexicalMemory(), None, "i_is") == {}


# ---- 4b. relevance can widen the pool -----------------------------------------

def _composer_with_generic_axis_words():
    c = SentenceComposer(LexicalMemory(), VoiceGenome())
    c._last_required_slot_attempts = 0
    c._last_floor_failures = []
    # generic words crystallized onto the axis/character the slot searches (what used
    # to win every time) ...
    for w in ("truth", "reality", "moment"):
        c.lexicon.add_word(w, "generic", "noun", valence=0.0, lineage="")
        c.lexicon.entries[w].noncomp_id = "X:MAGNITUDE"
    # ... and a topical word with NO channel (an OETS-bridged word looks exactly like this)
    c.lexicon.add_word("photosynthesis", "oets:topic", "noun", valence=0.0, lineage="oets")
    return c


def _picks(c, input_text, n=60):
    got = set()
    for _ in range(n):
        w = c._select_constraint_word(
            "object", "X", ("MAGNITUDE",), "noun", 0.0, [], input_text=input_text
        )
        if w:
            got.add(w)
    return got


def test_a_channelless_topical_word_can_now_be_chosen_when_the_input_is_about_it():
    c = _composer_with_generic_axis_words()
    assert "photosynthesis" in _picks(c, "tell me about photosynthesis")


def test_widening_does_not_inject_words_the_input_is_not_about():
    c = _composer_with_generic_axis_words()
    assert "photosynthesis" not in _picks(c, "tell me about something else entirely")


def test_widening_respects_the_slots_part_of_speech():
    c = _composer_with_generic_axis_words()
    c.lexicon.add_word("convert", "oets:topic", "verb", valence=0.0, lineage="oets")
    picks = set()
    for _ in range(40):
        w = c._select_constraint_word(
            "object", "X", ("MAGNITUDE",), "noun", 0.0, [], input_text="convert photosynthesis"
        )
        if w:
            picks.add(w)
    assert "convert" not in picks, "a verb must never fill an object slot"
    assert "photosynthesis" in picks


def test_widened_words_are_attributed_to_their_branch():
    c = _composer_with_generic_axis_words()
    for _ in range(80):
        w = c._select_constraint_word(
            "object", "X", ("MAGNITUDE",), "noun", 0.0, [], input_text="tell me about photosynthesis"
        )
        if w == "photosynthesis":
            src = c._last_word_sources.get("photosynthesis", {})
            assert "relevance_anchor" in str(src)
            return
    raise AssertionError("photosynthesis was never selected in 80 tries")
