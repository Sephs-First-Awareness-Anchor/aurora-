# Authors: Sunni (Sir) Morningstar & Cael Devo
"""The shape of an impact is carried in the pressure system's own terms (Sir, 2026-11-14).

A consequence carries the 5-axis pressure before and after and the relief between them, exactly as genealogy's
PressureVec.relief_from / ReliefRecord define them (higher pressure = worse; relief = before - after).  How finely a
memory is held then follows that SHAPE, not a flag: unknown shape is kept, measured-nil is ordinary, any measured
change (relief or harm) matters, repeats of a form already held are compacted into per-axis sums, and compaction
loses detail but never shape.
"""
from __future__ import annotations

import copy
import random

import pytest

from aurora_internal import evidence_qualification as Q
from aurora_internal.constraint_genealogy import AXES, PressureVec, ReliefRecord

S = "mara|like|tea"


def cons(target="cap:x", change="c", **kw):
    return {"target": target, "change": change, "attribution": kw.pop("attribution", []), **kw}


def ev(t=1, nonce="", relief=None, before=None, after=None, target="cap:x", change="c", negated=False, subject=S):
    c = cons(target, change)
    if relief is not None:
        c["relief"] = relief
    if before is not None:
        c["pressure_before"], c["pressure_after"] = before, after
    return Q.make_event(subject, occurrence="dreamed", t=t, nonce=nonce or str(t), negated=negated,
                        context={"world": "dreamed"}, consequence=c)


# -- the shape IS the pressure system's: same axes, same sign convention, same arithmetic ----------------------------

def test_the_axes_are_genealogys_axes_in_genealogys_order():
    assert Q.AXES == AXES


@pytest.mark.parametrize("seed", range(40))
def test_relief_and_shape_agree_with_pressurevec_relief_from(seed):
    rng = random.Random(seed)
    before = PressureVec(**{a: rng.random() for a in AXES})
    after = PressureVec(**{a: rng.random() for a in AXES})
    real = after.relief_from(before)                                   # genealogy's own: before - after
    mine = Q.shape_of(ev(before=before.to_dict(), after=after.to_dict()))
    for a in AXES:
        assert abs(mine["relief"][a] - real.to_dict()[a]) < 1e-8
    positive = round(sum(v for v in mine["relief"].values() if v > 0), 8)
    assert abs(positive - real.sum_positive_relief()) < 1e-7
    if real.dominant_positive_axis():
        top = max(AXES, key=lambda a: abs(mine["relief"][a]))
        assert mine["dominant"][0] == top


def test_a_real_reliefrecord_translates_into_a_consequence_without_recomputation():
    before, after = PressureVec(X=0.5, T=0.2, N=0.1, B=0.0, A=0.4), PressureVec(X=0.2, T=0.3, N=0.1, B=0.0, A=0.1)
    record = ReliefRecord(run_id="r", tick=3, state_sig_before="a", state_sig_after="b", pressure_before=before,
                          pressure_after=after, relief=after.relief_from(before), dominant_relief_axis="X", trace=[],
                          trace_cost_total={}, trace_risk_total={})
    c = Q.consequence_from_relief(record, target="link:L1", change="promoted", attribution=["e1", "e2"])
    assert c["relief"] == {a: round(v, 9) for a, v in record.relief.to_dict().items()}
    assert c["pressure_before"]["X"] == 0.5 and c["attribution"] == ["e1", "e2"] and c["attribution_complete"] is False
    e = Q.make_event(S, occurrence="simulated", t=1, context={"world": "simulated"}, consequence=c)
    assert Q.shape_of(e)["pattern"] == "+-00+" and Q.shape_of(e)["dominant"] == "X+"


def test_relief_that_contradicts_before_and_after_is_refused():
    with pytest.raises(ValueError):
        Q.make_event(S, occurrence="dreamed", t=1, context={"world": "dreamed"},
                     consequence=cons(pressure_before={"X": 0.5}, pressure_after={"X": 0.2}, relief={"X": 0.9}))
    with pytest.raises(ValueError):
        Q.make_event(S, occurrence="dreamed", t=1, context={"world": "dreamed"},
                     consequence=cons(pressure_before={"X": 0.5}))          # before without after
    with pytest.raises(ValueError):
        Q.make_event(S, occurrence="dreamed", t=1, context={"world": "dreamed"}, consequence=cons(relief={"Q": 1.0}))


def test_float_noise_does_not_make_a_replayed_event_a_different_event():
    a = ev(relief={"X": 0.3, "T": -0.1})
    b = ev(relief={"X": 0.3 + 1e-13, "T": -0.1 - 1e-13})
    assert a["id"] == b["id"]


