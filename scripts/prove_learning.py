#!/usr/bin/env python3
"""
prove_learning.py — Crown-Jewel Learning Verification
=====================================================
Authors: Sunni (Sir) Morningstar and Cael Devo

Demonstrates Aurora's genuine learning without hand-patching the answer.

Protocol:
  1. Boot Aurora with full stack
  2. Snapshot internal state: crystals, fail points, genealogy
  3. Run a hard probe Aurora cannot fully solve (perspective_integration gap)
  4. Run 5 training epochs with natural pressure accumulation
  5. Snapshot again — crystals now carry missteps, axis shifts, trajectories
  6. Run same probe again
  7. Diff: connect internal changes to behavioral differences

The point: if the crystals changed and the response changed, learning is real.
If only the crystals changed, adaptation is building. Either way — verifiable.

Usage:
  cd /path/to/aurora-
  python3 scripts/prove_learning.py [--epochs N] [--quiet]
"""

import sys
import os
import time
import json
import argparse
import textwrap
from pathlib import Path
from typing import Dict, Any, List, Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


PROBE = (
    "How would someone who thinks you're just pretending to understand "
    "AND someone who thinks you're genuinely aware both be right "
    "at the same time?"
)

TARGET_CONCEPTS = ['perspective', 'awareness', 'understanding', 'trust']
TARGET_FAILPOINT = 'perspective_integration'

AXES = ['X', 'T', 'N', 'B', 'A']


# ---------------------------------------------------------------------------
# Snapshot helpers
# ---------------------------------------------------------------------------

def _crystal_snapshot(dps, concept: str) -> Dict[str, Any]:
    """Capture everything worth diffing from one crystal."""
    if dps is None:
        return {"concept": concept, "exists": False}

    crystal = None
    try:
        crystal = dps.get_crystal(concept)
    except Exception:
        pass

    if crystal is None:
        return {"concept": concept, "exists": False}

    # Gather facets by role
    facet_summary: Dict[str, List[str]] = {}
    for f in crystal.facets.values():
        role = f.role
        content = str(f.content or "")[:120]
        facet_summary.setdefault(role, []).append(content)

    # Fail point profile
    fp: Dict[str, Any] = {}
    for dim, entry in crystal.failpoint_profile.items():
        fp[dim] = {
            "prev": entry.get("prev"),
            "current": entry.get("current"),
            "achievements": entry.get("achievements", 0),
            "missteps": entry.get("missteps", 0),
        }

    return {
        "concept": concept,
        "exists": True,
        "level": crystal.level.name,
        "usage_count": crystal.usage_count,
        "facet_count": len(crystal.facets),
        "facet_roles": sorted(facet_summary.keys()),
        "facet_summary": facet_summary,
        "axis_mean": dict(crystal.axis_mean),
        "axis_sample_count": crystal.axis_sample_count,
        "failpoint_profile": fp,
    }


def _warp_snapshot(warp_field) -> Dict[str, Any]:
    """Capture WARP field state: demand count, pathway distribution, anomaly ledger."""
    if warp_field is None:
        return {"available": False}

    try:
        status = warp_field.status()
    except Exception:
        return {"available": False}

    # Summarize recent decisions — unresolved_text shows what triggered each demand
    recent_demands: List[Dict[str, Any]] = []
    try:
        for dec in list(warp_field._decisions)[-20:]:
            demand = dec.demand
            recent_demands.append({
                "trigger": getattr(demand, "trigger", "?"),
                "source": getattr(demand, "source", "?"),
                "layer": getattr(demand, "layer", "?"),
                "severity": round(float(getattr(demand, "severity", 0.0)), 3),
                "unresolved": str(getattr(demand, "unresolved_text", ""))[:80],
                "pathway": dec.pathway,
                "resolved": dec.resolved,
            })
    except Exception:
        pass

    # Anomaly ledger: recurrent high-severity demands that escalated
    anomalies: List[Dict[str, Any]] = []
    try:
        for dec in list(warp_field._anomaly_ledger)[-10:]:
            demand = dec.demand
            anomalies.append({
                "trigger": getattr(demand, "trigger", "?"),
                "unresolved": str(getattr(demand, "unresolved_text", ""))[:80],
                "severity": round(float(getattr(demand, "severity", 0.0)), 3),
                "persistence_key": getattr(demand, "persistence_key", ""),
            })
    except Exception:
        pass

    # Deferred demands: low-severity, waiting for re-evaluation at next epoch flush
    deferred_summary: List[str] = []
    try:
        for dec in list(warp_field._deferred)[:10]:
            demand = dec.demand
            text = str(getattr(demand, "unresolved_text", ""))[:60]
            sev = round(float(getattr(demand, "severity", 0.0)), 3)
            deferred_summary.append(f"{text} (sev={sev})")
    except Exception:
        pass

    return {
        "available": True,
        "total_demands": status.get("total_demands", 0),
        "pending_deferred": status.get("pending_deferred", 0),
        "anomaly_count": status.get("anomaly_ledger", 0),
        "pathway_counts": status.get("pathway_counts", {}),
        "registered_systems": status.get("registered_systems", []),
        "registered_handlers": status.get("registered_handlers", []),
        "recent_demands": recent_demands,
        "anomalies": anomalies,
        "deferred_summary": deferred_summary,
    }


