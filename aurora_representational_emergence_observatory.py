#!/usr/bin/env python3
"""
aurora_representational_emergence_observatory.py

AURORA SYSTEM-WIDE REPRESENTATIONAL CONSERVATION, PROPAGATION, AND
EMERGENCE REPAIR DIRECTIVE -- Phase 8.

An observational, non-authoritative detector for candidate representational
depth emergence. This module:
  - never creates a new depth or coordinate,
  - never labels anything "depth three" or any other semantic name,
  - never alters routing, WARP, genealogy, meaning, or pressure geometry,
  - only RECORDS whether a previously-conditional relationship between two
    already-confirmed representational quantities has become independently
    measurable, and reports the raw evidence for a human (or Aurora's own
    later developmental machinery) to interpret.

Required evidence for a candidate new degree, per the directive, ALL of
which this module checks and none of which it decides on its own:
  1. independent variation
  2. measurable effect on existing physics
  3. recurrence across more than one configuration
  4. transfer beyond the originating example
  5. persistence long enough to rule out a transient artifact

A matching power-of-five cardinality is supporting geometry only -- this
module never treats cardinality as sufficient evidence by itself, and the
`cardinality_hint` field on a candidate is documented as exactly that: a
hint, not a criterion.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple


@dataclass
class ObservationSample:
    """One measured data point: a configuration, the candidate coordinate's
    value at that configuration, and the resulting value of whatever
    existing physics quantity is being watched."""
    configuration_id: str
    coordinate_value: Any
    effect_value: float
    source: str  # free-text provenance, e.g. "aurora_manifold_directory/X/...json"


@dataclass
class EmergenceEvidence:
    """The five required evidence categories, each independently scored
    from raw samples -- never asserted, always computed."""
    independent_variation: bool
    independent_variation_detail: str

    measurable_effect: bool
    measurable_effect_detail: str

    recurrence_count: int
    recurrence_detail: str

    transfer_confirmed: bool
    transfer_detail: str

    persistence_observations: int
    persistence_detail: str

    cardinality_hint: Optional[str] = None

    @property
    def all_criteria_met(self) -> bool:
        return (
            self.independent_variation
            and self.measurable_effect
            and self.recurrence_count >= 2
            and self.transfer_confirmed
            and self.persistence_observations >= 2
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "independent_variation": self.independent_variation,
            "independent_variation_detail": self.independent_variation_detail,
            "measurable_effect": self.measurable_effect,
            "measurable_effect_detail": self.measurable_effect_detail,
            "recurrence_count": self.recurrence_count,
            "recurrence_detail": self.recurrence_detail,
            "transfer_confirmed": self.transfer_confirmed,
            "transfer_detail": self.transfer_detail,
            "persistence_observations": self.persistence_observations,
            "persistence_detail": self.persistence_detail,
            "cardinality_hint": self.cardinality_hint,
            "all_criteria_met": self.all_criteria_met,
        }


def evaluate_candidate_relationship(
    samples_by_configuration: Dict[str, Sequence[ObservationSample]],
    *,
    numeric_tolerance: float = 1e-9,
    min_distinct_values_for_independence: int = 3,
    cardinality_hint: Optional[str] = None,
) -> EmergenceEvidence:
    """Evaluate one candidate C-D relationship for emergence evidence.

    `samples_by_configuration` maps a configuration identifier (e.g. a base
    NonComp name, or an episode id) to the samples collected under that
    configuration. This function does not know or care what the coordinate
    or the effect physically mean -- it only measures whether they behave
    like an independently real relationship across the supplied evidence.

    This function NEVER mutates any Aurora state; it only reads the sample
    values it is given.
    """
    all_samples: List[ObservationSample] = [
        s for samples in samples_by_configuration.values() for s in samples
    ]

    # 1. Independent variation: does the coordinate actually take on
    #    several distinct values across the evidence, rather than being
    #    constant (which would make "independent" meaningless)?
    distinct_coord_values = {s.coordinate_value for s in all_samples}
    independent_variation = len(distinct_coord_values) >= min_distinct_values_for_independence
    iv_detail = (
        f"{len(distinct_coord_values)} distinct coordinate values observed "
        f"across {len(all_samples)} samples "
        f"(threshold: {min_distinct_values_for_independence})"
    )

    # 2. Measurable effect: within at least one configuration, does the
    #    effect value actually change as the coordinate changes? A flat
    #    effect (all coordinate values producing the same effect) means the
    #    coordinate has no measured consequence yet.
    measurable_effect = False
    me_details = []
    for config_id, samples in samples_by_configuration.items():
        distinct_effects = {round(s.effect_value, 9) for s in samples}
        if len(distinct_effects) >= 2:
            measurable_effect = True
            me_details.append(f"{config_id}: {len(distinct_effects)} distinct effect values")
        else:
            me_details.append(f"{config_id}: flat effect ({distinct_effects})")
    me_detail = "; ".join(me_details) if me_details else "no configurations supplied"

    # 3. Recurrence: how many independent configurations show the same
    #    coordinate->effect pattern (both independent variation AND a
    #    measurable effect within that configuration)? A single
    #    configuration is a special case, not a recurring pattern.
    recurrence_count = 0
    for config_id, samples in samples_by_configuration.items():
        cvals = {s.coordinate_value for s in samples}
        evals = {round(s.effect_value, 9) for s in samples}
        if len(cvals) >= 2 and len(evals) >= 2:
            recurrence_count += 1
    recurrence_detail = f"{recurrence_count} of {len(samples_by_configuration)} configurations show the pattern"

    # 4. Transfer: does the pattern hold in a configuration that was not
    #    part of the ORIGINAL evidence set used to first notice it? Callers
    #    must mark this by passing configurations whose id starts with
    #    "transfer:" for held-out/held-later evidence.
    transfer_configs = {
        cid: s for cid, s in samples_by_configuration.items() if cid.startswith("transfer:")
    }
    transfer_confirmed = False
    if transfer_configs:
        transfer_confirmed = all(
            len({s.coordinate_value for s in samples}) >= 2
            and len({round(s.effect_value, 9) for s in samples}) >= 2
            for samples in transfer_configs.values()
        )
    transfer_detail = (
        f"{len(transfer_configs)} transfer configuration(s) supplied; "
        f"pattern held in all of them: {transfer_confirmed}"
        if transfer_configs
        else "no transfer (held-out) configuration supplied -- transfer NOT tested"
    )

    # 5. Persistence: how many independently-timestamped/independently-run
    #    observation batches were supplied? Caller must pass distinct
    #    configuration ids per independent run to avoid a single snapshot
    #    masquerading as repeated confirmation.
    persistence_observations = len(samples_by_configuration)
    persistence_detail = (
        f"{persistence_observations} independent configuration batches observed "
        "-- a single batch cannot rule out a transient artifact"
    )

    return EmergenceEvidence(
        independent_variation=independent_variation,
        independent_variation_detail=iv_detail,
        measurable_effect=measurable_effect,
        measurable_effect_detail=me_detail,
        recurrence_count=recurrence_count,
        recurrence_detail=recurrence_detail,
        transfer_confirmed=transfer_confirmed,
        transfer_detail=transfer_detail,
        persistence_observations=persistence_observations,
        persistence_detail=persistence_detail,
        cardinality_hint=cardinality_hint,
    )


def record_dependent_to_independent_transition(
    relationship_name: str,
    before_evidence: EmergenceEvidence,
    after_evidence: EmergenceEvidence,
) -> Dict[str, Any]:
    """Record (never name, never classify into a depth) the fact that a
    previously-conditional relationship's evidence has strengthened into
    the independently-measurable range. `relationship_name` is a free-text
    label supplied by the caller for their own bookkeeping (e.g.
    "sub_law_d_given_sub_law_c") -- this function does not interpret it and
    does not assign it any depth number or semantic category."""
    became_independent = (not before_evidence.all_criteria_met) and after_evidence.all_criteria_met
    return {
        "relationship_name": relationship_name,
        "before": before_evidence.to_dict(),
        "after": after_evidence.to_dict(),
        "became_independent_this_observation": became_independent,
        "note": (
            "This module records a behavior change only. It assigns no "
            "depth number, no semantic label, and makes no runtime-routing "
            "decision. Interpretation, naming, and any decision to act on "
            "this record belong to a separate, explicitly-authorized pass."
        ),
    }
