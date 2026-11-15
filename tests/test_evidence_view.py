# Authors: Sunni (Sir) Morningstar & Cael Devo
"""The live view: how finely a memory is held follows what it has done (Sir, 2026-11-14).

The full event log is the authority and is never shrunk; active cognition holds a derived view whose detail follows
impact (consequence, correction, contradiction, being relied on, first / latest), and ordinary repeats become counts.
These tests hold three properties: shrinking the view never changes the qualification (it is computed from the view
alone and must equal the whole log's), the log is never touched, and a memory that starts to matter regains its detail.
"""
from __future__ import annotations

import copy
import json
import random
import types

import pytest

from aurora_internal import aurora_propositional_understanding as P
from aurora_internal import evidence_qualification as Q

S = "mara|like|tea"


def ev(basis=None, **kw):
    kw.setdefault("t", 1)
    return Q.make_event(S, basis, **kw)


def _random_log(rng, n):
    events, ids = [], []
    for i in range(n):
        occ = rng.choice(["heard", "heard", "perceived", "dreamed", "simulated", "recalled", "tested", ""])
        basis = None
        if occ == "" or occ == "recalled":
            basis = rng.choice(["told", "unknown", "supposed", "observed"])
        if rng.random() < 0.12 and occ in ("heard", "read"):
            basis = "corrected"
        kw = {"t": i, "nonce": str(i), "negated": rng.random() < 0.35}
        if occ == "dreamed":
            kw["context"] = {"world": "dreamed"}
        if rng.random() < 0.15:
            kw["consequence"] = {"target": f"cap:{rng.randint(0, 2)}", "change": f"c{i}", "attribution": []}
        if ids and rng.random() < 0.2:
            kw["ancestry"] = [rng.choice(ids)]
        if rng.random() < 0.08 and occ == "":
            basis, kw["carried"] = "unknown", True
        e = Q.make_event(S, basis, occurrence=occ, **kw)
        events.append(e)
        ids.append(e["id"])
    return events


# -- the property that matters: shrinking never changes what the evidence says ---------------------------------------

@pytest.mark.parametrize("seed", range(120))
def test_the_qualification_computed_from_the_view_alone_equals_the_whole_logs(seed):
    rng = random.Random(seed)
    log = _random_log(rng, rng.randint(1, 40))
    whole = Q.qualification(Q.fold(log))
    for budget in (0, 1, 3, 8):
        view = Q.live_view(log, S, budget=budget)
        assert Q.view_qualification(view) == whole, (seed, budget)
        assert Q.view_problems(view, log) == [], (seed, budget)


def test_ordinary_repeats_become_counts_and_the_view_is_much_smaller_than_the_log():
    log = [ev("told", occurrence="heard", by="sunni", t=i, nonce=str(i)) for i in range(500)]
    view = Q.live_view(log, S, budget=8)
    assert len(view["detailed"]) <= 11 and view["rollup"]["events"] == 500 - len(view["detailed"])
    assert Q.view_qualification(view)["verdict"] == "held" and view["total"] == 500


# -- what mattered is held in full, whatever the budget -------------------------------------------------------------

def test_events_that_mattered_are_held_in_full_even_with_no_budget():
    plain = [ev("told", occurrence="heard", t=i, nonce=str(i)) for i in range(2, 40)]
    first = ev("told", occurrence="heard", t=1)
    corr = ev("corrected", occurrence="heard", t=20, negated=True, by="sunni", nonce="c")
    conseq = ev("supposed", occurrence="dreamed", t=25, context={"world": "dreamed"},
                consequence={"target": "cap:x", "change": "linked", "attribution": []}, nonce="q")
    relied = ev("told", occurrence="heard", t=30, nonce="relied")
    child = Q.make_event("d|r|m", occurrence="dreamed", t=50, ancestry=[relied["id"]], context={"world": "dreamed"})
    log = [first] + plain + [corr, conseq, relied, child]
    why = Q.impact(log, S)
    assert {"first", "correction", "consequence", "ancestor"} <= {r for rs in why.values() for r in rs}
    view = Q.live_view(log, S, budget=0)
    held = {e["id"] for e in view["detailed"]}
    assert {first["id"], corr["id"], conseq["id"], relied["id"]} <= held
    assert view["reasons"][corr["id"]] == ["correction"] and "ancestor" in view["reasons"][relied["id"]]


