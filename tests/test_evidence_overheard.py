# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Told means addressed or directly involved; overheard is curiosity and is never held as truth unless it is
confirmed through the told route (Sir, 2026-11-14)."""
from __future__ import annotations

import random

import pytest

from aurora_internal import evidence_qualification as Q

S = "teo|is|brother"


def ev(**kw):
    kw.setdefault("t", 1)
    return Q.make_event(S, **kw)


def test_an_overheard_utterance_is_a_real_event_but_says_nothing():
    e = ev(occurrence="overheard", by="tv", nonce="a")
    rec = Q.fold([e])
    assert e["basis"] == "unknown" and rec["n"] == 0 and Q.verdict(rec) == "unsaid"
    q = Q.qualification(rec)
    assert q["overheard_only"] and not q["overheard_confirmed"] and q["occurrence"] == {"overheard": 1}


@pytest.mark.parametrize("basis", ["told", "observed", "corrected", "supposed", "inferred"])
def test_overheard_cannot_carry_any_basis_but_unknown(basis):
    with pytest.raises(ValueError):
        ev(occurrence="overheard", basis=basis)


def test_a_denial_overheard_does_not_deny_and_a_correction_overheard_does_not_correct():
    told = ev(occurrence="heard", by="sunni", nonce="t")
    over = ev(occurrence="overheard", negated=True, by="tv", nonce="o", t=2)
    assert Q.verdict(Q.fold([told, over])) == "held" and not Q.qualification(Q.fold([told, over]))["contradicted"]


@pytest.mark.parametrize("n", [1, 3, 25])
def test_any_amount_of_overhearing_never_becomes_held(n):
    rec = Q.fold([ev(occurrence="overheard", t=i, nonce=str(i)) for i in range(n)])
    assert rec["n"] == 0 and Q.verdict(rec) == "unsaid"


def test_it_is_held_only_when_confirmed_through_the_told_route():
    over = ev(occurrence="overheard", nonce="o")
    told = ev(occurrence="heard", by="sunni", t=5, nonce="t", ancestry=[over["id"]])
    q = Q.qualification(Q.fold([over, told]))
    assert q["verdict"] == "held" and q["overheard_confirmed"] and not q["overheard_only"]
    assert Q.fold([over, told])["n"] == 1                                   # the overhearing added nothing; the telling did


def test_overhearing_is_lived_so_it_grounds_ancestry_but_never_counts_as_the_world_confirming_it():
    over = ev(occurrence="overheard", nonce="o")
    child = ev(occurrence="derived", nonce="d", t=3, derived_from=[over["id"]])
    assert Q.grounding([over, child], child["id"])["lived_roots"] == [over["id"]]
    c = {"target": "x", "change": "y", "attribution": [over["id"]]}
    dem = Q.demonstration([over, Q.make_event("x|y|-", occurrence="overheard", t=2, nonce="c", consequence=c)], "x|y|-")
    assert dem["applicability"] != "external_supported"


@pytest.mark.parametrize("address,stream,expect", [
    ("direct", "user_input", "heard"), ("direct", "", "heard"),
    ("mention", "user_input", "overheard"), ("ambient", "user_input", "overheard"), ("ambient", "", "overheard"),
    ("AMBIENT", "user_input", "overheard"),
    ("", "user_input", "heard"), ("", "", ""), ("who knows", "user_input", "heard"),         # no address: nothing guessed
    ("ambient", "knowledge_feed", "read"), ("ambient", "sensor_data", "perceived"),          # only speech is re-read
    ("ambient", "simulation", "simulated"), ("direct", "knowledge_feed", "read")])
def test_the_address_decides_whether_speech_is_testimony(address, stream, expect):
    assert Q.occurrence_of_address(address, stream) == expect


def test_dream_replay_stays_a_dream_whatever_the_address_says():
    assert Q.occurrence_of_address("ambient", "knowledge_feed", "dream_replay") == "dreamed"


@pytest.mark.parametrize("seed", range(40))
def test_overheard_never_changes_a_verdict_and_the_view_agrees(seed):
    rng = random.Random(seed)
    base, mixed = [], []
    for i in range(rng.randint(1, 12)):
        occ = rng.choice(["heard", "heard", "perceived"])
        e = Q.make_event(S, occurrence=occ, t=i * 2, nonce=f"b{i}", negated=rng.random() < 0.3)
        base.append(e); mixed.append(e)
        for j in range(rng.randint(0, 3)):
            mixed.append(Q.make_event(S, occurrence="overheard", t=i * 2 + 1, nonce=f"o{i}{j}", negated=rng.random() < 0.5))
    a, b = Q.qualification(Q.fold(base)), Q.qualification(Q.fold(mixed))
    for k in ("verdict", "contradicted", "corrected", "hypothetical_only"):
        assert a[k] == b[k]
    assert Q.fold(base)["n"] == Q.fold(mixed)["n"] and Q.fold(base)["denied"] == Q.fold(mixed)["denied"]
    for budget in (0, 2):
        view = Q.live_view(mixed, S, budget=budget)
        assert Q.view_qualification(view) == b and Q.view_problems(view, mixed) == []


def test_live_guard_ambient_tagged_speech_does_not_become_a_stated_fact():
    """The daemon notes every overheard utterance in working memory as "[ambient:<class>] text".  That tagging is what
    keeps TV and other people's talk out of `stated_facts` today; this pins it so a change to the tag cannot let
    overheard speech be learned as told."""
    import aurora_working_memory as W
    wm = W.WorkingMemory()
    wm.note_user_facts("grass is green")                                  # the same sentence, addressed, is learned
    assert "grass" in wm.stated_facts
    before = {k: repr(v) for k, v in wm.stated_facts.items()}
    for role in ("ambient", "mention"):
        wm.note_user_facts(f"[ambient:{role}] the sky is purple")
        wm.note_user_facts(f"[ambient:{role}] water is dry")
    assert {k: repr(v) for k, v in wm.stated_facts.items()} == before
