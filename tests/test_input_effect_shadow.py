# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Read-only shadow of what each input did to each representation (Sir, 2026-11-14).  It records; it decides nothing."""
from __future__ import annotations

import copy

import pytest

from aurora_internal import aurora_input_identity as I
from aurora_internal import evidence_qualification as Q
from aurora_internal.constraint_genealogy import (AXES, ConstraintGenealogyLogger, GenealogyConfig, PressureVec,
                                                  TraceItem)

HI, LO = PressureVec(X=0.9, T=0.4, N=0.1, B=0.1, A=0.1), PressureVec(X=0.2, T=0.4, N=0.1, B=0.5, A=0.1)


def make(tmp_path, name):
    return ConstraintGenealogyLogger(name, config=GenealogyConfig(), output_dir=str(tmp_path / name))


def abilities(gen, k=2):
    return [TraceItem("ABILITY", i) for i in list(gen.abilities)[:k]]


def one_input(gen, trace, text="scared", turn="t1", ticks=3):
    token = I.begin_input(turn, text, loads={"X": 1.0}, t=1)
    try:
        for _ in range(ticks):
            gen.observe(HI, trace, LO)
        return I.current_event()
    finally:
        I.end_input(token)


def test_it_records_one_aggregate_per_input_and_representation_not_one_per_tick(tmp_path):
    g = make(tmp_path, "a")
    tr = abilities(g)
    inp = one_input(g, tr, ticks=4)
    rows = g.input_effects(inp["id"])
    assert sorted(r["target"] for r in rows) == sorted(t.id for t in tr)
    assert all(r["n"] == 4 and r["crowd"] == 2 for r in rows)
    measured = [r for r in g._event_log][-4:]                                         # what genealogy itself measured
    assert len(measured) == 4
    for r in rows:
        for ax in AXES:
            assert r["relief"][ax] == pytest.approx(sum(m.relief.to_dict()[ax] for m in measured))   # carried, not recomputed


def test_it_sees_exactly_the_ticks_the_real_attribution_sees(tmp_path):
    g = make(tmp_path, "b")
    tr = abilities(g, 1)
    before = {t.id: int((g.abilities[t.id].consequence_profile or {}).get("samples", 0)) for t in tr}
    inp = one_input(g, tr, ticks=5)
    for t in tr:
        samples = int((g.abilities[t.id].consequence_profile or {}).get("samples", 0)) - before[t.id]
        shadow = next(r for r in g.input_effects(inp["id"]) if r["target"] == t.id)
        assert samples == shadow["n"] == 5


def test_a_synthetic_self_assessment_is_skipped_exactly_as_the_real_one_skips_it(tmp_path):
    g = make(tmp_path, "c")
    tr = abilities(g, 1)
    token = I.begin_input("t", "x")
    try:
        g.observe(HI, tr, LO, notes={"synthetic_self_assessment": True})
        inp = I.current_event()
    finally:
        I.end_input(token)
    assert g.input_effects(inp["id"]) == []


def test_an_observation_that_names_no_input_is_counted_never_guessed(tmp_path):
    g = make(tmp_path, "d")
    g.observe(HI, abilities(g), LO)
    assert g._input_effects_unattributed == 2 and not g._input_effects            # one per representation credited


def test_no_trace_means_nothing_to_record(tmp_path):
    g = make(tmp_path, "e")
    token = I.begin_input("t", "x")
    try:
        g.observe(HI, [], LO)
        inp = I.current_event()
    finally:
        I.end_input(token)
    assert g.input_effects(inp["id"]) == []


def test_the_shadow_changes_no_measurement_and_no_real_profile(tmp_path):
    a, b = make(tmp_path, "f1"), make(tmp_path, "f2")
    ta, tb = abilities(a), abilities(b)
    one_input(a, ta, ticks=4)
    for _ in range(4):
        b.observe(HI, tb, LO)                                                          # same, with no input named
    for x, y in zip(ta, tb):
        assert a.abilities[x.id].consequence_profile == b.abilities[y.id].consequence_profile
    assert a.relief_event_count == b.relief_event_count and a.tick_count == b.tick_count


def test_a_failure_in_the_shadow_never_affects_the_observation(tmp_path, monkeypatch):
    g = make(tmp_path, "g")
    monkeypatch.setattr(g, "_input_effects", None)                                     # make every shadow access raise
    token = I.begin_input("t", "x")
    try:
        assert g.observe(HI, abilities(g), LO) is not None
    finally:
        I.end_input(token)


def test_the_shadow_is_bounded(tmp_path):
    g = make(tmp_path, "h")
    tr = abilities(g, 1)
    for k in range(4200):
        token = I.begin_input(f"t{k}", f"w{k}")
        try:
            g._shadow_input_effect(tr[0].id, {"X": 0.5}, 1, {"input_event": f"i{k}"})
        finally:
            I.end_input(token)
    assert len(g._input_effects) == 4096


def test_rows_become_independent_consequences_the_contract_can_read(tmp_path):
    g = make(tmp_path, "i")
    tr = abilities(g)
    inp = one_input(g, tr, ticks=3)
    events = Q.consequences_from_input_effects(inp["id"], g.input_effects(inp["id"]), t=2)
    fx = Q.effects_of([inp] + events, inp["id"])
    assert fx["independent"] == 2 and fx["by_subsystem"]["development"]["samples"] == 2     # 3 ticks x 2 items = 2, not 6
    assert all(e["consequence"]["attribution_complete"] is False for e in events)             # measured with another active
    assert fx["input"]["dominant"] == "X"


def test_a_representation_measured_alone_is_a_complete_attribution(tmp_path):
    g = make(tmp_path, "j")
    inp = one_input(g, abilities(g, 1), ticks=2)
    ev = Q.consequences_from_input_effects(inp["id"], g.input_effects(inp["id"]), t=2)[0]
    assert ev["consequence"]["attribution_complete"] is True and ev["consequence"]["change"] == "relieved:X"


def test_no_relief_is_unchanged_not_relieved():
    ev = Q.consequences_from_input_effects("i", [{"target": "B:X", "n": 3, "crowd": 1, "relief": {a: 0.0 for a in AXES}}])[0]
    assert ev["consequence"]["change"] == "unchanged"
    assert Q.consequences_from_input_effects("i", [{"target": "B:X", "n": 1, "crowd": 1, "relief": {"B": -0.4}}])[0][
        "consequence"]["change"] == "loaded:B"


def test_a_representation_the_real_attribution_skips_is_not_recorded(tmp_path):
    g = make(tmp_path, "k")
    ghost = TraceItem("ABILITY", "NOT:A_REAL_REPRESENTATION")
    real = abilities(g, 1)
    inp = one_input(g, real + [ghost], ticks=2)
    assert [r["target"] for r in g.input_effects(inp["id"])] == [real[0].id]


def test_a_covered_pair_is_credited_to_its_promoted_link_exactly_as_the_real_one_credits_it(tmp_path):
    g = make(tmp_path, "l")
    a, b = abilities(g, 2)
    for _ in range(400):                                                                # a real, natural promotion
        g.observe(HI, [a, b], LO)
        if g.links:
            break
    assert g.links, "the pair should have been promoted by repeated measured relief"
    link_id = g._links_by_parents[(a.id, b.id)]
    before = int((g.links[link_id].consequence_profile or {}).get("samples", 0))
    inp = one_input(g, [a, b], ticks=3)
    rows = g.input_effects(inp["id"])
    assert [r["target"] for r in rows] == [link_id]                                     # the link, not R and S separately
    assert rows[0]["n"] == int((g.links[link_id].consequence_profile or {}).get("samples", 0)) - before == 3
