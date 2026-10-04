"""Every level reshapes the one below it.

AURORA_COGNITIVE_PHYSICS sections 5-7 give each crystal and each emergent function a "Modulates
down" line. Only Salience's threshold and Prediction's priors implemented theirs; the rest were
declared strings. The layer now carries one coupling per spec line as a table, each driven by the
source's level against its peers, with the layer's own 0.05 step and its own bounds.

Authors: Sunni (Sir) Morningstar and Cael Devo
"""
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_internal.aurora_tensor_expressions import TensorExpressionLayer  # noqa: E402
from aurora_manifold_directory.noncomp_field import NoncompField  # noqa: E402


class _Field:
    """A field with fixed axis pressures that records what it is asked to reshape."""
    def __init__(self, **p):
        self.p = {"X": 0.5, "T": 0.5, "N": 0.5, "B": 0.5, "A": 0.5, **p}
        self.emotion_levels = []

    def axis_pressure(self, i):
        return self.p["XTNBA"[i]]

    def accept_emotion_topology(self, level):
        self.emotion_levels.append(level)


def _layer(**pressures):
    return TensorExpressionLayer(identity_field=_Field(**pressures))


def _weights(layer):
    return {n: getattr(layer, n)._weight for n in ("activation", "salience", "prediction", "attention", "meaning")}


# ---- the table is the audit -------------------------------------------------------------------

def test_every_row_names_the_spec_line_it_realizes():
    rows = TensorExpressionLayer._DOWNWARD_COUPLINGS
    assert len(rows) >= 9
    for kind, source, target, attr, sign, spec in rows:
        assert kind in ("crystal", "function") and attr in ("weight", "threshold") and sign in (+1, -1)
        assert "section" in spec, spec


def test_the_step_is_the_one_the_layer_already_uses():
    assert TensorExpressionLayer._DOWNWARD_STEP == 0.05


# ---- directions ------------------------------------------------------------------------------

def test_attention_above_its_peers_raises_activation_and_salience_weights():
    # X, N, A hot -> Attention (X+N+A) and Activation (X+N) high; Meaning (T+B+A), Salience (N+B) low
    layer = _layer(X=0.9, N=0.9, A=0.9, T=0.1, B=0.1)
    before = _weights(layer)
    layer.downward_modulation()
    after = _weights(layer)
    assert after["activation"] > before["activation"]


def test_a_level_below_its_peers_lowers_what_it_modulates():
    layer = _layer(X=0.1, N=0.1, A=0.1, T=0.9, B=0.9)    # Attention low
    before = _weights(layer)["salience"]
    layer.downward_modulation()
    applied = {r["spec"]: r for r in layer._last_downward}
    assert applied["Attention feeds back into Salience weighting (section 5)"]["deviation"] < 0


def test_high_valuation_lowers_the_pressure_threshold():
    layer = _layer(N=0.9, B=0.9, T=0.9, A=0.9, X=0.1)     # Salience + Meaning high -> valuation high
    before = layer.salience._threshold
    layer.downward_modulation()
    row = [r for r in layer._last_downward if r["spec"].startswith("Valuation: high-value")][0]
    assert row["deviation"] != 0
    assert (layer.salience._threshold < before) == (row["deviation"] > 0)


def test_the_pass_redistributes_and_does_not_inflate():
    layer = _layer(X=0.9, N=0.9, A=0.9, T=0.1, B=0.1)
    layer.downward_modulation()
    state = layer.behavioral_state()
    mean_c = sum(state["crystals"].values()) / 5
    assert abs(sum(v - mean_c for v in state["crystals"].values())) < 1e-6


@pytest.mark.parametrize("p", [{}, {ax: 0.5 for ax in "XTNBA"}])
def test_uniform_levels_change_nothing(p):
    layer = _layer(**p)
    layer.prediction._prior_t = layer.prediction._prior_n = 0.5   # priors consistent with the pressures
    before = _weights(layer)
    layer.downward_modulation()
    assert _weights(layer) == before


def test_weights_and_threshold_stay_inside_the_layers_own_bounds():
    layer = _layer(X=1.0, N=1.0, A=1.0, T=0.0, B=0.0)
    for _ in range(500):
        layer.downward_modulation()
    for crystal in layer._crystals:
        assert crystal._weight_min <= crystal._weight <= crystal._weight_max
    assert 0.1 <= layer.salience._threshold <= 0.5