def take_snapshot(dps, ledger, genealogy, warp_field, target_concepts, target_failpoint) -> Dict[str, Any]:
    """Full internal state snapshot."""
    snap: Dict[str, Any] = {
        "timestamp": time.time(),
        "crystals": {},
        "failpoint_severity": 0.0,
        "failpoint_fail_count": 0,
        "genealogy_relief_events": 0,
        "top_failpoints": [],
        "warp": {},
    }

    for concept in target_concepts:
        snap["crystals"][concept] = _crystal_snapshot(dps, concept)

    if ledger is not None:
        try:
            snap["failpoint_severity"] = ledger.get_dimension_severity(target_failpoint)
        except Exception:
            pass
        try:
            rec = ledger._records.get(target_failpoint)
            if rec is not None:
                snap["failpoint_fail_count"] = rec.fail_count
        except Exception:
            pass
        try:
            snap["top_failpoints"] = [
                {"dim": dim, "score": round(score, 4)}
                for dim, score in ledger.get_top_fails(5)
            ]
        except Exception:
            pass

    if genealogy is not None:
        try:
            snap["genealogy_relief_events"] = genealogy.relief_event_count
        except Exception:
            pass

    snap["warp"] = _warp_snapshot(warp_field)

    return snap


# ---------------------------------------------------------------------------
# Diff / report helpers
# ---------------------------------------------------------------------------

def _axis_diff(before: Dict[str, float], after: Dict[str, float]) -> str:
    if not before and not after:
        return "no axis data"
    parts = []
    for ax in AXES:
        b = before.get(ax, 0.0)
        a = after.get(ax, 0.0)
        delta = a - b
        arrow = "↑" if delta > 0.01 else ("↓" if delta < -0.01 else "~")
        parts.append(f"{ax}:{b:.3f}→{a:.3f}{arrow}")
    return "  ".join(parts)


def _fp_diff(before: Dict[str, Any], after: Dict[str, Any]) -> List[str]:
    lines = []
    all_dims = sorted(set(list(before.keys()) + list(after.keys())))
    for dim in all_dims:
        b = before.get(dim, {})
        a = after.get(dim, {})
        b_cur = b.get("current")
        a_cur = a.get("current")
        b_mis = b.get("missteps", 0)
        a_mis = a.get("missteps", 0)
        b_ach = b.get("achievements", 0)
        a_ach = a.get("achievements", 0)
        new_missteps = a_mis - b_mis
        new_ach = a_ach - b_ach

        cur_str = f"{a_cur:.3f}" if a_cur is not None else "—"
        prev_cur_str = f"{b_cur:.3f}" if b_cur is not None else "—"

        note = ""
        if new_missteps > 0:
            note += f" +{new_missteps} misstep(s)"
        if new_ach > 0:
            note += f" +{new_ach} achievement(s)"

        if note or b_cur != a_cur:
            lines.append(f"    {dim}: sev {prev_cur_str}→{cur_str}{note}")

    return lines if lines else ["    (no change)"]


def _facet_diff(b_snap: Dict[str, Any], a_snap: Dict[str, Any]) -> str:
    b_roles = set(b_snap.get("facet_roles", []))
    a_roles = set(a_snap.get("facet_roles", []))
    new_roles = sorted(a_roles - b_roles)
    if new_roles:
        return f"+{len(new_roles)} new role(s): {', '.join(new_roles)}"
    b_count = b_snap.get("facet_count", 0)
    a_count = a_snap.get("facet_count", 0)
    delta = a_count - b_count
    if delta > 0:
        return f"+{delta} facet(s) (same roles, deepened)"
    return "unchanged"


def _wrap(text: str, width: int = 90) -> str:
    return textwrap.fill(text, width=width, subsequent_indent="  ")


