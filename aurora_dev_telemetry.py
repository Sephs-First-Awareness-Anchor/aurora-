# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_dev_telemetry.py
========================
TEMPORARY diagnostic instrumentation for development acceleration analysis.

Measures the three bottleneck indicators every epoch:
  1. Axis drift  — are X/T/N/B/A values changing epoch over epoch?
  2. OETS compounding — internal seek hit rate vs external, node growth
  3. DPS crystallization — crystal count growth + constraint reasoner alignment

Remove this file once the bottleneck is identified and fixed.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

_AXES = ("X", "T", "N", "B", "A")


_IVM_LONG_NAMES = ("existence", "temporal", "energy", "boundary", "agency")


def _axis_snapshot(systems: Dict[str, Any]) -> Dict[str, float]:
    """Read current X/T/N/B/A from IVM lattice, normalized to [0,1].
    IVM uses long names (existence/temporal/...) — map to short (X/T/N/B/A)."""
    lattice = systems.get("lattice")
    if lattice is not None and hasattr(lattice, "get_global_polarity"):
        try:
            raw = lattice.get_global_polarity()
            return {
                ax: round(max(0.0, min(1.0, (float(raw.get(long, 0.0)) + 1.0) / 2.0)), 3)
                for ax, long in zip(_AXES, _IVM_LONG_NAMES)
            }
        except Exception:
            pass
    # Fallback: constraint reasoner current_profile()
    cr = systems.get("constraint_reasoner")
    if cr is not None:
        try:
            return cr.current_profile()
        except Exception:
            pass
    return {ax: 0.5 for ax in _AXES}


def _oets_node_count(systems: Dict[str, Any]) -> int:
    try:
        perc = systems.get("perception")
        oets = getattr(perc, "oets", None) if perc else None
        web  = getattr(oets, "web", None) if oets else None
        if web is not None and hasattr(web, "nodes"):
            return len(web.nodes)
    except Exception:
        pass
    return 0


def _dps_crystal_count(systems: Dict[str, Any]) -> int:
    try:
        dim = systems.get("dimensional")
        dps = getattr(dim, "dps", None) if dim else None
        if dps is not None and hasattr(dps, "crystals"):
            return len(dps.crystals)
    except Exception:
        pass
    return 0


def _constraint_alignment(systems: Dict[str, Any]) -> Optional[float]:
    try:
        cr = systems.get("constraint_reasoner")
        if cr is not None and hasattr(cr, "reasoning_report"):
            report = cr.reasoning_report()
            return report.get("recent_alignment")
    except Exception:
        pass
    return None


def _seek_stats(systems: Dict[str, Any]) -> Dict[str, int]:
    """Read and RESET per-epoch seek counters."""
    stats = systems.get("_seek_stats") or {}
    out = {
        "internal": int(stats.get("internal", 0)),
        "self_relation": int(stats.get("self_relation", 0)),
        "external": int(stats.get("external", 0)),
        "exhausted": int(stats.get("exhausted", 0)),
    }
    # Reset for next epoch
    systems["_seek_stats"] = {"internal": 0, "self_relation": 0,
                               "external": 0, "exhausted": 0}
    return out


class EpochSnapshot:
    """One epoch's worth of telemetry data."""
    def __init__(
        self,
        epoch: int,
        systems: Dict[str, Any],
        epoch_result: Optional[Dict] = None,
    ) -> None:
        self.epoch        = epoch
        self.timestamp    = time.time()
        self.axes         = _axis_snapshot(systems)
        self.oets_nodes   = _oets_node_count(systems)
        self.dps_crystals = _dps_crystal_count(systems)
        self.cr_alignment = _constraint_alignment(systems)
        self.seek         = _seek_stats(systems)
        r = epoch_result or {}
        self.avg_fitness       = float(r.get("avg_fitness", 0.0) or 0.0)
        self.fail_lessons      = int(r.get("dream_lesson_specs", 0) or 0)
        self.retained          = int(r.get("retained_learnings", 0) or 0)
        self.warp_demands      = int(r.get("warp_demand_count", 0) or 0)


