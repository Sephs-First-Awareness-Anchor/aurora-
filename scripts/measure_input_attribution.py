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
        gen_box = {}
        orig = G.observe

        def samples(g):
            tot = 0
            for coll in (getattr(g, "abilities", {}), getattr(g, "links", {})):
                for obj in coll.values():
                    tot += int((getattr(obj, "consequence_profile", None) or {}).get("samples", 0) or 0)
            return tot

        def observe(self, *a, **kw):
            gen_box.setdefault("g", self)
            note = ident.note_for_observe()
            calls.append({"named": bool(note), "turn_id": note.get("input_event", ""),
                          "thread": "main" if threading.current_thread() is threading.main_thread() else "background",
                          "caller_named": bool((kw.get("notes") or {}).get("input_event"))})
            return orig(self, *a, **kw)

        G.observe = observe
        per_turn = []
        try:
            for text in TURNS:
                from aurora_internal.aurora_input_pressure import content_axis_loads as _cal
                loads = _cal(systems.get("perception"), text)
                n0 = len(calls)
                g = gen_box.get("g")
                s0 = samples(g) if g else 0
                e0 = {k: v["n"] for k, v in getattr(g, "_input_effects", {}).items()} if g else {}
                real = sys.stdout
                sys.stdout = io.StringIO()
                try:
                    result = aurora.process_external_user_turn(
                        systems, text, source_label="flutter_ui", session_id="attr", auto_search_enabled=False,
                        record_exchange=True, update_interactive_state=True, track_evolutionary_trace=True,
                        run_periodic_maintenance=True, mode_name="BOUNDED")
                finally:
                    sys.stdout = real
                blob = json.dumps(result, default=str).lower()
                leaks = [w for w in ("input_event", "overheard", "evidence_qualification", "input_pressure")
                         if w in blob]
                mine = calls[n0:]
                leaks += [f"id:{c['turn_id']}" for c in mine if c["turn_id"] and c["turn_id"].lower() in blob]
                g = gen_box.get("g")
                real_samples = (samples(g) - s0) if g else None
                shadow = ({k: v["n"] - e0.get(k, 0) for k, v in g._input_effects.items() if v["n"] - e0.get(k, 0)} if g else {})
                per_turn.append({"text": text, "observe_calls": len(mine), "leaks_in_result": leaks,
                                 "real_profile_samples_added": real_samples, "shadow_samples": sum(shadow.values()),
                                 "shadow_pairs": len(shadow),
                                 "shadow_relief_by_axis": ({ax: round(sum(v["relief"][ax] for k, v in g._input_effects.items()
                                                                          if k[0] in {c["turn_id"] for c in mine}), 3)
                                                            for ax in ("X", "T", "N", "B", "A")} if g else None),
                                 "input_loads": loads,
                                 "named": sum(c["named"] for c in mine),
                                 "by_thread": dict(collections.Counter((c["thread"], c["named"]) .__repr__() for c in mine))})
        finally:
            G.observe = orig
        tot = len(calls)
        return {"turns": per_turn, "total_observe": tot, "named": sum(c["named"] for c in calls),
                "distinct_turn_ids": len({c["turn_id"] for c in calls if c["turn_id"]}),
                "background_calls": sum(c["thread"] == "background" for c in calls),
                "unattributed_shadow": getattr(gen_box.get("g"), "_input_effects_unattributed", None)}
    finally:
        shutil.rmtree(scratch_root, ignore_errors=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--state-dir", default=str(ROOT / "aurora_state"))
    print(json.dumps(run(ap.parse_args().state_dir), indent=2))