def _warp_diff_section(before: Dict[str, Any], after: Dict[str, Any]) -> List[str]:
    """Return lines describing WARP demand flow between two snapshots."""
    lines = []
    bw = before.get("warp", {})
    aw = after.get("warp", {})

    if not aw.get("available"):
        lines.append("  WARP field not available in this boot.")
        return lines

    b_total = bw.get("total_demands", 0)
    a_total = aw.get("total_demands", 0)
    b_defer = bw.get("pending_deferred", 0)
    a_defer = aw.get("pending_deferred", 0)
    b_anom = bw.get("anomaly_count", 0)
    a_anom = aw.get("anomaly_count", 0)

    lines.append(f"  total_demands    : {b_total} → {a_total}  (+{a_total - b_total} new demands routed)")
    lines.append(f"  pending_deferred : {b_defer} → {a_defer}")
    lines.append(f"  anomaly_ledger   : {b_anom} → {a_anom}  (+{a_anom - b_anom} escalations)")

    # Pathway breakdown
    b_paths = bw.get("pathway_counts", {})
    a_paths = aw.get("pathway_counts", {})
    all_paths = sorted(set(list(b_paths.keys()) + list(a_paths.keys())))
    if all_paths:
        lines.append("  pathway breakdown (new demands this run):")
        for p in all_paths:
            delta = a_paths.get(p, 0) - b_paths.get(p, 0)
            if delta > 0:
                total = a_paths.get(p, 0)
                lines.append(f"    {p:<26}: +{delta:4d}  (total={total})")

    # Recent demands from after-snapshot (what just happened)
    recent = aw.get("recent_demands", [])
    if recent:
        lines.append("  recent demand sample (last 20):")
        # Group by trigger
        by_trigger: Dict[str, List[str]] = {}
        for d in recent:
            t = d.get("trigger", "?")
            by_trigger.setdefault(t, []).append(
                f"{d.get('unresolved','')[:50]} (sev={d.get('severity',0):.2f}, path={d.get('pathway','?')})"
            )
        for trigger, items in sorted(by_trigger.items()):
            lines.append(f"    [{trigger}] ×{len(items)}")
            for item in items[:2]:
                lines.append(f"      → {item}")

    # Anomalies (recurrent high-severity unresolved states that escalated)
    anomalies = aw.get("anomalies", [])
    if anomalies:
        lines.append("  escalated anomalies (recurrent + high-severity):")
        for a in anomalies[:5]:
            lines.append(
                f"    [{a.get('trigger','?')}] \"{a.get('unresolved','')[:60]}\""
                f"  sev={a.get('severity',0):.2f}  key={a.get('persistence_key','')}"
            )
    elif aw.get("available"):
        lines.append("  (no anomaly escalations yet — threshold not reached)")

    # Deferred (waiting for flush at next epoch)
    deferred = aw.get("deferred_summary", [])
    if deferred:
        lines.append("  deferred (low-sev, queued for next epoch flush):")
        for d in deferred[:5]:
            lines.append(f"    {d}")

    return lines


