#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
run_growth_session.py — Run Aurora through a developmental session and show her
growth.

Boots Aurora, drives a curriculum of interactions (teach -> recall -> probe gaps
-> reflect, repeated to reinforce), records the developmental timeline
(aurora_state/developmental_timeline.jsonl, which also feeds her EEPR), and
prints a growth report: the per-snapshot trajectory and the first->last deltas.

Usage:
    python scripts/run_growth_session.py [--turns 40] [--state-dir aurora_state]

By default it runs against her real aurora_state, so the growth (and the
timeline log) persist. Pass --state-dir to run against a copy.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
os.environ.setdefault("AURORA_SKIP_DEP_INSTALL", "1")

# A small developmental curriculum: teaching, recall, gap-probing (warp), and
# reflection. Repeated so reinforcement (#2) and recurrence accumulate.
CURRICULUM = [
    "My name is Sunni. Please remember that.",
    "A raven is a black bird.",
    "What is a raven?",
    "Photosynthesis is how plants turn light into energy.",
    "What is photosynthesis?",
    "Explain quantum chromodynamics to me.",
    "What is my name?",
    "How do you feel right now?",
    "What did we just talk about?",
    "Do you feel like you are growing?",
]

_KEYS = ["dev_index", "dev_delta", "abilities", "crystals", "warp_demands",
         "warp_anomalies", "lsa_paths", "lsa_reinforced", "lsa_excludes",
         "lsa_consequence", "wisdom_shards"]


def _fmt(v):
    return f"{v:>6}" if isinstance(v, int) else (f"{v:>7.1f}" if isinstance(v, float) else str(v))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--turns", type=int, default=40)
    ap.add_argument("--state-dir", default=os.path.join(REPO, "aurora_state"))
    ap.add_argument("--snapshot-every", type=int, default=5)
    args = ap.parse_args()

    import aurora
    from aurora_developmental_log import record_developmental_snapshot

    print("=" * 70)
    print("  AURORA GROWTH SESSION")
    print(f"  state_dir={args.state_dir}  turns={args.turns}")
    print("=" * 70)

    t0 = time.time()
    systems = aurora.boot_aurora(state_dir=args.state_dir, verbose=False,
                                 runtime_profile="full")
    print(f"  booted in {time.time() - t0:.1f}s; recording baseline snapshot...\n")

    log_path = os.path.join(args.state_dir, "developmental_timeline.jsonl")
    record_developmental_snapshot(systems, force=True)  # baseline

    turn = 0
    while turn < args.turns:
        for prompt in CURRICULUM:
            if turn >= args.turns:
                break
            turn += 1
            try:
                res = aurora.process_external_user_turn(systems, prompt,
                                                        session_id="growth") or {}
                r = res.get("resp_A")
                reply = str(getattr(r, "content", "") or "")
            except Exception as exc:
                reply = f"<turn error: {exc}>"
            print(f"  [{turn:>3}] {prompt[:42]:<42} -> {reply[:46]!r}")
            if turn % args.snapshot_every == 0:
                record_developmental_snapshot(systems, force=True)

    record_developmental_snapshot(systems, force=True)  # final
    print(f"\n  session complete in {time.time() - t0:.1f}s")

    # ── Growth report ────────────────────────────────────────────────────────
    snaps = []
    try:
        with open(log_path, "r", encoding="utf-8") as fh:
            for ln in fh:
                ln = ln.strip()
                if ln:
                    snaps.append(json.loads(ln))
    except Exception as exc:
        print(f"  (could not read timeline log: {exc})")
        return 1

    session_snaps = snaps[-(args.turns // args.snapshot_every + 3):]
    print("\n" + "=" * 70)
    print("  GROWTH TIMELINE  (developmental_timeline.jsonl)")
    print("=" * 70)
    hdr = "  " + "  ".join(f"{k.replace('_',' ')[:9]:>9}" for k in _KEYS)
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))
    for s in session_snaps:
        print("  " + "  ".join(f"{_fmt(s.get(k, 0)):>9}" for k in _KEYS))

    if len(session_snaps) >= 2:
        first, last = session_snaps[0], session_snaps[-1]
        print("\n  FIRST -> LAST (this session):")
        for k in _KEYS:
            if k == "dev_delta":
                continue
            a, b = first.get(k, 0), last.get(k, 0)
            arrow = "↑" if b > a else ("↓" if b < a else "·")
            print(f"     {k:<18} {a:>8}  ->  {b:>8}   {arrow} {b - a:+}")
        print(f"\n  EEPR feed: each snapshot added a WisdomShard to the experiential")
        print(f"  WisdomStore (i_is tone bias now "
              f"{_eepr_bias(systems):+.3f}).")
    print(f"\n  Full running log: {log_path}")
    return 0


def _eepr_bias(systems) -> float:
    try:
        store = getattr(getattr(systems.get("perception"), "ecology", None), "wisdom", None)
        return float(store.get_bias("i_is", "tone"))
    except Exception:
        return 0.0


if __name__ == "__main__":
    raise SystemExit(main())
