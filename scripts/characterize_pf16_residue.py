#!/usr/bin/env python3
"""
PF1.6 residue characterization -- one boot, one 60-probe pass, full anatomy
of every response failing the PF1.5 instruments (adequacy floor or
wellformed_and_coherent), so motif-mining and repair work aims at real
failure modes instead of guesses.

Captures per probe: delivered text, adequacy, coherence verdict, motif id +
role sequence used, per-word sources (attribution), frame source
(thought/claim/anchor/none), stratum.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
import json, shutil, sys, tempfile, time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aurora import boot_aurora, process_external_user_turn  # noqa: E402
from aurora_constraint_emission import build_relevance_anchor_set  # noqa: E402
from aurora_internal.aurora_semantic_probe_battery import (  # noqa: E402
    load_probes, PROMPT_STRATA,
)
from aurora_internal.aurora_pf1_5_instruments import (  # noqa: E402
    adequacy_score, wellformed_and_coherent,
)
from aurora_internal.aurora_attribution_trace import (  # noqa: E402
    enable_capture, disable_capture, pop_word_sources_and_motifs,
)
from run_probe_battery import _extract_delivered_response_text  # noqa: E402

STATE_DIR = REPO_ROOT / "aurora_state"
OUT = REPO_ROOT / "aurora_state" / "probe_battery" / "results" / "pf16_residue_characterization.json"

def _run(args, systems):
    t0 = time.time()
    probes = load_probes()
    aurora_gateway = systems.get("aurora")
    records = []
    enable_capture()
    for i, probe in enumerate(probes):
        text = probe.turns[-1] if probe.turns else ""
        for warm in probe.turns[:-1]:
            try:
                process_external_user_turn(systems, warm, session_id=f"residue_{i}")
            except Exception:
                pass
        try:
            result = dict(process_external_user_turn(
                systems, text, session_id=f"residue_{i}",
                run_periodic_maintenance=False) or {})
            delivered = _extract_delivered_response_text(result, text, aurora_gateway)
        except Exception as e:  # noqa: BLE001
            delivered = f"<TURN-ERROR {type(e).__name__}: {e}>"
        _ws, _mt = pop_word_sources_and_motifs()
        anchors = build_relevance_anchor_set(text, None, getattr(getattr(systems.get('perception'), 'oets', None), 'web', None))
        adequacy = None
        coherent = None
        try:
            adequacy = adequacy_score(delivered, anchors)
        except Exception as e:  # noqa: BLE001
            adequacy = f"<ERR {e}>"
        try:
            coherent = wellformed_and_coherent(delivered)
        except Exception as e:  # noqa: BLE001
            coherent = f"<ERR {e}>"
        frame = systems.get("_proposition_frame")
        records.append({
            "i": i, "probe_id": probe.probe_id,
            "dimension": probe.dimension,
            "stratum": PROMPT_STRATA.get(probe.dimension),
            "input": text,
            "delivered": delivered,
            "adequacy": adequacy,
            "coherent": coherent,
            "motifs": _mt,
            "word_sources": _ws,
            "frame_source": getattr(frame, "source", None) if frame else None,
        })
        if (i + 1) % 10 == 0:
            print(f"[probe] {i+1}/{len(probes)} elapsed {time.time()-t0:.0f}s", flush=True)
    disable_capture()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"generated": time.time(), "profile": args.profile, "records": records}, indent=1))
    fails = [r for r in records
             if (isinstance(r["coherent"], bool) and not r["coherent"])
             or (isinstance(r["adequacy"], (int, float)) and r["adequacy"] < 0.55)]
    print(f"[done] {len(records)} probes, {len(fails)} failing residue, wrote {out_path}", flush=True)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="surface", choices=["surface", "subsurface", "full"])
    parser.add_argument("--out", default=str(OUT))
    parser.add_argument("--no-scratch", action="store_true",
                        help="Boot against the real aurora_state/ instead of a scratch copy "
                             "(NOT recommended -- pollutes live state with probe-battery turns).")
    args = parser.parse_args()

    t0 = time.time()
    print(f"[boot] starting (profile={args.profile})...", flush=True)
    scratch_root = None
    scratch_state_dir = None
    try:
        if not args.no_scratch:
            scratch_root = tempfile.mkdtemp(prefix="aurora_pf16_residue_")
            scratch_state_dir = str(Path(scratch_root) / "aurora_state")
            shutil.copytree(str(STATE_DIR), scratch_state_dir)
        systems = boot_aurora(state_dir=scratch_state_dir, verbose=False, runtime_profile=args.profile)
        print(f"[boot] done in {time.time()-t0:.1f}s", flush=True)
        _run(args, systems)
    finally:
        if scratch_root is not None:
            shutil.rmtree(scratch_root, ignore_errors=True)


if __name__ == "__main__":
    main()
