#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Tests 9 and 10 (directive IX): the same matched experiential sequence on two checkouts, reporting what developed and what it cost.

    python scripts/compare_architectures.py --root <checkout> --state-dir <pristine state copy> --out result.json

Boots Aurora from `--root` on a COPY of `--state-dir`, says the fixed turns, and records, for comparison across checkouts and across
repeats of the same checkout (the repeat is the noise floor): each reply (operational behavior), representation profiles and
consequence attribution (sample counts, relief), relationship promotion (links, pair counts), memory (web nodes, relations, held and
unheld assertions by basis), and cost (foreground time per turn, genealogy observe calls and time, on the main thread vs others).
Reports; concludes nothing.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path

TURNS = ["Hello Aurora.", "Mara likes tea.", "Does Mara like tea?", "Suppose that Teo is Mara's brother.",
         "Is Teo Mara's brother?", "I feel calm today.", "What is a noun?", "Actually, Mara does not like tea.",
         "Does Mara like tea?", "Something terrible happened and I am scared.", "Thank you, that helps.",
         "What do you know about Mara?"]


def run(root, state_dir):
    sys.path.insert(0, str(root))
    os.chdir(root)
    os.environ.setdefault("AURORA_SKIP_DEP_INSTALL", "1")
    tmp = Path(tempfile.mkdtemp(prefix="cmp_arch_"))
    try:
        scratch = tmp / "aurora_state"
        shutil.copytree(state_dir, scratch)
        import aurora
        import aurora_internal.aurora_clone_harvest as clone_harvest
        clone_harvest.absorb_harvest = lambda systems, state_dir=None: {"status": "already_absorbed"}
        from aurora_internal.constraint_genealogy import ConstraintGenealogyLogger as G
        real = sys.stdout
        calls = {"main": [0, 0.0], "other": [0, 0.0]}
        orig = G.observe

        def timed(self, *a, **k):
            t = time.perf_counter()
            try:
                return orig(self, *a, **k)
            finally:
                slot = calls["main" if threading.current_thread() is threading.main_thread() else "other"]
                slot[0] += 1
                slot[1] += (time.perf_counter() - t) * 1000.0
        G.observe = timed
        sys.stdout = io.StringIO()
        t0 = time.perf_counter()
        try:
            systems = aurora.boot_aurora(state_dir=str(scratch), verbose=False)
        finally:
            sys.stdout = real
        boot_s = time.perf_counter() - t0
        gen = systems.get("genealogy")
        before = {k: (a.consequence_profile or {}).get("samples", 0) for k, a in gen.abilities.items()}
        links_before = set(gen.links)
        replies, lat = [], []
        for text in TURNS:
            sys.stdout = io.StringIO()
            t = time.perf_counter()
            try:
                r = aurora.process_external_user_turn(
                    systems, text, source_label="flutter_ui", session_id="cmp", auto_search_enabled=False,
                    record_exchange=True, update_interactive_state=True, track_evolutionary_trace=True,
                    run_periodic_maintenance=True, mode_name="BOUNDED")
            finally:
                sys.stdout = real
            lat.append(time.perf_counter() - t)
            text_out = getattr(r, "response", None) or getattr(r, "text", None) or (r.get("response") if isinstance(r, dict) else str(r))
            replies.append(str(text_out))
        time.sleep(3)                                              # let background threads settle
        profiles = {}
        for k, a in gen.abilities.items():
            cp = a.consequence_profile or {}
            if cp.get("samples", 0) != before.get(k, 0):
                profiles[k] = {"samples_added": cp.get("samples", 0) - before.get(k, 0),
                               "effect": {x: round(float(v), 6) for x, v in (cp.get("effect") or {}).items()}}
        oets = systems.get("oets") or getattr(systems.get("perception"), "oets", None) or (systems.get("perception") or {}).get("oets") \
            if not isinstance(systems.get("perception"), dict) else systems.get("oets") or systems["perception"].get("oets")
        web = oets.web
        bases, held, unheld = {}, 0, 0
        for rel in web.relations.values():
            for p in ((getattr(rel, "assertion", None) or {}).get("predicates") or {}).values():
                for b, n in (p.get("basis") or {}).items():
                    bases[b] = bases.get(b, 0) + int(n)
                held += 1 if p.get("n", 0) else 0
                unheld += 0 if p.get("n", 0) else 1
        out = {"root": str(root), "boot_seconds": round(boot_s, 2), "replies": replies,
               "turn_seconds": [round(x, 3) for x in lat], "turn_seconds_mean": round(sum(lat) / len(lat), 3),
               "observe": {"main_calls": calls["main"][0], "main_ms": round(calls["main"][1], 1),
                           "other_calls": calls["other"][0], "other_ms": round(calls["other"][1], 1)},
               "profiles_changed": profiles, "samples_added_total": sum(v["samples_added"] for v in profiles.values()),
               "links_added": sorted(set(gen.links) - links_before), "links_total": len(gen.links),
               "pair_stats_pairs": len(gen._pair_stats), "pair_stats_count_total": sum(v.count for v in gen._pair_stats.values()),
               "relief_event_count": int(gen.relief_event_count), "tick_count": int(gen.tick_count),
               "memory": {"web_nodes": len(web.nodes), "web_relations": len(web.relations), "assertion_basis_counts": bases,
                          "predicates_held": held, "predicates_not_held": unheld}}
        G.observe = orig
        return out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--state-dir", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    Path(a.out).write_text(json.dumps(run(Path(a.root).resolve(), a.state_dir), indent=1, default=str))
