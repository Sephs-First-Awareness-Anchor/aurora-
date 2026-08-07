#!/usr/bin/env python3
"""
AURORA GENEALOGY PROMOTION — DIMENSION-PARTICIPATION OBSERVER (Phase 2)
==========================================================================
Authors: Sunni (Sir) Morningstar & Cael Devo

Answers one question, empirically, against real Aurora runtime data: does
Aurora's live formation dynamics (the pressure/relief events that feed
ConstraintLink promotion) actually involve NonComp dimensions the current
OPERATOR x COST genealogy atoms cannot preserve — or is the OPERATOR/COST
confinement found in Phase 1 (docs/GENEALOGY_NATIVE_ENVIRONMENT_REPORT.md
section 3) a faithful compression of what promotion's own inputs ever
carried in the first place?

THIS MODULE OBSERVES. IT DOES NOT PROMOTE, HOOK, OR PATCH ANYTHING.
---------------------------------------------------------------------------
Every function here is a pure read: given an already-persisted ReliefRecord
(as JSON, from a real run) or an already-serialized DifferenceSnapshot /
active_concepts list, it classifies what dimension-level signal was present.
Nothing in this module imports, calls, monkeypatches, or otherwise touches
ConstraintGenealogyLogger.observe(), ._accumulate_pairs(), ._try_promote(),
or PairStats.update() — promotion behavior for any past, present, or future
Aurora run is completely unaffected by this module's existence. This is
verified by test_module_never_touches_constraint_genealogy_promotion_state
in tests/test_genealogy_promotion_dimension_observer.py.

STRUCTURAL FINDING (CONFIRMED, verified by direct source inspection, not
assumed) — the promotion input surface is axis-only, not dimension-typed:
---------------------------------------------------------------------------
`PairStats.update(self, relief: PressureVec, cost: Dict[str, float],
x_risk: float, tick: int)` (aurora_internal/constraint_genealogy.py:1280) —
its complete signature. `PressureVec` and `Dict[str, float]` are both keyed
by AXES (X/T/N/B/A), never by NonCompDimension. There is no parameter shape
in this signature that COULD carry "which dimension" information even if a
caller wanted to supply it. `_try_promote()` (:5433) reads only
`ps.mean_relief()/mean_pos_relief()/pos_fraction()/stdev_relief()/
mean_cost()/mean_x_risk_val()` — all axis-level aggregates of exactly that
input. The `ConstraintLink` it constructs (:5905) stores only
`mean_relief/stdev_relief/mean_cost/mean_x_risk/dominant_relief_axis` —
consistent with what Phase 1 already found on the OUTPUT side. This module
adds the INPUT-side half of that finding.

Meanwhile, in the exact same `observe()` call
(aurora_internal/constraint_genealogy.py:1869-2118, confirmed by reading it
top to bottom) that builds the `PairStats`-feeding `relief`/`cost_total`
values, a SEPARATE, genuinely dimension-typed live quantity is also
available and gets folded into the SAME tick's `ReliefRecord.notes`, but is
never forwarded to `_accumulate_pairs()` (verified: the exact call at
observe():2074 is `self._accumulate_pairs(trace, relief, cost_total,
x_risk_total)` — no difference_snapshot argument, confirmed via
inspect.getsource in this module's own test suite):

  - `difference_snapshot: Optional[DifferenceSnapshot]` — a real, live,
    per-axis DIFFERENCE-dimension value, computed by the evolution
    chamber's DifferenceHistoryBuffer via compute_difference() against each
    constraint's own DifferenceParams.ref_type (prior_self / peer_mean /
    background — aurora_internal/aurora_difference_buffer.py:21,347-360).
    That module's own docstring calls this snapshot "the live output of the
    Difference channel — the fifth lens made operationally real"
    (aurora_difference_buffer.py:136-137). This is the single strongest,
    most directly-confirmed piece of evidence in this investigation: a
    genuinely dimension-typed live physics quantity, computed at the same
    tick, structurally excluded from promotion's input by
    _accumulate_pairs()'s call signature, not merely dropped afterward.

A second, WEAKER-graded signal also exists in `active_concepts`
(observe():1983-1995, sourced from `self._dps.get_recently_active(5)`):
`aurora_internal/dual_strata/cers_tensor_locator.py`'s `record_tensor_trace()`
writes crystal concepts named `f"tensor:{coord.slot_id}"`, where `coord` is
a `SlotCoord` (aurora_constraint_manifold_router.py) whose `slot_id`
encodes two axes' CANONICAL dimensions, e.g.
`"MANIFOLD:X:NC[N:COST]xNC[T:DIFFERENCE]"`. This DOES reference dimensions
beyond OPERATOR/COST in real persisted data (confirmed below). But per
`_resolve_slot_coord()` (cers_tensor_locator.py:119-138), `nc_dim`/`law_d`
come from `axis_to_dim.get(axis, "OPERATOR")` — a STATIC per-axis lookup
table (aurora_constraint_manifold_router.py:231 `_DIMENSION_TO_AXIS`,
inverted), not a live per-event dimension computation. Only WHICH AXIS
ranks 2nd/3rd-most-active is genuinely live; the dimension NAME attached to
that axis is a fixed badge. This is graded weaker than the DifferenceSnapshot
finding: real evidence that a live subsystem treats dimension identity as
axis-determined (a different design choice than aurora_closure_basis's own
`_build_noncomp_channels()`, which gives all 5 dimension-channels of a
constraint identical physics — Phase 1, docs report section 1.3), but not
itself proof of live per-dimension physics computation.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

AXES = ("X", "T", "N", "B", "A")
NONOPERATOR_COST_DIMENSIONS = frozenset({"POLARITY", "MAGNITUDE", "DIFFERENCE"})

# Matches the real persisted form, e.g.
# "tensor:MANIFOLD:X:NC[N:COST]xNC[T:DIFFERENCE]"
# (verified against aurora_state/genealogy/events_recent.json; produced by
# cers_tensor_locator.record_tensor_trace()'s f"tensor:{coord.slot_id}").
_TENSOR_CONCEPT_PATTERN = re.compile(
    r"^tensor:MANIFOLD:[A-Z]:NC\[[A-Z]+:([A-Z]+)\]xNC\[[A-Z]+:([A-Z]+)\]$"
)

_DIFFERENCE_NONTRIVIAL_THRESHOLD = 1e-6  # any value distinguishable from exact zero


def extract_difference_dimension_signal(notes: Dict[str, Any]) -> Optional[Dict[str, float]]:
    """
    Pull the real per-axis DIFFERENCE-dimension values out of a ReliefRecord's
    `notes` dict, exactly as `observe()` serializes them
    (DifferenceSnapshot.to_dict(), aurora_difference_buffer.py:179-186).
    Returns None if this tick's `observe()` call was never given a
    difference_snapshot (the parameter is optional).
    """
    if not isinstance(notes, dict):
        return None
    snap = notes.get("difference_snapshot")
    if not isinstance(snap, dict):
        return None
    values = snap.get("values")
    if not isinstance(values, dict):
        return None
    return {a: float(values.get(a, 0.0) or 0.0) for a in AXES if a in values}


def difference_values_are_nontrivial(values: Optional[Dict[str, float]]) -> bool:
    """True if at least one real per-axis DIFFERENCE value is meaningfully
    nonzero — i.e. the DIFFERENCE channel actually had something to say at
    this tick, not just a present-but-empty/zeroed snapshot."""
    if not values:
        return False
    return any(abs(v) >= _DIFFERENCE_NONTRIVIAL_THRESHOLD for v in values.values())


def extract_tensor_dimension_labels(active_concepts: Optional[List[str]]) -> List[str]:
    """
    Parse every `tensor:MANIFOLD:...` concept string in `active_concepts`
    (as built by observe():1983-1995 from CERS's tensor locator) and return
    every dimension name referenced, in order, with repeats. Non-tensor
    concept strings are ignored. See module docstring for why this signal is
    graded weaker than extract_difference_dimension_signal().
    """
    labels: List[str] = []
    for concept in (active_concepts or []):
        match = _TENSOR_CONCEPT_PATTERN.match(str(concept))
        if match:
            labels.append(match.group(1))
            labels.append(match.group(2))
    return labels


@dataclass
class DimensionParticipationReading:
    """One record's classified dimension-participation reading."""
    difference_signal_present: bool = False
    difference_values_nontrivial: bool = False
    difference_values: Optional[Dict[str, float]] = None
    tensor_dimensions_referenced: List[str] = field(default_factory=list)
    non_operator_cost_tensor_dims: List[str] = field(default_factory=list)
    dominant_relief_axis: Optional[str] = None

    @property
    def shows_non_operator_cost_participation(self) -> bool:
        """True if EITHER the strong (DifferenceSnapshot) or weak (tensor
        concept) signal shows genuine non-OPERATOR/COST dimension activity
        for this record."""
        return self.difference_values_nontrivial or bool(self.non_operator_cost_tensor_dims)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "difference_signal_present": self.difference_signal_present,
            "difference_values_nontrivial": self.difference_values_nontrivial,
            "difference_values": dict(self.difference_values) if self.difference_values else None,
            "tensor_dimensions_referenced": list(self.tensor_dimensions_referenced),
            "non_operator_cost_tensor_dims": list(self.non_operator_cost_tensor_dims),
            "dominant_relief_axis": self.dominant_relief_axis,
            "shows_non_operator_cost_participation": self.shows_non_operator_cost_participation,
        }