def test_the_losing_side_of_a_contradiction_and_overruled_events_are_kept():
    told = [ev("told", occurrence="heard", t=i, nonce=str(i)) for i in range(10)]
    denial = ev("told", occurrence="heard", negated=True, t=50, nonce="d")
    view = Q.live_view(told + [denial], S, budget=0)
    assert denial["id"] in {e["id"] for e in view["detailed"]}
    assert "contradiction" in view["reasons"][denial["id"]]
    corrected = told + [denial, ev("corrected", occurrence="heard", t=60, negated=True)]
    v2 = Q.live_view(corrected, S, budget=0)
    kept = {e["id"] for e in v2["detailed"]}
    assert all(t["id"] in kept for t in told)          # every told event was overruled by the correction: all of them matter
    assert Q.view_qualification(v2)["contradicted"] and Q.view_qualification(v2)["corrected"]


def test_ordinary_unconsequential_repeats_do_not_get_detail():
    log = [ev("told", occurrence="heard", t=i, nonce=str(i)) for i in range(40)]
    why = Q.impact(log, S)
    assert set(why) == {log[0]["id"], log[-1]["id"]}      # first, latest (= latest counted); nothing else mattered


# -- importance shows up late: the view is rebuilt from the log and regains detail ------------------------------------

def test_a_memory_that_starts_to_matter_regains_the_detail_that_was_counts():
    old = [ev("told", occurrence="heard", t=i, nonce=str(i)) for i in range(30)]
    before = Q.live_view(old, S, budget=2)
    middle = old[15]
    assert middle["id"] not in {e["id"] for e in before["detailed"]}
    later = Q.make_event("d|r|m", occurrence="dreamed", t=99, ancestry=[middle["id"]], context={"world": "dreamed"})
    after = Q.live_view(old + [later], S, budget=2)
    assert middle["id"] in {e["id"] for e in after["detailed"]} and "ancestor" in after["reasons"][middle["id"]]


def test_building_a_view_never_touches_the_log():
    rng = random.Random(3)
    log = _random_log(rng, 30)
    snapshot = copy.deepcopy(log)
    for b in (0, 5):
        Q.live_view(log, S, budget=b)
    assert log == snapshot and Q.violations(snapshot, log) == []
    assert Q.violations(log, Q.merge(log)) == []         # and every event is still there to rebuild from


# -- a view that no longer matches its log is caught ---------------------------------------------------------------

def test_view_problems_catches_an_invented_altered_or_miscounted_view():
    log = [ev("told", occurrence="heard", t=i, nonce=str(i)) for i in range(20)]
    view = Q.live_view(log, S, budget=2)
    assert Q.view_problems(view, log) == []
    forged = copy.deepcopy(view)
    forged["detailed"][0] = dict(forged["detailed"][0], by="someone else")
    assert any("differently" in p for p in Q.view_problems(forged, log))
    invented = copy.deepcopy(view)
    invented["detailed"].append(Q.make_event(S, "told", t=999, occurrence="heard", nonce="made up"))
    assert any("not in the log" in p for p in Q.view_problems(invented, log))
    miscounted = copy.deepcopy(view)
    miscounted["rollup"]["keys"][0]["count"] += 1
    assert Q.view_problems(miscounted, log)
    dropped = copy.deepcopy(view)
    dropped["detailed"].pop()
    assert any("exactly once" in p for p in Q.view_problems(dropped, log))
    relabelled = copy.deepcopy(view)
    relabelled["rollup"]["keys"][0]["basis"] = "observed"
    assert Q.view_problems(relabelled, log)               # counts may not be relabelled into stronger evidence


def test_a_view_survives_json():
    log = _random_log(random.Random(9), 25)
    view = Q.live_view(log, S, budget=2)
    again = json.loads(json.dumps(view))
    assert Q.view_qualification(again) == Q.view_qualification(view) and Q.view_problems(again, log) == []


# -- the store today holds its history by position, not impact (named, so it can be changed on purpose) ---------------

def test_the_stores_history_is_the_first_and_latest_by_position_not_by_what_mattered():
    """FIX-A137 keeps the first exposure and the latest seven, so a correction in the middle of a long history is
    evicted from `history` (its effect lives on in `settled`, but the event itself is gone).  This is the crude
    form of the live view; replacing it with impact-aware selection is a store change, not made here."""
    rel = types.SimpleNamespace(assertion=None)
    seq = ["told"] * 3 + ["corrected"] + ["told"] * 12
    for i, b in enumerate(seq):
        P._record_assertion(rel, predicate="like", surface="likes", negated=(b == "corrected"), modality="", speaker="sunni",
                            time_ref="", profile={}, context=str(i), basis=b)
    p = rel.assertion["predicates"]["like"]
    assert len(p["history"]) == P.MAX_HISTORY and p["settled"]
    assert "corrected" not in [h["b"] for h in p["history"]]            # the correction event itself is gone
    kept = Q.live_view([Q.make_event(S, b, occurrence="heard", negated=(b == "corrected"), t=i, nonce=str(i))
                        for i, b in enumerate(seq)], S, budget=0)
    assert "corrected" in [e["basis"] for e in kept["detailed"]]        # the impact-aware view keeps it
