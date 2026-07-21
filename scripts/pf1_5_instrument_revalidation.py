#!/usr/bin/env python3
"""
PF1.5 (Directive PF1, 2026-07-21) -- two-direction golden re-validation.

Runs RW7's exact 60-probe battery through BOTH the existing instruments
(relevance = hits/len, _parseable) and the new PF1.5 ones (adequacy_score,
wellformed_and_coherent), for the same delivered text, and reports honest
deltas -- no floor relaxation, no forcing agreement either direction.

Reuses run_probe_battery.py's exact boot/scratch-isolation machinery and
resp_A delivered-text extraction (D2.4) -- no parallel measurement path.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aurora import boot_aurora, process_external_user_turn  # noqa: E402
from aurora_constraint_emission import build_relevance_anchor_set  # noqa: E402
from aurora_internal.aurora_semantic_probe_battery import (  # noqa: E402
    PROBES_PATH, load_probes, _parseable,
)
from aurora_internal.aurora_pf1_5_instruments import (  # noqa: E402
    adequacy_score, wellformed_and_coherent,
)
from run_probe_battery import _extract_delivered_response_text  # noqa: E402

STATE_DIR = REPO_ROOT / "aurora_state"


def _old_relevance(input_text: str, response_text: str, web) -> float:
    import re
    anchor = build_relevance_anchor_set(input_text, [], web)
    words = re.findall(r"[a-zA-Z][a-zA-Z']{2,}", response_text.lower())
    if not words:
        return None
    hits = sum(1 for w in words if w in anchor)
    return hits / len(words)


def main():
    scratch_root = tempfile.mkdtemp(prefix="aurora_pf1_5_revalidation_")
    scratch_state_dir = str(Path(scratch_root) / "aurora_state")
    try:
        shutil.copytree(str(STATE_DIR), scratch_state_dir)
        systems = boot_aurora(state_dir=scratch_state_dir, verbose=False, runtime_profile="surface")
        aurora_gateway = systems.get("aurora")
        perception = systems.get("perception")
        oets = getattr(perception, "oets", None)
        web = getattr(oets, "web", None) if oets is not None else None

        probes = load_probes(PROBES_PATH)
        records = []

        for probe in probes:
            session_id = f"pf1_5_revalidation_{probe.probe_id}"
            systems["_session_turn_buffer"] = []
            last_turn_text = ""
            last_response_text = ""
            for turn_text in probe.turns:
                response = dict(process_external_user_turn(
                    systems, turn_text,
                    source_label=f"pf1_5_revalidation_{probe.probe_id}",
                    session_id=session_id,
                    run_periodic_maintenance=False,
                ) or {})
                last_turn_text = turn_text
                last_response_text = _extract_delivered_response_text(response, turn_text, aurora_gateway)

            old_rel = _old_relevance(last_turn_text, last_response_text, web)
            anchor = build_relevance_anchor_set(last_turn_text, [], web)
            new_adq = adequacy_score(last_response_text, anchor)
            old_wf = _parseable(last_response_text)
            new_wf = wellformed_and_coherent(last_response_text)

            records.append({
                "probe_id": probe.probe_id,
                "dimension": probe.dimension,
                "response_text": last_response_text,
                "old_relevance": old_rel,
                "new_adequacy": new_adq,
                "old_parseable": old_wf,
                "new_wellformed_coherent": new_wf,
                "wellformedness_flipped": bool(old_wf != new_wf),
            })

        rel_vals = [r["old_relevance"] for r in records if r["old_relevance"] is not None]
        adq_vals = [r["new_adequacy"] for r in records if r["new_adequacy"] is not None]
        flipped = [r for r in records if r["wellformedness_flipped"]]

        summary = {
            "probe_count": len(records),
            "mean_old_relevance": sum(rel_vals) / len(rel_vals) if rel_vals else None,
            "mean_new_adequacy": sum(adq_vals) / len(adq_vals) if adq_vals else None,
            "old_parseable_pass_count": sum(1 for r in records if r["old_parseable"]),
            "new_wellformed_coherent_pass_count": sum(1 for r in records if r["new_wellformed_coherent"]),
            "wellformedness_flipped_count": len(flipped),
            "wellformedness_flipped_probe_ids": [r["probe_id"] for r in flipped],
        }

        print(json.dumps(summary, indent=2))
        print()
        for r in records:
            print(f"  [{r['dimension']:22s}] {r['probe_id']:24s} "
                  f"old_rel={r['old_relevance']} new_adq={r['new_adequacy']} "
                  f"old_wf={r['old_parseable']} new_wfc={r['new_wellformed_coherent']} "
                  f"flip={r['wellformedness_flipped']}")
            print(f"      {r['response_text']!r}")

        out_dir = REPO_ROOT / "aurora_state" / "probe_battery" / "results"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"pf1_5_revalidation_{int(time.time())}.json"
        with open(out_path, "w") as f:
            json.dump({"summary": summary, "records": records}, f, indent=2)
        print(f"\n[REPORT] wrote {out_path}")

    finally:
        shutil.rmtree(scratch_root, ignore_errors=True)


if __name__ == "__main__":
    main()
