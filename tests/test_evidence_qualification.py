# Authors: Sunni (Sir) Morningstar & Cael Devo
"""The contract that deferral must keep: how evidence is qualified, not only what it says.

Sir's integration requirement on the genealogy redistribution: the future environmental genealogy must preserve
"not just what was learned, but how the evidence is qualified, including hypothetical, observed, inferred,
contradicted, and corrected information."  These tests state that as properties, against the record the
propositional store already keeps, so the event log Stage 3 builds can be held to them.
"""
from __future__ import annotations

import json
import random
import types

import pytest

from aurora_internal import aurora_propositional_understanding as P
from aurora_internal import evidence_qualification as Q


def _ev(basis, negated=False, t=0, by="sunni", subject="mara|like|tea", **kw):
    return Q.make_event(subject, basis, negated=negated, by=by, t=t, **kw)


# -- hypothetical, inferred, unknown are kept and never counted ------------------------------------------------

def test_hypothetical_evidence_is_kept_recallable_as_hypothetical_and_never_becomes_held():
    rec = Q.fold([_ev("supposed", t=i, nonce=str(i)) for i in range(100)])
    q = Q.qualification(rec)
    assert q["verdict"] == "supposed" and q["hypothetical_only"] and rec["n"] == 0 and rec["supposed"] == 100


def test_an_inference_never_raises_confidence_in_its_own_premises():
    told = _ev("told", t=1)
    chain = [_ev("inferred", t=2 + i, derived_from=[told["id"]], nonce=str(i)) for i in range(50)]
    rec = Q.fold([told] + chain)
    assert rec["n"] == 1 and rec["inferred"] == 50 and Q.verdict(rec) == "held"
    only = Q.fold(chain)
    assert Q.qualification(only)["inferred_only"] and Q.verdict(only) == "inferred" and only["n"] == 0


def test_an_inference_must_say_what_it_was_derived_from():
    with pytest.raises(ValueError):
        Q.make_event("x", "inferred", t=1)


def test_an_unrecognised_basis_is_unknown_kept_and_never_upgraded_to_told():
    ev = Q.make_event("x|y|z", "hearsay", t=1)
    assert ev["basis"] == "unknown"
    rec = Q.fold([ev])
    assert rec["n"] == 0 and rec["unknown"] == 1 and Q.verdict(rec) == "unsaid"
    assert Q.basis_of_stream("telepathy") == "unknown" and Q.basis_of_stream("") == "unknown"
    assert Q.basis_of_stream("dream") == "supposed" and Q.basis_of_stream("user_input") == "observed"


# -- contradicted and corrected -------------------------------------------------------------------------------

def test_told_and_denied_about_equally_is_contested_and_flagged_contradicted_not_resolved():
    rec = Q.fold([_ev("told", t=1), _ev("told", negated=True, t=2)])
    q = Q.qualification(rec)
    assert q["verdict"] == "contested" and q["contradicted"] and not q["corrected"]


def test_a_correction_settles_the_verdict_and_the_contradiction_it_settled_stays_visible():
    events = [_ev("told", t=1), _ev("told", t=2), _ev("corrected", negated=True, t=3)]
    rec = Q.fold(events)
    q = Q.qualification(rec)
    assert q["verdict"] == "denied" and q["corrected"] and q["contradicted"]
    assert [e["basis"] for e in rec["history"]] == ["told", "told", "corrected"]     # what it corrected is still there
    # a later correction the other way decides instead
    later = Q.fold(events + [_ev("corrected", negated=False, t=4)])
    assert Q.verdict(later) == "held" and Q.qualification(later)["corrected"]


def test_observed_evidence_is_counted_like_told_and_reported_as_the_latest_basis():
    rec = Q.fold([_ev("told", t=1), _ev("observed", t=2)])
    q = Q.qualification(rec)
    assert q["verdict"] == "held" and q["latest_basis"] == "observed" and q["basis"] == {"told": 1, "observed": 1}


# -- deferral safety: order, replay, merge, loss --------------------------------------------------------------

def _random_events(rng, n, bases=("told", "observed", "corrected", "supposed", "inferred")):
    told = _ev("told", t=0, nonce="root")
    evs = [told]
    for i in range(1, n):
        b = rng.choice(bases)
        evs.append(_ev(b, negated=rng.random() < 0.35, t=i, nonce=str(i),
                       **({"derived_from": [told["id"]]} if b == "inferred" else {})))
    return evs


def test_the_fold_does_not_depend_on_the_order_events_arrive_in():
    rng = random.Random(5)
    for _ in range(40):
        evs = _random_events(rng, rng.randint(1, 12))
        shuffled = list(evs)
        rng.shuffle(shuffled)
        assert Q.fold(evs) == Q.fold(shuffled)


