#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_live_turn_smoke.py -- a real live turn must complete (FIX-A119, A120).

Commit 5aaa303 made every live turn raise UnboundLocalError on its first
statement, and it merged, because no test in CI ran a real turn.  This one
does: a full boot against a COPY of her state, then turns through
process_external_user_turn with the arguments her phone uses.

It asserts only that the machinery runs and reports -- never what she says.
"""
from __future__ import annotations

import ast
import io
import json
import os
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _function(name: str) -> ast.FunctionDef:
    tree = ast.parse((ROOT / "aurora.py").read_text(encoding="utf-8"))
    return next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)


def test_turn_ledger_exists_before_anything_reads_it():
    """Static guard for FIX-A119: in _run_live_response_turn, the ledger is
    assigned on an earlier line than its first read."""
    fn = _function("_run_live_response_turn")
    stores = [n.lineno for n in ast.walk(fn)
              if isinstance(n, ast.Name) and n.id == "_turn_ledger" and isinstance(n.ctx, ast.Store)]
    loads = [n.lineno for n in ast.walk(fn)
             if isinstance(n, ast.Name) and n.id == "_turn_ledger" and isinstance(n.ctx, ast.Load)]
    assert stores and loads
    assert min(stores) < min(loads)


def test_grounded_fallback_reads_no_name_it_was_never_given():
    """Static guard for FIX-A120: the fallback referenced a `state` that is
    not among its parameters or locals."""
    fn = _function("_build_grounded_fallback_response")
    bound = {a.arg for a in fn.args.args + fn.args.kwonlyargs}
    bound |= {n.id for n in ast.walk(fn) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
    assert "pipeline_state" in bound
    assert "state" not in {n.id for n in ast.walk(fn)
                           if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)} - bound


@pytest.fixture(scope="module")
def booted(tmp_path_factory):
    os.environ.setdefault("AURORA_SKIP_DEP_INSTALL", "1")
    state = tmp_path_factory.mktemp("live") / "aurora_state"
    shutil.copytree(ROOT / "aurora_state", state)
    import aurora
    real, sys.stdout = sys.stdout, io.StringIO()
    try:
        systems = aurora.boot_aurora(state_dir=str(state), verbose=False)
    finally:
        sys.stdout = real
    return aurora, systems, state


def _turn(aurora, systems, text):
    real, sys.stdout = sys.stdout, io.StringIO()
    try:
        return aurora.process_external_user_turn(
            systems, text, source_label="flutter_ui", session_id="smoke",
            auto_search_enabled=False, record_exchange=True, update_interactive_state=True,
            track_evolutionary_trace=True, run_periodic_maintenance=True, mode_name="BOUNDED")
    finally:
        sys.stdout = real


def test_live_turns_complete_and_share_their_parses(booted):
    aurora, systems, state = booted
    faults = state / "runtime_faults.jsonl"
    before = sum(1 for _ in faults.open()) if faults.exists() else 0
    for text in ("Hey Aurora, how are you today?",
                 "I spent the morning fixing the fence behind the house."):
        result = _turn(aurora, systems, text)
        assert isinstance(result, dict) and "resp_A" in result
        shared = systems["_turn_ledger"].computations.status()
        # the user's text is read by many organs; they must share, not reparse
        assert shared["cache_hits"] > shared["computations"]
    new = [json.loads(line) for i, line in enumerate(faults.open()) if i >= before] if faults.exists() else []
    swallowed_name_errors = [f for f in new if f.get("exception_type") in ("NameError", "UnboundLocalError")]
    assert swallowed_name_errors == [], swallowed_name_errors[:3]
