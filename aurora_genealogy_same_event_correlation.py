#!/usr/bin/env python3
"""
AURORA GENEALOGY SAME-EVENT CORRELATION (Phase 3A.3)
==========================================================
Authors: Sunni (Sir) Morningstar & Cael Devo

Phase 3A.2 correlated producer and consumer observations by tick proximity
alone -- and found the algorithm itself was initially wrong (an all-pairs
join over a loose window drifts into spurious cross-pairs). This phase asks
a stronger question: did a DIFFERENCE-bearing event and a pair-forming
event ever originate from the SAME NATIVE EVENT, using identifiers Aurora
already carries (session_id, lineage/episode ids, etc.) rather than clock
proximity?

This module's primary evidence source is STATIC: the real, already-
persisted `aurora_state/genealogy/events_recent.json` corpus's own `notes`
payloads, which (confirmed by reading, not assumed) already carry real
identity vocabulary -- `session_id`, `operation_lineage_id`,
`seed_lineage_id`, `constraint_combo_id`, `time_index` -- for exactly the
two populations this phase needs to compare. This requires no live
invocation of any heavy Aurora subsystem and carries no execution risk
whatsoever: it is a pure read of already-written JSON.

A secondary, live-code capability also exists: `aurora_genealogy_difference
_producer_observatory.py`'s `_capture_causal_context()` was extended in
this phase to scan free-function LOCAL VARIABLES directly (not only `self`
attributes), after discovering `aurora.py`'s `_run_live_response_turn` --
the single most important real producer call site (computes a real
DifferenceSnapshot on every ordinary conversational turn) -- is a plain
function, not a method, so the original self-only introspection would have
silently missed its real `session_id`/`turn_tick` parameters entirely.
Verified on a synthetic reproduction of that exact signature shape
(`tests/test_genealogy_difference_producer_observatory.py::
test_causal_context_found_in_free_function_locals`); NOT exercised against
the real 35,000-line `_run_live_response_turn` itself, which was assessed
as too heavily coupled to invoke safely in isolation for this investigation.

THREE OUTCOMES (as specified):
---------------------------------------------------------------------------
1. SAME EVENT, DISCONNECTED PATHS: a producer-bearing and a consumer-bearing
   record share an actual identity VALUE (not just a key name), but the
   consumer never received the snapshot. Closing evidence for a missing
   cross-organ substrate.
2. DIFFERENT EVENT POPULATIONS: no shared identity vocabulary (key names)
   between the two populations at all -- consistent with two developmental
   regimes that were never designed to reference each other's events.
3. SAME CAUSAL SEQUENCE, DIFFERENT MOMENTS: shared identity KEYS exist
   (the same kind of identifier appears on both sides) but no shared VALUES
   -- suggestive of a temporal/lifecycle question rather than an
   architectural one, IF the key itself is a genuine sequence identifier
   (not `tick`, which every record trivially has and which Phase 3A.2
   already analyzes separately as pure clock proximity).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from aurora_genealogy_promotion_dimension_observer import classify_promotion_relevant_dimension_participation

# Deliberately excludes bare "tick" -- ubiquitous, trivial, and already
# analyzed as pure clock proximity in Phase 3A.2's correlate_producer_consumer().
IDENTITY_KEYS = (
    "session_id", "turn_id", "turn_tick", "conversation_id", "episode_id",
    "operation_lineage_id", "seed_lineage_id", "lineage_id", "run_id",
    "constraint_combo_id", "time_index", "thread_id",
)


def extract_identity_fields(notes: Dict[str, Any]) -> Dict[str, Any]:
    """Pull out any of IDENTITY_KEYS present with a non-empty value."""
    if not isinstance(notes, dict):
        return {}
    return {k: notes[k] for k in IDENTITY_KEYS if notes.get(k) not in (None, "")}


@dataclass
class SameEventAnalysis:
    outcome: str   # "1_same_event_disconnected_paths" | "2_different_event_populations" | "3_same_sequence_different_moments" | "insufficient_data"
    producer_count: int = 0
    consumer_count: int = 0
    producer_identity_keys: Set[str] = field(default_factory=set)
    consumer_identity_keys: Set[str] = field(default_factory=set)
    shared_identity_keys: Set[str] = field(default_factory=set)
    shared_identity_values: Dict[str, Any] = field(default_factory=dict)  # key -> the shared value(s)
    producer_identity_samples: List[Dict[str, Any]] = field(default_factory=list)
    consumer_identity_samples: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "outcome": self.outcome,
            "producer_count": self.producer_count,
            "consumer_count": self.consumer_count,
            "producer_identity_keys": sorted(self.producer_identity_keys),
            "consumer_identity_keys": sorted(self.consumer_identity_keys),
            "shared_identity_keys": sorted(self.shared_identity_keys),
            "shared_identity_values": dict(self.shared_identity_values),
            "producer_identity_samples": self.producer_identity_samples[:3],
            "consumer_identity_samples": self.consumer_identity_samples[:3],
        }


def analyze_same_event_correlation(records: List[Dict[str, Any]]) -> SameEventAnalysis:
    """
    Partitions real ReliefRecord dicts into producer-bearing (real,
    nontrivial DifferenceSnapshot present) and consumer-bearing
    (pair-eligible, trace_length >= 2), extracts identity vocabulary from
    each population's `notes`, and classifies into one of the three
    outcomes. Pure read; no side effects; no live execution.
    """
    producer_records = []
    consumer_records = []
    for r in records:
        reading = classify_promotion_relevant_dimension_participation(r)
        if reading.difference_values_nontrivial:
            producer_records.append(r)
        if len(r.get("trace") or []) >= 2:
            consumer_records.append(r)

    if not producer_records or not consumer_records:
        return SameEventAnalysis(
            outcome="insufficient_data",
            producer_count=len(producer_records),
            consumer_count=len(consumer_records),
        )

    producer_identities = [extract_identity_fields(r.get("notes") or {}) for r in producer_records]
    consumer_identities = [extract_identity_fields(r.get("notes") or {}) for r in consumer_records]

    producer_keys = {k for d in producer_identities for k in d.keys()}
    consumer_keys = {k for d in consumer_identities for k in d.keys()}
    shared_keys = producer_keys & consumer_keys

    shared_values: Dict[str, Any] = {}
    for key in shared_keys:
        producer_values = {d[key] for d in producer_identities if key in d}
        consumer_values = {d[key] for d in consumer_identities if key in d}
        overlap = producer_values & consumer_values
        if overlap:
            shared_values[key] = sorted(overlap, key=str)

    if shared_values:
        # Same identified event exists on both sides. We already know
        # (Phase 3A/3A.1/3A.2) that no consumer record ever actually
        # carries a difference_snapshot -- so a shared identity value here
        # means the same native event produced both, on paths that don't see
        # each other.
        outcome = "1_same_event_disconnected_paths"
    elif not shared_keys:
        outcome = "2_different_event_populations"
    else:
        outcome = "3_same_sequence_different_moments"

    return SameEventAnalysis(
        outcome=outcome,
        producer_count=len(producer_records),
        consumer_count=len(consumer_records),
        producer_identity_keys=producer_keys,
        consumer_identity_keys=consumer_keys,
        shared_identity_keys=shared_keys,
        shared_identity_values=shared_values,
        producer_identity_samples=[d for d in producer_identities if d][:3],
        consumer_identity_samples=[d for d in consumer_identities if d][:3],
    )
