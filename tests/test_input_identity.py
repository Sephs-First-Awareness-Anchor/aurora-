# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Measured relief can be traced to the input it answers (Sir, 2026-11-14).  Identity only: no measurement changes."""
from __future__ import annotations

import ast
import pathlib
import threading

import pytest

from aurora_internal import aurora_input_identity as I
from aurora_internal import evidence_qualification as Q
from aurora_internal.constraint_genealogy import ConstraintGenealogyLogger, GenealogyConfig, PressureVec

HI, LO = PressureVec(X=0.9, T=0.1, N=0.1, B=0.1, A=0.1), PressureVec(X=0.2, T=0.1, N=0.1, B=0.1, A=0.1)


@pytest.fixture()
def gen(tmp_path):
    return ConstraintGenealogyLogger("input_identity_test", config=GenealogyConfig(), output_dir=str(tmp_path))


def test_nothing_is_named_when_no_input_is_being_processed():
    assert I.note_for_observe() == {} and I.current_event() is None


def test_the_identity_is_an_evidence_event_whose_occurrence_follows_the_address():
    direct = I.make_input_event("t1", "hello", address="direct", t=5)
    ambient = I.make_input_event("t1", "hello", address="ambient", t=5)
    assert direct["occurrence"] == "heard" and ambient["occurrence"] == "overheard"
    assert direct["id"] != ambient["id"]
    assert direct["id"] == I.make_input_event("t1", "hello", address="direct", t=5)["id"]          # deterministic
    assert direct["id"] != I.make_input_event("t2", "hello", address="direct", t=5)["id"]          # another turn, another input
    assert direct["id"] != I.make_input_event("t1", "goodbye", address="direct", t=5)["id"]


def test_the_intakes_pressure_is_carried_and_unknown_pressure_is_not_zero():
    with_loads = I.make_input_event("t", "x", loads={"X": 1.0}, t=1)
    assert with_loads["input_pressure"]["X"] == 1.0 and set(with_loads["input_pressure"]) == set(Q.AXES)
    assert "input_pressure" not in I.make_input_event("t", "x", loads=None, t=1)


def test_the_note_exists_only_between_begin_and_end_and_nests_cleanly():
    outer = I.begin_input("outer", "a")
    o = I.note_for_observe()["input_event"]
    inner = I.begin_input("inner", "b")
    assert I.note_for_observe()["input_event"] != o
    I.end_input(inner)
    assert I.note_for_observe()["input_event"] == o
    I.end_input(outer)
    assert I.note_for_observe() == {}


def test_a_thread_started_by_the_turn_carries_no_identity_it_is_unattributed_not_guessed():
    token = I.begin_input("t", "a")
    seen = []
    th = threading.Thread(target=lambda: seen.append(I.note_for_observe()))
    th.start(); th.join()
    I.end_input(token)
    assert seen == [{}]


def test_an_observation_carries_only_the_inputs_id_and_the_inputs_facts_are_kept_once(gen):
    bare = gen.observe(HI, [], LO)
    token = I.begin_input("turn_7", "scared", loads={"X": 1.0, "B": 0.5})
    try:
        many = [gen.observe(HI, [], LO) for _ in range(5)]
        inp = I.current_event()
    finally:
        I.end_input(token)
    after = gen.observe(HI, [], LO)
    assert bare.notes == {} and after.notes == {}
    assert all(r.notes == {"input_event": inp["id"]} for r in many)               # nothing else repeated on each one
    assert list(gen._input_events) == [inp["id"]]                                    # the input's facts, once
    assert gen._input_events[inp["id"]] == {"occurrence": "heard", "turn_id": "turn_7", "input_pressure": inp["input_pressure"]}


def test_the_persisted_file_repeats_nothing_per_record_and_keeps_only_inputs_it_still_refers_to(gen):
    import json
    for k in range(3):
        token = I.begin_input(f"t{k}", f"w{k}", loads={"X": 1.0})
        try:
            for _ in range(4):
                gen.observe(HI, [], LO)
        finally:
            I.end_input(token)
    gen._input_events["orphan"] = {"occurrence": "heard", "turn_id": "old"}
    gen._write_events_recent_file()
    data = json.loads(open(gen._events_recent_path).read())
    assert len(data["records"]) == 12 and len(data["inputs"]) == 3 and "orphan" not in data["inputs"]
    assert all(set(r["notes"]) == {"input_event"} and r["notes"]["input_event"] in data["inputs"] for r in data["records"])


def test_the_registry_is_bounded(gen):
    for k in range(300):
        token = I.begin_input(f"t{k}", f"w{k}")
        try:
            gen.observe(HI, [], LO)
        finally:
            I.end_input(token)
    assert len(gen._input_events) == 256 and "t0" not in {v["turn_id"] for v in gen._input_events.values()}


def test_identity_changes_no_measurement(gen, tmp_path):
    other = ConstraintGenealogyLogger("input_identity_test_b", config=GenealogyConfig(), output_dir=str(tmp_path / "b"))
    plain = other.observe(HI, [], LO)
    token = I.begin_input("turn_9", "anything", loads={"X": 1.0})
    try:
        named = gen.observe(HI, [], LO)
    finally:
        I.end_input(token)
    for field in ("relief", "dominant_relief_axis", "pressure_before", "pressure_after", "trace_cost_total"):
        assert getattr(plain, field) == getattr(named, field), field


def test_a_caller_that_already_named_an_input_keeps_its_own(gen):
    token = I.begin_input("turn_1", "x")
    try:
        r = gen.observe(HI, [], LO, notes={"input_event": "mine"})
    finally:
        I.end_input(token)
    assert r.notes["input_event"] == "mine"


def test_a_real_relief_record_becomes_a_consequence_that_effects_of_reads_back_to_its_input(gen):
    token = I.begin_input("turn_3", "scared", loads={"X": 1.0}, t=1)
    try:
        rec = gen.observe(HI, [], LO)
        inp = I.current_event()
    finally:
        I.end_input(token)
    assert rec.notes["input_event"] == inp["id"]
    c = Q.consequence_from_relief(rec, target="state:calm", change="moved", attribution=[rec.notes["input_event"]],
                                  measured_by="development")
    effect = Q.make_event("state|moved|-", "observed", t=2, nonce="e", consequence=c)
    fx = Q.effects_of([inp, effect], inp["id"])
    assert fx["independent"] == 1 and fx["by_subsystem"]["development"]["relief"]["X"] == pytest.approx(0.7)
    assert fx["input"]["dominant"] == "X"


def test_the_turn_entry_sets_and_always_resets_the_identity():
    """Source guard: begin right before the turn's try, reset in its finally, so identity cannot outlive the turn."""
    src = pathlib.Path(__file__).resolve().parents[1].joinpath("aurora.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_process_external_user_turn_impl")
    body = ast.get_source_segment(src, fn)
    assert body.count("begin_input as _begin_input") == 1 and body.count("end_input as _end_input") == 1
    assert body.index("begin_input as _begin_input") < body.index("_run_live_response_turn(") < body.index("end_input as _end_input")
    finals = [ast.get_source_segment(src, f) or "" for n in ast.walk(fn) if isinstance(n, ast.Try) for f in n.finalbody]
    assert any("_end_input(_input_identity_token)" in f for f in finals)        # the reset is a call, in a finally
