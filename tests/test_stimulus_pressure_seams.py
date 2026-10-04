"""Input arrives as pressure ON the axes its words sit on.

Three places that were meant to carry what was said used the dimensional aggregate instead,
which is the same for every utterance (measured: the pressure pump's input disturbance was
X .698 / B .697 / N .697 / T .697 / A .001 for two completely different questions; the turn's
sediment deposit and read-back were the same vector too). They now use the utterance's own
per-axis loads, with the aggregate only as the fallback for text no word of which has a channel.

Authors: Sunni (Sir) Morningstar and Cael Devo
"""
import os
import sys
from types import SimpleNamespace

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_internal.aurora_input_pressure import (  # noqa: E402
    content_axis_loads, content_phase_vector,
)


def _perception(words):
    """words: {word: "AXIS:CHARACTER"} -- a lexicon whose entries carry their channels."""
    entries = {w: SimpleNamespace(noncomp_id=ch) for w, ch in words.items()}
    return SimpleNamespace(composer=SimpleNamespace(lexicon=SimpleNamespace(entries=entries)))


WORDS = {"water": "N:MAGNITUDE", "flows": "T:OPERATOR", "down": "B:POLARITY",
         "hill": "B:POLARITY", "plants": "X:MAGNITUDE"}


# ---- the loads ------------------------------------------------------------------------

def test_loads_are_peak_normalized_per_axis():
    got = content_axis_loads(_perception(WORDS), "plants water flows down hill")
    assert got == {"X": 0.5, "T": 0.5, "N": 0.5, "B": 1.0, "A": 0.0}


def test_no_channeled_word_means_no_pressure():
    assert content_axis_loads(_perception(WORDS), "zqxv threbic") is None
    assert content_axis_loads(None, "water") is None
    assert content_axis_loads(_perception({}), "water") is None


def test_phases_are_exactly_the_loads_expressed_around_neutral():
    p = _perception(WORDS)
    loads = content_axis_loads(p, "water flows down hill")
    assert content_phase_vector(p, "water flows down hill") == [
        0.5 + 0.5 * loads[a] for a in ("X", "T", "N", "B", "A")]


def test_different_utterances_load_different_axes():
    p = _perception(WORDS)
    assert content_axis_loads(p, "down hill") != content_axis_loads(p, "water flows")


# ---- the vector that locates deposits and read-backs ------------------------------------

def _systems(words, aggregate):
    dim = SimpleNamespace(get_constraint_aggregate=lambda: dict(aggregate))
    return {"perception": _perception(words), "dimensional": dim}


AGG = {"X": 0.7, "T": 0.7, "N": 0.7, "B": 0.7, "A": 0.0}


def test_the_vector_is_the_utterances_own_pressure_when_a_word_has_a_channel():
    import aurora
    v = aurora._aggregate_constraint_vector(_systems(WORDS, AGG), "down hill")
    assert (v.X, v.T, v.N, v.B, v.A) == (0.01, 0.0, 0.0, 1.0, 0.0)
    w = aurora._aggregate_constraint_vector(_systems(WORDS, AGG), "water flows")
    assert (w.T, w.N, w.B) == (1.0, 1.0, 0.0), "a different stimulus must locate differently"


def test_the_aggregate_is_still_the_fallback():
    import aurora
    s = _systems(WORDS, AGG)
    for text in ("zqxv threbic", None):
        v = aurora._aggregate_constraint_vector(s, text)
        assert (v.X, v.T, v.N, v.B, v.A) == (0.7, 0.7, 0.7, 0.7, 0.0)


# ---- the injection into the identity field ------------------------------------------------

def test_the_pump_disturbance_is_built_from_the_utterances_loads():
    src = open(os.path.join(REPO_ROOT, "aurora.py"), encoding="utf-8").read()
    i = src.index('source="user_input_precomp"')
    block = src[i - 700:i]
    assert "_content_axis_loads(systems, user_text)" in block, \
        "the input disturbance must come from what was said, not the dimensional aggregate"


@pytest.mark.parametrize("anchor", [
    "_sedi.surface_recall(_cv, max_results=4)",
    "_misfit_cv = _aggregate_constraint_vector(systems, user_text)",
])
def test_turn_level_sediment_sites_pass_the_utterance(anchor):
    src = open(os.path.join(REPO_ROOT, "aurora.py"), encoding="utf-8").read()
    i = src.index(anchor)
    assert "_aggregate_constraint_vector(systems, user_text)" in src[max(0, i - 400):i + 200]
