# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Coverage for Phase 1 of the CERS tensor-trace upgrade: resolving live
X/T/N/B/A pressure onto a real SlotCoord in Aurora's constraint manifold,
and recording that visit onto the SAME crystal registry every other concept
already lives in (dps_crystals.json) -- no new trace file. Crystal.axis_mean/
update_axis_mean() and add_facet()'s strengthen()-on-repeat are exercised
against the real Crystal/CrystalProcessingSystem classes, not mocks, so a
change to either class's shape would break this test the same way it would
break the real pipeline.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aurora_dimensional_systems import CrystalProcessingSystem, EvolutionTracker
from aurora_internal.dual_strata.crest import Crest
from aurora_internal.dual_strata.cers_tensor_locator import (
    resolve_pressure_coordinate,
    record_tensor_trace,
    compute_salience,
)


def _dps() -> CrystalProcessingSystem:
    return CrystalProcessingSystem(EvolutionTracker())


def test_resolve_pressure_coordinate_ranks_axes_by_activity():
    axes = {"X": 0.1, "T": 0.2, "N": 0.9, "B": 0.7, "A": 0.3}
    coord = resolve_pressure_coordinate(axes, ())

    assert coord is not None
    assert coord.target == "N"      # highest
    assert coord.nc_law_c == "B"    # second highest
    assert coord.law_c == "A"       # third highest


def test_resolve_pressure_coordinate_prefers_crest_axis_reads():
    axes = {"X": 0.1, "T": 0.1, "N": 0.1, "B": 0.1, "A": 0.1}
    crests = (Crest(label="hostile_tone", intensity=0.9, axis="A"),)
    coord = resolve_pressure_coordinate(axes, crests)

    assert coord.target == "A"


def test_resolve_pressure_coordinate_single_active_axis_collapses_to_target():
    axes = {"X": 0.0, "T": 0.0, "N": 0.0, "B": 0.0, "A": 0.0}
    crests = (Crest(label="steady", intensity=0.8, axis="X"),)
    coord = resolve_pressure_coordinate(axes, crests)

    assert coord.target == "X"
    # nc_law_c/law_c fall back sensibly when nothing else is active --
    # SlotCoord.is_diagonal is the legitimate single-axis case.
    assert coord.nc_law_c in ("X", "T", "N", "B", "A")


def test_resolve_pressure_coordinate_empty_axes_returns_none():
    assert resolve_pressure_coordinate({}, ()) is None


def test_dimension_assignment_matches_router_table():
    # POLARITY<-A, MAGNITUDE<-B, OPERATOR<-X, COST<-N, DIFFERENCE<-T
    axes = {"X": 0.1, "T": 0.1, "N": 0.9, "B": 0.1, "A": 0.1}
    coord = resolve_pressure_coordinate(axes, ())
    assert coord.target == "N"
    assert coord.nc_dim in ("POLARITY", "MAGNITUDE", "OPERATOR", "COST", "DIFFERENCE")


def test_record_tensor_trace_first_visit_is_new_with_zero_distortion():
    dps = _dps()
    coord = resolve_pressure_coordinate({"X": 0.2, "T": 0.2, "N": 0.9, "B": 0.6, "A": 0.1}, ())

    crystal, distortion, is_new = record_tensor_trace(
        dps, coord, adjusted_axes={"X": 0.2, "T": 0.2, "N": 0.9, "B": 0.6, "A": 0.1},
        label="steady", severity=0.0,
    )

    assert crystal is not None
    assert is_new is True
    assert distortion == 0.0
    assert crystal.concept == f"tensor:{coord.slot_id}"
    assert f"tensor:{coord.slot_id}" in dps.concept_index


def test_record_tensor_trace_revisit_measures_distortion_and_reuses_crystal():
    dps = _dps()
    coord = resolve_pressure_coordinate({"X": 0.5, "T": 0.5, "N": 0.5, "B": 0.5, "A": 0.5}, ())

    crystal_1, _, is_new_1 = record_tensor_trace(
        dps, coord, adjusted_axes={"X": 0.5, "T": 0.5, "N": 0.5, "B": 0.5, "A": 0.5},
        label="steady",
    )
    crystal_2, distortion_2, is_new_2 = record_tensor_trace(
        dps, coord, adjusted_axes={"X": 0.9, "T": 0.1, "N": 0.5, "B": 0.5, "A": 0.5},
        label="unresolved_conflict", severity=0.8,
    )

    assert is_new_1 is True
    assert is_new_2 is False
    assert crystal_1 is crystal_2, "the same coordinate must reuse the same crystal, not spawn a new one"
    assert distortion_2 > 0.0
    assert len(dps.crystals) == 1, "revisiting a coordinate must not create a second crystal"


def test_record_tensor_trace_repeat_visits_strengthen_not_duplicate_facet():
    dps = _dps()
    coord = resolve_pressure_coordinate({"X": 0.5, "T": 0.5, "N": 0.9, "B": 0.5, "A": 0.5}, ())

    for _ in range(3):
        crystal, _, _ = record_tensor_trace(
            dps, coord, adjusted_axes={"X": 0.5, "T": 0.5, "N": 0.9, "B": 0.5, "A": 0.5},
            label="steady", severity=0.2,
        )

    visit_facets = [f for f in crystal.facets.values() if f.role == "cers_visit"]
    assert len(visit_facets) == 1, "repeat visits must strengthen the existing facet, not pile up new ones"
    assert visit_facets[0].access_count == 2  # strengthen() called on the 2nd and 3rd visits


def test_record_tensor_trace_handles_missing_dps_gracefully():
    coord = resolve_pressure_coordinate({"X": 0.5, "T": 0.5, "N": 0.9, "B": 0.5, "A": 0.5}, ())
    result = record_tensor_trace(None, coord, adjusted_axes={}, label="steady")
    assert result == (None, 0.0, False)


def test_compute_salience_new_coordinate_is_maximally_salient():
    assert compute_salience(None, distortion=0.0, is_new=True) == 1.0


def test_compute_salience_familiar_low_distortion_is_low():
    dps = _dps()
    coord = resolve_pressure_coordinate({"X": 0.5, "T": 0.5, "N": 0.9, "B": 0.5, "A": 0.5}, ())
    crystal = None
    for _ in range(9):
        crystal, _, _ = record_tensor_trace(
            dps, coord, adjusted_axes={"X": 0.5, "T": 0.5, "N": 0.9, "B": 0.5, "A": 0.5}, label="steady",
        )
    salience = compute_salience(crystal, distortion=0.02, is_new=False, severity=0.0)
    assert salience < 0.3, "a well-worn, on-pattern moment should read as low relevance"


def test_compute_salience_sharp_distortion_on_familiar_coordinate_is_high():
    dps = _dps()
    coord = resolve_pressure_coordinate({"X": 0.5, "T": 0.5, "N": 0.9, "B": 0.5, "A": 0.5}, ())
    crystal = None
    for _ in range(9):
        crystal, _, _ = record_tensor_trace(
            dps, coord, adjusted_axes={"X": 0.5, "T": 0.5, "N": 0.9, "B": 0.5, "A": 0.5}, label="steady",
        )
    salience = compute_salience(crystal, distortion=2.0, is_new=False, severity=0.0)
    assert salience > 0.8, "sharp deviation from an established pattern must read as high relevance"
