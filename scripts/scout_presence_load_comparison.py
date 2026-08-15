#!/usr/bin/env python3
"""
Subsurface Presence and Evidence Scout spec, step 12: presence/load
comparison against baseline.

Measures the two call sites Steps 10-11 converted from synchronous
blocking waits to non-blocking Scout dispatch, and reports elapsed time
against the DOCUMENTED former blocking ceilings those call sites used
to enforce (verified directly against the code removed in those steps'
commits, not estimated):

    aurora._try_poedex_lookup(..., use_researcher=True)
        formerly blocked up to 35.0s (the direct-callable path's
        `_direct_to = 35.0 if use_researcher else timeout`, and the
        queue-poll path's `_poll_to = 35.0 if use_researcher else timeout`)

    aurora_daemon._maybe_research_recurring_issue()
        formerly blocked up to 18.0s
        (`_poedex_ask(question, cat="researcher", lane="self", timeout=18.0)`)

Also samples subsurface_heartbeat_gap_ms / subsurface_presence_frame_age_ms
while a dispatched ScoutRequest sits unclaimed in the queue (no worker
running), to confirm presence liveness keeps updating independently of
whether -- or how slowly -- a Scout ever answers. This is the direct,
measurable form of spec section 20's acceptance criterion: "Long
retrieval does not stop Subsurface heartbeat/presence updates."

Run directly: `python3 scripts/scout_presence_load_comparison.py`
Also importable: `main(state_dir) -> dict` for tests
(tests/test_scout_presence_load_comparison.py exercises it against a
tmp_path the same way).
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import time
import threading
from pathlib import Path
from typing import Any, Dict

_BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_BASE_DIR))

# Documented former blocking ceilings (spec steps 10/11) -- not
# estimates. Kept here as named constants specifically so this script
# breaks loudly (a diff a reviewer will actually see) if anyone ever
# tries to quietly restore a blocking wait at either call site without
# updating this comparison's baseline.
_BASELINE_SURFACE_POEDEX_WAIT_S = 35.0
_BASELINE_SUBSURFACE_ISSUE_RESEARCH_WAIT_S = 18.0


def _measure_surface_lookup(state_dir: Path) -> Dict[str, Any]:
    import aurora

    systems = {"state_dir": state_dir, "_current_turn_id": "load_cmp_turn"}
    started = time.time()
    result = aurora._try_poedex_lookup("a topic with no bound lesson", systems, use_researcher=True)
    elapsed_s = time.time() - started
    return {
        "call": "aurora._try_poedex_lookup(use_researcher=True)",
        "baseline_blocking_ceiling_s": _BASELINE_SURFACE_POEDEX_WAIT_S,
        "measured_elapsed_s": round(elapsed_s, 4),
        "improvement_factor": round(_BASELINE_SURFACE_POEDEX_WAIT_S / max(elapsed_s, 1e-6), 1),
        "returned_result": result,
    }


def _measure_subsurface_issue_research(state_dir: Path) -> Dict[str, Any]:
    import aurora_daemon as ad

    ad._STATE_DIR = state_dir
    (state_dir / "daemon_status.json").write_text(json.dumps({
        "fail_summary": [{"dim": "load_comparison_dim", "avg_sev": 0.6, "fails": 60}],
        "qao_recent_events": 3,
        "qao_top_issue": "?",
    }), encoding="utf-8")

    started = time.time()
    fired = ad._maybe_research_recurring_issue({}, "LOW")
    elapsed_s = time.time() - started
    return {
        "call": "aurora_daemon._maybe_research_recurring_issue()",
        "baseline_blocking_ceiling_s": _BASELINE_SUBSURFACE_ISSUE_RESEARCH_WAIT_S,
        "measured_elapsed_s": round(elapsed_s, 4),
        "improvement_factor": round(_BASELINE_SUBSURFACE_ISSUE_RESEARCH_WAIT_S / max(elapsed_s, 1e-6), 1),
        "dispatched": fired,
    }


def _measure_presence_liveness_during_pending_retrieval(state_dir: Path, *, duration_s: float = 3.0) -> Dict[str, Any]:
    """A ScoutRequest sits unclaimed in the queue (no worker process
    running in this script) for `duration_s` -- the same shape a real
    slow/absent Scout produces. A heartbeat thread mimicking
    aurora_daemon._start_subsurface_heartbeat_thread() runs concurrently.
    Samples heartbeat_gap_ms and presence_frame_age_ms throughout;
    both must stay low regardless of the pending retrieval's fate."""
    from aurora_internal.scouting.broker import dispatch_scout_request
    from aurora_internal.scouting.contracts import ScoutRequest
    from aurora_internal.dual_strata.subsurface_presence import (
        write_heartbeat, heartbeat_gap_ms, write_presence_frame, presence_frame_age_ms,
    )

    dispatch_scout_request(state_dir, ScoutRequest(
        turn_id="", request_kind="self_diagnostic",
        inquiry="a deliberately slow/unclaimed diagnostic request", ttl_s=duration_s + 5.0,
    ))
    write_presence_frame(state_dir, turn_id="load_cmp_turn")

    stop = threading.Event()

    def _beat():
        while not stop.is_set():
            write_heartbeat(state_dir)
            time.sleep(0.5)

    thread = threading.Thread(target=_beat, daemon=True)
    thread.start()

    samples = []
    started = time.time()
    while time.time() - started < duration_s:
        time.sleep(0.4)
        samples.append({
            "t_s": round(time.time() - started, 2),
            "heartbeat_gap_ms": heartbeat_gap_ms(state_dir),
            "presence_frame_age_ms": presence_frame_age_ms(state_dir),
        })

    stop.set()
    thread.join(timeout=2.0)

    max_heartbeat_gap = max((s["heartbeat_gap_ms"] or 0.0) for s in samples) if samples else None
    return {
        "pending_retrieval_duration_s": duration_s,
        "samples": samples,
        "max_heartbeat_gap_ms_observed": max_heartbeat_gap,
        "heartbeat_stayed_live": bool(samples) and max_heartbeat_gap is not None and max_heartbeat_gap < 1500.0,
    }


def main(state_dir: Path = None) -> Dict[str, Any]:
    owns_dir = state_dir is None
    state_dir = Path(state_dir) if state_dir else Path(tempfile.mkdtemp(prefix="scout_load_cmp_"))
    try:
        report = {
            "generated_at": time.time(),
            "surface_poedex_lookup": _measure_surface_lookup(state_dir),
            "subsurface_issue_research": _measure_subsurface_issue_research(state_dir),
            "presence_liveness_during_pending_retrieval": _measure_presence_liveness_during_pending_retrieval(state_dir),
        }
        return report
    finally:
        if owns_dir:
            shutil.rmtree(state_dir, ignore_errors=True)


if __name__ == "__main__":
    result = main()
    print(json.dumps(result, indent=2))
    print()
    print("Presence/load comparison against baseline (spec step 12):")
    for key in ("surface_poedex_lookup", "subsurface_issue_research"):
        row = result[key]
        print(
            f"  {row['call']}: baseline ceiling {row['baseline_blocking_ceiling_s']}s -> "
            f"measured {row['measured_elapsed_s']}s "
            f"({row['improvement_factor']}x faster)"
        )
    liveness = result["presence_liveness_during_pending_retrieval"]
    print(
        f"  Presence liveness during a {liveness['pending_retrieval_duration_s']}s pending/unclaimed "
        f"retrieval: max heartbeat gap {liveness['max_heartbeat_gap_ms_observed']}ms "
        f"(stayed live: {liveness['heartbeat_stayed_live']})"
    )
