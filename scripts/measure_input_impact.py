#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Is an input's impact tied to the pressure it imposed?  (Sir, 2026-11-14: her lower subsystems, emotion and
development, are all measured through pressure, so impact should be tied to the received input.)

Boots Aurora on a COPY of the state and says a fixed script through `process_external_user_turn`.  For each turn it
records (a) the utterance's own per-axis pressure (`aurora_input_pressure.content_axis_loads`, the same function the
live turn injects into the identity field), (b) the DER emotion values before and after, and (c) the 5-axis pressure
and relief that genealogy.observe received during the turn.  It states what it saw; it does not fit a model.

    python scripts/measure_input_impact.py [--state-dir aurora_state]
"""
from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TURNS = ["Hello Aurora.", "Mara likes tea.", "Does Mara like tea?", "Suppose that Teo is Mara's brother.",
         "I feel calm today.", "What is a noun?", "Something terrible happened and I am scared.", "Thank you, that helps."]
AXES = ("X", "T", "N", "B", "A")


def _vec(v):
    if v is None:
        return None
    if hasattr(v, "to_dict"):
        v = v.to_dict()
    return {a: round(float(dict(v).get(a, 0.0)), 6) for a in AXES}


def run(state_dir):
    sys.path.insert(0, str(ROOT))
    os.chdir(ROOT)
    os.environ.setdefault("AURORA_SKIP_DEP_INSTALL", "1")
    scratch_root = Path(tempfile.mkdtemp(prefix="input_impact_"))
    try:
        scratch = scratch_root / "aurora_state"
        shutil.copytree(state_dir, scratch)
        import aurora
        import aurora_internal.aurora_clone_harvest as clone_harvest
        clone_harvest.absorb_harvest = lambda systems, state_dir=None: {"status": "already_absorbed"}
        from aurora_internal.aurora_input_pressure import content_axis_loads
        from aurora_internal.constraint_genealogy import ConstraintGenealogyLogger as G
        real = sys.stdout
        sys.stdout = io.StringIO()
        try:
            systems = aurora.boot_aurora(state_dir=str(scratch), verbose=False)
        finally:
            sys.stdout = real
        der = getattr(systems.get("dimensional"), "der", None)
        seen = []
        orig = G.observe

        def observe(self, *a, **kw):
            seen.append({"before": _vec(kw.get("pressure_before") if "pressure_before" in kw else (a[0] if a else None)),
                         "after": _vec(kw.get("pressure_after") if "pressure_after" in kw else (a[2] if len(a) > 2 else None))})
            return orig(self, *a, **kw)

        G.observe = observe
        rows = []
        try:
            for text in TURNS:
                loads = content_axis_loads(systems.get("perception"), text)
                emo0 = dict(getattr(der, "emotions", {}) or {})
                n0 = len(seen)
                real = sys.stdout
                sys.stdout = io.StringIO()
                try:
                    aurora.process_external_user_turn(
                        systems, text, source_label="flutter_ui", session_id="impact", auto_search_enabled=False,
                        record_exchange=True, update_interactive_state=True, track_evolutionary_trace=True,
                        run_periodic_maintenance=True, mode_name="BOUNDED")
                finally:
                    sys.stdout = real
                emo1 = dict(getattr(der, "emotions", {}) or {})
                moved = {k: round(emo1.get(k, 0.0) - emo0.get(k, 0.0), 4) for k in emo1 if abs(emo1.get(k, 0.0) - emo0.get(k, 0.0)) > 1e-9}
                obs = seen[n0:]
                relief = {a: 0.0 for a in AXES}
                shaped = 0
                for o in obs:
                    if o["before"] and o["after"]:
                        shaped += 1
                        for a in AXES:
                            relief[a] = round(relief[a] + o["before"][a] - o["after"][a], 6)
                top = sorted(moved.items(), key=lambda kv: -abs(kv[1]))[:3]
                rows.append({"text": text, "input_loads": ({a: round(v, 3) for a, v in loads.items()} if loads else None),
                             "emotions_moved": len(moved), "top_emotion_moves": top,
                             "observe_calls": len(obs), "observe_with_pressure": shaped,
                             "net_relief_over_turn": relief})
        finally:
            G.observe = orig
        return {"der_found": der is not None, "turns": rows}
    finally:
        shutil.rmtree(scratch_root, ignore_errors=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--state-dir", default=str(ROOT / "aurora_state"))
    a = ap.parse_args()
    print(json.dumps(run(a.state_dir), indent=1))
