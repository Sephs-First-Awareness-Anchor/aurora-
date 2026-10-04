"""The assembly's response to a stimulus must reach structure selection.

compose() looked the assembly's axes up as "X","T","N","B","A" while the DCE names them
existence/temporal/energy/boundary/agency, so every axis silently fell back to 0.5 on every
turn: the selector was handed a constant. And even with matching names the raw activations
(0..~0.25) are floored to 0.5 by the selector's clamp(correction, 0.5, 2.0), so the unit
had to change too: the selector wants RELATIVE pressure (1.0 = neutral).

Authors: Sunni (Sir) Morningstar and Cael Devo
"""
import os
import sys
from types import SimpleNamespace

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_expression_perception import (  # noqa: E402
    ExpressionOffspring, LexicalMemory, SentenceComposer, VoiceGenome,
    assembly_axis_activation, axis_corrections,
)

DCE = {"existence": 0.175, "temporal": 0.045, "energy": 0.03, "boundary": 0.105, "agency": 0.0}


# ---- naming ------------------------------------------------------------------------

def test_the_dces_long_axis_names_map_to_xtnba():
    got = assembly_axis_activation(DCE)
    assert got == {"X": 0.175, "T": 0.045, "N": 0.03, "B": 0.105, "A": 0.0}


def test_short_names_are_unchanged():
    short = {"X": 0.2, "T": 0.3, "N": 0.1, "B": 0.4, "A": 0.5}
    assert assembly_axis_activation(short) == short


def test_an_axis_the_assembly_does_not_carry_is_neutral_not_invented():
    got = assembly_axis_activation({"existence": 0.2, "boundary": 0.4})
    assert got["T"] == got["N"] == got["A"] == pytest.approx(0.3)   # mean of what it has
    assert got["X"] == 0.2 and got["B"] == 0.4


@pytest.mark.parametrize("bad", [None, {}, "x", [], {"unrelated": 1.0}, {"X": "nan?"}])
def test_nothing_usable_means_no_signal(bad):
    assert assembly_axis_activation(bad) is None


# ---- the unit ------------------------------------------------------------------------

def test_corrections_are_relative_pressure_with_one_as_neutral():
    c = axis_corrections(assembly_axis_activation(DCE))
    mean = sum(DCE.values()) / 5
    assert c["X"] == pytest.approx(0.175 / mean) and c["X"] > 1.0     # consolidating
    assert c["N"] < 1.0 and c["A"] == 0.0                             # below the mean
    assert sum(c.values()) / 5 == pytest.approx(1.0)


def test_corrections_are_scale_free():
    a = axis_corrections(assembly_axis_activation(DCE))
    b = axis_corrections(assembly_axis_activation({k: v * 10 for k, v in DCE.items()}))
    for ax in a:
        assert a[ax] == pytest.approx(b[ax])


@pytest.mark.parametrize("flat", [{ax: 0.5 for ax in "XTNBA"}, {ax: 0.0 for ax in "XTNBA"}])
def test_no_pressure_difference_is_neutral(flat):
    assert axis_corrections(flat) == {ax: 1.0 for ax in "XTNBA"}


# ---- end to end: what the selector actually receives -------------------------------------

class _RecordingLineage:
    def __init__(self):
        self.calls = []

    def best_for_pressure(self, orientation, outlet):
        self.calls.append((dict(orientation), outlet))
        return None

    def get_promoted(self, *a, **k):
        return []


def _compose_with(adjusted_axes):
    c = SentenceComposer(LexicalMemory(), VoiceGenome())
    c._last_required_slot_attempts = 0
    c._last_floor_failures = []
    lineage = _RecordingLineage()
    c.grammar_engine = SimpleNamespace(_lineage=lineage)
    off = ExpressionOffspring(offspring_id="t", lineage="i_is", generation=0, tone="neutral",
                              structure_weight=0.5, rhythm_bias=0.5)
    asm = SimpleNamespace(adjusted_axes=adjusted_axes, coherence=0.8, dominant_axis="boundary",
                          synthesis=SimpleNamespace(active_count=8))
    try:
        c.compose(off, asm, "i_is", {"curiosity": 0.5}, None, "what is photosynthesis")
    except Exception:
        pass   # only the orientation handed to the selector matters here
    return lineage.calls


def test_the_selector_receives_the_assemblys_relative_pressure_not_a_constant():
    calls = _compose_with(dict(DCE))
    assert calls, "compose never consulted the selector"
    first = calls[0][0]
    # perturbation per sentence is at most +/-8%
    assert first["X"] > 1.5, first            # existence is the consolidating axis
    assert first["N"] < 0.7 and first["A"] < 0.2, first
    assert len({round(v, 1) for v in first.values()}) > 2, "must not be a flat constant"


def test_two_different_assemblies_hand_the_selector_different_orientations():
    a = _compose_with({"existence": 0.175, "temporal": 0.045, "energy": 0.03, "boundary": 0.105, "agency": 0.0})[0][0]
    b = _compose_with({"existence": 0.075, "temporal": 0.105, "energy": 0.07, "boundary": 0.105, "agency": 0.0})[0][0]
    assert a["X"] > b["X"] and a["T"] < b["T"]


def test_an_assembly_with_no_axes_is_neutral_as_before():
    first = _compose_with({})[0][0]
    assert all(0.9 < v < 1.1 for v in first.values()), first


# ---- working memory's fallback --------------------------------------------------------------

