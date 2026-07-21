#!/usr/bin/env python3
"""
RW7 (Architecture Wiring Audit, 2026-07-20) -- attribution run for relevance.

The delivered path's word selection (SentenceComposer._select_constraint_word)
has no input-relevance term, and the one branch that used to compute a
relevance boost (_fill_primitive_slot, "20x context-relevance boost") is
dead code -- compose() never routes through _fill_template. Yet the probe
battery measures a real relevance score against the DELIVERED text
(resp_A.content, per run_probe_battery.py's own D2.4 fix). This script
answers where that score actually comes from: does resp_A.content, for
the SCORED (last) turn of each probe, carry the composer's own words
verbatim, or is it built entirely by the waterfall chain's own anchor-
injection repair functions (_repair_unproductive_echo / _repair_
unanswered_question / _repair_discourse_coherence), which never call
SentenceComposer at all?

Reuses run_probe_battery.py's exact boot/scratch-isolation/relevance-
scorer machinery -- no parallel measurement path invented. Per probe,
drives every turn (matching run_probe's own real transcript), and for
the LAST (scored) turn captures: resp_A.src (the waterfall's own
attribution label, or "composer_unified" if D2.1 swapped it in),
resp_A.content (== the scored text), resp_B.content, and the composer's
raw pre-D2.1 output via aurora_internal.aurora_attribution_trace.

No fixes ship before this lands (per the audit's own RW7 mandate) --
this script performs measurement only, zero behavioral change to any
live boot (capture is opt-in, disabled by default everywhere else).
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
import json
import shutil
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aurora import boot_aurora, process_external_user_turn  # noqa: E402
from aurora_internal.aurora_semantic_probe_battery import PROBES_PATH, load_probes  # noqa: E402
from aurora_internal.aurora_attribution_trace import (  # noqa: E402
    enable_capture, disable_capture, pop_composer_raw,
)

STATE_DIR = REPO_ROOT / "aurora_state"


def _relevance_scorer(systems):
    perception = systems.get("perception")
    oets = getattr(perception, "oets", None)
    web = getattr(oets, "web", None) if oets is not None else None

    def scorer(input_text, response_text):
        try:
            import re as _re
            from aurora_constraint_emission import build_relevance_anchor_set
            anchor = build_relevance_anchor_set(input_text, [], web)
            words = _re.findall(r"[a-zA-Z][a-zA-Z']{2,}", str(response_text or "").lower())
            if not words:
                return None
            hits = sum(1 for w in words if w in anchor)
            return hits / len(words)
        except Exception:
            return None

    return scorer


def main():
    scratch_root = tempfile.mkdtemp(prefix="aurora_rw7_attribution_")
    scratch_state_dir = str(Path(scratch_root) / "aurora_state")
    try:
        shutil.copytree(str(STATE_DIR), scratch_state_dir)
        systems = boot_aurora(state_dir=scratch_state_dir, verbose=False, runtime_profile="surface")
        enable_capture()
        scorer = _relevance_scorer(systems)

        probes = load_probes(PROBES_PATH)
        records = []

        for probe in probes:
            session_id = f"rw7_attribution_{probe.probe_id}"
            systems["_session_turn_buffer"] = []
            last_response = None
            for turn_text in probe.turns:
                response = dict(
                    process_external_user_turn(
                        systems, turn_text,
                        source_label=f"rw7_attribution_{probe.probe_id}",
                        session_id=session_id,
                        run_periodic_maintenance=False,
                    ) or {}
                )
                composer_raw = pop_composer_raw()
                last_response = (turn_text, response, composer_raw)

            if last_response is None:
                continue
            last_turn_text, response, composer_raw = last_response
            resp_a = response.get("resp_A")
            resp_b = response.get("resp_B")
            final_delivered = str(getattr(resp_a, "content", "") or "").strip()
            resp_b_content = str(getattr(resp_b, "content", "") or "").strip() if resp_b is not None else None
            branch = str(getattr(resp_a, "src", "") or "")

            relevance = None
            if final_delivered:
                relevance = scorer(last_turn_text, final_delivered)

            composer_reached = bool(
                composer_raw and final_delivered
                and composer_raw.strip() == final_delivered.strip()
            )

            records.append({
                "probe_id": probe.probe_id,
                "dimension": probe.dimension,
                "last_user_turn": last_turn_text,
                "branch": branch,
                "composer_raw": composer_raw,
                "final_delivered": final_delivered,
                "resp_b_content": resp_b_content,
                "composer_reached_delivery_verbatim": composer_reached,
                "relevance": relevance,
            })

        disable_capture()

        # ── Attribution summary ─────────────────────────────────────────
        branch_counts = Counter(r["branch"] or "(empty)" for r in records)
        composer_unified = [r for r in records if r["branch"] == "composer_unified"]
        non_composer = [r for r in records if r["branch"] != "composer_unified"]
        verbatim_composer = [r for r in composer_unified if r["composer_reached_delivery_verbatim"]]

        def _mean_relevance(recs):
            vals = [r["relevance"] for r in recs if r["relevance"] is not None]
            return (sum(vals) / len(vals)) if vals else None

        summary = {
            "probe_count": len(records),
            "branch_distribution": dict(branch_counts),
            "composer_unified_count": len(composer_unified),
            "composer_unified_verbatim_count": len(verbatim_composer),
            "composer_unified_but_modified_count": len(composer_unified) - len(verbatim_composer),
            "non_composer_count": len(non_composer),
            "mean_relevance_all": _mean_relevance(records),
            "mean_relevance_composer_unified": _mean_relevance(composer_unified),
            "mean_relevance_non_composer": _mean_relevance(non_composer),
        }

        print(json.dumps(summary, indent=2))
        print()
        print("Per-probe branch + relevance:")
        for r in records:
            rel = f"{r['relevance']:.3f}" if r["relevance"] is not None else "None"
            print(f"  [{r['dimension']:22s}] {r['probe_id']:20s} branch={r['branch']:24s} "
                  f"verbatim_composer={r['composer_reached_delivery_verbatim']!s:5s} relevance={rel}")

        out_dir = REPO_ROOT / "aurora_state" / "probe_battery" / "results"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"rw7_attribution_{int(time.time())}.json"
        with open(out_path, "w") as f:
            json.dump({"summary": summary, "records": records}, f, indent=2)
        print(f"\n[REPORT] wrote {out_path}")

    finally:
        shutil.rmtree(scratch_root, ignore_errors=True)


if __name__ == "__main__":
    main()
