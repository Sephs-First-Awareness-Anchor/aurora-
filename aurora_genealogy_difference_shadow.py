#!/usr/bin/env python3
"""
AURORA GENEALOGY DIFFERENCE SHADOW (Phase 3A)
==================================================
Authors: Sunni (Sir) Morningstar & Cael Devo

Native DIFFERENCE Preservation Shadow. Does NOT alter PairStats, promotion
scoring, WARP authority, or genealogy atoms. Builds a PARALLEL structure
(`ShadowPairStats`) that mirrors `PairStats`'s real axis-level accumulation
shape exactly, plus a companion channel for the live DIFFERENCE signal
Phase 2 found is computed but never forwarded to promotion, then replays
real, already-persisted events through it to ask whether that dropped
signal carries anything worth having.

THIS MODULE OBSERVES. IT DOES NOT PROMOTE, HOOK, OR PATCH ANYTHING.
---------------------------------------------------------------------------
`replay_events()` reads real ReliefRecord dicts and reconstructs pair keys
using the EXACT SAME rule `_accumulate_pairs()` uses (adjacent items in
`trace`, `constraint_genealogy.py:5388-5391`: `key = (trace[i].id,
trace[i+1].id)`), and accumulates axis-level relief/cost the same way
`PairStats.update()` does (`:1280-1290`) -- but this is a REPLAY over
static, already-written JSON, not a hook into the live logger. It never
imports `ConstraintGenealogyLogger`, never calls `PairStats.update()` or
`_try_promote()`, and never writes back to `aurora_state/genealogy/`.
Verified by `tests/test_genealogy_difference_shadow.py`.

THE HEADLINE FINDING FROM RUNNING THIS AGAINST REAL DATA (see
docs/GENEALOGY_NATIVE_ENVIRONMENT_REPORT.md section 11 for full writeup):
the only available real corpus (aurora_state/genealogy/events_recent.json,
137 records) shows a complete split: every one of the 49 records carrying a
real DifferenceSnapshot has trace length exactly 1 (a single already-
promoted LINK being replayed by a dream episode -- `notes.artificial_seed`
is True and `notes.seed_lineage_id == "dream_episode"` on all 49, verified),
and `_accumulate_pairs()` requires `len(trace) >= 2` to form any pair at
all. Every record with trace length >= 2 (the 88 records that DO form the
252 real pair-observations in this corpus) has NO difference_snapshot.
This is not just a property of this sample: `aurora_grammar_engine.py`'s
own `observe()` call site (one confirmed real, organic, multi-item-trace
caller) hardcodes `difference_snapshot=None` (line 1563) -- it never even
attempts to read a live difference buffer. The dream/evolution-chamber path
(`aurora_internal/aurora_evolution_chamber.py:1434`) does pass a real one,
but (in this corpus) only for single-link replay traces.

Consequence: the strongest version of the "killer experiment" this phase
was designed to run -- comparing DIFFERENCE-divergent PAIRS that collapse
to the same current signature, and checking whether their later
genealogical behavior differs -- cannot be executed against this specific
corpus, because no real pair-observation in it ever carries a real
DIFFERENCE value to compare. `find_pairs_with_divergent_difference()` below
is implemented correctly and generically (ready for a corpus where the two
signals do co-occur) and is run against the real data; it correctly finds
zero qualifying candidates, for the reason above, not from a bug.

What CAN be answered from this corpus, and is: whether the 49 real
DIFFERENCE values carry information beyond axis identity (yes -- see
`measure_information_beyond_axis_identity()` and the report), and whether
DIFFERENCE shows within-substrate persistence versus tick-to-tick noise
across the 6 real ConstraintLinks that DO get replayed repeatedly in this
window (`measure_persistence_across_reused_links()`).
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from aurora_genealogy_promotion_dimension_observer import (
    classify_promotion_relevant_dimension_participation,
    DimensionParticipationReading,
)

AXES = ("X", "T", "N", "B", "A")


def _axis_of_id(item_id: str, links_index: Dict[str, Dict[str, Any]]) -> Optional[str]:
    """Same rule constraint_genealogy._axis_counts_from_item() uses for
    non-Link ids (constraint_genealogy.py:2664-2670): the axis is the
    letter before the first ':'. For a real promoted LINK id, use its own
    persisted dominant_relief_axis instead."""
    if item_id.startswith("L:"):
        link = links_index.get(item_id)
        return link.get("dominant_relief_axis") if link else None
    if ":" in item_id:
        prefix = item_id.split(":", 1)[0].strip().upper()
        return prefix if prefix in AXES else None
    return None


# ---------------------------------------------------------------------------
# The parallel structure
# ---------------------------------------------------------------------------

@dataclass
class ShadowPairStats:
    """
    Mirrors real PairStats's axis-level accumulation exactly (same fields,
    same update rule) PLUS the shadow companion channel PairStats structurally
    cannot carry (Phase 2, section 10.1): per-tick DIFFERENCE participation,
    with explicit provenance -- never collapsed into "axis" the way the
    genealogy atoms would.
    """
    left_id: str
    right_id: str

    # --- existing (mirrors real PairStats) ---
    count: int = 0
    relief_sum: Dict[str, float] = field(default_factory=lambda: {a: 0.0 for a in AXES})
    cost_sum: Dict[str, float] = field(default_factory=lambda: {a: 0.0 for a in AXES})
    x_risk_sum: float = 0.0
    ticks: List[int] = field(default_factory=list)

    # --- shadow companion (the missing channel) ---
    difference_participation_ticks: List[int] = field(default_factory=list)
    difference_values_by_tick: Dict[int, Dict[str, float]] = field(default_factory=dict)
    difference_source: str = "evolution_chamber"  # provenance label; see module doctrine
    non_operator_cost_tensor_dims_by_tick: Dict[int, List[str]] = field(default_factory=dict)
    dominant_relief_axis_by_tick: Dict[int, Optional[str]] = field(default_factory=dict)

    def update_axis_stats(self, relief: Dict[str, float], cost: Dict[str, float], x_risk: float, tick: int) -> None:
        self.count += 1
        for a in AXES:
            self.relief_sum[a] += float(relief.get(a, 0.0) or 0.0)
            self.cost_sum[a] += float(cost.get(a, 0.0) or 0.0)
        self.x_risk_sum += x_risk
        self.ticks.append(tick)

    def update_difference_companion(self, reading: DimensionParticipationReading, tick: int) -> None:
        self.dominant_relief_axis_by_tick[tick] = reading.dominant_relief_axis
        if reading.difference_values_nontrivial and reading.difference_values:
            self.difference_participation_ticks.append(tick)
            self.difference_values_by_tick[tick] = dict(reading.difference_values)
        if reading.non_operator_cost_tensor_dims:
            self.non_operator_cost_tensor_dims_by_tick[tick] = list(reading.non_operator_cost_tensor_dims)

    def mean_relief(self) -> Dict[str, float]:
        n = max(1, self.count)
        return {a: self.relief_sum[a] / n for a in AXES}

    def difference_participation_rate(self) -> float:
        return len(self.difference_participation_ticks) / max(1, self.count)

    def current_signature(self, links_index: Dict[str, Dict[str, Any]]) -> Tuple[Optional[str], Optional[str]]:
        """The (left_axis, right_axis) pair this key would resolve to under
        the existing OPERATOR x COST genealogy-atom vocabulary (Phase 1,
        genealogy_atom_to_channel_pair: NC:{left}>{right} = NC:left:OPERATOR
        x NC:right:COST). Two different pair-keys sharing this signature are
        indistinguishable under the current representation."""
        return (_axis_of_id(self.left_id, links_index), _axis_of_id(self.right_id, links_index))


def replay_events(records: List[Dict[str, Any]], links_index: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[Tuple[str, str], ShadowPairStats]:
    """
    Replay real ReliefRecord dicts into ShadowPairStats, using the exact
    adjacent-pair rule _accumulate_pairs() uses. x_risk is approximated as
    sum(abs(trace_risk_total.values())) -- the real scalar x_risk_total is
    computed from live AbilityProfile.x_risk() lookups this static replay
    has no access to; this approximation is used ONLY for shape parity, and
    no promotion gate (which would need the real value) is evaluated here.
    """
    links_index = links_index or {}
    pair_stats: Dict[Tuple[str, str], ShadowPairStats] = {}

    for record in records:
        trace = record.get("trace") or []
        if len(trace) < 2:
            continue
        relief = record.get("relief") or {}
        cost_total = record.get("trace_cost_total") or {}
        risk_total = record.get("trace_risk_total") or {}
        x_risk_approx = sum(abs(float(v or 0.0)) for v in risk_total.values())
        tick = record.get("tick")
        reading = classify_promotion_relevant_dimension_participation(record)

        for i in range(len(trace) - 1):
            left = trace[i]
            right = trace[i + 1]
            key = (left.get("id"), right.get("id"))
            if key not in pair_stats:
                pair_stats[key] = ShadowPairStats(left_id=key[0], right_id=key[1])
            ps = pair_stats[key]
            ps.update_axis_stats(relief, cost_total, x_risk_approx, tick)
            ps.update_difference_companion(reading, tick)

    return pair_stats


# ---------------------------------------------------------------------------
# Measurements
# ---------------------------------------------------------------------------

@dataclass
class SignatureCollisionResult:
    signature: Tuple[Optional[str], Optional[str]]
    pair_keys: List[Tuple[str, str]]
    difference_rates: List[float]

    @property
    def collides(self) -> bool:
        return len(self.pair_keys) > 1

    @property
    def difference_rates_diverge(self) -> bool:
        return self.collides and (max(self.difference_rates) - min(self.difference_rates)) > 0.0


def measure_collision_differentiation(
    pair_stats: Dict[Tuple[str, str], ShadowPairStats],
    links_index: Dict[str, Dict[str, Any]],
) -> List[SignatureCollisionResult]:
    """Question 1: does DIFFERENCE differentiate genealogies that currently
    collapse to the same OPERATOR x COST signature? Groups pair-keys by
    current_signature() and reports, per group, whether difference
    participation rate diverges across members."""
    groups: Dict[Tuple[Optional[str], Optional[str]], List[Tuple[str, str]]] = {}
    for key, ps in pair_stats.items():
        sig = ps.current_signature(links_index)
        groups.setdefault(sig, []).append(key)

    results = []
    for sig, keys in groups.items():
        rates = [pair_stats[k].difference_participation_rate() for k in keys]
        results.append(SignatureCollisionResult(signature=sig, pair_keys=keys, difference_rates=rates))
    return results


def measure_information_beyond_axis_identity(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Question 6 (the important one): is the DIFFERENCE value reconstructible
    from axis identity alone, or does it carry information beyond it?

    Method: group real DIFFERENCE-bearing records by dominant_relief_axis
    (the single categorical label the current representation would keep),
    then measure the spread of the ACTUAL 5-value DifferenceSnapshot within
    each group. If axis identity fully determined the DIFFERENCE reading,
    same-axis records would show ~zero within-group spread. Nonzero spread
    is direct evidence of information the axis label alone does not carry.
    Also reports whether NON-dominant axes carry nonzero DIFFERENCE signal
    at all -- axis identity is a single label; a nonzero 5-vector where the
    axis is only 1 of 5 slots is, by construction, not reducible to that label.
    """
    by_axis: Dict[str, List[Dict[str, float]]] = {}
    for record in records:
        reading = classify_promotion_relevant_dimension_participation(record)
        if not reading.difference_values_nontrivial or not reading.difference_values:
            continue
        axis = reading.dominant_relief_axis
        if axis not in AXES:
            continue
        by_axis.setdefault(axis, []).append(reading.difference_values)

    per_axis_spread: Dict[str, Dict[str, float]] = {}
    non_dominant_nonzero_count = 0
    total_nontrivial = 0
    for axis, value_dicts in by_axis.items():
        total_nontrivial += len(value_dicts)
        dominant_axis_values = [v.get(axis, 0.0) for v in value_dicts]
        per_axis_spread[axis] = {
            "n": len(value_dicts),
            "dominant_axis_value_stdev": statistics.pstdev(dominant_axis_values) if len(dominant_axis_values) > 1 else 0.0,
            "dominant_axis_value_min": min(dominant_axis_values) if dominant_axis_values else None,
            "dominant_axis_value_max": max(dominant_axis_values) if dominant_axis_values else None,
        }
        for v in value_dicts:
            for other_axis in AXES:
                if other_axis != axis and abs(v.get(other_axis, 0.0)) >= 1e-6:
                    non_dominant_nonzero_count += 1

    return {
        "per_axis_spread": per_axis_spread,
        "total_nontrivial_records": total_nontrivial,
        "records_with_nonzero_non_dominant_axis_value": non_dominant_nonzero_count,
    }


