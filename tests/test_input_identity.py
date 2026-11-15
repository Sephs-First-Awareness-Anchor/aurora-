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
    assert I.note_for_observe()["turn_id"] == "outer"
    inner = I.begin_input("inner", "b")
    assert I.note_for_observe()["turn_id"] == "inner"
    I.end_input(inner)
    assert I.note_for_observe()["turn_id"] == "outer"
    I.end_input(outer)
    assert I.note_for_observe() == {}


def test_a_thread_started_by_the_turn_carries_no_identity_it_is_unattributed_not_guessed():
    token = I.begin_input("t", "a")
    seen = []
    th = threading.Thread(target=lambda: seen.append(I.note_for_observe()))
    th.start(); th.join()
    I.end_input(token)
    assert seen == [{}]


def test_observe_merges_the_identity_into_the_relief_records_notes(gen):
    bare = gen.observe(HI, [], LO)
    token = I.begin_input("turn_7", "scared", loads={"X": 1.0, "B": 0.5})
    try:
        named = gen.observe(HI, [], LO)
    finally:
        I.end_input(token)
    after = gen.observe(HI, [], LO)
    assert bare.notes == {} and after.notes == {}
    ev = I.make_input_event("turn_7", "scared", loads={"X": 1.0, "B": 0.5}, t=0)           # same text/turn: nonce matches
    assert named.notes["turn_id"] == "turn_7" and named.notes["input_occurrence"] == "heard"
    assert named.notes["input_pressure"] == ev["input_pressure"] and isinstance(named.notes["input_event"], str)


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
        r = gen.observe(HI, [], LO, notes={"turn_id": "mine"})
    finally:
        I.end_input(token)
    assert r.notes["turn_id"] == "mine"


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
