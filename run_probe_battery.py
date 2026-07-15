#!/usr/bin/env python3
"""
Run Aurora's held-out semantic probe battery against the live local stack.

Phase R0.2 of the Semantic Plateau Remediation Directive (2026-07-15):
"No further classroom lessons are scored by dev_index. Competence = probe
score." This is the runner for that instrument. It boots the same live
stack as run_full_competency_gauntlet.py, drives every probe in
aurora_state/probe_battery/probes.json through the canonical
process_external_user_turn() response path (never a shortcut path), scores
each resulting transcript with the existing ConversationRubricEngine (no
parallel scorer), and writes a timestamped report to
aurora_state/probe_battery/results/.

A blocked probe is reported blocked, never silently passed -- modality-honest
reporting, matching run_full_competency_gauntlet.py's own doctrine.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Dict

from aurora import boot_aurora, process_external_user_turn
from aurora_developmental_log import record_developmental_snapshot
from aurora_internal.aurora_semantic_probe_battery import (
    PROBES_PATH,
    RESULTS_DIR,
    Probe,
    load_probes,
    run_battery,
)

REPO_ROOT = Path(__file__).resolve().parent
STATE_DIR = REPO_ROOT / "aurora_state"
RESULTS_DIR_PATH = Path(RESULTS_DIR)


def _json_safe(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except Exception:
        if isinstance(value, dict):
            return {str(k): _json_safe(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [_json_safe(v) for v in value]
        return str(value)


def _make_process_turn_fn_factory(systems: Dict[str, Any]):
    aurora_gateway = systems.get("aurora")

    def factory(probe: Probe):
        session_id = f"probe_battery_{probe.probe_id}"
        # aurora.py's recent-context injection reads systems["_session_turn_buffer"]
        # as one flat, unscoped list -- session_id alone does not isolate it. Clear
        # it before each probe starts so probe N can never see probe N-1's last
        # exchange (held-out scores must not depend on run order). A held-out
        # probe's OWN turns still see each other normally within the probe, since
        # the buffer accumulates turn-by-turn as this same probe's calls run.
        systems["_session_turn_buffer"] = []

        def _process(turn_text: str) -> Dict[str, Any]:
            response = dict(
                process_external_user_turn(
                    systems,
                    turn_text,
                    source_label=f"probe_battery_{probe.probe_id}",
                    session_id=session_id,
                    run_periodic_maintenance=False,
                ) or {}
            )
            response_text = str(response.get("response_text") or "").strip()
            # Same fallback run_full_competency_gauntlet.py uses -- the
            # canonical bridge sometimes returns no text depending on which
            # subsystems are live under a given runtime profile; falling
            # through to the gateway keeps this the SAME path the gauntlet
            # already relies on, not a shortcut invented for this script.
            if not response_text and aurora_gateway is not None and hasattr(aurora_gateway, "speak_to_aurora"):
                try:
                    gateway_response = aurora_gateway.speak_to_aurora(turn_text)
                    response_text = str(getattr(gateway_response, "content", "") or "").strip()
                    response["response_src"] = str(response.get("response_src") or "") or "gateway_fallback"
                except Exception as exc:
                    response["response_src"] = f"gateway_error:{exc.__class__.__name__}"
            response["response_text"] = response_text
            return response

        return _process

    return factory


def run_probe_battery(run_id: str = "", verbose: bool = True) -> Dict[str, Any]:
    if not run_id:
        run_id = f"run_{int(time.time())}"

    # Boot against a throwaway COPY of aurora_state, not the live directory.
    # process_external_user_turn's live-learning path (conversation memory,
    # dream-trainer fail ledger, recommendations) writes real side effects
    # into state_dir regardless of record_exchange/track_evolutionary_trace,
    # so a probe battery run against the real directory would feed held-out
    # probe content back into Aurora's training signal -- exactly the leak
    # is_seed_excluded() exists to prevent, just via a different door. The
    # copy starts as an exact snapshot of the real state so responses stay
    # representative of Aurora's actual current competence; every write
    # during the run lands in the scratch copy and is discarded after.
    scratch_root = tempfile.mkdtemp(prefix="aurora_probe_battery_")
    scratch_state_dir = str(Path(scratch_root) / "aurora_state")
    try:
        shutil.copytree(str(STATE_DIR), scratch_state_dir)

        systems = boot_aurora(state_dir=scratch_state_dir, verbose=verbose, runtime_profile="surface")

        try:
            pre_snapshot = record_developmental_snapshot(systems, force=True)
        except Exception as exc:
            pre_snapshot = {"status": "unavailable", "reason": str(exc)}

        try:
            probes = load_probes(PROBES_PATH)
            probe_count = len(probes)
        except Exception as exc:
            return {
                "run_id": run_id,
                "status": "blocked",
                "reason": f"could not load probe manifest: {exc}",
                "timestamp": time.time(),
            }

        report = run_battery(_make_process_turn_fn_factory(systems), run_id=run_id, probes_path=PROBES_PATH)

        try:
            post_snapshot = record_developmental_snapshot(systems, force=True)
        except Exception as exc:
            post_snapshot = {"status": "unavailable", "reason": str(exc)}

        result = report.to_dict()
        result.update({
            "status": "ok",
            "probe_count": probe_count,
            # dev_index is bracketed here for cross-reference only -- per the
            # directive, it is never the verdict. The probe score is.
            "dev_index_pre": (pre_snapshot or {}).get("dev_index"),
            "dev_index_post": (post_snapshot or {}).get("dev_index"),
        })
        return result
    finally:
        shutil.rmtree(scratch_root, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Aurora's held-out semantic probe battery.")
    parser.add_argument("--run-id", type=str, default="", help="Label for this run (default: run_<timestamp>).")
    parser.add_argument("--quiet", action="store_true", help="Reduce boot logging.")
    args = parser.parse_args()

    result = run_probe_battery(run_id=str(args.run_id or ""), verbose=not args.quiet)

    RESULTS_DIR_PATH.mkdir(parents=True, exist_ok=True)
    run_id = result.get("run_id") or f"run_{int(time.time())}"
    out_path = RESULTS_DIR_PATH / f"{run_id}.json"
    safe_result = _json_safe(result)
    out_path.write_text(json.dumps(safe_result, indent=2), encoding="utf-8")

    print(json.dumps(safe_result, indent=2))
    print(f"\n[REPORT] wrote {out_path}")
    if result.get("status") == "ok":
        print(f"[SUMMARY] overall_pass_rate={result.get('overall_pass_rate')}")
        for dim, summ in (result.get("per_dimension") or {}).items():
            print(f"  {dim}: {summ}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
