# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Genealogy baseline: what genealogy costs a live turn, and what in the live turn depends on it.

Boots Aurora on a COPY of the state, says a fixed script of turns through `process_external_user_turn`,
and observes -- by wrapping methods in this process only, never editing the repository.

Three modes, because measuring cost and measuring what changed disturb each other and must not share a run
(Stage 1 mixed them; its wrapper overhead inflated its timings -- see the Stage 1 addendum):

  timing   (default)  Only `observe` is wrapped (two clock reads per call).  Per call: thread, caller
                      (file:line), lock-wait ms vs compute ms (from genealogy's own `_last_observe_profile`),
                      per-stage ms.  Per turn: wall time and the part spent in observe on the turn's thread.
                      The numbers to quote for cost.
  diff                Wraps `observe` and fingerprints genealogy's abilities, links, promoted links and
                      collision records before and after every call, by CONTENT (a stable hash of the records),
                      not by size: an in-place edit of a field is a change.  Also records every live read of
                      the ability pool against the observe calls that came before it in the SAME turn.  The
                      numbers to quote for "does observe change what live code reads".  Its timings are
                      inflated by the hashing and are not reported as cost.
  methods             `timing` plus an inclusive timer on the heavy methods (nested calls double-count).  The
                      timers add overhead: use it to see WHERE the time goes, not how much there is.

    python3 scripts/baseline_genealogy.py [--mode timing|diff|methods] [--state-dir DIR] [--turns FILE] [--json]

Run alone (no other heavy process): the numbers are wall-clock.  Nothing here changes behaviour.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TURNS = [
    "Hello Aurora.", "What do you see?", "Tell me something you remember.", "The letter b comes after a.",
    "Is b after a?", "I felt calm this morning.", "What is a greeting?", "Thank you.",
]
# What live code reads from genealogy, versus what only later inquiry reads.
LIVE_READ = ("abilities", "links", "links_promoted")
OTHER = ("collisions",)
HEAVY_METHODS = ("representation_collision_candidates", "representation_gap_candidates", "_representation_index",
                 "_representation_discrepancy", "_collision_signature_for_item", "_semantic_identity_for_item",
                 "_record_representation_collisions", "_record_representation_inquiries", "_write_event",
                 "_accumulate_pairs", "_attribute_consequence", "_update_coupling_roots", "flush_files")


# -- pure helpers (tested in tests/test_baseline_genealogy.py) ----------------------------------------------

def fingerprint(value: Any) -> str:
    """A stable hash of a structure's CONTENT: key order and object identity do not matter, a changed field does."""
    blob = json.dumps(value, sort_keys=True, default=repr, separators=(",", ":"))
    return hashlib.blake2b(blob.encode("utf-8"), digest_size=12).hexdigest()


def _item_blob(obj: Any) -> str:
    """One record as a stable string: a field changed in place or by `dataclasses.replace` shows as a different blob."""
    try:
        d = obj if isinstance(obj, dict) else dict(vars(obj))
    except TypeError:
        d = {"_repr": repr(obj)}
    return json.dumps(d, sort_keys=True, default=repr, separators=(",", ":"))


def collect(g: Any, deep: bool) -> Dict[str, Any]:
    """The parts of genealogy state in question: size always; when `deep`, each record's content (abilities,
    links, promoted links one by one, so a later diff can say WHICH fields changed) or a content hash."""
    parts = {"abilities": getattr(g, "abilities", None), "links": getattr(g, "links", None),
             "links_promoted": getattr(g, "links_promoted", None),
             "collisions": getattr(g, "_representation_collisions", None)}
    out: Dict[str, Any] = {}
    for name, obj in parts.items():
        try:
            size = len(obj) if hasattr(obj, "__len__") else 0
        except Exception:
            size = 0
        out[name] = {"n": size}
        if deep:
            if name in ("abilities", "links") and isinstance(obj, Mapping):
                out[name]["items"] = {str(k): _item_blob(v) for k, v in list(obj.items())}
            else:
                out[name]["fp"] = fingerprint(obj if obj is not None else {})
    return out


def diff_state(before: Mapping[str, Any], after: Mapping[str, Any]) -> Dict[str, Any]:
    """What one call changed, kept apart: size changes, content changes, and (for abilities and links) which
    FIELDS changed on how many records."""
    out: Dict[str, Any] = {}
    for name in LIVE_READ + OTHER:
        b, a = before.get(name) or {}, after.get(name) or {}
        if a.get("n") != b.get("n"):
            out[name + "_size"] = int(a.get("n", 0)) - int(b.get("n", 0))
        if "items" in a and "items" in b:
            bi, ai = b["items"], a["items"]
            changed = [k for k in ai if k in bi and ai[k] != bi[k]]
            if changed or set(ai) != set(bi):
                out[name + "_content"] = True
            fields: Dict[str, int] = {}
            for k in changed:
                try:
                    x, y = json.loads(bi[k]), json.loads(ai[k])
                except ValueError:
                    continue
                for f in set(x) | set(y):
                    if x.get(f) != y.get(f):
                        fields[f] = fields.get(f, 0) + 1
            if fields:
                out[name + "_fields"] = fields
        elif "fp" in a and "fp" in b and a["fp"] != b["fp"]:
            out[name + "_content"] = True
    return out


def scratch_index(g: Any) -> Dict[str, List[str]]:
    """The representation index built from nothing for the state as it stands: the oracle the cached,
    change-aware index must equal at every moment."""
    from collections import defaultdict
    observed, activity = g._representation_observed_and_activity()
    index: Dict[str, List[str]] = defaultdict(list)
    for iid in sorted(observed):
        if g.representation_is_eligible(iid):
            index[g._collision_signature_for_item(iid)].append(iid)
    for bucket in index.values():
        bucket.sort(key=lambda iid: (-activity[iid][0], -activity[iid][1], iid))
    return {k: list(v) for k, v in index.items()}


def touches_live_reads(change: Mapping[str, Any]) -> bool:
    """Did this call change something live code reads (abilities / links / promoted links)?  A collision-only
    change is not that."""
    return any(f"{name}_{kind}" in change for name in LIVE_READ for kind in ("size", "content"))


def touches_collisions(change: Mapping[str, Any]) -> bool:
    return "collisions_size" in change or "collisions_content" in change


def reads_after_same_turn_observe(readers: Sequence[Mapping[str, Any]], turn_start_rev: Mapping[int, int]) -> int:
    """Live reads made after at least one observe call earlier in the SAME turn.  The comparison is the revision
    AT the read against the revision at the turn's start -- not the turn's final call count, which would count a
    read that happened before the observe."""
    n = 0
    for r in readers:
        if r.get("in_turn") and int(r["rev"]) > int(turn_start_rev.get(r["turn"], r["rev"])):
            n += 1
    return n


# -- the run ---------------------------------------------------------------------------------------------------

def run(state_dir: str, turns: Sequence[str], mode: str) -> Dict[str, Any]:
    deep = mode == "diff"
    sys.path.insert(0, str(ROOT))
    os.chdir(ROOT)
    os.environ.setdefault("AURORA_SKIP_DEP_INSTALL", "1")
    scratch_root = Path(tempfile.mkdtemp(prefix="baseline_gen_"))
    try:
        scratch = scratch_root / "aurora_state"
        shutil.copytree(state_dir, scratch)
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
        state = {"rev": 0, "in_turn": False, "turn_observe_ms": 0.0}
        calls: List[Dict[str, Any]] = []
        index_checks: List[bool] = []
        readers: List[Dict[str, Any]] = []
        selected: List[List[str]] = []
        turn_start_rev: Dict[int, int] = {}
        turn_rows: List[Dict[str, Any]] = []
        orig_observe = G.observe

        def observe(self, *args, **kw):
            before = collect(self, True) if deep else None
            t0 = time.perf_counter()
            try:
                return orig_observe(self, *args, **kw)
            finally:
                wall = (time.perf_counter() - t0) * 1000.0
                prof = dict(getattr(self, "_last_observe_profile", {}) or {})
                fr = sys._getframe(1)
                where = f"{Path(fr.f_code.co_filename).name}:{fr.f_lineno}:{fr.f_code.co_name}"
                on_main = threading.get_ident() == main_thread
                rec = {"where": where, "main_thread": on_main, "in_turn": state["in_turn"], "wall_ms": wall,
                       "lock_wait_ms": float(prof.get("lock_wait_ms", 0.0)),
                       "compute_ms": float(prof.get("compute_ms", 0.0)),
                       "stages_ms": dict(prof.get("stages_ms") or {})}
                if deep:
                    rec["changed"] = diff_state(before, collect(self, True))
                    if hasattr(self, "_representation_observed_and_activity"):
                        live = {k: list(v) for k, v in self._representation_index().items()}
                        index_checks.append(live == scratch_index(self))
                calls.append(rec)
                state["rev"] += 1
                if on_main and state["in_turn"]:
                    state["turn_observe_ms"] += wall
        G.observe = observe

        method_stats = collections.defaultdict(lambda: {"n": 0, "ms": 0.0, "slow_n": 0})
        if mode == "methods":
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
                        st["slow_n"] += 1 if dt > 5.0 else 0      # a "rebuild" of an index shows as a slow call
                setattr(G, name, timed)
            for _m in HEAVY_METHODS:
                _wrap(_m)

        import aurora as A
        orig_select = getattr(A, "_select_active_abilities", None)
        if orig_select is not None:
            def select(*args, **kw):
                readers.append({"rev": state["rev"], "in_turn": state["in_turn"], "turn": len(turn_rows),
                                "main_thread": threading.get_ident() == main_thread})
                res = orig_select(*args, **kw)
                try:
                    selected.append([str(x.get("id", "")) for x in (res or [])])
                except Exception:
                    pass
                return res
            A._select_active_abilities = select

        for text in turns:
            state.update(in_turn=True, turn_observe_ms=0.0)
            turn_start_rev[len(turn_rows)] = state["rev"]
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
        report = summarize(mode, turn_rows, calls, readers, selected, turn_start_rev, method_stats,
                           getattr(systems.get("genealogy"), "abilities", {}) or {}, systems.get("genealogy"))
        if deep:
            report["representation_index_vs_full_rebuild"] = {"checked_after_observe_calls": len(index_checks),
                                                               "mismatches": sum(1 for ok in index_checks if not ok)}
        return report
    finally:
        shutil.rmtree(scratch_root, ignore_errors=True)


def summarize(mode, turn_rows, calls, readers, selected, turn_start_rev, method_stats, abil, gen) -> Dict[str, Any]:
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
    lineage = sum(1 for i in abil if "CODE_EVOLV" in str(i) or "CODE_LINEA" in str(i))
    picked = [i for row in selected for i in row]
    picked_lineage = sum(1 for i in picked if "CODE_EVOLV" in i or "CODE_LINEA" in i)
    report: Dict[str, Any] = {
        "mode": mode,
        "timings_are_cost": mode in ("timing", "methods"),
        "selection": {"candidates": len(abil), "code_lineage_records": lineage, "other": len(abil) - lineage,
                      "selections": len(selected), "picked": len(picked), "picked_code_lineage": picked_lineage,
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
        "live_reads_of_abilities": {
            "reads": len(readers),
            "reads_on_turn_thread": sum(1 for r in readers if r["main_thread"] and r["in_turn"]),
            "reads_after_a_same_turn_observe": reads_after_same_turn_observe(readers, turn_start_rev)},
        "genealogy": {"abilities": len(abil), "links": len(getattr(gen, "links", {}) or {}),
                      "tick": int(getattr(gen, "tick_count", 0) or 0)},
    }
    if mode == "diff":
        ch = [c.get("changed", {}) for c in calls]
        net = collections.Counter()
        for c in ch:
            for k, v in c.items():
                if isinstance(v, int) and not isinstance(v, bool):
                    net[k] += v
        fields: Dict[str, collections.Counter] = {"abilities": collections.Counter(), "links": collections.Counter()}
        for c in ch:
            for name in fields:
                fields[name].update(c.get(name + "_fields", {}))
        report["state_changed_by_observe"] = {
            "fields_changed": {name: dict(cnt.most_common()) for name, cnt in fields.items()},
            "calls": len(calls),
            "calls_that_changed_what_live_code_reads": sum(1 for c in ch if touches_live_reads(c)),
            "calls_that_changed_collisions_only": sum(1 for c in ch if touches_collisions(c) and not touches_live_reads(c)),
            "calls_that_changed_abilities": sum(1 for c in ch if any(k.startswith("abilities_") for k in c)),
            "calls_that_changed_links": sum(1 for c in ch if any(k.startswith("links_") for k in c)),
            "calls_that_changed_ability_content_in_place": sum(1 for c in ch if "abilities_content" in c
                                                               and "abilities_size" not in c),
            "net_size_change": {k: v for k, v in net.items() if k.endswith("_size")},
        }
    return report


def render(r: Mapping[str, Any]) -> str:
    o = r["observe"]
    out = [f"mode {r['mode']}: {len(r['turns'])} turns, {r['total_turn_ms']} ms total"
           + ("" if r["timings_are_cost"] else "   (fingerprinting inflates timings: NOT a cost measurement)")]
    for t in r["turns"]:
        out.append(f"  {t['wall_ms']:>8} ms  (observe on turn thread {t['observe_main_thread_ms']} ms, "
                   f"{t['observe_calls_this_turn']} calls)  {t['text']}")
    out.append(f"observe: {o['calls']} calls ({o['calls_on_turn_thread']} on the turn thread, {o['calls_on_other_threads']} elsewhere); "
               f"{o['turn_thread_ms']} ms on the turn thread; lock wait {o['lock_wait_ms_total']} ms vs compute {o['compute_ms_total']} ms")
    for k, v in o["by_call_site"].items():
        out.append(f"  {k:<58} n={v['n']:<4} wall={v['wall_ms']:<9} lock={v['lock_wait_ms']:<8} compute={v['compute_ms']:<9} on-main={v['main']}")
    out.append("stage totals (ms): " + ", ".join(f"{k}={v}" for k, v in o["stage_ms_totals"].items()))
    lr = r["live_reads_of_abilities"]
    out.append(f"live ability-selection reads: {lr['reads']} ({lr['reads_on_turn_thread']} on the turn thread); "
               f"made after an observe earlier in the same turn: {lr['reads_after_a_same_turn_observe']}")
    if r["methods"]:
        out.append("method totals (inclusive; nested calls double-count; timers add overhead):")
        for k, v in r["methods"].items():
            out.append(f"  {k:<42} n={v['n']:<5} ms={v['ms']:<9} calls>5ms={v['calls_over_5ms']}")
    se = r["selection"]
    out.append(f"ability selection: {se['candidates']} candidates, {se['code_lineage_records']} are code-lineage records, "
               f"{se['other']} other; {se['selections']} selections picked {se['picked']}, of which code-lineage "
               f"{se['picked_code_lineage']}; sample {se['picked_ids_sample']}")
    if "state_changed_by_observe" in r:
        sc = r["state_changed_by_observe"]
        out.append(f"observe calls that changed what live code reads (abilities / links / promoted links, by content): "
                   f"{sc['calls_that_changed_what_live_code_reads']} of {sc['calls']}")
        out.append(f"  of which abilities {sc['calls_that_changed_abilities']}, links {sc['calls_that_changed_links']}, "
                   f"abilities edited in place with no size change {sc['calls_that_changed_ability_content_in_place']}; "
                   f"calls that changed collision records only: {sc['calls_that_changed_collisions_only']}; "
                   f"net size change {sc['net_size_change']}")
        for name, cnt in sc["fields_changed"].items():
            out.append(f"  fields changed on {name} (record-changes, summed over calls): {cnt or 'none'}")
    if "representation_index_vs_full_rebuild" in r:
        v = r["representation_index_vs_full_rebuild"]
        out.append(f"representation index vs a full rebuild from nothing, after every observe call: "
                   f"{v['checked_after_observe_calls']} checked, {v['mismatches']} differ")
    g = r["genealogy"]
    out.append(f"genealogy: {g['abilities']} abilities, {g['links']} links, tick {g['tick']}")
    return "\n".join(out)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--mode", choices=("timing", "diff", "methods"), default="timing")
    ap.add_argument("--state-dir", default=str(ROOT / "aurora_state"))
    ap.add_argument("--turns", default="")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    turns = [t.strip() for t in Path(a.turns).read_text().splitlines() if t.strip()] if a.turns else DEFAULT_TURNS
    report = run(a.state_dir, turns, a.mode)
    print(json.dumps(report, indent=1) if a.json else render(report))
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    os._exit(main())
