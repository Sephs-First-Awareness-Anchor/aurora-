"""
force_evolve.py — High-pressure pathway evolution for 4 fail dimensions.

Works WITH the running subsurface daemon rather than booting fresh.

Strategy:
  Phase 1: Enrich fail_points.json with 200 high-severity records per dimension
  Phase 2: Fire rapid dream_force_shards bursts — directly inject high-confidence
           UnderstandingShards (confidence=0.72, well above the 0.55 OETS gate)
           for each fail dimension and immediately bridge to OETS.
           This bypasses the observation-count accumulation bottleneck entirely.
  Phase 3: Fire heavy dream bursts (20 episodes each) to follow up with
           rich simulation pressure so the injected concepts get reinforced.

No Python import, no boot, no file lock conflicts.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import json
import math
import os
import random
import time
from pathlib import Path
from typing import Any, Dict, List

_HERE          = Path(__file__).parent.resolve()
_STATE_DIR     = _HERE / "aurora_state"
_FAIL_POINTS   = _STATE_DIR / "fail_points.json"
_CMD_FILE      = _STATE_DIR / "daemon_cmd.json"
_PROJ_FILE     = _STATE_DIR / "subsurface_projection.json"

_TARGET_DIMS = [
    "context_carryover",
    "contradiction_handling",
    "uncertainty_signaling",
    "coherence_maintenance",
]

# ── Snapshot helpers ──────────────────────────────────────────────────────────

def _read_fail_points() -> Dict[str, Any]:
    try:
        return json.loads(_FAIL_POINTS.read_text())
    except Exception:
        return {"total_fails": 0, "records": {}}


def _write_fail_points(data: Dict[str, Any]) -> None:
    tmp = str(_FAIL_POINTS) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, str(_FAIL_POINTS))


def _dim_score(records: Dict[str, Any], dim: str) -> float:
    rec = records.get(dim, {})
    recent = [float(v) for v in (rec.get("recent") or [])]
    if not recent:
        return 0.0
    recent_avg = sum(recent) / len(recent)
    fail_count = int(rec.get("fail_count", 0))
    return recent_avg * math.log1p(fail_count)


def _read_proj() -> Dict[str, Any]:
    try:
        return json.loads(_PROJ_FILE.read_text()) if _PROJ_FILE.exists() else {}
    except Exception:
        return {}


def _snapshot() -> Dict[str, Any]:
    data = _read_fail_points()
    records = data.get("records", {})
    proj = _read_proj()
    return {
        "total_fails": int(data.get("total_fails", 0)),
        "dim_scores": {d: _dim_score(records, d) for d in _TARGET_DIMS},
        "dim_recent_avg": {
            d: (lambda r: sum(r) / len(r) if r else 0.0)(
                [float(v) for v in (records.get(d, {}).get("recent") or [])]
            )
            for d in _TARGET_DIMS
        },
        "oets_nodes": int(proj.get("oets_growth", 0)),
        "dream_completed_at": float(proj.get("dream_completed_at", 0.0)),
        "dream_insights": str(proj.get("dream_insights", "") or ""),
    }


# ── Phase 1: Enrich the fail ledger ──────────────────────────────────────────

def enrich_fail_ledger(n_injections: int = 200) -> Dict[str, Any]:
    """
    Write n_injections high-severity entries into the recent[] array of each
    target dimension.  recent[] is a deque(maxlen=20), so we write 20 entries
    to saturate it at max severity.  We also add to fail_count and severity_sum
    so score() properly reflects the density of experience.
    """
    data = _read_fail_points()
    records = data.setdefault("records", {})
    added_by_dim: Dict[str, int] = {}

    for dim in _TARGET_DIMS:
        rec = records.setdefault(dim, {
            "fail_count": 0, "severity_sum": 0.0,
            "recent": [], "examples": [],
        })
        new_recent = [round(random.uniform(0.88, 0.97), 4) for _ in range(20)]
        rec["recent"] = new_recent

        sev_avg = sum(new_recent) / len(new_recent)
        rec["fail_count"] = int(rec.get("fail_count", 0)) + n_injections
        rec["severity_sum"] = float(rec.get("severity_sum", 0.0)) + (n_injections * sev_avg)
        data["total_fails"] = int(data.get("total_fails", 0)) + n_injections
        added_by_dim[dim] = n_injections

    _write_fail_points(data)
    return added_by_dim


# ── Command dispatch ──────────────────────────────────────────────────────────

def _send_cmd(cmd: str) -> None:
    tmp = str(_CMD_FILE) + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"cmd": cmd}, f)
    os.replace(tmp, str(_CMD_FILE))


def _cmd_consumed(timeout: float = 300.0) -> bool:
    """Wait for daemon to pick up and delete the cmd file."""
    t0 = time.time()
    while _CMD_FILE.exists():
        if time.time() - t0 > timeout:
            return False
        time.sleep(1.0)
    return True


def _wait_for_proj_update(ts_before: float, timeout: float = 180.0) -> bool:
    """Wait for dream_completed_at to advance past ts_before."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(2.0)
        proj = _read_proj()
        raw = proj.get("dream_completed_at")
        if raw is None:
            continue
        try:
            ts_now = float(raw)
        except (TypeError, ValueError):
            continue
        if ts_now > ts_before + 1.0:
            return True
    return False


