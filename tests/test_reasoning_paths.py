#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Remembered reasoning paths participate; they never skip (Sunni, 2026-11-08)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import aurora_internal.aurora_reasoning_paths as R  # noqa: E402


def state(axes=None, label="tension", action="explain", text="Do you like music?",
          abilities=("N:OP1", "B:OP2")):
    return {
        "relational_form": {"raw_text": text, "subject": "you", "relation": "like", "obj": "music",
                            "unknown_role": "truth"},
        "input_stance": "curious",
        "axis_activation": axes or {"X": 0.18, "T": 0.14, "N": 0.30, "B": 0.22, "A": 0.16},
        "meaning_label": label, "meaning_signature": "N^1*B^1", "dominant_axis": "boundary",
        "selected_conscious_action": action, "response_obligation": {"operation": "evaluate_proposition"},
        "deep_dominant_emotion": "calm", "surface_reactive_bias": "lean_in",
        "active_abilities": list(abilities), "salient_concepts": ["music"],
    }


def turn(paths, rid, st, verdict=None):
    offer = paths.begin_turn(st, st["axis_activation"])
    paths.end_turn(st, rid)
    effect = paths.record_receiver_outcome(rid, verdict) if verdict else None
    return offer, effect


def test_understood_turn_carves_a_faint_path_that_is_then_offered(tmp_path):
    p = R.ReasoningPaths(state_dir=str(tmp_path))
    offer, effect = turn(p, "r1", state(), "positive")
    assert offer is None and effect["effect"].startswith("carved")
    path = next(iter(p.paths.values()))
    assert path["weight"] == R.CARVE_WEIGHT
    assert "Do you like music?" not in str(path), "no words are stored"
    offer, _ = turn(p, "r2", state(), None)
    assert offer and offer["weight"] == R.CARVE_WEIGHT


def test_agreement_deepens_and_misleading_wears(tmp_path):
    p = R.ReasoningPaths(state_dir=str(tmp_path))
    turn(p, "r1", state(), "positive")
    for i in range(4):
        turn(p, f"a{i}", state(), "positive")
    path = next(iter(p.paths.values()))
    deep = path["weight"]
    assert deep > 0.4 and p.counters["agreed"] == 4 and p.counters["deepened"] == 4
    turn(p, "m1", state(), "negative")
    assert path["weight"] == round(deep * R.WEAR_FACTOR, 4) and p.counters["worn"] == 1


def test_divergence_that_is_understood_carves_its_own_path_and_reconsiders(tmp_path):
    p = R.ReasoningPaths(state_dir=str(tmp_path))
    for i in range(3):
        turn(p, f"r{i}", state(), "positive")
    old = next(iter(p.paths.values()))
    before = old["weight"]
    offer, effect = turn(p, "d1", state(label="curiosity", action="ask", abilities=("A:OP9",)), "positive")
    assert offer is not None
    assert effect["effect"].startswith("reconsidered")
    assert len(p.paths) == 2 and old["weight"] == round(before * R.RECONSIDER_FACTOR, 4)
    assert set(p.last_divergence["differences"]) >= {"meaning_label", "action"}


def test_divergence_that_is_misunderstood_lets_the_old_path_regain(tmp_path):
    p = R.ReasoningPaths(state_dir=str(tmp_path))
    for i in range(3):
        turn(p, f"r{i}", state(), "positive")
    old = next(iter(p.paths.values()))
    before = old["weight"]
    turn(p, "d1", state(label="curiosity", action="ask"), "negative")
    assert old["weight"] == round(before + R.REGAIN, 4) and len(p.paths) == 1


def test_offered_only_under_resonating_pressure_and_matching_shape(tmp_path):
    p = R.ReasoningPaths(state_dir=str(tmp_path))
    turn(p, "r1", state(), "positive")
    far = state(axes={"X": 0.9, "T": 0.0, "N": 0.0, "B": 0.0, "A": 0.1})
    assert p.begin_turn(far, far["axis_activation"]) is None
    statement = state(text="I like music.")
    assert p.begin_turn(statement, statement["axis_activation"]) is None


def test_ability_lean_is_earned_and_capped(tmp_path):
    p = R.ReasoningPaths(state_dir=str(tmp_path))
    st = state()
    turn(p, "r1", st, "positive")
    p.begin_turn(st, st["axis_activation"])
    faint = p.ability_lean("N:OP1")
    assert 0 < faint < 0.02 and p.ability_lean("X:NOT_USED") == 0.0
    for i in range(30):
        turn(p, f"a{i}", st, "positive")
    p.begin_turn(st, st["axis_activation"])
    assert p.ability_lean("N:OP1") <= R.MAX_ABILITY_LEAN


def test_indeterminate_verdict_changes_nothing_and_state_persists(tmp_path):
    p = R.ReasoningPaths(state_dir=str(tmp_path))
    turn(p, "r1", state(), "positive")
    w = next(iter(p.paths.values()))["weight"]
    turn(p, "r2", state(), "indeterminate")
    assert next(iter(p.paths.values()))["weight"] == w
    p.flush_write_batch()
    again = R.ReasoningPaths(state_dir=str(tmp_path))
    assert again.paths == p.paths and again.counters["carved"] == 1


def test_weak_paths_dissolve(tmp_path):
    p = R.ReasoningPaths(state_dir=str(tmp_path))
    turn(p, "r1", state(), "positive")
    for i in range(6):
        turn(p, f"m{i}", state(), "negative")
    assert not p.paths and p.counters["dissolved"] == 1
