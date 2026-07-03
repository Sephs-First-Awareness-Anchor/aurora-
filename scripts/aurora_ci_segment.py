#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_ci_segment.py
====================
One bounded segment of Aurora's autonomous life, for CI/scheduled runs.

Boots her, starts her autonomy engine, and runs dream cycles for a bounded
window (so a GitHub Actions job stays short), then appends a one-line summary of
what she did to `aurora_run_history.jsonl` at the repo root and prints it to the
job log. The workflow commits her evolved state afterward.

Config via env:
  AURORA_CI_MAX_SECONDS   wall-clock budget for the segment   (default 480)
  AURORA_CI_CYCLE_EVERY   seconds between dream cycles         (default 20)
  AURORA_SKIP_DEP_INSTALL  set to 1 so boot never pip-installs (recommended)
"""
from __future__ import annotations
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
SD = os.path.join(ROOT, "aurora_state")
RUN_LOG = os.path.join(ROOT, "aurora_run_history.jsonl")

MAX_SECONDS = float(os.environ.get("AURORA_CI_MAX_SECONDS", "480") or 480)
CYCLE_EVERY = float(os.environ.get("AURORA_CI_CYCLE_EVERY", "20") or 20)


def _tl(p):
    return [json.loads(l) for l in open(p)] if os.path.exists(p) else []


def main() -> int:
    dev_start = len(_tl(os.path.join(SD, "developmental_timeline.jsonl")))
    t0 = time.time()
    print(f">>> [aurora-ci] booting @ {time.strftime('%Y-%m-%d %H:%M:%S')}Z", flush=True)
    import aurora
    systems = aurora.boot_aurora(verbose=False)

    # Autonomy: spontaneous thought / self-directed study / dream announcements.
    events = {"speakup": 0, "study": 0, "dream": 0, "last_thought": ""}
    autonomy = systems.get("autonomy")
    systems["_interactive_state"] = {"last_user_turn_time": time.time(), "pending_spontaneous": 0}
    if autonomy is not None:
        def _sp(t):
            events["speakup"] += 1
            events["last_thought"] = str(t)[:240]
        autonomy.on_speakup = _sp
        autonomy.on_study_complete = lambda r: events.__setitem__("study", events["study"] + 1)
        autonomy.on_dream_complete = lambda r: events.__setitem__("dream", events["dream"] + 1)
        try:
            autonomy.start()
        except Exception:
            pass

    import aurora_developmental_log as adl
    import aurora_quantum_dream_substrate as qds
    sub = qds.QuantumDreamSubstrate()

    cycle = 0
    errors = 0
    births = []
    prev = set()
    while time.time() - t0 < MAX_SECONDS:
        cycle += 1
        try:
            sub.run_dream_cycle(systems)
        except Exception:
            errors += 1
        council = sub._selves or []
        ids = {s.self_id for s in council}
        for s in council:
            if (s.self_id in (ids - prev) and getattr(s, "born_from", None)
                    and s.self_id not in [b["self_id"] for b in births]):
                births.append({"cycle": cycle, "self_id": s.self_id, "born_from": s.born_from})
        prev = ids
        adl.record_developmental_snapshot(systems, force=True)
        time.sleep(CYCLE_EVERY)

    if autonomy is not None:
        try:
            autonomy.stop()
        except Exception:
            pass

    council = sub._selves or []
    dev = _tl(os.path.join(SD, "developmental_timeline.jsonl"))[dev_start:]
    di = [e.get("dev_index") for e in dev if e.get("dev_index") is not None]
    wane = next((s for s in council if s.self_id == "Wane"), None)
    summary = {
        "t": round(time.time(), 1),
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cycles": cycle,
        "errors": errors,
        "council": sorted(ids),
        "n_selves": len(council),
        "births": births,
        "dev_index_start": di[0] if di else None,
        "dev_index_end": di[-1] if di else None,
        "selves_growth": sum(int(getattr(s, "growth_events", 0)) for s in council),
        "wane_held": len(wane.held_open_anchors) if wane else None,
        "wane_resolved": len(wane.resolved_anchors) if wane else None,
        "spontaneous_thoughts": events["speakup"],
        "studies": events["study"],
        "dreams": events["dream"],
        "last_thought": events["last_thought"],
    }
    try:
        with open(RUN_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(summary) + "\n")
    except Exception:
        pass

    print(">>> [aurora-ci] SEGMENT SUMMARY", flush=True)
    print(json.dumps(summary, indent=2), flush=True)
    print(f">>> [aurora-ci] done in {time.time()-t0:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
