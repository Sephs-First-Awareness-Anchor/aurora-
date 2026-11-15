# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Impact is tied to the received or environmental input (Sir, 2026-11-14).

Her lower subsystems (emotion, development) are all measured through pressure, so an input's impact is read from the
pressure it imposed and from the relief each subsystem was measured to undergo because of it, in the one 5-axis
language, with the effect naming the input it answers.  Nothing here is asserted importance.
"""
from __future__ import annotations

import copy
import random
import types

import pytest

from aurora_internal import evidence_qualification as Q
from aurora_internal.aurora_input_pressure import content_axis_loads

S = "mara|like|tea"


def _perception(words):
    entries = {w: types.SimpleNamespace(noncomp_id=nc) for w, nc in words.items()}
    return types.SimpleNamespace(lexicon=types.SimpleNamespace(entries=entries))


PERCEPTION = _perception({"noun": "X:MAGNITUDE", "scared": "X:MAGNITUDE", "terrible": "B:DIFFERENCE", "calm": "N:COST",
                          "thanks": "A:OPERATOR"})


def heard(text, t, **kw):
    loads = content_axis_loads(PERCEPTION, text)             # the function the live turn injects into the identity field
    return Q.make_event(S, occurrence="heard", t=t, nonce=text, by="sunni",
                        **({"input_pressure": loads} if loads is not None else {}), **kw)


def effect(of, t, relief, by="emotion", target="state:calm", change="moved"):
    c = {"target": target, "change": change, "attribution": [of["id"]], "measured_by": by}
    if relief is not None:
        c["relief"] = relief
    # a lower subsystem's own measurement of her state: observed by her, producer occurrence unspecified
    return Q.make_event("state|moved|-", "observed", t=t, nonce=f"{of['id']}{t}{by}", consequence=c)


# -- the input's own pressure, as the intake measures it --------------------------------------------------------------

def test_the_inputs_pressure_is_the_intakes_measurement_carried_not_recomputed():
    scared = heard("noun scared terrible", 1)
    assert scared["input_pressure"] == {"X": 1.0, "T": 0.0, "N": 0.0, "B": 0.5, "A": 0.0}
    sh = Q.input_shape_of(scared)
    assert sh["dominant"] == "X" and sh["profile"] == "X..B." and sh["peak"] == 1.0


def test_an_input_that_loaded_no_axis_has_unknown_pressure_not_zero_pressure():
    assert content_axis_loads(PERCEPTION, "hello there") is None
    e = heard("hello there", 1)
    assert "input_pressure" not in e and Q.input_shape_of(e) is None
    assert Q.input_shape_of(Q.make_event(S, occurrence="heard", t=1, input_pressure={})) is not None   # measured, loaded nothing
    assert Q.input_shape_of(Q.make_event(S, occurrence="heard", t=1, input_pressure={}))["dominant"] == ""


@pytest.mark.parametrize("bad", [{"X": -0.1}, {"X": float("nan")}, {"X": float("inf")}, {"Q": 1.0}])
def test_input_pressure_must_be_finite_nonnegative_and_on_the_real_axes(bad):
    with pytest.raises(ValueError):
        Q.make_event(S, occurrence="heard", t=1, input_pressure=bad)


def test_input_pressure_is_part_of_identity_when_set_and_old_events_keep_their_ids():
    plain = Q.make_event(S, occurrence="heard", t=1)
    assert plain["id"] != Q.make_event(S, occurrence="heard", t=1, input_pressure={"X": 1.0})["id"]
    assert plain["id"] == Q.make_event(S, occurrence="heard", t=1, input_pressure=None)["id"]


# -- impact is measured separately from evidence status ------------------------------------------------------------

@pytest.mark.parametrize("seed", range(40))
def test_pressure_never_changes_what_the_evidence_says(seed):
    rng = random.Random(seed)
    plain, loaded = [], []
    for i in range(rng.randint(1, 15)):
        occ = rng.choice(["heard", "perceived", "dreamed", "simulated"])
        kw = dict(occurrence=occ, t=i, nonce=str(i), negated=rng.random() < 0.3,
                  **({"context": {"world": occ}} if occ in ("dreamed", "simulated") else {}))
        plain.append(Q.make_event(S, **kw))
        loaded.append(Q.make_event(S, input_pressure={a: rng.random() for a in Q.AXES}, **kw))
    assert Q.qualification(Q.fold(plain)) == Q.qualification(Q.fold(loaded))


def test_a_dream_that_imposes_pressure_is_still_a_dream_and_counts_as_nothing_said():
    d = Q.make_event(S, occurrence="dreamed", t=1, context={"world": "dreamed"}, input_pressure={"X": 1.0, "B": 1.0})
    rec = Q.fold([d])
    assert rec["n"] == 0 and Q.qualification(rec)["hypothetical_only"]


# -- what the input did, as each lower subsystem measured it ---------------------------------------------------------

def test_effects_are_read_per_lower_subsystem_and_pair_with_what_came_in():
    inp = heard("scared terrible", 1)
    log = [inp, effect(inp, 2, {"X": 0.3, "B": -0.1}, by="emotion"),
           effect(inp, 3, {"A": 0.2}, by="development", target="cap:x", change="refined"),
           effect(inp, 4, None, by="development", target="cap:y", change="unmeasured thing")]
    fx = Q.effects_of(log, inp["id"])
    assert fx["input"]["dominant"] == "XB" and fx["independent"] == 3 and fx["unmeasured"] == 1   # both peak: a tie, kept as one
    assert set(fx["by_subsystem"]) == {"emotion", "development"}
    emo, dev = fx["by_subsystem"]["emotion"], fx["by_subsystem"]["development"]
    assert emo["relief"]["X"] == 0.3 and emo["relief"]["B"] == -0.1 and emo["pattern"] == "+00-0"
    assert dev["samples"] == 1 and dev["effects"] == 2 and dev["relief"]["A"] == 0.2


def test_the_same_relief_measured_by_different_subsystems_is_two_effects_and_a_replay_is_one():
    inp = heard("scared", 1)
    a = effect(inp, 2, {"X": 0.3}, by="emotion")
    b = effect(inp, 3, {"X": 0.3}, by="development")
    rerun = effect(inp, 4, {"X": 0.9}, by="emotion")                        # same effect re-run, larger noise
    fx = Q.effects_of([inp, a, b, rerun], inp["id"])
    assert fx["independent"] == 2
    assert fx["by_subsystem"]["emotion"]["relief"]["X"] == 0.3                # the first occurrence stands for the signature


def test_an_effect_that_names_a_different_input_is_not_this_inputs():
    one, two = heard("scared", 1), heard("calm", 2)
    log = [one, two, effect(two, 3, {"N": 0.4})]
    assert Q.effects_of(log, one["id"])["independent"] == 0
    assert Q.effects_of(log, two["id"])["independent"] == 1


def test_a_recollection_is_not_an_effect():
    inp = heard("scared", 1)
    recalled = Q.make_event("state|moved|-", occurrence="recalled", basis="supposed", t=5, ancestry=[inp["id"]],
                            consequence={"target": "state:calm", "change": "moved", "attribution": [inp["id"]],
                                         "relief": {"X": 0.5}, "measured_by": "emotion"})
    assert Q.effects_of([inp, recalled], inp["id"])["independent"] == 0


# -- fineness follows what the input did ----------------------------------------------------------------------------

def test_an_input_is_held_by_what_it_did_nil_effects_do_not_hold_it_unknown_and_real_ones_do():
    filler = [heard("calm", i) for i in range(10, 40)]
    nil = heard("scared", 50)
    real = heard("terrible", 51)
    unmeasured = heard("thanks", 52)
    unrelated = heard("noun", 53)
    log = filler + [nil, real, unmeasured, unrelated,
                    effect(nil, 60, {a: 0.0 for a in Q.AXES}), effect(real, 61, {"B": 0.4}),
                    effect(unmeasured, 62, None)]
    why = Q.impact(log, S)
    assert nil["id"] not in why                                              # every recorded effect was measured nil
    assert "effect" in why[real["id"]] and "effect" in why[unmeasured["id"]]
    assert "effect" not in why.get(unrelated["id"], [])


def test_being_relied_on_as_ancestry_is_still_its_own_reason_separate_from_effects():
    base = heard("scared", 1)
    child = Q.make_event("d|r|m", occurrence="dreamed", t=9, ancestry=[base["id"]], context={"world": "dreamed"})
    assert "ancestor" in Q.impact([base, child], S)[base["id"]]
    assert "effect" not in Q.impact([base, child], S)[base["id"]]


# -- compaction keeps what came in, as well as what it did -------------------------------------------------------------

@pytest.mark.parametrize("seed", range(60))
def test_the_input_pressure_of_the_view_equals_the_whole_logs_and_every_other_property_still_holds(seed):
    rng = random.Random(seed)
    log, inputs = [], []
    texts = ["scared", "terrible", "calm", "thanks", "noun", "hello there", "scared terrible calm"]
    for i in range(rng.randint(1, 40)):
        e = heard(rng.choice(texts), i)
        if e["id"] in {x["id"] for x in log}:
            continue
        log.append(e)
        inputs.append(e)
        if rng.random() < 0.4:
            log.append(effect(e, i + 1000, rng.choice([None, {a: 0.0 for a in Q.AXES}, {"X": round(rng.random(), 3)}]),
                              by=rng.choice(["emotion", "development"])))
    whole = Q.log_input_shape(log, S)
    for budget in (0, 3):
        view = Q.live_view(log, S, budget=budget)
        got = Q.view_input_shape(view)
        assert got["measured"] == whole["measured"]
        assert all(abs(got["loads"][a] - whole["loads"][a]) < 1e-6 for a in Q.AXES)
        assert Q.view_problems(view, log) == []
        assert Q.view_qualification(view) == Q.qualification(Q.fold([e for e in log if e["subject"] == S]))


def test_a_view_that_lost_the_input_pressure_of_what_it_compacted_is_caught():
    log = [heard("scared terrible", i) for i in range(20)] + [heard("noun", 99)]
    view = Q.live_view(log, S, budget=0)
    forged = copy.deepcopy(view)
    forged["rollup"]["input"]["loads"]["X"] += 1.0
    assert Q.view_problems(forged, log)