def classify_promotion_relevant_dimension_participation(record: Dict[str, Any]) -> DimensionParticipationReading:
    """
    Given one real, already-persisted ReliefRecord dict (the exact shape
    ConstraintGenealogyLogger._write_event() / events_recent.json write),
    classify what dimension-level signal existed at that tick — the same
    tick whose axis-only relief/cost fed PairStats.update() and therefore
    promotion, per the structural finding in this module's docstring.
    """
    notes = record.get("notes") or {}
    diff_values = extract_difference_dimension_signal(notes)
    tensor_dims = extract_tensor_dimension_labels(record.get("active_concepts"))
    non_oc_tensor_dims = [d for d in tensor_dims if d in NONOPERATOR_COST_DIMENSIONS]

    return DimensionParticipationReading(
        difference_signal_present=diff_values is not None,
        difference_values_nontrivial=difference_values_are_nontrivial(diff_values),
        difference_values=diff_values,
        tensor_dimensions_referenced=tensor_dims,
        non_operator_cost_tensor_dims=non_oc_tensor_dims,
        dominant_relief_axis=record.get("dominant_relief_axis"),
    )


@dataclass
class CorpusDimensionParticipationSummary:
    record_count: int = 0
    difference_signal_present_count: int = 0
    difference_nontrivial_count: int = 0
    tensor_reference_count: int = 0
    non_operator_cost_tensor_count: int = 0
    any_non_operator_cost_signal_count: int = 0
    non_operator_cost_dimension_counts: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        n = max(1, self.record_count)
        return {
            "record_count": self.record_count,
            "difference_signal_present": {
                "count": self.difference_signal_present_count,
                "fraction": self.difference_signal_present_count / n,
            },
            "difference_values_nontrivial": {
                "count": self.difference_nontrivial_count,
                "fraction": self.difference_nontrivial_count / n,
            },
            "tensor_concept_reference_present": {
                "count": self.tensor_reference_count,
                "fraction": self.tensor_reference_count / n,
            },
            "non_operator_cost_tensor_reference": {
                "count": self.non_operator_cost_tensor_count,
                "fraction": self.non_operator_cost_tensor_count / n,
            },
            "any_non_operator_cost_signal": {
                "count": self.any_non_operator_cost_signal_count,
                "fraction": self.any_non_operator_cost_signal_count / n,
            },
            "non_operator_cost_dimension_counts": dict(self.non_operator_cost_dimension_counts),
        }


def summarize_corpus(records: List[Dict[str, Any]]) -> CorpusDimensionParticipationSummary:
    """
    Aggregate classify_promotion_relevant_dimension_participation() across a
    real corpus of persisted ReliefRecords. Pure read; no side effects.
    """
    summary = CorpusDimensionParticipationSummary(record_count=len(records))
    for record in records:
        reading = classify_promotion_relevant_dimension_participation(record)
        if reading.difference_signal_present:
            summary.difference_signal_present_count += 1
        if reading.difference_values_nontrivial:
            summary.difference_nontrivial_count += 1
        if reading.tensor_dimensions_referenced:
            summary.tensor_reference_count += 1
        if reading.non_operator_cost_tensor_dims:
            summary.non_operator_cost_tensor_count += 1
        if reading.shows_non_operator_cost_participation:
            summary.any_non_operator_cost_signal_count += 1
        for dim in reading.non_operator_cost_tensor_dims:
            summary.non_operator_cost_dimension_counts[dim] = (
                summary.non_operator_cost_dimension_counts.get(dim, 0) + 1
            )
    return summary
