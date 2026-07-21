#!/usr/bin/env python3
"""
PF1.0 (Directive PF1, 2026-07-20) -- attribution instrumentation.

RW7 established that the composer's own output IS the delivered text on
59/60 probes, but left open WHICH mechanism inside word selection carries
topical words through: the directive's own hypothesis names two
candidates -- (a) per-turn lexicon/OETS registration giving fresh words
usage_count=0, which sorts first in _select_constraint_word's diversity
tiebreak, or (b) per-turn intake crystallization placing input words in
fresh DPS crystals whose signatures resonate with the live dominant axis.
This script settles it from real per-turn data, and baselines motif
diversity (expected: near-1 distinct motifs/turn, the mechanical cause of
the "I [verb] [word] clear/real." monotony RW7 found).

Reuses run_probe_battery.py's exact boot/scratch-isolation machinery --
no parallel measurement path. Logging only; zero behavioral change (per
PF1.0's own gate).
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
    enable_capture, disable_capture, pop_composer_raw, pop_word_sources_and_motifs,
)

STATE_DIR = REPO_ROOT / "aurora_state"


def main():
    scratch_root = tempfile.mkdtemp(prefix="aurora_pf1_0_attribution_")
    scratch_state_dir = str(Path(scratch_root) / "aurora_state")
    try:
        shutil.copytree(str(STATE_DIR), scratch_state_dir)
        systems = boot_aurora(state_dir=scratch_state_dir, verbose=False, runtime_profile="surface")
        enable_capture()

        probes = load_probes(PROBES_PATH)
        records = []

        for probe in probes:
            session_id = f"pf1_0_attribution_{probe.probe_id}"
            systems["_session_turn_buffer"] = []
            last_capture = None
            for turn_text in probe.turns:
                process_external_user_turn(
                    systems, turn_text,
                    source_label=f"pf1_0_attribution_{probe.probe_id}",
                    session_id=session_id,
                    run_periodic_maintenance=False,
                )
                composer_raw = pop_composer_raw()
                word_sources, motif_summaries = pop_word_sources_and_motifs()
                last_capture = (turn_text, composer_raw, word_sources, motif_summaries)

            if last_capture is None:
                continue
            last_turn_text, composer_raw, word_sources, motif_summaries = last_capture

            records.append({
                "probe_id": probe.probe_id,
                "dimension": probe.dimension,
                "last_user_turn": last_turn_text,
                "composer_raw": composer_raw,
                "word_sources": word_sources or {},
                "motif_summaries": motif_summaries or [],
            })

        disable_capture()

        # ── Side-channel attribution: candidate_source distribution ────
        source_counts = Counter()
        usage_zero_count = 0
        usage_nonzero_count = 0
        for r in records:
            for word, info in (r["word_sources"] or {}).items():
                if not isinstance(info, dict):
                    continue
                source_counts[info.get("candidate_source", "unknown")] += 1
                if int(info.get("usage_count_at_selection", -1) or 0) == 0:
                    usage_zero_count += 1
                else:
                    usage_nonzero_count += 1

        # ── Motif diversity ─────────────────────────────────────────────
        all_motif_ids = []
        role_seq_counts = Counter()
        for r in records:
            for m in r["motif_summaries"]:
                all_motif_ids.append(m["motif_id"])
                role_seq_counts[tuple(m["role_sequence"])] += 1
        distinct_motif_ids = len(set(all_motif_ids))
        distinct_role_sequences = len(role_seq_counts)

        summary = {
            "probe_count": len(records),
            "candidate_source_distribution": dict(source_counts),
            "usage_count_zero_at_selection": usage_zero_count,
            "usage_count_nonzero_at_selection": usage_nonzero_count,
            "total_words_selected": usage_zero_count + usage_nonzero_count,
            "distinct_motif_ids_used": distinct_motif_ids,
            "distinct_role_sequences_used": distinct_role_sequences,
            "role_sequence_distribution": {str(k): v for k, v in role_seq_counts.items()},
            "motif_turns_captured": len(all_motif_ids),
        }

        print(json.dumps(summary, indent=2))
        print()
        print("Per-probe word sources (last scored turn):")
        for r in records:
            print(f"  [{r['dimension']:22s}] {r['probe_id']:20s}")
            for word, info in (r["word_sources"] or {}).items():
                if isinstance(info, dict):
                    print(f"      {word!r:20s} source={info.get('candidate_source'):16s} "
                          f"usage_at_selection={info.get('usage_count_at_selection')}")
            for m in r["motif_summaries"]:
                print(f"      motif={m['motif_id']} roles={m['role_sequence']}")

        out_dir = REPO_ROOT / "aurora_state" / "probe_battery" / "results"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"pf1_0_attribution_{int(time.time())}.json"
        with open(out_path, "w") as f:
            json.dump({"summary": summary, "records": records}, f, indent=2)
        print(f"\n[REPORT] wrote {out_path}")

    finally:
        shutil.rmtree(scratch_root, ignore_errors=True)


if __name__ == "__main__":
    main()
