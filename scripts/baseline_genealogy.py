# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Stage 1 baseline: what genealogy costs a live turn, and what in the live turn depends on it.

Boots Aurora on a COPY of the state, says a fixed script of turns through `process_external_user_turn`,
and observes -- by wrapping methods in this process only, never editing the repository -- :

  * every ConstraintGenealogyLogger.observe call: which thread, which caller (file:line), lock-wait ms versus
    compute ms (from genealogy's own `_last_observe_profile`), and whether it ran inside a live turn
  * per-turn wall time, and the part of it spent inside observe on the turn's own thread
  * a state revision counter (bumped by every observe) and every read of genealogy.abilities made by
    `_select_active_abilities`: how often a same-turn read would have seen different state had the
    same-turn observe calls been deferred -- the evidence for "is it safe to defer this?"

Nothing here changes behaviour; it only counts and times.  Run alone (no other heavy process): the numbers
are wall-clock.

    python3 scripts/baseline_genealogy.py [--state-dir DIR] [--turns FILE] [--json]
"""
from __future__ import annotations

import argparse
import collections
import io
import json
import os
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TURNS = [
    "Hello Aurora.", "What do you see?", "Tell me something you remember.", "The letter b comes after a.",
    "Is b after a?", "I felt calm this morning.", "What is a greeting?", "Thank you.",
]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state-dir", default=str(ROOT / "aurora_state"))
    ap.add_argument("--turns", default="")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    turns = [t.strip() for t in Path(a.turns).read_text().splitlines() if t.strip()] if a.turns else DEFAULT_TURNS
    sys.path.insert(0, str(ROOT))
    os.chdir(ROOT)
    os.environ.setdefault("AURORA_SKIP_DEP_INSTALL", "1")
    scratch_root = Path(tempfile.mkdtemp(prefix="baseline_gen_"))
    try:
        scratch = scratch_root / "aurora_state"
        shutil.copytree(a.state_dir, scratch)
        import aurora
        import aurora_internal.aurora_clone_harvest as clone_harvest
        clone_harvest.absorb_harvest = lambda systems, state_dir=None: {"status": "already_absorbed"}
        from aurora_internal.constraint_genealogy import ConstraintGenealogyLogger as G
        real = sys.stdout
        sys.stdout = io.StringIO()
        try:
            systems = aurora.boot_aurora(state_dir=str(scratch), verbose=False)
        finally:
            sys.stdout = real

        main_thread = threading.get_ident()
        state = {"rev": 0, "in_turn": False, "turn_started": 0.0, "turn_observe_ms": 0.0}
        calls, readers, selected = [], [], []

        orig_observe = G.observe

        def _shape(g):
            ab = getattr(g, "abilities", {}) or {}
            return (len(ab), len(getattr(g, "links", {}) or {}), len(getattr(g, "links_promoted", {}) or {}
                    if hasattr(getattr(g, "links_promoted", None), "__len__") else []),
                    len(getattr(g, "_representation_collisions", {}) or {}))

        def observe(self, *args, **kw):
            t0 = time.perf_counter()
            shape0 = _shape(self)
            try:
                return orig_observe(self, *args, **kw)
            finally:
                shape1 = _shape(self)
                wall = (time.perf_counter() - t0) * 1000.0
                prof = dict(getattr(self, "_last_observe_profile", {}) or {})
                fr = sys._getframe(1)
                where = f"{Path(fr.f_code.co_filename).name}:{fr.f_lineno}:{fr.f_code.co_name}"
                on_main = threading.get_ident() == main_thread
                calls.append({"where": where, "main_thread": on_main, "in_turn": state["in_turn"], "wall_ms": wall,
                              "lock_wait_ms": float(prof.get("lock_wait_ms", 0.0)),
                              "compute_ms": float(prof.get("compute_ms", 0.0)),
                              "stages_ms": dict(prof.get("stages_ms") or {}),
                              "changed": {k: b - a for k, a, b in zip(("abilities", "links", "links_promoted", "collisions"), shape0, shape1) if a != b}})
                state["rev"] += 1
                if on_main and state["in_turn"]:
                    state["turn_observe_ms"] += wall
        G.observe = observe

        method_stats = collections.defaultdict(lambda: {"n": 0, "ms": 0.0, "slow_n": 0})

        def _wrap(name):
            fn = getattr(G, name, None)
            if fn is None:
                return

            def timed(self, *args, **kw):
                t0 = time.perf_counter()
                try:
                    return fn(self, *args, **kw)
                finally:
                    dt = (time.perf_counter() - t0) * 1000.0
                    st = method_stats[name]
                    st["n"] += 1
                    st["ms"] += dt
                    st["slow_n"] += 1 if dt > 5.0 else 0          # a "rebuild" of an index shows as a slow call
            setattr(G, name, timed)
        for _m in ("representation_collision_candidates", "representation_gap_candidates", "_representation_index",
                   "_representation_discrepancy", "_collision_signature_for_item", "_semantic_identity_for_item",
                   "_record_representation_collisions", "_record_representation_inquiries", "_write_event",
                   "_accumulate_pairs", "_attribute_consequence", "_update_coupling_roots", "flush_files"):
            _wrap(_m)

        import aurora as A
        orig_select = getattr(A, "_select_active_abilities", None)
        if orig_select is not None:
            def select(*args, **kw):
                readers.append({"rev": state["rev"], "in_turn": state["in_turn"], "turn": len(turn_rows)})
                res = orig_select(*args, **kw)
                try:
                    selected.append([str(x.get("id", "")) for x in (res or [])])
                except Exception:
                    pass
                return res
            A._select_active_abilities = select

        turn_rows = []
        for text in turns:
            state.update(in_turn=True, turn_observe_ms=0.0)
            rev_before = state["rev"]
            t0 = time.perf_counter()
            real = sys.stdout
            sys.stdout = io.StringIO()
            try:
                aurora.process_external_user_turn(
                    systems, text, source_label="flutter_ui", session_id="baseline", auto_search_enabled=False,
                    record_exchange=True, update_interactive_state=True, track_evolutionary_trace=True,
                    run_periodic_maintenance=True, mode_name="BOUNDED")
            finally:
                sys.stdout = real
            wall = (time.perf_counter() - t0) * 1000.0
            state["in_turn"] = False
            turn_rows.append({"text": text, "wall_ms": round(wall, 1),
                              "observe_main_thread_ms": round(state["turn_observe_ms"], 1),
                              "observe_calls_this_turn": state["rev"] - rev_before})
        time.sleep(1.0)

        gen = systems.get("genealogy")
        by_site = collections.defaultdict(lambda: {"n": 0, "wall_ms": 0.0, "lock_wait_ms": 0.0, "compute_ms": 0.0, "main": 0})
        for c in calls:
            s = by_site[c["where"]]
            s["n"] += 1
            s["wall_ms"] += c["wall_ms"]
            s["lock_wait_ms"] += c["lock_wait_ms"]
            s["compute_ms"] += c["compute_ms"]
            s["main"] += 1 if c["main_thread"] else 0
        stage_totals = collections.Counter()
        for c in calls:
            for k, v in c["stages_ms"].items():
                try:
                    stage_totals[k] += float(v)
                except (TypeError, ValueError):
                    pass
        changed_calls = [c for c in calls if c["changed"]]
        changed_sum = collections.Counter()
        for c in changed_calls:
            for k, v in c["changed"].items():
                changed_sum[k] += v
        # a live read of genealogy.abilities sees changed state if an observe ran earlier in the same turn
        same_turn_before_read = 0
        for r in readers:
            if r["in_turn"] and r["turn"] < len(turn_rows) and turn_rows[r["turn"]]["observe_calls_this_turn"]:
                same_turn_before_read += 1
        abil = getattr(gen, "abilities", {}) or {}
        lineage = sum(1 for i in abil if "CODE_EVOLV" in str(i) or "CODE_LINEA" in str(i))
        picked = [i for row in selected for i in row]
        picked_lineage = sum(1 for i in picked if "CODE_EVOLV" in i or "CODE_LINEA" in i)
        report = {
            "selection": {"candidates": len(abil), "code_lineage_records": lineage,
                          "other": len(abil) - lineage, "selections": len(selected), "picked": len(picked),
                          "picked_code_lineage": picked_lineage,
                          "picked_ids_sample": sorted(set(picked))[:8]},
            "turns": turn_rows,
            "total_turn_ms": round(sum(t["wall_ms"] for t in turn_rows), 1),
            "observe": {
                "calls": len(calls),
                "calls_on_turn_thread": sum(1 for c in calls if c["main_thread"] and c["in_turn"]),
                "calls_on_other_threads": sum(1 for c in calls if not c["main_thread"]),
                "turn_thread_ms": round(sum(c["wall_ms"] for c in calls if c["main_thread"] and c["in_turn"]), 1),
                "lock_wait_ms_total": round(sum(c["lock_wait_ms"] for c in calls), 1),
                "compute_ms_total": round(sum(c["compute_ms"] for c in calls), 1),
                "by_call_site": {k: {kk: round(vv, 1) if isinstance(vv, float) else vv for kk, vv in v.items()}
                                 for k, v in sorted(by_site.items(), key=lambda kv: -kv[1]["wall_ms"])},
                "stage_ms_totals": {k: round(v, 1) for k, v in stage_totals.most_common(12)},
            },
            "methods": {k: {"n": v["n"], "ms": round(v["ms"], 1), "calls_over_5ms": v["slow_n"]}
                        for k, v in sorted(method_stats.items(), key=lambda kv: -kv[1]["ms"])},
            "live_reads_of_abilities": {"reads": len(readers), "reads_after_a_same_turn_observe": same_turn_before_read},
            "state_changed_by_observe": {"calls_that_changed_abilities_or_links": len(changed_calls),
                                         "net_change": dict(changed_sum),
                                         "calls_that_changed_abilities": sum(1 for c in calls if "abilities" in c["changed"])},
            "genealogy": {"abilities": len(getattr(gen, "abilities", {}) or {}), "links": len(getattr(gen, "links", {}) or {}),
                          "tick": int(getattr(gen, "tick_count", 0) or 0)},
        }
        print(json.dumps(report, indent=1) if a.json else _render(report))
        sys.stdout.flush()
        return 0
    finally:
        shutil.rmtree(scratch_root, ignore_errors=True)


def _render(r):
    o = r["observe"]
    out = [f"{len(r['turns'])} turns, {r['total_turn_ms']} ms total"]
    for t in r["turns"]:
        out.append(f"  {t['wall_ms']:>8} ms  (observe on turn thread {t['observe_main_thread_ms']} ms, {t['observe_calls_this_turn']} calls)  {t['text']}")
    out.append(f"observe: {o['calls']} calls ({o['calls_on_turn_thread']} on the turn thread, {o['calls_on_other_threads']} elsewhere); "
               f"{o['turn_thread_ms']} ms on the turn thread; lock wait {o['lock_wait_ms_total']} ms vs compute {o['compute_ms_total']} ms")
    for k, v in o["by_call_site"].items():
        out.append(f"  {k:<58} n={v['n']:<4} wall={v['wall_ms']:<9} lock={v['lock_wait_ms']:<8} compute={v['compute_ms']:<9} on-main={v['main']}")
    out.append("stage totals (ms): " + ", ".join(f"{k}={v}" for k, v in o["stage_ms_totals"].items()))
    lr = r["live_reads_of_abilities"]
    out.append(f"live ability-selection reads: {lr['reads']}; made after a same-turn observe: {lr['reads_after_a_same_turn_observe']}")
    out.append("method totals (inclusive; nested calls double-count):")
    for k, v in r["methods"].items():
        out.append(f"  {k:<42} n={v['n']:<5} ms={v['ms']:<9} calls>5ms={v['calls_over_5ms']}")
    se = r["selection"]
    out.append(f"ability selection: {se['candidates']} candidates, {se['code_lineage_records']} are code-lineage records, "
               f"{se['other']} other; {se['selections']} selections picked {se['picked']}, of which code-lineage {se['picked_code_lineage']}; "
               f"sample {se['picked_ids_sample']}")
    sc = r["state_changed_by_observe"]
    out.append(f"observe calls that changed what live code reads: {sc['calls_that_changed_abilities_or_links']} of {o['calls']} "
               f"(net {sc['net_change']}; abilities changed in {sc['calls_that_changed_abilities']})")
    g = r["genealogy"]
    out.append(f"genealogy: {g['abilities']} abilities, {g['links']} links, tick {g['tick']}")
    return "\n".join(out)


if __name__ == "__main__":
    code = main()
    os._exit(code)
