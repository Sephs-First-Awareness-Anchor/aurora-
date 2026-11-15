#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Stage F on the live path: after lived turns and a dream episode, does the real QuasiArch observer answer the six developmental
questions from recorded evidence, say what it cannot tell, and change nothing?

Boots Aurora on a COPY of the state, says the fixed turns, runs a dream episode (over representations lived turns credited plus
one never credited) through the dream bridge's own formatting, then asks `quasiarch_observer.investigate_development` each question
and checks the genealogy's state is byte-identical before and after.  Reports; concludes nothing about development.

    python scripts/measure_quasiarch_inquiry.py [--state-dir aurora_state]
"""
from __future__ import annotations

import argparse
import hashlib
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


def run(state_dir):
    sys.path.insert(0, str(ROOT))
    os.chdir(ROOT)
    os.environ.setdefault("AURORA_SKIP_DEP_INSTALL", "1")
    scratch_root = Path(tempfile.mkdtemp(prefix="qa_inquiry_"))
    try:
        scratch = scratch_root / "aurora_state"
        shutil.copytree(state_dir, scratch)
        import aurora
        import aurora_internal.aurora_clone_harvest as clone_harvest
        clone_harvest.absorb_harvest = lambda systems, state_dir=None: {"status": "already_absorbed"}
        from aurora_internal.aurora_dream_genealogy_bridge import DreamEvidenceRecord, DreamGenealogyBridge
        from aurora_internal.constraint_genealogy import PressureVec, TraceItem
        real = sys.stdout
        sys.stdout = io.StringIO()
        try:
            systems = aurora.boot_aurora(state_dir=str(scratch), verbose=False)
        finally:
            sys.stdout = real
        gen = systems.get("genealogy")
        qa = systems.get("quasiarch_observer")
        out = {"quasiarch_present": qa is not None}
        if qa is None:
            return out
        qa.attach_systems(systems)
        for text in TURNS:
            sys.stdout = io.StringIO()
            try:
                aurora.process_external_user_turn(
                    systems, text, source_label="flutter_ui", session_id="qa_inquiry", auto_search_enabled=False,
                    record_exchange=True, update_interactive_state=True, track_evolutionary_trace=True,
                    run_periodic_maintenance=True, mode_name="BOUNDED")
            finally:
                sys.stdout = real
        lived = [r for r, row in gen._rep_ledger.items() if row["lived"]]
        used, ghost = lived[:2], "X:NEVER_CREDITED_IN_ANY_LIVED_TURN"
        bridge = DreamGenealogyBridge(storage_dir=str(scratch_root / "bridge"))
        rec = DreamEvidenceRecord(
            evidence_id="live_e1", episode_id="live_ep1", evidence_type="improvement",
            pressure_before={"X": 0.9, "T": 0.4, "N": 0.1, "B": 0.1, "A": 0.1},
            pressure_after={"X": 0.2, "T": 0.4, "N": 0.1, "B": 0.1, "A": 0.1},
            trace_abilities=used + [ghost], origin_tags={"source": "dream_episode", "seed_lineage_id": "live_ep1"})
        for e in bridge.format_for_genealogy([rec]):
            gen.observe(pressure_before=PressureVec(**e["pressure_before"]), trace=[TraceItem(**t) for t in e["trace"]],
                        pressure_after=PressureVec(**e["pressure_after"]), notes=dict(e["notes"]))

        def digest():
            return hashlib.blake2b(json.dumps([gen._rep_ledger, {f"{l}|{r}": v for (l, r), v in gen._pair_ledger.items()},
                                               dict(gen._input_events), gen.tick_count, gen._replays_skipped,
                                               {k: a.consequence_profile for k, a in gen.abilities.items()}],
                                              sort_keys=True, default=str).encode(), digest_size=12).hexdigest()
        before = digest()
        a = qa.investigate_development("dream_ancestry", episode="live_ep1")
        r = qa.investigate_development("new_relationships", episode="live_ep1")
        c = qa.investigate_development("consequential_changes", episode="live_ep1")
        v = qa.investigate_development("validation")
        u = qa.investigate_development("uncertain")
        out["dream_ancestry"] = {"found": a["found"], "status": a["status"], "n_representations": len(a["representations"]),
                                 "lived_ancestors": [(x["occurrence"], x["name"]) for x in a["lived_ancestors"]][:8],
                                 "unattributed": a["unattributed"], "unknown": a["unknown"]}
        out["new_relationships"] = {"n": len(r["relationships"]), "only_dreamed": sum(x["only_ever_dreamed_or_simulated"] for x in r["relationships"]),
                                    "also_lived": sum(x["also_lived"] for x in r["relationships"]), "promoted": sum(x["promoted"] for x in r["relationships"]),
                                    "unknown": r["unknown"]}
        out["consequential_changes"] = {"n": len(c["changes"]), "consequential": len(c["consequential"]),
                                        "effects": sorted({x["effect"] for x in c["changes"]}), "unknown": c["unknown"]}
        out["validation"] = {"counts": v["counts"], "n_examined": v["n_examined"], "unknown": v["unknown"]}
        out["uncertain"] = {k: (x["n"] if isinstance(x, dict) and "n" in x else x if not isinstance(x, list) else len(x))
                            for k, x in u["items"].items()}
        out["read_only"] = digest() == before
        out["all_answers_non_authoritative"] = not any(x["authoritative"] for x in (a, r, c, v, u))
        return out
    finally:
        shutil.rmtree(scratch_root, ignore_errors=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--state-dir", default=str(ROOT / "aurora_state"))
    print(json.dumps(run(ap.parse_args().state_dir), indent=2, default=str))