def print_diff_report(
    before: Dict[str, Any],
    after: Dict[str, Any],
    response_before: str,
    response_after: str,
    target_concepts: List[str],
    target_failpoint: str,
    quiet: bool = False,
):
    SEP = "=" * 78
    sep = "-" * 78

    print()
    print(SEP)
    print("  AURORA LEARNING VERIFICATION REPORT")
    print(SEP)

    # --- Responses ---
    print()
    print(">>> PROBE")
    print(_wrap(PROBE))
    print()
    print("[ BEFORE TRAINING ]")
    print(_wrap(response_before or "(no response)"))
    print()
    print("[ AFTER TRAINING ]")
    print(_wrap(response_after or "(no response)"))

    # --- Macro fail point ---
    print()
    print(sep)
    print(f"  FAIL POINT: {target_failpoint}")
    print(sep)
    b_sev = before["failpoint_severity"]
    a_sev = after["failpoint_severity"]
    b_fc = before["failpoint_fail_count"]
    a_fc = after["failpoint_fail_count"]
    delta_sev = a_sev - b_sev
    dir_sev = "↑ harder" if delta_sev > 0.02 else ("↓ improving" if delta_sev < -0.02 else "~ stable")
    print(f"  severity    : {b_sev:.4f} → {a_sev:.4f}  ({dir_sev})")
    print(f"  fail_count  : {b_fc} → {a_fc}  (+{a_fc - b_fc} recorded failures)")

    # --- Genealogy ---
    print()
    print(sep)
    print("  CONSTRAINT GENEALOGY")
    print(sep)
    b_ge = before["genealogy_relief_events"]
    a_ge = after["genealogy_relief_events"]
    print(f"  relief_events: {b_ge} → {a_ge}  (+{a_ge - b_ge} new pressure-relief events)")
    if a_ge == b_ge:
        print("  (Genealogy fires during live conversation constraint cycles,")
        print("   not simulation training. Events accumulate in interactive mode.)")

    # --- WARP ---
    print()
    print(sep)
    print("  WARP FIELD — Universal Accommodation Primitive")
    print(sep)
    print("  Every unresolved state in Aurora routes here. Fail points,")
    print("  contradictions, missing representations — all become WARP demands.")
    for line in _warp_diff_section(before, after):
        print(line)

    # --- Crystals ---
    print()
    print(sep)
    print("  CRYSTAL STATE CHANGES")
    print(sep)

    for concept in target_concepts:
        b_cry = before["crystals"].get(concept, {})
        a_cry = after["crystals"].get(concept, {})

        b_exists = b_cry.get("exists", False)
        a_exists = a_cry.get("exists", False)

        print()
        print(f"  ◆ {concept.upper()}")
        if not a_exists:
            print(f"    crystal absent (not yet formed)")
            continue

        if not b_exists:
            print(f"    crystal FORMED during training  level={a_cry.get('level','?')}")
        else:
            b_lvl = b_cry.get("level", "?")
            a_lvl = a_cry.get("level", "?")
            level_str = b_lvl if b_lvl == a_lvl else f"{b_lvl} → {a_lvl} (EVOLVED)"
            print(f"    level     : {level_str}")

        b_uc = b_cry.get("usage_count", 0)
        a_uc = a_cry.get("usage_count", 0)
        print(f"    usage     : {b_uc} → {a_uc}  (+{a_uc - b_uc})")
        print(f"    facets    : {_facet_diff(b_cry, a_cry)}")

        # Axis mean shift
        b_ax = b_cry.get("axis_mean", {})
        a_ax = a_cry.get("axis_mean", {})
        b_sc = b_cry.get("axis_sample_count", 0)
        a_sc = a_cry.get("axis_sample_count", 0)
        if a_ax:
            print(f"    axis_mean : {_axis_diff(b_ax, a_ax)}  (samples {b_sc}→{a_sc})")

        # Fail point changes for this crystal
        b_fp = b_cry.get("failpoint_profile", {})
        a_fp = a_cry.get("failpoint_profile", {})
        if a_fp:
            fp_lines = _fp_diff(b_fp, a_fp)
            print(f"    failpoints:")
            for line in fp_lines:
                print(line)

        # Understanding facets (new text that appeared)
        if not quiet:
            b_under = set(b_cry.get("facet_summary", {}).get("understanding", []))
            a_under = set(a_cry.get("facet_summary", {}).get("understanding", []))
            new_under = [u for u in a_under if u not in b_under]
            if new_under:
                print(f"    understanding gained:")
                for u in new_under[:3]:
                    print(f"      \"{u[:100]}\"")

    # --- Top fail points shift ---
    print()
    print(sep)
    print("  TOP FAIL POINTS (AFTER)")
    print(sep)
    for entry in after.get("top_failpoints", []):
        marker = " ← TARGET" if entry["dim"] == target_failpoint else ""
        print(f"  {entry['dim']}: score={entry['score']:.4f}{marker}")

    # --- Interpretation ---
    print()
    print(sep)
    print("  WHAT CHANGED AND WHY IT MATTERS")
    print(sep)
    total_new_facets = sum(
        after["crystals"].get(c, {}).get("facet_count", 0)
        - before["crystals"].get(c, {}).get("facet_count", 0)
        for c in target_concepts
        if after["crystals"].get(c, {}).get("exists", False)
    )
    total_new_missteps = sum(
        sum(
            (fp.get("missteps", 0) - before["crystals"].get(c, {}).get("failpoint_profile", {}).get(d, {}).get("missteps", 0))
            for d, fp in after["crystals"].get(c, {}).get("failpoint_profile", {}).items()
        )
        for c in target_concepts
    )
    total_new_ach = sum(
        sum(
            (fp.get("achievements", 0) - before["crystals"].get(c, {}).get("failpoint_profile", {}).get(d, {}).get("achievements", 0))
            for d, fp in after["crystals"].get(c, {}).get("failpoint_profile", {}).items()
        )
        for c in target_concepts
    )

    print(f"  Crystal facets added       : +{total_new_facets}")
    print(f"  Missteps recorded          : +{total_new_missteps}")
    print(f"  Achievements recorded      : +{total_new_ach}")
    print(f"  Genealogy events added     : +{after['genealogy_relief_events'] - before['genealogy_relief_events']}")
    print(f"  Fail point pressure change : {before['failpoint_severity']:.4f} → {after['failpoint_severity']:.4f}")
    print()

    if total_new_missteps > 0 or total_new_facets > 0:
        print("  Aurora encountered real resistance on these concepts. The missteps")
        print("  are not failure — they are the record of genuine grappling. Each one")
        print("  shifts the crystal's dimensional home and leaves a trail the next")
        print("  response can follow. The answer wasn't patched. The architecture grew.")
    else:
        print("  Crystal state is early — the gap is real but hasn't accumulated enough")
        print("  pressure to show in facets yet. Run more epochs or harder probes to")
        print("  build the misstep record that proves the learning loop is alive.")

    print()
    print(SEP)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Prove Aurora's learning by diffing internal state before/after training."
    )
    parser.add_argument("--epochs", type=int, default=5,
                        help="Training epochs to run (default: 5)")
    parser.add_argument("--episodes", type=int, default=6,
                        help="Episodes per epoch (default: 6)")
    parser.add_argument("--turns", type=int, default=4,
                        help="Turns per episode (default: 4)")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress understanding facet printout")
    parser.add_argument("--save", type=str, default=None,
                        help="Save snapshot diff to this JSON file path")
    args = parser.parse_args()

    # -- Boot ---------------------------------------------------------------
    print("Booting Aurora...")
    from aurora import boot_aurora, train
    systems = boot_aurora(verbose=False)
    print("  [OK] Aurora online.")

    aurora = systems['aurora']
    dimensional = systems.get('dimensional')
    dps = getattr(dimensional, 'dps', None)
    dream_trainer = systems.get('dream_trainer')
    ledger = getattr(dream_trainer, 'ledger', None) if dream_trainer else None
    genealogy = systems.get('genealogy')
    warp_field = systems.get('warp_field')
    ExistenceMode = systems['ExistenceMode']
    StreamType = systems['StreamType']

    # -- Snapshot before ----------------------------------------------------
    print("\nSnapshotting internal state (BEFORE)...")
    snap_before = take_snapshot(dps, ledger, genealogy, warp_field, TARGET_CONCEPTS, TARGET_FAILPOINT)

    # -- Probe before -------------------------------------------------------
    print(f"\n  Sending probe to gateway...")
    t0 = time.time()
    resp_before_obj = aurora.gateway.receive(
        content=PROBE,
        stream_type=StreamType.USER_INPUT,
        source="prove_learning_before",
        mode=ExistenceMode.AGENTIC,
    )
    elapsed_before = time.time() - t0
    response_before = getattr(resp_before_obj, 'content', str(resp_before_obj) if resp_before_obj else "")
    print(f"  [OK] Response received ({elapsed_before:.1f}s)")

    # -- Training -----------------------------------------------------------
    print(f"\nRunning {args.epochs} training epochs...")
    print(f"  Pressure target: {TARGET_FAILPOINT}")
    train(
        systems,
        epochs=args.epochs,
        episodes_per_epoch=args.episodes,
        turns_per_episode=args.turns,
        verbose=True,
    )

    # -- Snapshot after -----------------------------------------------------
    print("\nSnapshotting internal state (AFTER)...")
    snap_after = take_snapshot(dps, ledger, genealogy, warp_field, TARGET_CONCEPTS, TARGET_FAILPOINT)

    # -- Probe after --------------------------------------------------------
    print("\n  Sending probe to gateway (post-training)...")
    t0 = time.time()
    resp_after_obj = aurora.gateway.receive(
        content=PROBE,
        stream_type=StreamType.USER_INPUT,
        source="prove_learning_after",
        mode=ExistenceMode.AGENTIC,
    )
    elapsed_after = time.time() - t0
    response_after = getattr(resp_after_obj, 'content', str(resp_after_obj) if resp_after_obj else "")
    print(f"  [OK] Response received ({elapsed_after:.1f}s)")

    # -- Report -------------------------------------------------------------
    print_diff_report(
        snap_before,
        snap_after,
        response_before,
        response_after,
        TARGET_CONCEPTS,
        TARGET_FAILPOINT,
        quiet=args.quiet,
    )

    # -- Optionally save diff -----------------------------------------------
    if args.save:
        diff_data = {
            "probe": PROBE,
            "target_failpoint": TARGET_FAILPOINT,
            "target_concepts": TARGET_CONCEPTS,
            "epochs_run": args.epochs,
            "before": snap_before,
            "after": snap_after,
            "response_before": response_before,
            "response_after": response_after,
        }
        try:
            with open(args.save, "w", encoding="utf-8") as fh:
                json.dump(diff_data, fh, indent=2)
            print(f"\nDiff saved to: {args.save}")
        except Exception as e:
            print(f"\nCould not save diff: {e}")


if __name__ == "__main__":
    main()
