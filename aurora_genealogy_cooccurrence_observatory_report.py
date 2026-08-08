#!/usr/bin/env python3
"""
AURORA GENEALOGY CO-OCCURRENCE OBSERVATORY — REPORT RUN (Phase 3A.1)
==========================================================================
Authors: Sunni (Sir) Morningstar & Cael Devo

Replays the real aurora_state/genealogy/events_recent.json corpus through
the REAL, LIVE ConstraintGenealogyLogger.observe() -- not a parallel shadow
structure (that was Phase 3A) -- with the co-occurrence observatory sidecar
installed, so every classification in this report reflects an actual live
call into real Aurora code, not static analysis of persisted JSON alone.

A FRESH, throwaway ConstraintGenealogyLogger is used (temp directory,
separate run_id) -- this never touches real aurora_state/genealogy/, and
promotion decisions made during this replay do not need to (and will not)
match the original historical run's decisions, since ability registries,
already-promoted-link state, and governor history all differ from a fresh
instance. That is fine and expected: this replay exists to exercise the
real observe()/_accumulate_pairs() code path with real inputs, not to
reproduce history's promotion outcomes. No promotion gate output is read or
reported by this script.

Also directly exercises the real, confirmed aurora_grammar_engine.py call
site (GrammarEngine._log_relief_to_genealogy(), which hardcodes
difference_snapshot=None) against the SAME fresh logger, for a live,
non-replayed confirmation of the Phase 3A.1 finding for that specific
caller.

KNOWN SIDE EFFECT OF RUNNING THIS SCRIPT: _try_promote()'s Gate 2/4/5
rejection logging calls PressureExperienceLedger.get() (a process-wide
singleton with a hardcoded path,
aurora_internal/aurora_pressure_ledger.py:114), which appends to the real,
shared aurora_state/pressure_experiences.jsonl regardless of which
(throwaway) logger triggered the rejection. This is a real, unavoidable
consequence of exercising real promotion-gate code, not a bug in this
script. `tests/test_genealogy_cooccurrence_observatory.py` guards against
this with an autouse fixture that snapshots and restores that file; this
standalone diagnostic script does not, since it isn't part of the automated
suite -- `git checkout -- aurora_state/pressure_experiences.jsonl` after
running it manually if you want the repo left byte-identical.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aurora_internal.constraint_genealogy import ConstraintGenealogyLogger, PressureVec, TraceItem
from aurora_internal.aurora_difference_buffer import DifferenceSnapshot
from aurora_internal.aurora_constraint_manifold_patched import Constraint
from aurora_genealogy_cooccurrence_observatory import install


def _pressure_vec_from_dict(d):
    return PressureVec(**{a: float(d.get(a, 0.0) or 0.0) for a in ("X", "T", "N", "B", "A")})


def _difference_snapshot_from_dict(d):
    if not isinstance(d, dict):
        return None
    values = d.get("values") or {}
    refs = d.get("refs") or {}
    try:
        return DifferenceSnapshot(
            tick=int(d.get("tick", 0) or 0),
            values={Constraint[a]: float(values.get(a, 0.0) or 0.0) for a in ("X", "T", "N", "B", "A")},
            ref_magnitudes={Constraint[a]: float(refs.get(a, 0.0) or 0.0) for a in ("X", "T", "N", "B", "A")},
            warm_up=bool(d.get("warm_up", False)),
        )
    except Exception:
        return None


def replay_real_corpus_live(events_path: str = None):
    """`events_path` defaults to the live, current
    aurora_state/genealogy/events_recent.json (correct for this diagnostic
    script's own purpose: reflect current real state). Tests that need a
    deterministic, committed snapshot instead (found: some other test in
    the full suite boots a real ConstraintGenealogyLogger against that live
    path and overwrites it) should pass tests/fixtures/genealogy_events_
    recent_snapshot.json explicitly."""
    root = os.path.dirname(os.path.abspath(__file__))
    if events_path is None:
        events_path = os.path.join(root, "aurora_state", "genealogy", "events_recent.json")
    with open(events_path, "r", encoding="utf-8") as f:
        records = list(json.load(f).get("records") or [])

    logger = ConstraintGenealogyLogger(run_id="cooccurrence_observatory_replay", output_dir=tempfile.mkdtemp())
    sink, uninstall = install(logger)

    for record in records:
        trace = [TraceItem(kind=t.get("kind", "ABILITY"), id=t.get("id", "")) for t in (record.get("trace") or [])]
        if not trace:
            continue
        pressure_before = _pressure_vec_from_dict(record.get("pressure_before") or {})
        pressure_after = _pressure_vec_from_dict(record.get("pressure_after") or {})
        notes = dict(record.get("notes") or {})
        diff_snapshot = _difference_snapshot_from_dict(notes.pop("difference_snapshot", None))
        logger.observe(
            pressure_before=pressure_before,
            trace=trace,
            pressure_after=pressure_after,
            notes=notes,
            difference_snapshot=diff_snapshot,
        )

    uninstall()
    return sink


def exercise_grammar_engine_live(n_calls: int = 10):
    import aurora_grammar_engine

    logger = ConstraintGenealogyLogger(run_id="cooccurrence_observatory_grammar", output_dir=tempfile.mkdtemp())
    sink, uninstall = install(logger)

    engine = aurora_grammar_engine.GrammarEngine(state_dir=tempfile.mkdtemp())
    engine.set_genealogy(logger)
    for i in range(n_calls):
        engine._log_relief_to_genealogy(text_changed=True, clarity=0.5 + (i % 5) * 0.1, motif=None)

    uninstall()
    return sink


def summarize(sink, label):
    print(f"=== {label} ===")
    print(f"  total observe() calls recorded: {len(sink)}")
    eligible = [o for o in sink if o.pair_eligible]
    print(f"  pair-eligible (trace_length >= 2): {len(eligible)}")
    passed = [o for o in sink if o.difference_passed]
    print(f"  difference_passed=True: {len(passed)}")
    eligible_and_passed = [o for o in eligible if o.difference_passed]
    print(f"  pair-eligible AND difference_passed (genuine co-occurrence): {len(eligible_and_passed)}")
    sources = Counter(o.difference_source for o in sink if not o.difference_passed)
    print(f"  difference_source, when not passed directly: {dict(sources)}")
    reasons = Counter(o.difference_unavailable_reason for o in sink if o.difference_unavailable_reason)
    for reason, count in reasons.items():
        print(f"    [{count}x] {reason}")
    callers = Counter(o.caller_qualname for o in sink)
    print(f"  callers observed: {dict(callers)}")
    print()


if __name__ == "__main__":
    replay_sink = replay_real_corpus_live()
    summarize(replay_sink, "LIVE replay of real events_recent.json through real observe()")

    grammar_sink = exercise_grammar_engine_live()
    summarize(grammar_sink, "LIVE direct exercise of aurora_grammar_engine.GrammarEngine._log_relief_to_genealogy()")
