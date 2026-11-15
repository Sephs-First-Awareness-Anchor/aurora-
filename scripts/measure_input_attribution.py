#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""How many genealogy observations made during live turns carry the identity of the input they answer?

Boots Aurora on a COPY of the state, says a fixed script through `process_external_user_turn`, and for every
`ConstraintGenealogyLogger.observe` call records whether the observation's merged notes name an input (turn_id /
input_event), on which thread, and whether the call happened inside a turn at all.  Reports the counts; draws no
conclusion about relief.

    python scripts/measure_input_attribution.py [--state-dir aurora_state]
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
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TURNS = ["Hello Aurora.", "Mara likes tea.", "Does Mara like tea?", "Suppose that Teo is Mara's brother.",
         "I feel calm today.", "What is a noun?", "Something terrible happened and I am scared.", "Thank you, that helps."]


def run(state_dir):
    sys.path.insert(0, str(ROOT))
    os.chdir(ROOT)
    os.environ.setdefault("AURORA_SKIP_DEP_INSTALL", "1")
    scratch_root = Path(tempfile.mkdtemp(prefix="input_attr_"))
    try:
        scratch = scratch_root / "aurora_state"
        shutil.copytree(state_dir, scratch)
        import aurora
        import aurora_internal.aurora_clone_harvest as clone_harvest
        clone_harvest.absorb_harvest = lambda systems, state_dir=None: {"status": "already_absorbed"}
        from aurora_internal import aurora_input_identity as ident
        from aurora_internal.constraint_genealogy import ConstraintGenealogyLogger as G
        real = sys.stdout
        sys.stdout = io.StringIO()
        try:
            systems = aurora.boot_aurora(state_dir=str(scratch), verbose=False)
        finally:
            sys.stdout = real
        calls = []
        orig = G.observe

        def observe(self, *a, **kw):
            note = ident.note_for_observe()
            calls.append({"named": bool(note), "turn_id": note.get("input_event", ""),
                          "thread": "main" if threading.current_thread() is threading.main_thread() else "background",
                          "caller_named": bool((kw.get("notes") or {}).get("input_event"))})
            return orig(self, *a, **kw)

        G.observe = observe
        per_turn = []
        try:
            for text in TURNS:
                n0 = len(calls)
                real = sys.stdout
                sys.stdout = io.StringIO()
                try:
                    aurora.process_external_user_turn(
                        systems, text, source_label="flutter_ui", session_id="attr", auto_search_enabled=False,
                        record_exchange=True, update_interactive_state=True, track_evolutionary_trace=True,
                        run_periodic_maintenance=True, mode_name="BOUNDED")
                finally:
                    sys.stdout = real
                mine = calls[n0:]
                per_turn.append({"text": text, "observe_calls": len(mine),
                                 "named": sum(c["named"] for c in mine),
                                 "by_thread": dict(collections.Counter((c["thread"], c["named"]) .__repr__() for c in mine))})
        finally:
            G.observe = orig
        tot = len(calls)
        return {"turns": per_turn, "total_observe": tot, "named": sum(c["named"] for c in calls),
                "distinct_turn_ids": len({c["turn_id"] for c in calls if c["turn_id"]}),
                "background_calls": sum(c["thread"] == "background" for c in calls)}
    finally:
        shutil.rmtree(scratch_root, ignore_errors=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--state-dir", default=str(ROOT / "aurora_state"))
    print(json.dumps(run(ap.parse_args().state_dir), indent=2))
