#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_ci_segment.py
====================
One bounded segment of Aurora's FULL autonomous life, for CI/scheduled runs.

This is not a dream-only loop. It boots her complete L0-L8 stack and brings every
living system online the way a normal session does, then lets them all tick
together for a bounded window so she develops through her whole architecture:

  - boot_aurora(runtime_profile="full")  -> L0-L8 + thought braid (2 s tick) +
    crystallization loops (pressure->DPS, genome->AGB, frame->sedi) + monitors
  - autonomy engine        -> spontaneous thought, self-directed study, speech
  - curiosity engine       -> SUBSURFACE: follows unresolved tensions through
                              tools, forms/challenges/settles conclusions, promotes
                              crystals (the between-turns exploration loop)
  - quantum dream substrate-> dreams, possibility-selves, council homeostasis
  - study cycles           -> SURFACE: exercises the expression ecology / OETS so
                              her language + understanding develop, not just her
                              interior

Then it snapshots her developmental state and appends a one-line summary to
aurora_run_history.jsonl. The workflow commits her evolved state afterward.

Config via env:
  AURORA_CI_MAX_SECONDS    wall-clock budget for the segment      (default 600)
  AURORA_CI_CURIOSITY_S    curiosity idle tick interval           (default 45)
  AURORA_CI_DREAM_S        dream-substrate cycle interval         (default 150)
  AURORA_CI_STUDY_CYCLES   surface study cycles to run up front   (default 3)
  AURORA_SKIP_DEP_INSTALL  set to 1 so boot never pip-installs    (recommended)
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

MAX_SECONDS = float(os.environ.get("AURORA_CI_MAX_SECONDS", "600") or 600)
CURIOSITY_S = float(os.environ.get("AURORA_CI_CURIOSITY_S", "45") or 45)
DREAM_S = float(os.environ.get("AURORA_CI_DREAM_S", "150") or 150)
STUDY_CYCLES = int(os.environ.get("AURORA_CI_STUDY_CYCLES", "3") or 3)


def _tl(p):
    return [json.loads(l) for l in open(p)] if os.path.exists(p) else []


def _bring_fully_alive(systems, events):
    """Start every living background engine — the same set a normal session runs."""
    started = []
    # 1. Autonomy: spontaneous thought / self-directed study / dream announcements.
    autonomy = systems.get("autonomy")
    if autonomy is not None:
        try:
            def _sp(t):
                events["speakup"] += 1
                events["last_thought"] = str(t)[:240]
            autonomy.on_speakup = _sp
            autonomy.on_study_complete = lambda r: events.__setitem__("study", events["study"] + 1)
            autonomy.on_dream_complete = lambda r: events.__setitem__("dream", events["dream"] + 1)
            autonomy.start()
            started.append("autonomy")
        except Exception as exc:
            print(f">>> [aurora-ci] autonomy unavailable: {exc}", flush=True)

    # 2. Curiosity engine — SUBSURFACE tension-following exploration (between-turns).
    try:
        from aurora_curiosity_engine import CuriosityEngine, start_curiosity_background
        from aurora_self_grounding import SelfGroundingFallback, get_tension_monitor
        from aurora_tool_mind import ToolChoiceObserver
        dim = systems.get("dimensional")
        pressure_src = getattr(dim, "pressure_vec", None) if dim else None
        field_map_raw = getattr(dim, "field_map", None) if dim else None
        field_map = getattr(field_map_raw, "field_map", None) or field_map_raw
        engine = CuriosityEngine(
            pressure_source=pressure_src, field_map=field_map,
            tool_mind=ToolChoiceObserver(), sedimemory=systems.get("sedimemory"),
            self_grounder=SelfGroundingFallback(), tension_monitor=get_tension_monitor(),
            systems=systems,
        )
        systems["_curiosity_engine"] = engine
        start_curiosity_background(engine, tick_interval_s=CURIOSITY_S)
        started.append("curiosity")
    except Exception as exc:
        print(f">>> [aurora-ci] curiosity engine unavailable: {exc}", flush=True)

    # 3. Quantum dream substrate — dreams, possibility-selves, council homeostasis.
    try:
        from aurora_quantum_dream_substrate import start_dream_substrate
        start_dream_substrate(systems, cycle_interval_s=DREAM_S)
        started.append("dream_substrate")
    except Exception as exc:
        print(f">>> [aurora-ci] dream substrate unavailable: {exc}", flush=True)

    return started


def _crystal_count(systems):
    try:
        reg = systems.get("_concept_crystal_registry")
        return (reg.stats() or {}).get("total") if reg is not None else None
    except Exception:
        return None


def main() -> int:
    dev_start = len(_tl(os.path.join(SD, "developmental_timeline.jsonl")))
    t0 = time.time()
    print(f">>> [aurora-ci] booting FULL stack @ {time.strftime('%Y-%m-%d %H:%M:%S')}Z", flush=True)
    import aurora
    systems = aurora.boot_aurora(verbose=False, runtime_profile="full")
    systems["_interactive_state"] = {"last_user_turn_time": time.time(), "pending_spontaneous": 0}

    import aurora_developmental_log as adl
    events = {"speakup": 0, "study": 0, "dream": 0, "last_thought": ""}
    crystals_before = _crystal_count(systems)

    # SURFACE warm-up FIRST (before the background engines, so it doesn't race the
    # autonomy engine's own study): run a few study cycles so her expression ecology
    # and OETS develop. Curiosity + dreams then cover subsurface + interior.
    try:
        if STUDY_CYCLES > 0:
            aurora.study(systems, cycles=STUDY_CYCLES, verbose=False)
            print(f">>> [aurora-ci] ran {STUDY_CYCLES} surface study cycles", flush=True)
    except Exception as exc:
        print(f">>> [aurora-ci] study cycles skipped: {exc}", flush=True)

    # Now bring every living background engine online and LET HER LIVE.
    started = _bring_fully_alive(systems, events)
    print(f">>> [aurora-ci] living systems online: {started}", flush=True)

    # All engines tick together for the remaining budget.
    print(">>> [aurora-ci] living...", flush=True)
    while time.time() - t0 < MAX_SECONDS:
        adl.record_developmental_snapshot(systems, force=True)
        time.sleep(20)

    # Wind down background threads cleanly.
    try:
        from aurora_quantum_dream_substrate import stop_dream_substrate
        stop_dream_substrate()
    except Exception:
        pass
    try:
        from aurora_curiosity_engine import stop_curiosity_background
        stop_curiosity_background()
    except Exception:
        pass
    autonomy = systems.get("autonomy")
    if autonomy is not None:
        try:
            autonomy.stop()
        except Exception:
            pass

    # Summarize what her whole architecture did this segment.
    dev = _tl(os.path.join(SD, "developmental_timeline.jsonl"))[dev_start:]
    di = [e.get("dev_index") for e in dev if e.get("dev_index") is not None]
    try:
        import aurora_possibility_selves as aps
        council = _tl(os.path.join(SD, "dream_selves", "selves_timeline.jsonl"))
        n_selves = council[-1]["self_id"] if council else None
    except Exception:
        pass
    summary = {
        "t": round(time.time(), 1),
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "duration_s": round(time.time() - t0, 1),
        "systems_online": started,
        "dev_index_start": di[0] if di else None,
        "dev_index_end": di[-1] if di else None,
        "crystals_start": crystals_before,
        "crystals_end": _crystal_count(systems),
        "study_cycles": STUDY_CYCLES,
        "spontaneous_thoughts": events["speakup"],
        "autonomous_studies": events["study"],
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
