# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
CERS Stage 3 (the originally-scoped step that got skipped in Phases 1-3):
cers_converge() itself -- not just the downstream tensor-trace recording --
now consults real coordinate history. detect_conflicts() can only ever
compare live crest clusters against each other; it has no memory of what's
normal at a specific pressure coordinate. GeometryDeviation is the distinct
signal that catches "this exact geometry has real precedent and just broke
sharply," which is structurally invisible to the classic conflict check.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aurora_internal.dual_strata.cers_regulator import (
    cers_converge,
    PotentialTracker,
    GEOMETRY_DEVIATION_THRESHOLD,
)
from aurora_internal.dual_strata.cers_potential_trial import PotentialTrialBoard
from aurora_internal.dual_strata.crest import Crest


def _steady_crests():
    # None of these form an opposed-cluster pair (see _OPPOSED_CLUSTER_PAIRS) --
    # a clean baseline with zero classic conflict.
    return (
        Crest(label="steady", intensity=0.5, axis="N"),
        Crest(label="attend", intensity=0.3, axis="X"),
    )


def test_new_coordinate_never_produces_geometry_deviation():
    """A coordinate with no history can't 'deviate' from history it
    doesn't have -- is_new must hard-gate this regardless of distortion."""
    _, verdict = cers_converge(
        _steady_crests(), PotentialTracker(), PotentialTrialBoard(),
        geometry_coord_id="MANIFOLD:N:...", geometry_axis="N",
        geometry_distortion_normalized=0.95, geometry_is_new=True,
    )
    assert verdict.geometry_deviation is None
    assert verdict.permitted is True


def test_no_coordinate_resolved_never_produces_geometry_deviation():
    _, verdict = cers_converge(
        _steady_crests(), PotentialTracker(), PotentialTrialBoard(),
        geometry_coord_id=None, geometry_distortion_normalized=0.95, geometry_is_new=False,
    )
    assert verdict.geometry_deviation is None


def test_established_coordinate_below_threshold_is_not_flagged():
    _, verdict = cers_converge(
        _steady_crests(), PotentialTracker(), PotentialTrialBoard(),
        geometry_coord_id="MANIFOLD:N:...", geometry_axis="N",
        geometry_distortion_normalized=GEOMETRY_DEVIATION_THRESHOLD - 0.05,
        geometry_is_new=False,
    )
    assert verdict.geometry_deviation is None
    assert verdict.permitted is True


def test_established_coordinate_sharp_deviation_with_no_classic_conflict():
    """The real new case: nothing in sub_crests looks like a classic
    opposed-cluster conflict, but the coordinate's own history broke
    sharply -- CERS's OWN verdict must catch this, not just record it
    afterward for the tensor pass to notice."""
    cers_crest, verdict = cers_converge(
        _steady_crests(), PotentialTracker(), PotentialTrialBoard(),
        geometry_coord_id="MANIFOLD:N:NC[B:MAGNITUDE]xNC[T:DIFFERENCE]", geometry_axis="N",
        geometry_distortion_normalized=0.9, geometry_is_new=False,
    )
    assert verdict.permitted is False
    assert verdict.geometry_deviation is not None
    assert verdict.geometry_deviation.coord_id == "MANIFOLD:N:NC[B:MAGNITUDE]xNC[T:DIFFERENCE]"
    assert verdict.geometry_deviation.severity == 0.9
    assert verdict.intervention_label == "pattern_deviation"
    assert verdict.cers_label == "pattern_deviation"
    assert verdict.agrees_with_legacy is False
    assert cers_crest.label == "pattern_deviation"
    assert cers_crest.axis == "N"
    assert cers_crest.intensity == 0.9
    assert verdict.conflicts == [], "no classic conflict should be fabricated"


def test_classic_conflict_still_takes_intervention_precedence_but_keeps_geometry_context():
    """Opposed clusters: comfort vs urgency. When BOTH a classic conflict
    and a geometry deviation are present, the existing conflict-selection
    behavior (unresolved_conflict wins as intervention_label) must be
    unchanged -- geometry_deviation rides along as additional context,
    it doesn't silently take over."""
    crests = (
        Crest(label="comfort", intensity=0.6, axis="B"),
        Crest(label="urgency", intensity=0.55, axis="A"),
    )
    cers_crest, verdict = cers_converge(
        crests, PotentialTracker(), PotentialTrialBoard(),
        geometry_coord_id="MANIFOLD:A:...", geometry_axis="A",
        geometry_distortion_normalized=0.9, geometry_is_new=False,
    )
    assert verdict.permitted is False
    assert verdict.conflicts, "classic conflict must still be detected"
    assert verdict.intervention_label == "unresolved_conflict"
    assert cers_crest.label == "unresolved_conflict"
    # Geometry context still present, just not overriding the intervention choice.
    assert verdict.geometry_deviation is not None
    assert verdict.geometry_deviation.severity == 0.9


def test_geometry_deviation_serializes_to_dict():
    _, verdict = cers_converge(
        _steady_crests(), PotentialTracker(), PotentialTrialBoard(),
        geometry_coord_id="MANIFOLD:N:...", geometry_axis="N",
        geometry_distortion_normalized=0.7, geometry_is_new=False,
    )
    d = verdict.to_dict()
    assert d["geometry_deviation"] == {
        "coord_id": "MANIFOLD:N:...", "axis": "N", "distortion": 0.7, "severity": 0.7,
    }


def test_geometry_deviation_none_serializes_to_none():
    _, verdict = cers_converge(_steady_crests(), PotentialTracker(), PotentialTrialBoard())
    assert verdict.to_dict()["geometry_deviation"] is None


def test_default_call_shape_unaffected_backward_compatible():
    """No geometry_* args at all -- must behave exactly as before Stage 3."""
    cers_crest, verdict = cers_converge(_steady_crests(), PotentialTracker(), PotentialTrialBoard())
    assert verdict.permitted is True
    assert verdict.geometry_deviation is None