class DevTelemetry:
    """
    Captures EpochSnapshots across a training run and produces a
    diagnostic report that identifies development acceleration bottlenecks.
    """

    def __init__(self, systems: Dict[str, Any]) -> None:
        self._systems = systems
        # Initialize seek stats counter if not present
        if systems.get("_seek_stats") is None:
            systems["_seek_stats"] = {"internal": 0, "self_relation": 0,
                                       "external": 0, "exhausted": 0}
        self._snapshots: List[EpochSnapshot] = []
        # Capture baseline (epoch 0 = before any training)
        self._baseline = EpochSnapshot(0, systems)

    def record(self, epoch: int, epoch_result: Dict) -> EpochSnapshot:
        snap = EpochSnapshot(epoch, self._systems, epoch_result)
        self._snapshots.append(snap)
        return snap

    def report(self) -> str:
        b   = self._baseline
        snaps = self._snapshots
        if not snaps:
            return "  [TELEMETRY] No epochs recorded."

        lines: List[str] = []
        lines.append("")
        lines.append("=" * 70)
        lines.append("  DEVELOPMENT ACCELERATION TELEMETRY")
        lines.append("=" * 70)

        # ── Axis drift ──────────────────────────────────────────────────────
        lines.append("\n  [1] AXIS DRIFT  (are X/T/N/B/A values building?)")
        lines.append(f"      {'':6s}  {'X':>7s}  {'T':>7s}  {'N':>7s}  {'B':>7s}  {'A':>7s}")
        lines.append(f"      {'base':6s}  " +
                     "  ".join(f"{b.axes.get(ax, 0.5):>7.3f}" for ax in _AXES))
        for s in snaps:
            delta = {ax: s.axes.get(ax, 0.5) - b.axes.get(ax, 0.5) for ax in _AXES}
            drift_str = "  ".join(
                f"{s.axes.get(ax, 0.5):>5.3f}{'↑' if delta[ax] > 0.02 else ('↓' if delta[ax] < -0.02 else '·')}"
                for ax in _AXES
            )
            lines.append(f"      E{s.epoch:4d}   {drift_str}")
        final = snaps[-1]
        total_drift = sum(abs(final.axes.get(ax, 0.5) - b.axes.get(ax, 0.5)) for ax in _AXES)
        if total_drift < 0.05:
            diag = "  ⚠ FLAT — axis states are not moving. Lessons are not reaching IVM."
        elif total_drift < 0.15:
            diag = "  ~ SLOW — some movement but marginal. Check lesson → axis path."
        else:
            diag = "  ✓ MOVING — axis states are building across epochs."
        lines.append(f"      Total drift across all axes: {total_drift:.3f}  {diag}")

        # ── OETS compounding ────────────────────────────────────────────────
        lines.append("\n  [2] OETS COMPOUNDING  (is internal knowledge building?)")
        lines.append(f"      {'':6s}  {'nodes':>7s}  {'+nodes':>7s}  {'intern':>7s}  {'self_r':>7s}  {'extern':>7s}  {'exhaus':>7s}  {'int%':>6s}")
        prev_nodes = b.oets_nodes
        for s in snaps:
            new_nodes = s.oets_nodes - prev_nodes
            total_seeks = s.seek["internal"] + s.seek["self_relation"] + s.seek["external"] + s.seek["exhausted"]
            internal_total = s.seek["internal"] + s.seek["self_relation"]
            int_pct = (internal_total / total_seeks * 100) if total_seeks > 0 else 0.0
            lines.append(
                f"      E{s.epoch:4d}   "
                f"{s.oets_nodes:>7d}  "
                f"{new_nodes:>+7d}  "
                f"{s.seek['internal']:>7d}  "
                f"{s.seek['self_relation']:>7d}  "
                f"{s.seek['external']:>7d}  "
                f"{s.seek['exhausted']:>7d}  "
                f"{int_pct:>5.1f}%"
            )
            prev_nodes = s.oets_nodes

        # Trend: is internal% growing?
        int_pcts = []
        for s in snaps:
            total_seeks = s.seek["internal"] + s.seek["self_relation"] + s.seek["external"] + s.seek["exhausted"]
            internal_total = s.seek["internal"] + s.seek["self_relation"]
            int_pcts.append((internal_total / total_seeks * 100) if total_seeks > 0 else 0.0)

        if len(int_pcts) >= 2:
            pct_trend = int_pcts[-1] - int_pcts[0]
            if pct_trend > 5:
                oets_diag = f"  ✓ COMPOUNDING — internal resolution rate rising (+{pct_trend:.1f}%)"
            elif int_pcts[-1] < 20:
                oets_diag = f"  ⚠ BOTTLENECK — {int_pcts[-1]:.1f}% internal. OETS isn't accumulating usable knowledge."
            else:
                oets_diag = f"  ~ STABLE at {int_pcts[-1]:.1f}% internal"
        else:
            oets_diag = f"  (need ≥2 epochs for trend)"
        lines.append(f"      {oets_diag}")

        # ── DPS crystallization ─────────────────────────────────────────────
        lines.append("\n  [3] DPS CRYSTALLIZATION  (is knowledge hardening?)")
        lines.append(f"      {'':6s}  {'crystals':>9s}  {'+crystals':>9s}  {'cr_align':>9s}  {'fitness':>8s}  {'retained':>8s}")
        prev_crys = b.dps_crystals
        for s in snaps:
            new_crys = s.dps_crystals - prev_crys
            cr_a = f"{s.cr_alignment:.3f}" if s.cr_alignment is not None else "  n/a "
            lines.append(
                f"      E{s.epoch:4d}   "
                f"{s.dps_crystals:>9d}  "
                f"{new_crys:>+9d}  "
                f"{cr_a:>9s}  "
                f"{s.avg_fitness:>8.3f}  "
                f"{s.retained:>8d}"
            )
            prev_crys = s.dps_crystals

        total_new_crys = snaps[-1].dps_crystals - b.dps_crystals
        if total_new_crys == 0:
            crys_diag = "  ⚠ NO CRYSTALLIZATION — nothing is hardening into permanent vocabulary."
        elif total_new_crys < 3:
            crys_diag = f"  ~ SLOW — only {total_new_crys} new crystal(s). Check DPS formation threshold."
        else:
            crys_diag = f"  ✓ FORMING — {total_new_crys} new crystal(s) across run."
        lines.append(f"      {crys_diag}")

        # ── Verdict ─────────────────────────────────────────────────────────
        lines.append("\n  [VERDICT]")
        issues = []
        if total_drift < 0.05:
            issues.append("AXIS FLAT: lessons not reaching IVM — identity isn't building")
        if int_pcts and int_pcts[-1] < 20:
            issues.append("OETS BOTTLENECK: >80% of seeks going external — no internal compounding")
        if total_new_crys == 0:
            issues.append("NO CRYSTALS: knowledge never hardens — Aurora rederives everything every time")

        if not issues:
            lines.append("  All three acceleration indicators are healthy.")
        else:
            for issue in issues:
                lines.append(f"  ✗ {issue}")

        lines.append("=" * 70)
        return "\n".join(lines)
