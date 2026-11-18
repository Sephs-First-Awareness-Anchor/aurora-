#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_cognition_gap_wiring.py -- three bus slots that were read but never
written, each wired to the source that already holds the value.

Found by the knowledge graph's "read and never written" list and confirmed in
the code:

1. aurora_braid_wiring._build_turn_process_contexts read
   systems["_open_curiosity_loops"], which nothing writes, so the curiosity
   process never entered the turn.  The live loops belong to the curiosity
   engine (systems["_curiosity_engine"]) and are now read through
   CuriosityEngine.open_curiosity_loops().
2. aurora.py's conversation-memory snapshot read systems["_noncomp_output"]
   for its "nc" field; the writer is _apply_noncomp_output_guidance, which
   stores systems["_last_noncomp_output"].  "nc" was always empty.
3. The curiosity engine pursues an unresolved inability from
   systems["_pending_capability_gap"]; the phone bridge kept the gap only in a
   module global.  It now shares the same dict, and clears it when taught.
"""
from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

import pytest

from aurora_braid_wiring import _build_turn_process_contexts
from aurora_curiosity_engine import CuriosityEngine, CuriosityObject

_REPO = Path(__file__).resolve().parents[1]


def _engine(systems):
    return CuriosityEngine(pressure_source=None, field_map=None, tool_mind=None,
                           sedimemory=None, self_grounder=None,
                           tension_monitor=None, systems=systems)


def _curiosity_contexts(contexts):
    return [c for c in contexts
            if getattr(c, "process_type", None) == "curiosity"]


# ---------------------------------------------------------------------------
# 1. Open curiosity loops reach the turn's process contexts
# ---------------------------------------------------------------------------

def test_open_curiosity_loops_is_a_snapshot_the_engine_still_owns():
    engine = _engine({})
    loop = CuriosityObject(subject="why the tide turns", origin_axis="T",
                           curiosity_type="temporal")
    engine._open_curiosity_loops.append(loop)
    snapshot = engine.open_curiosity_loops()
    assert snapshot == [loop]
    snapshot.clear()
    assert engine.open_curiosity_loops() == [loop]


def test_engine_loops_form_the_curiosity_process():
    systems = {}
    engine = _engine(systems)
    systems["_curiosity_engine"] = engine
    engine._open_curiosity_loops.append(CuriosityObject(
        subject="why the tide turns", origin_axis="T", curiosity_type="temporal"))

    contexts = _curiosity_contexts(_build_turn_process_contexts(systems, tick=3))
    assert len(contexts) == 1
    assert contexts[0].what_it_is_operating_on == "why the tide turns"


def test_no_curiosity_process_without_open_loops():
    systems = {"_curiosity_engine": _engine({})}
    assert _curiosity_contexts(_build_turn_process_contexts(systems, tick=3)) == []
    assert _curiosity_contexts(_build_turn_process_contexts({}, tick=3)) == []


# ---------------------------------------------------------------------------
# 2. The conversation-memory snapshot reads the slot that is written
# ---------------------------------------------------------------------------

def _string_keys_read_from_systems(source: str):
    """Every literal key in systems.get("...") / systems["..."] reads."""
    keys = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "get" \
                and isinstance(getattr(node.func, "value", None), ast.Name) \
                and node.func.value.id == "systems" and node.args \
                and isinstance(node.args[0], ast.Constant):
            keys.add(node.args[0].value)
    return keys


def test_aurora_reads_the_noncomp_slot_its_writer_fills():
    source = (_REPO / "aurora.py").read_text(encoding="utf-8")
    reads = _string_keys_read_from_systems(source)
    assert "_noncomp_output" not in reads
    assert "_last_noncomp_output" in reads
    assert 'systems["_last_noncomp_output"] = dict(summary)' in source


# ---------------------------------------------------------------------------
# 3. The phone's capability gap reaches the curiosity engine
# ---------------------------------------------------------------------------

_APP_PY = _REPO / "flutter_app" / "android" / "app" / "src" / "main" / "python"


@pytest.fixture()
def ab(monkeypatch):
    if not (_APP_PY / "aurora_bridge.py").exists():
        pytest.skip("app aurora_bridge.py not found")
    monkeypatch.syspath_prepend(str(_APP_PY))
    module = pytest.importorskip("aurora_bridge")
    if not hasattr(module, "_register_capability_gap"):
        pytest.skip("this aurora_bridge.py has no capability-gap loop")
    systems = {}
    monkeypatch.setattr(module, "_systems", systems)
    monkeypatch.setattr(module, "_pending_capability_gap", {})
    monkeypatch.setattr(module, "_capability_learning_mode", False)
    monkeypatch.setattr(module, "_capability_learning_context", {})
    return module


def test_registered_gap_is_the_dict_the_curiosity_engine_reads(ab):
    pre = {"X": 0.5, "T": 0.5, "N": 0.4, "B": 0.4, "A": 0.8}
    post = {"X": 0.5, "T": 0.5, "N": 0.8, "B": 0.85, "A": 0.25}
    ab._register_capability_gap("tie a bowline knot", pre, post)

    shared = ab._systems["_pending_capability_gap"]
    assert shared is ab._pending_capability_gap
    assert shared["task_text"] == "tie a bowline knot"

    engine = _engine(ab._systems)
    curiosity = engine._step1_emergence(1)
    assert curiosity is not None
    assert curiosity.subject == "tie a bowline knot"
    assert curiosity.curiosity_type == "self"
    # The engine's mark is visible to the bridge, so the gap does not re-fire.
    assert ab._pending_capability_gap.get("_investigated") is True