def test_replay_is_not_new_experience():
    rng = random.Random(6)
    for _ in range(30):
        evs = _random_events(rng, rng.randint(1, 10))
        once, twice = Q.fold(evs), Q.fold(evs + evs + evs[:3])
        assert once == twice
        assert once["n"] + once["supposed"] + once["inferred"] + once["unknown"] == len(evs)


def test_merge_is_a_union_by_event_id_commutative_associative_and_idempotent():
    rng = random.Random(7)
    evs = _random_events(rng, 12)
    a, b, c = evs[:5], evs[3:9], evs[7:]
    assert Q.merge(a, b) == Q.merge(b, a)
    assert Q.merge(Q.merge(a, b), c) == Q.merge(a, Q.merge(b, c))
    assert Q.merge(a, a) == Q.merge(a)
    assert {e["id"] for e in Q.merge(a, b, c)} == {e["id"] for e in evs}


def test_the_same_id_recorded_two_ways_is_a_conflict_and_nothing_is_dropped_to_hide_it():
    ev = _ev("supposed", t=1)
    forged = dict(ev, basis="told")                    # the same id, laundered from an example into testimony
    with pytest.raises(Q.EvidenceConflict):
        Q.merge([ev], [forged])


def test_violations_name_what_a_deferral_dropped_or_rewrote_and_allow_what_it_added():
    base = [_ev("told", t=1), _ev("supposed", t=2), _ev("observed", t=3)]
    assert Q.violations(base, base + [_ev("told", t=4)]) == []              # later evidence is fine
    assert any("dropped" in v for v in Q.violations(base, base[:2]))
    laundered = [dict(base[1], basis="told")] + [base[0], base[2]]
    assert any("was supposed and is now told" in v for v in Q.violations(base, laundered))
    rewritten = [dict(base[0], by="someone else")] + base[1:]
    assert any("rewritten" in v for v in Q.violations(base, rewritten))


def test_a_record_survives_the_trip_through_json_that_a_durable_log_takes():
    rng = random.Random(8)
    evs = _random_events(rng, 9)
    again = json.loads(json.dumps(evs))
    assert Q.fold(again) == Q.fold(evs)
    assert Q.qualification(Q.fold(again)) == Q.qualification(Q.fold(evs))


def test_one_record_folds_one_subject():
    with pytest.raises(ValueError):
        Q.fold([_ev("told", subject="a|b|c", t=1), _ev("told", subject="d|e|f", t=2)])


# -- the same view over what the propositional store keeps today --------------------------------------------------

def _stored(events):
    """Say the same events through the propositional store's own recorder and return its predicate record."""
    rel = types.SimpleNamespace(assertion=None)
    for e in events:
        P._record_assertion(rel, predicate="like", surface="likes", negated=e["negated"], modality="",
                            speaker=e["by"], time_ref="", profile={}, context="", basis=e["basis"])
    return dict(rel.assertion["predicates"]["like"])


@pytest.mark.parametrize("seed", range(25))
def test_the_contract_agrees_with_the_propositional_store_on_what_it_already_keeps(seed):
    rng = random.Random(seed)
    # the store keeps these four bases; inference and unknown are not stored there (see the next test)
    events = [_ev(rng.choice(["told", "observed", "corrected", "supposed"]), negated=rng.random() < 0.4, t=i, nonce=str(i))
              for i in range(rng.randint(1, 7))]                       # <= 7: inside the store's bounded history
    mine = Q.qualification(Q.fold(events))
    theirs = Q.qualification_of_predicate(_stored(events))
    for key in ("verdict", "basis", "latest_basis", "contradicted", "corrected", "hypothetical_only"):
        assert mine[key] == theirs[key], (key, mine, theirs, [(e["basis"], e["negated"]) for e in events])
    assert theirs["verdict"] == P.verdict(_stored(events))


def test_what_the_propositional_store_does_not_yet_keep_apart_is_named_here_so_it_cannot_be_forgotten():
    """The store records a missing or unrecognised basis as `told` (an upgrade of unknown evidence into testimony)
    and has no `inferred` basis.  An event log built on this contract must not inherit that.  If the store is
    changed, this test is the thing that says the contract and the store now agree."""
    stored = _stored([types.SimpleNamespace(**{"basis": "hearsay", "negated": False, "by": "sunni"}).__dict__])
    assert stored["basis"] == {"told": 1} and stored["n"] == 1                 # the upgrade, today
    rec = Q.fold([Q.make_event("x|y|z", "hearsay", t=1)])
    assert rec["n"] == 0 and rec["basis"] == {"unknown": 1}                    # the contract does not
