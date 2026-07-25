# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Directive PF3, PF3.3: descriptor neighborhood constraint (carried
forward from PF2.3, unchanged scope).

Rationale (PF2.1's own finding): with real participants flowing through
more often (W1), the descriptor slot is the last generic-filler leak
("clear"/"real"). When a frame is present and the role is "descriptor"
(dispatch point aurora_expression_perception.py, SentenceComposer.
compose()), the _select_constraint_word candidate pool is filtered to
words whose OETS node lies within one relation hop of frame.subject or
frame.obj BEFORE the existing resonance/valence ranking runs. Her web
defines "about" -- no word lists, no tuned constants. Empty
neighborhood (or empty intersection with the candidate pool) falls
through to the unfiltered pool, fail-quiet.
"""
import os
import sys
import tempfile
import types

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_expression_perception import (  # noqa: E402
    LexicalMemory, VoiceGenome, SentenceComposer,
)


class _FakeRelation:
    def __init__(self, source_word, target_word, source_of_knowledge="conversation"):
        self.source_word = source_word
        self.target_word = target_word
        self.source_of_knowledge = source_of_knowledge


class _FakeWeb:
    def __init__(self, relations_by_word):
        self._relations_by_word = relations_by_word

    def get_all_relations_for(self, word):
        return self._relations_by_word.get(word, [])


class _FakeOets:
    def __init__(self, relations_by_word):
        self.web = _FakeWeb(relations_by_word)


def _composer(relations_by_word=None):
    tmp = tempfile.mkdtemp(prefix="aurora_pf3_3_test_")
    lexicon = LexicalMemory(state_dir=tmp)
    composer = SentenceComposer(lexicon, VoiceGenome())
    if relations_by_word is not None:
        composer.set_oets(_FakeOets(relations_by_word))
    return composer


def _frame(subject="he", obj="nervous"):
    return types.SimpleNamespace(subject=subject, relation="is", obj=obj)


def test_neighborhood_filter_prefers_one_hop_word_over_generic_filler():
    """"clear" is already seeded (B:POLARITY); "anxious" is added at the
    SAME noncomp channel so both are equally eligible candidates before
    filtering -- only the neighborhood filter can distinguish them."""
    composer = _composer(relations_by_word={
        "nervous": [_FakeRelation("nervous", "anxious")],
    })
    composer.lexicon.add_word("anxious", "worried", "adjective",
                               valence=-0.2, lineage="test")
    composer.lexicon.entries["anxious"].noncomp_id = "B:POLARITY"

    chosen = composer._select_constraint_word(
        role="descriptor", dominant_axis="B",
        chars=("MAGNITUDE", "POLARITY"), lex_role="adjective",
        valence_target=0.0, already=[], input_text="",
        frame=_frame(),
    )
    assert chosen == "anxious"


def test_empty_neighborhood_intersection_falls_through_unfiltered():
    """The frame's neighborhood exists but shares nothing with the
    candidate pool -- fail-quiet: fall through to the unfiltered pool
    rather than returning nothing."""
    composer = _composer(relations_by_word={
        "nervous": [_FakeRelation("nervous", "totally_unrelated_word")],
    })
    chosen = composer._select_constraint_word(
        role="descriptor", dominant_axis="B",
        chars=("MAGNITUDE", "POLARITY"), lex_role="adjective",
        valence_target=0.0, already=[], input_text="",
        frame=_frame(),
    )
    # "clear" is the only seeded B:POLARITY adjective candidate --
    # the unfiltered pool still produces a real word, not "".
    assert chosen == "clear"


def test_no_frame_behaves_exactly_as_before():
    composer = _composer(relations_by_word={})
    chosen = composer._select_constraint_word(
        role="descriptor", dominant_axis="B",
        chars=("MAGNITUDE", "POLARITY"), lex_role="adjective",
        valence_target=0.0, already=[], input_text="",
        frame=None,
    )
    assert chosen == "clear"


def test_frame_present_but_no_oets_falls_through_unfiltered():
    composer = _composer(relations_by_word=None)  # set_oets never called
    chosen = composer._select_constraint_word(
        role="descriptor", dominant_axis="B",
        chars=("MAGNITUDE", "POLARITY"), lex_role="adjective",
        valence_target=0.0, already=[], input_text="",
        frame=_frame(),
    )
    assert chosen == "clear"


def test_non_descriptor_role_ignores_frame_neighborhood():
    """The filter is scoped to role=="descriptor" only -- other roles
    must be completely unaffected by a frame being present."""
    composer = _composer(relations_by_word={
        "water": [_FakeRelation("water", "need")],
    })
    # role="action"/"object" read floor-failure tracking state compose()
    # normally resets each call -- calling _select_constraint_word
    # directly (bypassing compose()) needs the same setup.
    composer._last_floor_failures = []
    composer._last_required_slot_attempts = 0
    chosen = composer._select_constraint_word(
        role="action", dominant_axis="N",
        chars=("OPERATOR", "COST"), lex_role="verb",
        valence_target=0.0, already=[], input_text="",
        frame=types.SimpleNamespace(subject="i", relation="need", obj="water"),
    )
    # "do" is the seeded N:OPERATOR verb -- unaffected by frame presence.
    assert chosen == "do"


def test_descriptor_neighborhood_includes_frame_terms_themselves():
    composer = _composer(relations_by_word={})
    neighborhood = composer._descriptor_neighborhood(_frame(subject="he", obj="nervous"))
    assert "he" in neighborhood
    assert "nervous" in neighborhood


def test_descriptor_neighborhood_empty_when_frame_has_no_subject_or_obj():
    composer = _composer(relations_by_word={})
    frame = types.SimpleNamespace(subject="", relation="", obj="")
    assert composer._descriptor_neighborhood(frame) == set()


def test_descriptor_neighborhood_empty_when_frame_is_none():
    composer = _composer(relations_by_word={})
    assert composer._descriptor_neighborhood(None) == set()


def test_cooccurrence_relations_excluded_from_descriptor_neighborhood():
    """Regression: the real, committed OETS graph shows "clear"/"real" --
    the exact generic-filler words this phase targets -- carrying 39 and
    131 co-occurrence-sourced edges respectively, to near-arbitrary
    common words purely from being used so often across this whole
    campaign's testing history (confirmed live). A first version of this
    filter with no source_of_knowledge check measured WORSE than the
    unfiltered baseline (9.22% -> 9.64% descriptor repetition share) --
    "clear" rode along as a false one-hop neighbor of nearly any frame
    term. Same FIX-A048 exclusion, applied here too."""
    composer = _composer(relations_by_word={
        "nervous": [
            _FakeRelation("nervous", "clear", source_of_knowledge="co-occurrence"),
            _FakeRelation("nervous", "anxious", source_of_knowledge="conversation"),
        ],
    })
    neighborhood = composer._descriptor_neighborhood(_frame())
    assert "clear" not in neighborhood


def test_coexpression_relations_also_excluded_from_descriptor_neighborhood():
    """Second regression: excluding co-occurrence ALONE still measured
    no improvement live (9.22% -> 9.64%) -- traced and found the actual
    leak was "co-expression" relations created fresh during the very
    session being measured (every response containing "clear"/"real"
    wires a co-expression edge from every OTHER word in that response
    back to them, a self-reinforcing loop). Confirmed live via
    scripts/pf3_3_descriptor_trace.py against the real committed OETS
    graph: 'favorite'/'color' -> 'clear'/'real' via co-expression, not
    co-occurrence."""
    composer = _composer(relations_by_word={
        "nervous": [
            _FakeRelation("nervous", "real", source_of_knowledge="co-expression"),
            _FakeRelation("nervous", "anxious", source_of_knowledge="conversation"),
        ],
    })
    neighborhood = composer._descriptor_neighborhood(_frame())
    assert "real" not in neighborhood
    assert "anxious" in neighborhood
    assert "anxious" in neighborhood