def measure_persistence_across_reused_links(
    pair_stats: Dict[Tuple[str, str], ShadowPairStats],
    records: List[Dict[str, Any]],
    links_index: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Question 4/2: for real ConstraintLinks that get replayed (reused)
    multiple times in this corpus, does DIFFERENCE show within-link
    consistency (same link, repeated observations, similar values --
    suggesting a persistent trait) or pure tick-to-tick noise? Also reports
    each reused link's real ancestry structure (via
    aurora_genealogy_environment, reusing Phase 1/1.1 machinery) alongside
    its difference statistics, for question 2 (DAG structure correlation)
    and question 3's "closure grade" correlation.

    Note: this operates on single-item (trace length 1) LINK-replay records
    directly, NOT on ShadowPairStats -- those replay events never form pairs
    (len(trace) == 1), which is itself the headline finding this phase
    surfaces. This function is the closest available real-data analog for
    "does DIFFERENCE persist across ancestry" given that constraint.
    """
    per_link_values: Dict[str, List[Dict[str, float]]] = {}
    for record in records:
        trace = record.get("trace") or []
        if len(trace) != 1 or trace[0].get("kind") != "LINK":
            continue
        link_id = trace[0].get("id")
        if link_id not in links_index:
            continue
        reading = classify_promotion_relevant_dimension_participation(record)
        if reading.difference_values_nontrivial and reading.difference_values:
            per_link_values.setdefault(link_id, []).append(reading.difference_values)

    result: Dict[str, Any] = {"links": {}}
    for link_id, value_dicts in per_link_values.items():
        link = links_index[link_id]
        dominant_axis = link.get("dominant_relief_axis")
        same_axis_values = [v.get(dominant_axis, 0.0) for v in value_dicts if dominant_axis in AXES]
        result["links"][link_id] = {
            "replay_count": len(value_dicts),
            "dominant_relief_axis": dominant_axis,
            "depth": link.get("depth"),
            "own_axis_difference_values": same_axis_values,
            "own_axis_difference_stdev": statistics.pstdev(same_axis_values) if len(same_axis_values) > 1 else 0.0,
            "own_axis_difference_mean": statistics.mean(same_axis_values) if same_axis_values else None,
        }

    # Cross-link pooled comparison intentionally omitted: with only a
    # handful of reused links in this corpus (see report), a pooled
    # within-vs-between variance test would have too few groups to mean
    # anything -- the per-link breakdown above is reported as-is instead.
    all_within_link_stdevs = [v["own_axis_difference_stdev"] for v in result["links"].values() if v["replay_count"] > 1]
    result["mean_within_link_stdev"] = statistics.mean(all_within_link_stdevs) if all_within_link_stdevs else None
    result["n_links_with_repeated_replay"] = len(all_within_link_stdevs)
    return result


def find_pairs_with_divergent_difference(
    pair_stats: Dict[Tuple[str, str], ShadowPairStats],
    links_index: Dict[str, Dict[str, Any]],
    relief_tolerance: float = 0.25,
) -> List[Dict[str, Any]]:
    """
    THE KILLER EXPERIMENT, implemented generically and correctly: find pairs
    of pair-keys (A, B) that are near-identical under the CURRENT
    representation (same current_signature() -- same axis pair, hence same
    OPERATOR x COST genealogy atom -- and mean relief within
    `relief_tolerance` of each other by relative magnitude) but whose live
    DIFFERENCE participation materially differs (one has real nontrivial
    DIFFERENCE signal, the other does not, or their per-axis values differ
    substantially). For each qualifying pair, reports whether their
    SUBSEQUENT behavior (recurrence count, i.e. `.count`) also differs.

    Requires at least one member on each side of the comparison to have
    nontrivial difference participation -- on the real corpus available to
    this phase, zero pair-keys ever do (see module docstring), so this
    correctly returns an empty list there. Implemented and tested against
    synthetic data (tests/test_genealogy_difference_shadow.py) so it is
    ready for a corpus where the two signals actually co-occur.
    """
    by_signature: Dict[Tuple[Optional[str], Optional[str]], List[Tuple[str, str]]] = {}
    for key, ps in pair_stats.items():
        sig = ps.current_signature(links_index)
        by_signature.setdefault(sig, []).append(key)

    candidates: List[Dict[str, Any]] = []
    for sig, keys in by_signature.items():
        if len(keys) < 2:
            continue
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                a, b = pair_stats[keys[i]], pair_stats[keys[j]]
                mean_a = sum(a.mean_relief().values())
                mean_b = sum(b.mean_relief().values())
                denom = max(abs(mean_a), abs(mean_b), 1e-9)
                if abs(mean_a - mean_b) / denom > relief_tolerance:
                    continue  # not near-identical under current representation
                a_has_diff = len(a.difference_participation_ticks) > 0
                b_has_diff = len(b.difference_participation_ticks) > 0
                if a_has_diff == b_has_diff:
                    continue  # both/neither carry difference signal -- not divergent
                candidates.append({
                    "signature": sig,
                    "pair_a": keys[i], "pair_b": keys[j],
                    "mean_relief_a": mean_a, "mean_relief_b": mean_b,
                    "difference_present_a": a_has_diff, "difference_present_b": b_has_diff,
                    "recurrence_a": a.count, "recurrence_b": b.count,
                    "recurrence_diverges": a.count != b.count,
                })
    return candidates