def test_all_zero_axis_weights_do_not_count_as_signal():
    from aurora_working_memory import _axis_weights_carry_signal as carry
    assert carry({"X": 0.0, "T": 0.0, "N": 0.0, "B": 0.0, "A": 0.0}) is False
    assert carry({}) is False and carry(None) is False
    assert carry({"X": 0.0, "T": 0.4}) is True
    assert carry({"X": "oops"}) is False


# ---- the learning side records the orientation that was actually used ----------------------

def test_a_successful_motif_is_credited_with_the_orientation_it_was_composed_under():
    """feedback() recorded a hard-coded {ax: 1.0} for every success, so no motif could ever
    learn which axis pressure it succeeded under."""
    import inspect
    src = inspect.getsource(SentenceComposer.feedback)
    assert "_last_axis_corrections" in src
    assert "{ax: 1.0 for ax in (\"X\", \"T\", \"N\", \"B\", \"A\")},\n                        )" not in src


def test_compose_remembers_the_corrections_it_used():
    c = SentenceComposer(LexicalMemory(), VoiceGenome())
    c._last_required_slot_attempts = 0
    c._last_floor_failures = []
    c.grammar_engine = SimpleNamespace(_lineage=_RecordingLineage())
    off = ExpressionOffspring(offspring_id="t", lineage="i_is", generation=0, tone="neutral",
                              structure_weight=0.5, rhythm_bias=0.5)
    asm = SimpleNamespace(adjusted_axes=dict(DCE), coherence=0.8, dominant_axis="boundary",
                          synthesis=SimpleNamespace(active_count=8))
    try:
        c.compose(off, asm, "i_is", {"curiosity": 0.5}, None, "what is photosynthesis")
    except Exception:
        pass
    used = c._last_axis_corrections
    assert used["X"] > 1.5 and used["A"] == 0.0


# ---- agency: the sender's own state fills what the observed node's mode leaves inactive -------

from aurora_expression_perception import fill_inactive_axes  # noqa: E402

SENDER = {"X": 0.26, "T": 0.177, "N": 0.167, "B": 0.248, "A": 0.148}   # shares (sum ~1)


def test_inactive_agency_takes_the_senders_relative_weight():
    act = assembly_axis_activation(DCE)               # agency 0.0: the node's mode, not Aurora
    out = fill_inactive_axes(act, SENDER)
    active = ("X", "T", "N", "B")
    scale = sum(act[a] for a in active) / sum(SENDER[a] for a in active)
    assert out["A"] == pytest.approx(SENDER["A"] * scale) and out["A"] > 0.0
    for ax in active:
        assert out[ax] == act[ax], "axes the assembly carries are never altered"


def test_the_fill_is_scale_matched_not_a_raw_copy():
    out = fill_inactive_axes(assembly_axis_activation(DCE), SENDER)
    assert out["A"] < SENDER["A"], "the assembly lives in 0..~0.25, the sender in shares of 1"
    ratio_sender = SENDER["A"] / SENDER["X"]
    assert out["A"] / out["X"] == pytest.approx(ratio_sender * (DCE["existence"] / DCE["existence"]), rel=0.5)


@pytest.mark.parametrize("sender", [None, {}, {"X": 0.0, "T": 0.0, "N": 0.0, "B": 0.0, "A": 0.0}])
def test_no_sender_state_leaves_the_activation_untouched(sender):
    act = assembly_axis_activation(DCE)
    assert fill_inactive_axes(act, sender) == act


def test_an_axis_the_sender_has_no_pressure_on_stays_inactive():
    out = fill_inactive_axes(assembly_axis_activation(DCE), {**SENDER, "A": 0.0})
    assert out["A"] == 0.0


def test_nothing_to_fill_when_every_axis_is_active_or_none_is():
    full = {"X": 0.2, "T": 0.1, "N": 0.1, "B": 0.1, "A": 0.1}
    assert fill_inactive_axes(full, SENDER) == full
    none = {ax: 0.0 for ax in "XTNBA"}
    assert fill_inactive_axes(none, SENDER) == none


def test_compose_gives_the_selector_her_agency_when_perception_has_it():
    def run(sender_axes):
        c = SentenceComposer(LexicalMemory(), VoiceGenome())
        c._last_required_slot_attempts = 0
        c._last_floor_failures = []
        lin = _RecordingLineage()
        c.grammar_engine = SimpleNamespace(_lineage=lin)
        if sender_axes is not None:
            c._axis_activation = dict(sender_axes)
        off = ExpressionOffspring(offspring_id="t", lineage="i_is", generation=0, tone="neutral",
                                  structure_weight=0.5, rhythm_bias=0.5)
        asm = SimpleNamespace(adjusted_axes=dict(DCE), coherence=0.8, dominant_axis="boundary",
                              synthesis=SimpleNamespace(active_count=8))
        try:
            c.compose(off, asm, "i_is", {"curiosity": 0.5}, None, "what is photosynthesis")
        except Exception:
            pass
        return lin.calls[0][0]
    without = run(None)
    with_her = run(SENDER)
    assert without["A"] == 0.0, "agency was always 0 without her own state"
    assert with_her["A"] > 0.4, with_her


def test_perception_hands_its_axis_state_to_the_composer():
    from aurora_expression_perception import ExpressionPerceptionEngine
    import inspect
    src = inspect.getsource(ExpressionPerceptionEngine.set_axis_context)
    assert "_composer._axis_activation" in src
    eng = ExpressionPerceptionEngine.__new__(ExpressionPerceptionEngine)
    eng.composer = SimpleNamespace()
    eng.set_axis_context({"X": 0.3, "B": 0.4, "A": 0.1})
    assert eng.composer._axis_activation == {"X": 0.3, "B": 0.4, "A": 0.1}
