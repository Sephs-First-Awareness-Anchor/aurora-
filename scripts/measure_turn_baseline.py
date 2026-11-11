#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
measure_turn_baseline.py -- a reproducible per-turn baseline (Unified
Directive, Part XV section 43).

Boots Aurora against a COPY of aurora_state (her real state is never touched),
runs a fixed sequence of live turns through process_external_user_turn with
the same arguments her phone uses, and records for each turn:

  * wall time and her actual reply (so a later comparison can check that an
    optimisation changed the cost and not what she said);
  * a call profile: which functions ran, how many times, and at what cost.

The profile is what makes "repeated computation" a measured claim: a function
called hundreds of times inside one turn is evidence to investigate, not a
conclusion.  This script changes nothing in her; it only watches.

Usage:
  python scripts/measure_turn_baseline.py --out baseline.json
  python scripts/measure_turn_baseline.py --out after.json --compare baseline.json
"""
from __future__ import annotations

import argparse
import cProfile
import io
import json
import os
import pstats
import resource
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# A fixed conversation: greeting, a question, something told to her, a
# follow-up that depends on it, a correction, and a return to an earlier
# topic.  Fixed so two runs are comparable; it is input, never expected output.
DEFAULT_TURNS = [
    "Hey Aurora, how are you today?",
    "What have you been thinking about?",
    "I spent the morning fixing the fence behind the house.",
    "It took longer than I expected because the posts were rotten.",
    "No, I meant the wooden posts, not the wire.",
    "What do you remember about what I was working on?",
]


def _rss_mb() -> float:
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1)


def _reply_text(result: Dict[str, Any]) -> str:
    for key in ("resp_B", "resp_A"):
        content = getattr(result.get(key), "content", None)
        if content:
            return str(content)
    return str(result.get("response") or result.get("text") or "")


def _top(stats: pstats.Stats, limit: int) -> Dict[str, List[Dict[str, Any]]]:
    rows = []
    for (filename, line, name), (cc, nc, tt, ct, _callers) in stats.stats.items():  # type: ignore[attr-defined]
        short = os.path.relpath(filename, ROOT) if filename.startswith(str(ROOT)) else os.path.basename(filename)
        rows.append({"fn": f"{short}:{line}:{name}", "calls": int(nc),
                     "self_s": round(tt, 4), "cum_s": round(ct, 4)})
    ours = [r for r in rows if not r["fn"].startswith(("~", "<"))]
    return {
        "by_self_time": sorted(ours, key=lambda r: -r["self_s"])[:limit],
        "by_calls": sorted(ours, key=lambda r: -r["calls"])[:limit],
        "by_cum_time": sorted(ours, key=lambda r: -r["cum_s"])[:limit],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--compare", default="")
    parser.add_argument("--state-dir", default=str(ROOT / "aurora_state"))
    parser.add_argument("--top", type=int, default=40)
    parser.add_argument("--callers", default="",
                        help="comma list of function-name patterns to print callers for")
    parser.add_argument("--no-profile", action="store_true",
                        help="wall times only (profiling itself slows a turn)")
    args = parser.parse_args()

    os.environ.setdefault("AURORA_SKIP_DEP_INSTALL", "1")
    workdir = Path(tempfile.mkdtemp(prefix="aurora_baseline_"))
    state_copy = workdir / "aurora_state"
    shutil.copytree(args.state_dir, state_copy)

    import aurora as aurora_mod

    started = time.time()
    real_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        systems = aurora_mod.boot_aurora(state_dir=str(state_copy), verbose=False)
    finally:
        sys.stdout = real_stdout
    boot_s = round(time.time() - started, 2)

    profiler = cProfile.Profile()
    turns = []
    for index, text in enumerate(DEFAULT_TURNS):
        sys.stdout = io.StringIO()
        t0 = time.time()
        try:
            # Turn 1 pays one-time cold-start costs (index builds, lazy
            # imports).  It is timed, but kept out of the call profile so the
            # profile shows what EVERY turn costs.
            if not args.no_profile and index > 0:
                profiler.enable()
            result = aurora_mod.process_external_user_turn(
                systems, text, source_label="flutter_ui", session_id="baseline",
                auto_search_enabled=False, record_exchange=True,
                update_interactive_state=True, track_evolutionary_trace=True,
                run_periodic_maintenance=True, mode_name="BOUNDED")
        finally:
            profiler.disable()
            sys.stdout = real_stdout
        turns.append({"n": index + 1, "said": text, "reply": _reply_text(result),
                      "src": str(getattr(result.get("resp_B") or result.get("resp_A"), "src", "") or ""),
                      "wall_s": round(time.time() - t0, 3)})
        print(f"turn {index + 1}: {turns[-1]['wall_s']}s  {turns[-1]['reply'][:110]!r}", flush=True)

    report: Dict[str, Any] = {
        "commit": os.popen(f"git -C {ROOT} rev-parse --short HEAD").read().strip(),
        "python": sys.version.split()[0], "profiled": not args.no_profile,
        "boot_s": boot_s, "peak_rss_mb": _rss_mb(),
        "total_turn_s": round(sum(t["wall_s"] for t in turns), 3),
        "turns": turns,
    }
    if not args.no_profile:
        stats = pstats.Stats(profiler)
        report["total_calls"] = int(stats.total_calls)  # type: ignore[attr-defined]
        report["profile_covers"] = "turns 2..N (turn 1 is cold start)"
        report["profile"] = _top(stats, args.top)
        if args.callers:
            buffer = io.StringIO()
            stats.stream = buffer  # type: ignore[attr-defined]
            for pattern in args.callers.split(","):
                stats.sort_stats("cumulative").print_callers(pattern.strip(), 12)
            report["callers"] = buffer.getvalue()
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"boot {boot_s}s · turns {report['total_turn_s']}s · peak {report['peak_rss_mb']} MB"
          + (f" · {report['total_calls']:,} calls" if "total_calls" in report else ""))

    if args.compare:
        before = json.loads(Path(args.compare).read_text(encoding="utf-8"))
        same = [a["reply"] == b["reply"] for a, b in zip(before["turns"], turns)]
        print(f"vs {args.compare}: turns {before['total_turn_s']}s -> {report['total_turn_s']}s"
              + (f" · calls {before.get('total_calls', 0):,} -> {report.get('total_calls', 0):,}"
                 if "total_calls" in report else "")
              + f" · replies identical: {sum(same)}/{len(same)}")
    shutil.rmtree(workdir, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
