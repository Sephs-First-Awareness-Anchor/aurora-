#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Replay the historical experiential baseline through the resolution ledger.

This is a measurement harness, not part of Aurora's cognition.  It feeds the
archive's events through AuroraResolutionLedger exactly as the historical
environment does (chronology and size only, no text content) and reports, per
subject, which axis paths (length 2 = the 25 transitions, 3 = the 125 triples, 4 =
the 625 channel-through-channel slots) a subject must be seen through.

The shuffle modes are NEGATIVE CONTROLS.  A finding that survives shuffling is
an artifact of the marginal distributions, not of experience:

  none            real order
  within_episode  events permuted inside each episode (sequence destroyed,
                  each event keeps its own size and gap)
  episode_order   whole episodes permuted (within-episode order intact,
                  cross-episode order destroyed)
  global          every event permuted

Usage:
  python3 scripts/resolution_ledger_replay.py \\
      --events aurora_state/historical_experience/baseline_v1/events.jsonl.gz \\
      --episodes aurora_state/historical_experience/baseline_v1/episodes.jsonl \\
      --shuffle none --shuffle within_episode --shuffle global
"""
import argparse
import gzip
import json
import random
import sys
import tempfile
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aurora_internal.aurora_resolution_ledger import AuroraResolutionLedger, role_subject  # noqa: E402


def _safe_float(value):
    try:
        out = float(value)
    except Exception:
        return None
    return out if out == out and out not in (float("inf"), float("-inf")) else None


def _actor_label(actor):
    """Same mapping as HistoricalExperienceEnvironment._actor_label."""
    raw = str(actor or "").strip().lower()
    if raw == "user":
        return "historical_user"
    if raw in {"historical_other_assistant", "assistant"}:
        return "historical_other_assistant"
    return f"historical_{raw or 'unknown_participant'}"


def _open(path):
    path = str(path)
    return gzip.open(path, "rt", encoding="utf-8") if path.endswith(".gz") else open(path, encoding="utf-8")


def load_events(path, limit=None):
    events = []
    with _open(path) as fh:
        for line in fh:
            if not line.strip():
                continue
            events.append(json.loads(line))
            if limit and len(events) >= limit:
                break
    return events


def load_episodes(path):
    out = {}
    if path and Path(path).exists():
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    row = json.loads(line)
                    out[str(row.get("episode_id", ""))] = row
    return out


def shuffled(events, mode, seed):
    rng = random.Random(seed)
    events = list(events)
    if mode == "none":
        return events
    if mode == "global":
        rng.shuffle(events)
        return events
    episodes = OrderedDict()
    for ev in events:
        episodes.setdefault(str(ev.get("episode_id", "")), []).append(ev)
    groups = list(episodes.values())
    if mode == "within_episode":
        for group in groups:
            rng.shuffle(group)
    elif mode == "episode_order":
        rng.shuffle(groups)
    else:
        raise ValueError(f"unknown shuffle mode: {mode}")
    return [ev for group in groups for ev in group]


class _Warp:
    def __init__(self):
        self.demands = []

    def submit(self, demand):
        self.demands.append(demand)


def replay(events, episodes, max_path=4):
    ledger = AuroraResolutionLedger(state_dir=tempfile.mkdtemp(), persist=False, max_path=max_path)
    warp = _Warp()
    for index, ev in enumerate(events):
        episode = episodes.get(str(ev.get("episode_id", "")), {})
        ledger.observe_event(
            event_index=index,
            event_id=str(ev.get("event_id", "") or ""),
            episode_id=str(ev.get("episode_id", "") or ""),
            actor=role_subject(_actor_label(ev.get("actor", ""))),
            text_length=len(str(ev.get("text", "") or "")),
            elapsed_seconds=_safe_float(ev.get("delta_seconds_from_previous_turn")),
            episode_gap_seconds=_safe_float(episode.get("previous_episode_gap_seconds")),
            warp_field=warp,
        )
    return ledger, warp


def report(label, ledger, warp):
    status = ledger.status()
    print(f"\n=== {label} ===  events observed: {status['events_observed_through_index']}  "
          f"WARP demands: {len(warp.demands)}")
    for subject in status["subjects"]:
        print(f"  subject {subject}  (active path length {status['active_path_length'][subject]}, "
              f"{status['observations'][subject]} observations)")
        print(f"    deepest path that earned its keep, by target root: {status['natural_resolution'][subject]}")
        found = ledger.discovered(subject)
        for rec in found[:8]:
            print(f"    {rec['path']:<8s} {rec['resolution']:<13s} +{rec['diff_bits']:.4f} bits over "
                  f"{'null' if rec['baseline'] is None else rec['baseline']}  z={rec['z']:.1f}")
        if not found:
            print("    nothing earned its keep")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--events", required=True)
    parser.add_argument("--episodes", default="")
    parser.add_argument("--shuffle", action="append", choices=["none", "within_episode", "episode_order", "global"])
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--max-path", type=int, default=4, help="deepest axis-path length to evaluate (4 = the 625 slots)")
    args = parser.parse_args(argv)

    events = load_events(args.events, args.limit or None)
    episodes = load_episodes(args.episodes)
    print(f"loaded {len(events)} events, {len(episodes)} episode records")
    results = {}
    for mode in (args.shuffle or ["none", "within_episode", "global"]):
        ledger, warp = replay(shuffled(events, mode, args.seed), episodes, args.max_path)
        report(f"shuffle={mode}", ledger, warp)
        results[mode] = {
            (subject, rec["path"]): rec
            for subject in ledger.status()["subjects"] for rec in ledger.discovered(subject)
        }
    # Only shuffles that destroy WITHIN-episode sequence are negative controls for
    # sequential structure.  episode_order keeps each episode intact, so it is
    # informational only.
    controls = [m for m in ("within_episode", "global") if m in results]
    if "none" in results and controls:
        control_keys = set().union(*(set(results[m]) for m in controls))
        specific = {k: v for k, v in results["none"].items() if k not in control_keys}
        survivors = {k: v for k, v in results["none"].items() if k in control_keys}
        print("\n=== real order vs negative controls (" + ", ".join(controls) + ") ===")
        print(f"  discovered in real order: {len(results['none'])}")
        print(f"  also found under a control (positional or marginal by construction): {len(survivors)}")
        print(f"  experience-specific (absent from every control): {len(specific)}")
        for (subject, path), rec in sorted(specific.items(), key=lambda kv: -kv[1]["diff_bits"])[:20]:
            print(f"    {subject:<28s} {path:<9s} {rec['resolution']:<13s} +{rec['diff_bits']:.4f} bits  z={rec['z']:.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
