#!/usr/bin/env python3
"""
PF1.6 (Directive PF1, 2026-07-21) -- acceptance.

Composition battery x3 under PF1.5's new instruments (adequacy_score,
wellformed_and_coherent), stratified simple_concrete/abstract_conceptual
exactly like every prior composition-battery gate in this campaign
(PROMPT_STRATA, aurora_internal/aurora_semantic_probe_battery.py) --
new honest baselines, no comparison to old blind-scorer numbers, no
floor relaxation. Also measures motif diversity, descriptor ("clear"/
"real") repetition share, abstain rate, and a diagnostic-leakage check
(same telemetry-token check PF1.4's own verification used).

Boots ONCE (not x3) and loops the 60-probe battery three times against
the same live state, each pass its own session_ids -- three independent
measurement passes, not three fresh boots (the expensive part). Reuses
run_probe_battery.py's exact scratch-isolation and D2.4 delivered-text
extraction -- no parallel measurement path.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
import json
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aurora import boot_aurora, process_external_user_turn  # noqa: E402
from aurora_constraint_emission import build_relevance_anchor_set  # noqa: E402
from aurora_expression_perception import SentenceComposer  # noqa: E402
from aurora_internal.aurora_semantic_probe_battery import (  # noqa: E402
    PROBES_PATH, load_probes, PROMPT_STRATA,
)
from aurora_internal.aurora_pf1_5_instruments import (  # noqa: E402
    adequacy_score, wellformed_and_coherent,
)
from aurora_internal.aurora_attribution_trace import (  # noqa: E402
    enable_capture, disable_capture, pop_word_sources_and_motifs,
)
from run_probe_battery import _extract_delivered_response_text  # noqa: E402

STATE_DIR = REPO_ROOT / "aurora_state"
_TELEMETRY_TOKEN_RE = re.compile(r"[a-zA-Z_]+=[^\s]+|\btriggered\b|\[partial\]", re.IGNORECASE)
_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z']{2,}")
_ABSTAIN_TEXTS = set(SentenceComposer._ABSTAIN_TEMPLATES)


def _stratum_mean(records, key):
    by_stratum = {"simple_concrete": [], "abstract_conceptual": []}
    for r in records:
        stratum = PROMPT_STRATA.get(r["dimension"])
        if stratum in by_stratum and r[key] is not None:
            by_stratum[stratum].append(r[key])
    return {
        s: (sum(vals) / len(vals) if vals else None)
        for s, vals in by_stratum.items()
    }


def _stratum_rate(records, key):
    by_stratum = {"simple_concrete": [], "abstract_conceptual": []}
    for r in records:
        stratum = PROMPT_STRATA.get(r["dimension"])
        if stratum in by_stratum:
            by_stratum[stratum].append(bool(r[key]))
    return {
        s: (sum(vals) / len(vals) if vals else None)
        for s, vals in by_stratum.items()
    }


def _run_one_pass(systems, aurora_gateway, web, probes, run_idx):
    records = []
    all_motif_role_seqs = []
    total_content_words = 0
    clear_real_count = 0
    abstain_count = 0
    leaked_count = 0

    enable_capture()
    for probe in probes:
        session_id = f"pf1_6_acceptance_r{run_idx}_{probe.probe_id}"
        systems["_session_turn_buffer"] = []
        last_turn_text = ""
        last_response_text = ""
        for turn_text in probe.turns:
            response = dict(process_external_user_turn(
                systems, turn_text,
                source_label=f"pf1_6_acceptance_r{run_idx}_{probe.probe_id}",
                session_id=session_id,
                run_periodic_maintenance=False,
            ) or {})
            last_turn_text = turn_text
            last_response_text = _extract_delivered_response_text(response, turn_text, aurora_gateway)
            _word_sources, motif_summaries = pop_word_sources_and_motifs()
            for m in motif_summaries:
                all_motif_role_seqs.append(tuple(m["role_sequence"]))

        anchor = build_relevance_anchor_set(last_turn_text, [], web)
        adq = adequacy_score(last_response_text, anchor)
        wfc = wellformed_and_coherent(last_response_text)
        is_abstain = last_response_text.strip() in _ABSTAIN_TEXTS
        leaked = bool(_TELEMETRY_TOKEN_RE.search(last_response_text))

        words = _WORD_RE.findall(last_response_text.lower())
        total_content_words += len(words)
        clear_real_count += sum(1 for w in words if w in ("clear", "real"))
        if is_abstain:
            abstain_count += 1
        if leaked:
            leaked_count += 1

        records.append({
            "probe_id": probe.probe_id,
            "dimension": probe.dimension,
            "response_text": last_response_text,
            "adequacy": adq,
            "wellformed_coherent": wfc,
            "is_abstain": is_abstain,
            "leaked_diagnostic": leaked,
        })
    disable_capture()

    distinct_motifs = len(set(all_motif_role_seqs))
    return {
        "records": records,
        "adequacy_by_stratum": _stratum_mean(records, "adequacy"),
        "wellformed_rate_by_stratum": _stratum_rate(records, "wellformed_coherent"),
        "distinct_motif_shapes": distinct_motifs,
        "motif_role_seqs": [list(s) for s in set(all_motif_role_seqs)],
        "motif_turns_captured": len(all_motif_role_seqs),
        "descriptor_repetition_share": (clear_real_count / total_content_words) if total_content_words else None,
        "abstain_rate": abstain_count / len(probes),
        "diagnostic_leakage_count": leaked_count,
    }


def main():
    scratch_root = tempfile.mkdtemp(prefix="aurora_pf1_6_acceptance_")
    scratch_state_dir = str(Path(scratch_root) / "aurora_state")
    try:
        shutil.copytree(str(STATE_DIR), scratch_state_dir)
        systems = boot_aurora(state_dir=scratch_state_dir, verbose=False, runtime_profile="surface")
        aurora_gateway = systems.get("aurora")
        perception = systems.get("perception")
        oets = getattr(perception, "oets", None)
        web = getattr(oets, "web", None) if oets is not None else None

        probes = load_probes(PROBES_PATH)

        passes = []
        for run_idx in range(1, 4):
            passes.append(_run_one_pass(systems, aurora_gateway, web, probes, run_idx))

        simple_vals = [p["adequacy_by_stratum"]["simple_concrete"] for p in passes
                       if p["adequacy_by_stratum"]["simple_concrete"] is not None]
        abstract_vals = [p["adequacy_by_stratum"]["abstract_conceptual"] for p in passes
                          if p["adequacy_by_stratum"]["abstract_conceptual"] is not None]
        distinct_across_runs = len({
            tuple(seq) for p in passes for seq in p["motif_role_seqs"]
        })

        summary = {
            "runs": [
                {
                    "adequacy_by_stratum": p["adequacy_by_stratum"],
                    "wellformed_rate_by_stratum": p["wellformed_rate_by_stratum"],
                    "distinct_motif_shapes": p["distinct_motif_shapes"],
                    "motif_turns_captured": p["motif_turns_captured"],
                    "descriptor_repetition_share": p["descriptor_repetition_share"],
                    "abstain_rate": p["abstain_rate"],
                    "diagnostic_leakage_count": p["diagnostic_leakage_count"],
                }
                for p in passes
            ],
            "mean_simple_concrete_adequacy": sum(simple_vals) / len(simple_vals) if simple_vals else None,
            "mean_abstract_conceptual_adequacy": sum(abstract_vals) / len(abstract_vals) if abstract_vals else None,
            "distinct_motif_shapes_across_all_runs": distinct_across_runs,
        }

        print(json.dumps(summary, indent=2))

        out_dir = REPO_ROOT / "aurora_state" / "probe_battery" / "results"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"pf1_6_acceptance_{int(time.time())}.json"
        with open(out_path, "w") as f:
            json.dump({"summary": summary, "passes": passes}, f, indent=2)
        print(f"\n[REPORT] wrote {out_path}")

    finally:
        shutil.rmtree(scratch_root, ignore_errors=True)


if __name__ == "__main__":
    main()
