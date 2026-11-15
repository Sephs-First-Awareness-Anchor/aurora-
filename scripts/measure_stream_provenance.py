#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Which evidence-origin labels actually reach the genealogy?  (Directive "Developmental Evidence, Simulated
Experience, and Consequence-Grounded Promotion", Stages B/D audit.)

Boots Aurora on a COPY of the state, says a fixed script through `process_external_user_turn`, wraps
`ConstraintGenealogyLogger.observe`, and tallies every trace item's `EnvironmentVector` (module, stream_type,
call_tag) and the caller.  Live-turn traffic only: it does not run the dream trainer, so it says nothing about
what the dream path would send.  Nothing in the state directory is modified.

    python scripts/measure_stream_provenance.py [--state-dir aurora_state] [--json]
"""
from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TURNS = ["Hello Aurora.", "Mara likes tea.", "Does Mara like tea?", "Suppose that Teo is Mara's brother.",
         "Who is Teo?", "What is a noun?", "I feel calm today.", "Tell me what you know about tea."]


def run(state_dir: str):
    sys.path.insert(0, str(ROOT))
    os.chdir(ROOT)
    os.environ.setdefault("AURORA_SKIP_DEP_INSTALL", "1")
    scratch_root = Path(tempfile.mkdtemp(prefix="stream_prov_"))
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
        envs, callers, kinds = Counter(), Counter(), Counter()
        calls = {"n": 0}
        orig = G.observe

        def observe(self, *args, **kw):
            calls["n"] += 1
            trace = kw.get("trace")
            if trace is None and len(args) > 1:
                trace = args[1]
            fr = sys._getframe(1)
            callers[f"{Path(fr.f_code.co_filename).name}:{fr.f_code.co_name}"] += 1
            for item in list(trace or []):
                env = getattr(item, "env", None)
                kinds[str(getattr(item, "kind", ""))] += 1
                envs[(getattr(env, "module", "") if env else "", getattr(env, "stream_type", "") if env else "",
                      getattr(env, "call_tag", "") if env else "")] += 1
            return orig(self, *args, **kw)

        G.observe = observe
        try:
            for text in TURNS:
                real = sys.stdout
                sys.stdout = io.StringIO()
                try:
                    aurora.process_external_user_turn(
                        systems, text, source_label="flutter_ui", session_id="streams", auto_search_enabled=False,
                        record_exchange=True, update_interactive_state=True, track_evolutionary_trace=True,
                        run_periodic_maintenance=True, mode_name="BOUNDED")
                finally:
                    sys.stdout = real
        finally:
            G.observe = orig
        return {"turns": len(TURNS), "observe_calls": calls["n"], "trace_item_kinds": dict(kinds),
                "environment_vectors": [{"module": m, "stream_type": s, "call_tag": c, "items": n}
                                        for (m, s, c), n in envs.most_common()],
                "stream_types_seen": sorted({s for (_, s, _) in envs}),
                "callers": dict(callers.most_common(12))}
    finally:
        shutil.rmtree(scratch_root, ignore_errors=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--state-dir", default=str(ROOT / "aurora_state"))
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    report = run(a.state_dir)
    print(json.dumps(report, indent=2) if a.json else json.dumps(report, indent=1))
