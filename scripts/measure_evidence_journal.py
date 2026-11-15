#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Stage E on the live path: does a booted Surface profile journal what its genealogy observes, and can a canonical logger
consolidate it once, in order, at what cost?

Boots Aurora with runtime_profile="surface" on a COPY of the state, says the fixed turns, then reports the journal (events,
identities, inputs described once, bytes, per-observe journaling cost), and consolidates it into a canonical logger built on a
copy of the canonical genealogy directory (events/second; a second pass applies nothing).  Reports; concludes nothing about
development.

    python scripts/measure_evidence_journal.py [--state-dir aurora_state]
"""
from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TURNS = ["Hello Aurora.", "Mara likes tea.", "Does Mara like tea?", "Suppose that Teo is Mara's brother.",
         "I feel calm today.", "What is a noun?", "Something terrible happened and I am scared.", "Thank you, that helps."]


def run(state_dir):
    sys.path.insert(0, str(ROOT))
    os.chdir(ROOT)
    os.environ.setdefault("AURORA_SKIP_DEP_INSTALL", "1")
    scratch_root = Path(tempfile.mkdtemp(prefix="ev_journal_"))
    try:
        scratch = scratch_root / "aurora_state"
        shutil.copytree(state_dir, scratch)
        import aurora
        import aurora_internal.aurora_clone_harvest as clone_harvest
        clone_harvest.absorb_harvest = lambda systems, state_dir=None: {"status": "already_absorbed"}
        from aurora_internal import genealogy_evidence_journal as J
        from aurora_internal.constraint_genealogy import ConstraintGenealogyLogger as G, GenealogyConfig
        real = sys.stdout
        sys.stdout = io.StringIO()
        try:
            systems = aurora.boot_aurora(state_dir=str(scratch), verbose=False, runtime_profile="surface")
        finally:
            sys.stdout = real
        gen = systems.get("genealogy")
        out = {"persist_scope": gen.persist_scope}
        t_obs = []
        orig = G._journal_observation

        def timed(self, *a, **k):
            t = time.perf_counter()
            r = orig(self, *a, **k)
            t_obs.append((time.perf_counter() - t) * 1000.0)
            return r

        G._journal_observation = timed
        try:
            for text in TURNS:
                sys.stdout = io.StringIO()
                try:
                    aurora.process_external_user_turn(
                        systems, text, source_label="flutter_ui", session_id="ev_journal", auto_search_enabled=False,
                        record_exchange=True, update_interactive_state=True, track_evolutionary_trace=True,
                        run_periodic_maintenance=True, mode_name="BOUNDED")
                finally:
                    sys.stdout = real
        finally:
            G._journal_observation = orig
        gen.persist_session_state()
        recs, bad = J.read_records(gen._journal_path())
        own = [r for r in recs if r["origin"] == gen.run_id]
        ids = [r["notes"].get("input_event") for r in own if r["notes"].get("input_event")]
        out["journal"] = {"events": len(own), "malformed": bad, "seq_contiguous": [r["seq"] for r in own] == list(range(1, len(own) + 1)),
                          "events_naming_an_input": len(ids), "distinct_inputs": len(set(ids)),
                          "inputs_described": sum(1 for r in own if "input" in r),
                          "bytes": os.path.getsize(gen._journal_path()),
                          "bytes_per_event": round(os.path.getsize(gen._journal_path()) / max(1, len(own)), 1),
                          "journal_ms_per_observe_mean": round(sum(t_obs) / max(1, len(t_obs)), 4),
                          "journal_ms_per_observe_max": round(max(t_obs or [0.0]), 4), "journal_ms_total": round(sum(t_obs), 2)}
        canon_dir = scratch_root / "canon" / "genealogy"
        shutil.copytree(scratch / "genealogy", canon_dir)
        shutil.copy(gen._journal_path(), canon_dir.parent / "genealogy_surface_journal.jsonl")
        canon = G("canon_check", config=GenealogyConfig(), output_dir=str(canon_dir))
        from aurora_runtime import _restore_genealogy_state
        _restore_genealogy_state(canon, str(canon_dir))
        t0 = time.perf_counter()
        first = canon.consolidate_journal(str(canon_dir.parent / "genealogy_surface_journal.jsonl"), max_events=10 ** 6)
        dt = time.perf_counter() - t0
        second = canon.consolidate_journal(str(canon_dir.parent / "genealogy_surface_journal.jsonl"), max_events=10 ** 6)
        out["consolidation"] = {"first": first, "seconds": round(dt, 3),
                                "events_per_second": round(first["applied"] / dt, 1) if dt else None, "second": second,
                                "ledger_reps": len(canon._rep_ledger),
                                "inputs_known_to_canonical": len(canon._input_events),
                                "occurrences": sorted({v.get("occurrence", "") for v in canon._input_events.values()})}
        return out
    finally:
        shutil.rmtree(scratch_root, ignore_errors=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--state-dir", default=str(ROOT / "aurora_state"))
    print(json.dumps(run(ap.parse_args().state_dir), indent=2, default=str))