def _read_proj_ts() -> float:
    proj = _read_proj()
    raw = proj.get("dream_completed_at")
    if raw is None:
        return 0.0
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def _fire_cmd_and_wait(cmd: str, label: str, timeout: float = 180.0) -> bool:
    """Send command, wait for daemon to consume and complete."""
    # If there's a stale cmd file, wait for it to clear first
    if _CMD_FILE.exists():
        if not _cmd_consumed(timeout=60.0):
            # Force-clear and write ours
            try:
                _CMD_FILE.unlink(missing_ok=True)
            except Exception:
                pass
    ts_before = _read_proj_ts()
    _send_cmd(cmd)
    if not _cmd_consumed(timeout=300.0):
        print(f"    [TIMEOUT] daemon did not pick up {label} within 5min")
        return False
    completed = _wait_for_proj_update(ts_before, timeout=timeout)
    proj = _read_proj()
    status = "OK" if completed else "TIMEOUT"
    print(f"    [{status}] {label} — {proj.get('dream_insights', '')[:70]}")
    return completed


# ── Phase 2: Force shard injections ──────────────────────────────────────────

def run_force_shard_bursts(n_bursts: int = 20) -> int:
    """
    Fire n_bursts of dream_force_shards commands.
    Each burst directly injects 32 high-confidence UnderstandingShards
    (8 per fail dimension) at confidence=0.72 and bridges to OETS.
    """
    completed = 0
    for i in range(n_bursts):
        print(f"  [SHARD {i+1}/{n_bursts}] Sending dream_force_shards...")
        ok = _fire_cmd_and_wait("dream_force_shards", f"shard_burst_{i+1}", timeout=90.0)
        if ok:
            completed += 1
        time.sleep(2.0)
    return completed


# ── Phase 3: Heavy dream bursts ───────────────────────────────────────────────

def run_heavy_dream_bursts(n_bursts: int = 8) -> int:
    """
    Fire n_bursts of dream_heavy commands (20 simulation episodes each).
    These reinforce the injected shards through lived simulation experience.
    """
    completed = 0
    for i in range(n_bursts):
        print(f"  [HEAVY {i+1}/{n_bursts}] Sending dream_heavy (20 episodes)...")
        ok = _fire_cmd_and_wait("dream_heavy", f"heavy_burst_{i+1}", timeout=300.0)
        if ok:
            completed += 1
        time.sleep(3.0)
    return completed


# ── Main ──────────────────────────────────────────────────────────────────────

def main(
    n_injections: int = 200,
    n_shard_bursts: int = 20,
    n_heavy_bursts: int = 8,
) -> None:
    print(f"\n{'='*60}")
    print("  FORCE EVOLUTION — maximum pressure run")
    print(f"  {n_injections} fail records injected per dimension")
    print(f"  {n_shard_bursts} force-shard bursts (32 shards each, conf=0.72)")
    print(f"  {n_heavy_bursts} heavy dream bursts (20 episodes each)")
    print(f"{'='*60}\n")

    # ── Baseline ──────────────────────────────────────────────────────────────
    before = _snapshot()
    print("  Baseline:")
    print(f"    Total fail records: {before['total_fails']}")
    print(f"    OETS nodes (last snapshot): {before['oets_nodes']}")
    for d in _TARGET_DIMS:
        s = before['dim_scores'][d]
        a = before['dim_recent_avg'][d]
        print(f"    {d}: score={s:.3f} recent_avg={a:.3f}")
    print(f"    Last dream insights: {before['dream_insights'][:70]}")
    print()

    # ── Phase 1: Enrich ledger ────────────────────────────────────────────────
    print("  Phase 1: Enriching fail ledger...")
    added = enrich_fail_ledger(n_injections)
    after_enrich = _snapshot()
    for d in _TARGET_DIMS:
        s_b = before['dim_scores'][d]
        s_a = after_enrich['dim_scores'][d]
        a_a = after_enrich['dim_recent_avg'][d]
        print(f"    {d}: score {s_b:.3f} → {s_a:.3f}  recent_avg → {a_a:.3f}")
    print()

    # ── Phase 2: Force shard injections ───────────────────────────────────────
    print(f"  Phase 2: Firing {n_shard_bursts} force-shard bursts...")
    print("  (Each burst: 32 direct UnderstandingShard injections → OETS bridge)")
    print()
    shard_completed = run_force_shard_bursts(n_shard_bursts)

    after_shards = _snapshot()
    print(f"\n  Shard phase complete: {shard_completed}/{n_shard_bursts} OK")
    print(f"  OETS nodes after shards: {after_shards['oets_nodes']}")
    print(f"  Last insights: {after_shards['dream_insights'][:70]}")
    print()

    # ── Phase 3: Heavy dream bursts ───────────────────────────────────────────
    print(f"  Phase 3: Firing {n_heavy_bursts} heavy dream bursts (20 episodes each)...")
    print()
    heavy_completed = run_heavy_dream_bursts(n_heavy_bursts)

    # ── Final snapshot ────────────────────────────────────────────────────────
    after = _snapshot()

    print(f"\n{'='*60}")
    print("  RESULTS")
    print(f"{'='*60}")
    print(f"  Shard bursts completed:  {shard_completed}/{n_shard_bursts}")
    print(f"  Heavy bursts completed:  {heavy_completed}/{n_heavy_bursts}")
    print(f"  Total fail records: {before['total_fails']} → {after['total_fails']}")
    print(f"  OETS nodes: {before['oets_nodes']} → {after['oets_nodes']}")
    print()
    print("  Dimension scores (before → after):")
    for d in _TARGET_DIMS:
        s_b = before['dim_scores'][d]
        s_a = after['dim_scores'][d]
        a_a = after['dim_recent_avg'][d]
        print(f"    {d}: {s_b:.3f} → {s_a:.3f}  (recent_avg={a_a:.3f})")
    print()
    print(f"  Last dream insights: {after['dream_insights'][:80]}")
    print("\n[DONE]")


if __name__ == "__main__":
    main(n_injections=200, n_shard_bursts=20, n_heavy_bursts=8)