# -- unknown is not zero; nil is ordinary; harm matters ------------------------------------------------------------

def test_an_unknown_shape_is_kept_a_measured_nil_is_ordinary_and_a_harm_matters():
    filler = [ev(t=i, relief={"X": 0.2}, nonce=f"f{i}") for i in range(10, 30)]
    unknown = ev(t=40, nonce="u")                                      # consequence, shape never measured
    nil = ev(t=41, nonce="n", relief={a: 0.0 for a in AXES})           # measured, and nothing moved
    harm = ev(t=42, nonce="h", relief={"X": -0.4, "N": -0.1}, target="cap:y")   # pressure ROSE
    why = Q.impact(filler + [unknown, nil, harm], S)
    assert "consequence" in why[unknown["id"]]
    assert nil["id"] not in why
    assert "shape_first" in why[harm["id"]] and "shape_strongest" in why[harm["id"]]
    assert Q.shape_of(harm)["dominant"] == "X-" and Q.shape_of(harm)["pattern"] == "-0-00"


def test_repeats_of_a_form_already_held_are_compacted_but_the_first_and_strongest_of_each_form_stay():
    same = [ev(t=i, relief={"X": 0.1 * (1 + (i % 7)), "T": -0.05}, nonce=str(i)) for i in range(100, 160)]
    other = ev(t=300, nonce="o", relief={"A": 0.2, "B": -0.1})
    view = Q.live_view(same + [other], S, budget=0)
    held = {e["id"] for e in view["detailed"]}
    strongest = max(same, key=lambda e: (Q.shape_of(e)["magnitude"], -e["t"]))
    assert same[0]["id"] in held and strongest["id"] in held and other["id"] in held
    assert len(view["detailed"]) <= 6 and view["rollup"]["shaped"] >= 55          # the rest are counts with shape


# -- compaction loses detail, never shape -------------------------------------------------------------------------

@pytest.mark.parametrize("seed", range(80))
def test_the_pressure_shape_of_the_view_equals_the_shape_of_the_whole_log(seed):
    rng = random.Random(seed)
    log = []
    for i in range(rng.randint(1, 50)):
        relief = rng.choice([None, {a: 0.0 for a in AXES},
                             {a: round(rng.uniform(-0.5, 0.5), 3) for a in AXES if rng.random() < 0.6}])
        log.append(ev(t=i, nonce=str(i), relief=relief, target=rng.choice(["cap:x", "cap:y"]),
                      change=f"c{rng.randint(0, 3)}"))
    whole = Q.log_shape(log, S)
    for budget in (0, 2, 8):
        view = Q.live_view(log, S, budget=budget)
        got = Q.view_shape(view)
        assert got["shaped"] == whole["shaped"], (seed, budget)
        assert all(abs(got["relief"][a] - whole["relief"][a]) < 1e-6 for a in AXES), (seed, budget)
        assert Q.view_problems(view, log) == [], (seed, budget)
        assert Q.view_qualification(view) == Q.qualification(Q.fold(log)), (seed, budget)


def test_a_view_that_relabels_or_drops_shape_is_caught():
    log = [ev(t=i, relief={"X": 0.1}, nonce=str(i)) for i in range(30)]
    view = Q.live_view(log, S, budget=0)
    forged = copy.deepcopy(view)
    forged["rollup"]["relief"]["X"] += 0.5
    assert Q.view_problems(forged, log)                                # the roll-up no longer matches its events


# -- demonstration reads the shape without letting replay noise inflate it -------------------------------------------

def test_the_effect_is_the_mean_shape_of_independent_consequences_and_replays_do_not_inflate_it():
    a = ev(t=1, change="linked", relief={"X": 0.4}, nonce="a")
    replay = ev(t=2, change="linked", relief={"X": 0.9}, nonce="b")            # same consequence re-run, noisy/bigger relief
    b = ev(t=3, change="refined", relief={"X": 0.2, "A": 0.2}, nonce="c")
    d = Q.demonstration([a, replay, b], "cap:x")
    assert d["independent"] == 2 and d["samples"] == 2
    assert d["effect"]["X"] == pytest.approx(0.3) and d["effect"]["A"] == pytest.approx(0.1)   # (0.4+0.2)/2: the first occurrence stands for its signature
    assert d["distinct_contexts"] == 1


def test_an_effect_is_absent_not_zero_when_no_shape_was_measured():
    d = Q.demonstration([ev(t=1, nonce="a")], "cap:x")
    assert d["effect"] == {} and d["samples"] == 0 and d["internal_demonstrated"]