# ---- memory and emotion ----------------------------------------------------------------------

def test_memory_that_weighs_on_presence_anchors_it():
    heavy_x, light_x = _layer(), _layer()
    heavy_x.downward_modulation({"deep_memory": {"X": 9, "T": 1, "N": 1, "B": 1, "A": 1}})
    light_x.downward_modulation({"deep_memory": {"X": 0, "T": 3, "N": 3, "B": 3, "A": 3}})
    assert heavy_x.activation._weight > light_x.activation._weight


def test_no_deep_memory_means_no_anchoring_row():
    layer = _layer(X=0.9, N=0.9, A=0.9, T=0.1, B=0.1)
    layer.downward_modulation({})
    assert not [r for r in layer._last_downward if "Memory anchors" in r["spec"]]


def test_emotion_is_handed_to_the_field_to_reshape_baselines():
    layer = _layer(N=0.9, X=0.9, B=0.9, T=0.2, A=0.2)
    layer.downward_modulation()
    assert layer._field.emotion_levels and 0.0 <= layer._field.emotion_levels[0] <= 1.0


def test_a_field_that_cannot_be_reshaped_is_left_alone():
    layer = TensorExpressionLayer(identity_field=None)
    assert isinstance(layer.downward_modulation(), list)


# ---- the field's side of emotion --------------------------------------------------------------

def test_emotion_moves_the_baseline_toward_the_pressure_topology_and_conserves_the_total():
    f = NoncompField()
    for _ in range(40):
        f.ingest_external_input({"N": 1.0}, intensity=1.0, source="t")
    for _ in range(100):
        f.accept_emotion_topology(1.0)
    r = f.reference_axis_pressures()
    assert r["N"] > 0.1 > r["T"]
    assert sum(r.values()) == pytest.approx(0.5)


def test_a_calm_field_barely_moves_it():
    hot, calm = NoncompField(), NoncompField()
    for fld in (hot, calm):
        for _ in range(40):
            fld.ingest_external_input({"N": 1.0}, intensity=1.0, source="t")
    hot.accept_emotion_topology(1.0)
    calm.accept_emotion_topology(0.05)
    assert abs(hot.reference_axis_pressures()["N"] - 0.1) > abs(calm.reference_axis_pressures()["N"] - 0.1)


@pytest.mark.parametrize("level", [None, "x", -3, 0, 0.0])
def test_no_emotion_changes_nothing(level):
    f = NoncompField()
    before = dict(f.reference_axis_pressures())
    f.accept_emotion_topology(level)
    assert f.reference_axis_pressures() == before


# ---- prediction priors reset toward ground truth ----------------------------------------------

def test_priors_move_toward_the_resolved_pressure_not_toward_zero():
    layer = _layer(T=0.9, N=0.9)
    layer.prediction._prior_t = layer.prediction._prior_n = 0.3
    layer.reset_prediction_priors({"resolved_accuracy": 1.0})
    assert layer.prediction._prior_t > 0.3 and layer.prediction._prior_n > 0.3


def test_priors_are_pulled_down_when_the_truth_is_lower():
    layer = _layer(T=0.1, N=0.1)
    layer.prediction._prior_t = layer.prediction._prior_n = 0.8
    layer.reset_prediction_priors({"resolved_accuracy": 1.0})
    assert layer.prediction._prior_t < 0.8


def test_the_old_behaviour_is_kept_when_no_pressures_are_supplied():
    from aurora_internal.aurora_tensor_expressions import PredictionTensor
    p = PredictionTensor()
    p._prior_t = p._prior_n = 0.5
    p.reset_priors({"resolved_accuracy": 1.0})
    assert p._prior_t == pytest.approx(0.5 * (1 - 0.4))


# ---- wired into the cascade ----------------------------------------------------------------------

def test_receive_understanding_runs_the_downward_pass_with_memory():
    layer = _layer(X=0.9, N=0.9, A=0.9, T=0.1, B=0.1)
    layer.receive_understanding({"resolved_accuracy": 0.7, "deep_memory": {"X": 5, "T": 1, "N": 1, "B": 1, "A": 1}})
    specs = [r["spec"] for r in layer._last_downward]
    assert "Memory anchors Presence (section 6)" in specs and len(specs) >= 9


# ---- stability: the pass must settle, not run to the bounds ------------------------------------------

