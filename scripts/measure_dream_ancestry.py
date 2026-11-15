#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Stage C on the live path: after lived turns, do dreams trace to what was lived, and does dream replay reach genealogy?

Boots Aurora on a COPY of the state, says the fixed turns, reads the representation ledger, then (a) pushes a dream episode through
the dream bridge's own formatting into the live genealogy (what the dream orchestrator's `_apply_genealogy` does) and (b)
runs the dream trainer's replay path (`_witness_directed_training_samples`) and counts how its genealogy observations are
identified.  Reports; concludes nothing about development.

    python scripts/measure_dream_ancestry.py [--state-dir aurora_state]
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
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TURNS = ["Hello Aurora.", "Mara likes tea.", "Does Mara like tea?", "Suppose that Teo is Mara's brother.",
         "I feel calm today.", "What is a noun?", "Something terrible happened and I am scared.", "Thank you, that helps."]


def run(state_dir):
    sys.path.insert(0, str(ROOT))
    os.chdir(ROOT)
    os.environ.setdefault("AURORA_SKIP_DEP_INSTALL", "1")
    scratch_root = Path(tempfile.mkdtemp(prefix="dream_anc_"))
    try:
        scratch = scratch_root / "aurora_state"
        shutil.copytree(state_dir, scratch)
        import aurora
        import aurora_internal.aurora_clone_harvest as clone_harvest
        clone_harvest.absorb_harvest = lambda systems, state_dir=None: {"status": "already_absorbed"}
        from aurora_internal import aurora_input_identity as ident
        from aurora_internal.aurora_dream_genealogy_bridge import DreamEvidenceRecord, DreamGenealogyBridge
        from aurora_internal.constraint_genealogy import ConstraintGenealogyLogger as G, PressureVec, TraceItem
        real = sys.stdout
        sys.stdout = io.StringIO()
        try:
            systems = aurora.boot_aurora(state_dir=str(scratch), verbose=False)
        finally:
            sys.stdout = real
        gen = systems.get("genealogy")
        calls = []
        orig = G.observe

        def observe(self, *a, **kw):
            note = ident.note_for_observe()
            src = str((kw.get("notes") or {}).get("source", ""))
            calls.append({"named": bool(note), "from_notes": bool(not note and ident.identity_from_notes(kw.get("notes"))),
                          "source": src, "thread": "main" if threading.current_thread() is threading.main_thread() else "bg"})
            return orig(self, *a, **kw)

        G.observe = observe
        try:
            for text in TURNS:
                sys.stdout = io.StringIO()
                try:
                    aurora.process_external_user_turn(
                        systems, text, source_label="flutter_ui", session_id="dream_anc", auto_search_enabled=False,
                        record_exchange=True, update_interactive_state=True, track_evolutionary_trace=True,
                        run_periodic_maintenance=True, mode_name="BOUNDED")
                finally:
                    sys.stdout = real
            lived_credited = [r for r, row in gen._rep_ledger.items() if row["lived"]]
            out = {"representations_with_lived_ancestry": len(lived_credited),
                   "ledger_entries": len(gen._rep_ledger)}
            # (a) a dream episode over representations that WERE credited by lived turns, plus one that never was
            used = lived_credited[:2]
            ghost = "X:NEVER_CREDITED_IN_ANY_LIVED_TURN"
            bridge = DreamGenealogyBridge(storage_dir=str(scratch_root / "bridge"))
            rec = DreamEvidenceRecord(
                evidence_id="live_e1", episode_id="live_ep1", evidence_type="improvement",
                pressure_before={"X": 0.9, "T": 0.4, "N": 0.1, "B": 0.1, "A": 0.1},
                pressure_after={"X": 0.2, "T": 0.4, "N": 0.1, "B": 0.1, "A": 0.1},
                trace_abilities=used + [ghost], origin_tags={"source": "dream_episode", "seed_lineage_id": "live_ep1"})
            n0 = len(calls)
            for e in bridge.format_for_genealogy([rec]):
                gen.observe(pressure_before=PressureVec(**e["pressure_before"]), trace=[TraceItem(**t) for t in e["trace"]],
                            pressure_after=PressureVec(**e["pressure_after"]), notes=dict(e["notes"]))
            anc = gen.ancestry_of(used + [ghost])
            out["dream_episode"] = {"observations": len(calls) - n0, "ancestry_status": anc["status"],
                                    "traced": len(anc["traced"]), "unattributed": anc["unattributed"],
                                    "lived_inputs": len(anc["lived_inputs"]),
                                    "ghost_has_lived_history": bool(gen.representation_evidence(ghost)["lived_inputs"]),
                                    "used_lived_total_unchanged": all(
                                        gen.representation_evidence(r)["lived_total"] == gen._rep_ledger[r]["lived_total"]
                                        for r in used)}
            # (b) the dream trainer's replay path
            trainer = systems.get("dream_trainer")
            n1 = len(calls)
            replayed = None
            if trainer is not None:
                sys.stdout = io.StringIO()
                try:
                    replayed = trainer._witness_directed_training_samples(
                        systems, ["Mara likes tea and drinks it every morning.", "A noun names a person place or thing."],
                        response_id="", dims=["clarity"])
                except Exception as exc:
                    replayed = f"error: {type(exc).__name__}"
                finally:
                    sys.stdout = real
            mine = calls[n1:]
            out["dream_replay_path"] = {"trainer_present": trainer is not None, "witnessed": replayed,
                                        "observations": len(mine), "named": sum(c["named"] for c in mine),
                                        "from_notes": sum(c["from_notes"] for c in mine),
                                        "unidentified": sum(1 for c in mine if not c["named"] and not c["from_notes"])}
            out["unattributed_credits"] = gen._input_effects_unattributed
        finally:
            G.observe = orig
        return out
    finally:
        shutil.rmtree(scratch_root, ignore_errors=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--state-dir", default=str(ROOT / "aurora_state"))
    print(json.dumps(run(ap.parse_args().state_dir), indent=2, default=str))