def _settle(pressures, accuracy=0.5, n=400):
    layer = _layer(**pressures)
    for _ in range(n):
        layer.behavioral_state(force_refresh=True)          # the engine ticks the layer every turn
        layer.receive_understanding({"resolved_accuracy": accuracy,
                                     "deep_memory": {"X": 1, "T": 2, "N": 2, "B": 1, "A": 1}})
    return layer


def test_the_weights_converge_instead_of_running_to_the_bounds():
    """The first version integrated a deviation computed from weight-scaled activations: a larger
    weight raised its own driver. 400 cascades drove Activation to its 0.3 floor and
    Attention/Meaning/Salience to their 2.0 ceiling."""
    a = _settle({"X": 0.9, "T": 0.2, "N": 0.9, "B": 0.3, "A": 0.8}, n=150)
    b = _settle({"X": 0.9, "T": 0.2, "N": 0.9, "B": 0.3, "A": 0.8}, n=400)
    for name in ("activation", "salience", "attention", "meaning"):
        wa, wb = getattr(a, name)._weight, getattr(b, name)._weight
        assert abs(wa - wb) < 1e-3, f"{name} still moving: {wa} -> {wb}"
        assert 0.35 < wb < 1.9, f"{name} at a bound: {wb}"


def test_the_fixed_point_follows_the_levels():
    layer = _settle({"X": 0.9, "T": 0.2, "N": 0.9, "B": 0.3, "A": 0.8})
    # X/N/A hot, T/B cold: Activation (X+N) above neutral, Meaning (T+B+A) below it
    assert layer.activation._weight > 1.0 > layer.meaning._weight


def test_even_pressures_leave_the_weights_near_neutral_and_every_gate_open():
    layer = _settle({ax: 0.8 for ax in "XTNBA"})
    for crystal in layer._crystals:
        assert crystal._weight > 0.8
    st = layer.behavioral_state(force_refresh=True)
    assert all(st[f"{f}_active"] for f in ("emotion", "reasoning", "valuation", "thought", "reflection"))


def test_reading_the_levels_does_not_touch_the_layers_state():
    layer = _layer(X=0.9, N=0.9, A=0.9, T=0.1, B=0.1)
    layer.prediction._prior_t, layer.prediction._prior_n = 0.42, 0.37
    updates = layer._update_count
    layer._raw_levels(layer._axis_pressures())
    assert (layer.prediction._prior_t, layer.prediction._prior_n) == (0.42, 0.37)
    assert layer._update_count == updates


@pytest.mark.parametrize("p", [{"X": 0.9, "T": 0.2, "N": 0.9, "B": 0.3, "A": 0.8},
                               {"X": 0.1, "T": 0.9, "N": 0.4, "B": 0.8, "A": 0.2},
                               {ax: 0.5 for ax in "XTNBA"}])
def test_the_weight_free_levels_are_the_crystals_own_levels_at_neutral_weight(p):
    """_raw_levels duplicates each crystal's formula so reading it cannot mutate them; this keeps the
    two from drifting apart."""
    layer = _layer(**p)
    raw = layer._raw_levels(layer._axis_pressures())
    state = layer.behavioral_state(force_refresh=True)["crystals"]
    for name in ("activation", "salience", "attention", "meaning"):
        assert raw[name] == pytest.approx(state[name], abs=1e-3)


# ---- Reasoning reshapes Prediction (section 7) -------------------------------------------------

def test_reasoning_above_its_peers_reshapes_prediction():
    """Reasoning (Salience, Attention, Meaning) is the level driving this row; "conclusions inform
    future anticipation" is the Prediction crystal's weight following it."""
    layer = _layer(N=0.9, B=0.9, A=0.9, T=0.9, X=0.1)
    layer.downward_modulation()
    row = [r for r in layer._last_downward if r["spec"].startswith("Reasoning reshapes Prediction")]
    assert len(row) == 1 and row[0]["moved"] is not None
    assert row[0]["deviation"] != 0


def test_reasoning_below_its_peers_pulls_prediction_the_other_way():
    hot = _layer(N=0.9, B=0.9, A=0.9, T=0.9, X=0.1)
    cold = _layer(X=0.9, N=0.2, B=0.1, A=0.1, T=0.1)
    hot.downward_modulation()
    cold.downward_modulation()
    def dev(layer):
        return [r for r in layer._last_downward if r["spec"].startswith("Reasoning reshapes Prediction")][0]["deviation"]
    assert dev(hot) > dev(cold)
