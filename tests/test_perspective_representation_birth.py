#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_perspective_representation_birth.py -- Primitive Perspective directive,
Sections 14, 15 and 16.

  K  representation-birth timing: perspective profiles are attached DURING
     representation formation, before the joint link/resonance pass -- not
     stamped afterwards as decorative metadata
  I  independent representational support: P0-only, P1-only and both
     survive persistence and rehydration
  15 profiles are per lineage, never averaged, never a sixth axis
  16 resolution evidence carries a perspective lineage; a lineage resolves
     fields independently, and nothing is copied or inferred across lineages

Built against real classes: Crystal, CrystalProcessingSystem, ConceptSignal,
RepresentationalResolutionEngine, ConstraintGenealogyLogger.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from aurora_dimensional_systems import (
    ConceptSignal,
    Crystal,
    CrystalProcessingSystem,
    EvolutionTracker,
)
from aurora_internal.constraint_genealogy import ConstraintGenealogyLogger, GenealogyConfig
from aurora_ivm import ExistenceMode
from aurora_representational_address import RepresentationalRef
from aurora_representational_resolution import (
    RepresentationalResolutionEngine,
    perspective_scope,
)

try:
    from aurora_internal.aurora_primitive_perspective import (
        LINEAGE_P0, LINEAGE_P1, PerspectivePair, PerspectiveProjection,
    )
except ImportError:     # the app build flattens modules into one directory
    from aurora_primitive_perspective import (      # type: ignore
        LINEAGE_P0, LINEAGE_P1, PerspectivePair, PerspectiveProjection,
    )

AXES = {"X", "T", "N", "B", "A"}


class _Envelope:
    def __init__(self, data="a live occurrence", mode=ExistenceMode.AGENTIC):
        self.data = data
        self.data_type = "text"
        self.node_id = "node_1"
        self.mode = mode
        self.position = None


def _projection(lineage, axes, occurrence="occ_1", provenance=("I_IS",)):
    return PerspectiveProjection(
        lineage_id=lineage, occurrence_id=occurrence, source_mode="AGENTIC",
        predicate_activation={p: 0.1 for p in provenance},
        axis_projection=dict(axes), depth_distribution={"SURFACE": 1.0},
        continuity_indicators={}, accessibility_signature=f"sig_{lineage}",
        coherence=0.5, maturity=0.1, provenance=tuple(provenance))


def _pair(p0_axes, p1_axes, occurrence="occ_1"):
    return PerspectivePair(occurrence_id=occurrence,
                           p0=_projection(LINEAGE_P0, p0_axes, occurrence),
                           p1=_projection(LINEAGE_P1, p1_axes, occurrence))


def _dps():
    return CrystalProcessingSystem(EvolutionTracker())


def _signals(*concepts):
    return [ConceptSignal(concept=c, role="topic", confidence=0.9,
                          constraint_weights={"X": 0.5}) for c in concepts]


# ---------------------------------------------------------------------------
# K. Representation-birth timing
# ---------------------------------------------------------------------------

def test_profiles_exist_before_joint_linking_begins():
    """Spy on the Pass 2 joint step: every crystal it touches must ALREADY
    carry this occurrence's perspective evidence when linking starts."""
    dps = _dps()
    seen = {}
    original = dps._update_crystal_links

    def _spy(crystal_id):
        crystal = dps.crystals[crystal_id]
        seen[crystal_id] = {k: dict(v) for k, v in crystal.perspective_profiles.items()}
        return original(crystal_id)

    dps._update_crystal_links = _spy
    dps.process_concepts(_Envelope(), _signals("tide", "harbour"),
                         perspective_pair=_pair({"X": 0.8}, {"A": -0.3}))
    assert seen, "joint linking never ran"
    for crystal_id, profiles in seen.items():
        assert set(profiles) == {LINEAGE_P0, LINEAGE_P1}, crystal_id


def test_raw_path_also_conditions_birth_before_linking():
    dps = _dps()
    seen = []
    original = dps._update_crystal_links

    def _spy(crystal_id):
        seen.append(dps.crystals[crystal_id].perspective_support())
        return original(crystal_id)

    dps._update_crystal_links = _spy
    dps.process(_Envelope("no signals at all"),
                perspective_pair=_pair({"T": 0.4}, {"B": 0.2}))
    assert seen and seen[0] == [LINEAGE_P0, LINEAGE_P1]


def test_process_synthesis_hands_the_pair_in_rather_than_stamping_after():
    import inspect

    import aurora_dimensional_systems as ds
    source = inspect.getsource(ds.DimensionalSystems.process_synthesis)
    handed_in = source.index("perspective_pair=perspective_pair")
    stamped = source.index("constraint_context: Dict[str, Any] = {")
    assert handed_in < stamped, "perspective must reach birth before the stamp"


def test_one_occurrence_is_one_piece_of_evidence_per_crystal():
    """Several signals landing on one crystal are still one occurrence."""
    dps = _dps()
    dps.process_concepts(_Envelope(), _signals("tide", "tide", "tide"),
                         perspective_pair=_pair({"X": 0.8}, {"A": -0.3}))
    crystal = dps.get_crystal("tide")
    assert crystal.perspective_profiles[LINEAGE_P0]["evidence_count"] == 1
    assert crystal.perspective_profiles[LINEAGE_P1]["evidence_count"] == 1


def test_no_pair_means_no_profiles_and_no_change_in_behaviour():
    dps = _dps()
    dps.process_concepts(_Envelope(), _signals("tide"))
    assert dps.get_crystal("tide").perspective_profiles == {}


# ---------------------------------------------------------------------------
# I. Independent support -- all cases legitimate, all survive persistence
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("p0,p1,expected", [
    ({"X": 0.8}, {"X": 0.0}, [LINEAGE_P0]),
    ({"X": 0.0}, {"A": -0.4}, [LINEAGE_P1]),
    ({"X": 0.8}, {"A": -0.4}, [LINEAGE_P0, LINEAGE_P1]),
])
def test_support_cases_survive_a_persistence_round_trip(p0, p1, expected):
    crystal = Crystal(crystal_id="c1", concept="tide")
    supported = crystal.absorb_perspective_pair(_pair(p0, p1))
    assert sorted(supported) == expected
    rehydrated = Crystal.from_dict(json.loads(json.dumps(crystal.to_dict())))
    assert rehydrated.perspective_support() == expected
    assert rehydrated.perspective_profiles == crystal.perspective_profiles


def test_different_structures_from_each_lineage_are_both_kept():
    crystal = Crystal(crystal_id="c1", concept="tide")
    crystal.absorb_perspective_pair(_pair({"X": 0.9, "T": 0.2}, {"A": -0.5, "B": 0.1}))
    assert set(crystal.perspective_profiles[LINEAGE_P0]["axis_signature"]) == {"X", "T"}
    assert set(crystal.perspective_profiles[LINEAGE_P1]["axis_signature"]) == {"A", "B"}


def test_an_old_crystal_without_profiles_still_loads():
    legacy = Crystal(crystal_id="c0", concept="old").to_dict()
    legacy.pop("perspective_profiles")
    assert Crystal.from_dict(legacy).perspective_profiles == {}


# ---------------------------------------------------------------------------
# 15. Per lineage, never averaged, never an axis
# ---------------------------------------------------------------------------

def test_profiles_are_never_averaged_together():
    crystal = Crystal(crystal_id="c1", concept="tide")
    for index in range(10):
        crystal.absorb_perspective_pair(_pair({"X": 0.9}, {"X": -0.9},
                                              occurrence=f"o{index}"))
    p0 = crystal.perspective_profiles[LINEAGE_P0]["axis_signature"]["X"]
    p1 = crystal.perspective_profiles[LINEAGE_P1]["axis_signature"]["X"]
    assert p0 > 0.8 and p1 < -0.8, "lineages drifted toward a shared mean"
    assert set(crystal.perspective_profiles) == {LINEAGE_P0, LINEAGE_P1}


def test_one_lineage_evidence_never_touches_the_other_profile():
    crystal = Crystal(crystal_id="c1", concept="tide")
    crystal.absorb_perspective_pair(_pair({"X": 0.5}, {"A": 0.5}))
    before = json.dumps(crystal.perspective_profiles[LINEAGE_P1], sort_keys=True)
    crystal.absorb_perspective(_projection(LINEAGE_P0, {"X": -0.9, "N": 0.4}, "o2"))
    assert json.dumps(crystal.perspective_profiles[LINEAGE_P1], sort_keys=True) == before


def test_signed_values_stay_signed():
    crystal = Crystal(crystal_id="c1", concept="tide")
    crystal.absorb_perspective_pair(_pair({"B": -0.6}, {"A": -0.2}))
    assert crystal.perspective_profiles[LINEAGE_P0]["axis_signature"]["B"] < 0
    assert crystal.perspective_profiles[LINEAGE_P1]["axis_signature"]["A"] < 0


def test_lineage_is_a_key_never_an_axis_or_dimension():
    crystal = Crystal(crystal_id="c1", concept="tide")
    crystal.absorb_perspective_pair(_pair({"X": 0.5}, {"A": 0.5}))
    for profile in crystal.perspective_profiles.values():
        assert set(profile["axis_signature"]) <= AXES
    assert crystal.constraint_signature is None, \
        "perspective must not write into the collapsed signature"


# ---------------------------------------------------------------------------
# 16. Resolution evidence carries a perspective lineage
# ---------------------------------------------------------------------------

def _engine(tmp_path, name="persp"):
    genealogy = ConstraintGenealogyLogger(name, config=GenealogyConfig(),
                                          output_dir=str(tmp_path / name / "g"))
    return RepresentationalResolutionEngine(genealogy, state_dir=str(tmp_path / name / "s"))


def _resolve(engine, ref, field, value, lineage):
    return engine.resolve_field(
        ref, field, value, evidence={}, discrepancy_before=0.9, discrepancy_after=0.3,
        pressure_before=0.5, pressure_after=0.0, cost=1.0, _allow_direct_call=True,
        context_scope=perspective_scope(lineage), perspective_lineage=lineage)


def test_a_field_one_lineage_resolves_stays_unresolved_for_the_other(tmp_path):
    engine = _engine(tmp_path)
    ref = RepresentationalRef.for_c1("T", "MAGNITUDE", "B")
    _resolve(engine, ref, "col_law_c", "N", LINEAGE_P0)
    assert engine.lineage_resolution(ref, LINEAGE_P0).col_law_c == "N"
    assert engine.lineage_resolution(ref, LINEAGE_P1).col_law_c is None


def test_the_lineages_may_resolve_different_fields(tmp_path):
    engine = _engine(tmp_path)
    ref = RepresentationalRef.for_c1("T", "MAGNITUDE", "B")
    _resolve(engine, ref, "col_law_c", "N", LINEAGE_P0)
    _resolve(engine, ref, "col_law_d", "COST", LINEAGE_P1)
    p0 = engine.lineage_resolution(ref, LINEAGE_P0)
    p1 = engine.lineage_resolution(ref, LINEAGE_P1)
    assert (p0.col_law_c, p0.col_law_d) == ("N", None)
    assert (p1.col_law_c, p1.col_law_d) == (None, "COST")


def test_lineage_view_does_not_fall_back_to_global(tmp_path):
    """A strictly lineage-local view: a field earned without perspective is
    not claimed by either lineage."""
    engine = _engine(tmp_path)
    ref = RepresentationalRef.for_c1("T", "MAGNITUDE", "B")
    engine.resolve_field(ref, "col_law_c", "N", evidence={}, discrepancy_before=0.9,
                         discrepancy_after=0.3, pressure_before=0.5,
                         pressure_after=0.0, cost=1.0, _allow_direct_call=True)
    assert engine.current_resolution(ref).col_law_c == "N"        # unchanged
    assert engine.lineage_resolution(ref, LINEAGE_P0).col_law_c is None
    assert engine.lineage_resolution(ref, LINEAGE_P1).col_law_c is None


def test_existing_scoped_callers_are_unaffected(tmp_path):
    engine = _engine(tmp_path)
    ref = RepresentationalRef.for_c1("T", "MAGNITUDE", "B")
    engine.resolve_field(ref, "col_law_c", "N", evidence={}, discrepancy_before=0.9,
                         discrepancy_after=0.3, pressure_before=0.5,
                         pressure_after=0.0, cost=1.0, _allow_direct_call=True,
                         context_scope="territory:shore")
    assert engine.current_resolution(ref, context_scope="territory:shore").col_law_c == "N"


def test_genealogy_records_which_lineage_earned_a_field(tmp_path):
    engine = _engine(tmp_path)
    ref = RepresentationalRef.for_c1("T", "MAGNITUDE", "B")
    _resolve(engine, ref, "col_law_c", "N", LINEAGE_P1)
    record = engine.genealogy_for(ref)[-1]
    assert record["perspective_lineage"] == LINEAGE_P1
    assert record["context_scope"] == perspective_scope(LINEAGE_P1)


def test_lineage_resolution_survives_rehydration(tmp_path):
    engine = _engine(tmp_path)
    ref = RepresentationalRef.for_c1("T", "MAGNITUDE", "B")
    _resolve(engine, ref, "col_law_c", "N", LINEAGE_P0)
    genealogy = ConstraintGenealogyLogger("persp", config=GenealogyConfig(),
                                          output_dir=str(tmp_path / "persp" / "g"))
    reopened = RepresentationalResolutionEngine(genealogy,
                                                state_dir=str(tmp_path / "persp" / "s"))
    assert reopened.lineage_resolution(ref, LINEAGE_P0).col_law_c == "N"
    assert reopened.lineage_resolution(ref, LINEAGE_P1).col_law_c is None


def test_a_context_scope_composes_with_lineage_rather_than_being_replaced():
    assert perspective_scope(LINEAGE_P0) == "perspective:P0"
    assert perspective_scope(LINEAGE_P0, "territory:shore") == \
        "territory:shore#perspective:P0"


def test_the_sealed_production_path_stays_sealed(tmp_path):
    engine = _engine(tmp_path)
    ref = RepresentationalRef.for_c1("T", "MAGNITUDE", "B")
    with pytest.raises(PermissionError):
        engine.resolve_field(ref, "col_law_c", "N", evidence={}, discrepancy_before=0.9,
                             discrepancy_after=0.3, pressure_before=0.5,
                             pressure_after=0.0, cost=1.0,
                             perspective_lineage=LINEAGE_P0)


# ---------------------------------------------------------------------------
# 22. The directive's canary -- a depth-law CONSISTENCY check, not emergence
# ---------------------------------------------------------------------------
#
# Aurora's recursion architecture already maps SURFACE->X, SHALLOW->T,
# MODERATE->N, DEEP->B, CORE->A, while REACT_GAIN strongly favours SURFACE and
# ALIGN_GAIN strongly favours CORE.  So in the canary occurrence, "P0
# concentrates in X/T and P1 in A/B" is largely GUARANTEED by those gain
# laws.  It shows the layer is consistent with Aurora's physics; it is NOT
# evidence that the lineages discovered X/T versus A/B.  The evidence for
# genuine informational non-equivalence is the access-fence and window tests,
# and the equal-depth test below, where the gain laws are neutralised.

def _canary_pair(tmp_path, *, level_override=None, resonances=None,
                 polarity=None, phases=None):
    from aurora_i_state_beings import BeingResponse
    from aurora_ivm import RecursionLevel
    try:
        from aurora_internal.aurora_primitive_perspective import PrimitivePerspectiveEngine
    except ImportError:
        from aurora_primitive_perspective import PrimitivePerspectiveEngine
    rows = [("I_IS", "X", RecursionLevel.SURFACE, 0.682),
            ("I_CAN", "T", RecursionLevel.SHALLOW, 0.430),
            ("I_DO", "N", RecursionLevel.MODERATE, 0.070),
            ("I_SAW", "B", RecursionLevel.DEEP, -0.341),
            ("I_DID", "A", RecursionLevel.CORE, -0.636)]
    responses = {
        p: BeingResponse(predicate=p, axis=a, polarity="positive",
                         input_mode=ExistenceMode.AGENTIC, required_mode=ExistenceMode.AGENTIC,
                         recursion_level=level_override or lvl, constraint_axis=a,
                         silent=False, resonance=(resonances or {}).get(a, 0.4),
                         constraint_displacement=d)
        for p, a, lvl, d in rows}
    observations = {p: type("O", (), {"silent": False, "resonance": r.resonance,
                                      "constraint_displacement": r.constraint_displacement})()
                    for p, r in responses.items()}
    snapshot = PrimitivePerspectiveEngine.freeze(
        _Envelope(), observations,
        lattice_axes={a: {"phase": (phases or {}).get(a, 0.3), "inertia": 1.0} for a in AXES},
        global_polarity=polarity or {a: 0.0 for a in AXES},
        being_continuity={p: {"coherence": 1.0} for p in responses},
        collective_continuity={}, occurrence_id="canary")
    return PrimitivePerspectiveEngine(state_dir=str(tmp_path)).form(snapshot, responses)


def _shares(axes):
    total = sum(abs(v) for v in axes.values())
    return {k: abs(v) / total for k, v in axes.items()}


def _rank(axes):
    shares = _shares(axes)
    return sorted(shares, key=shares.get, reverse=True)


def test_canary_is_consistent_with_the_depth_gain_laws(tmp_path):
    """Consistency only: the canary's axis ranking is what the gain tables
    predict.  Asserted AGAINST the tables themselves, so this reads as the
    depth law being honoured, never as a discovery."""
    from aurora_ivm import ALIGN_GAIN, REACT_GAIN, RecursionLevel
    level_of = {"X": RecursionLevel.SURFACE, "T": RecursionLevel.SHALLOW,
                "N": RecursionLevel.MODERATE, "B": RecursionLevel.DEEP,
                "A": RecursionLevel.CORE}
    pair = _canary_pair(tmp_path / "c")
    by_react = sorted(level_of, key=lambda a: REACT_GAIN[level_of[a]], reverse=True)
    by_align = sorted(level_of, key=lambda a: ALIGN_GAIN[level_of[a]], reverse=True)
    assert _rank(pair.p0.axis_projection)[:2] == by_react[:2] == ["X", "T"]
    assert _rank(pair.p1.axis_projection)[:2] == by_align[:2] == ["A", "B"]


def test_at_equal_depth_the_canary_split_is_not_intrinsic(tmp_path):
    """Neutralise the gain laws (every response at one depth) and the X/T
    versus A/B split is no longer imposed: give A the strongest local
    reaction and P0's leading axis follows it to A."""
    from aurora_ivm import RecursionLevel
    pair = _canary_pair(tmp_path / "e", level_override=RecursionLevel.MODERATE,
                        resonances={"X": 0.1, "T": 0.1, "N": 0.1, "B": 0.1, "A": 0.9})
    assert _rank(pair.p0.axis_projection)[0] == "A"


def test_at_equal_depth_differences_come_only_from_access(tmp_path):
    """With every gain equal, local state moves only P0 and whole-subject
    orientation moves only P1 -- the informational distinction on its own."""
    from aurora_ivm import RecursionLevel
    moderate = RecursionLevel.MODERATE
    base = _canary_pair(tmp_path / "b", level_override=moderate)
    local = _canary_pair(tmp_path / "l", level_override=moderate,
                         phases={"B": 4.2})
    global_ = _canary_pair(tmp_path / "g", level_override=moderate,
                           polarity={"X": 0.0, "T": 0.0, "N": 0.0, "B": 0.9, "A": 0.0})
    assert local.p0.axis_projection != base.p0.axis_projection
    assert local.p1.axis_projection == base.p1.axis_projection
    assert global_.p1.axis_projection != base.p1.axis_projection
    assert global_.p0.axis_projection == base.p0.axis_projection


# ---------------------------------------------------------------------------
# 20. Birth retention diagnostic
# ---------------------------------------------------------------------------

def test_dps_reports_which_lineages_each_crystal_retained():
    dps = _dps()
    result = dps.process_concepts(_Envelope(), _signals("tide", "harbour"),
                                  perspective_pair=_pair({"X": 0.8}, {"A": 0.0}))
    for info in result["crystals"]:
        assert info["perspective_support"] == [LINEAGE_P0]


def test_retention_report_is_read_only():
    from aurora_dimensional_systems import DimensionalSystems
    report = DimensionalSystems._perspective_retention(
        type("S", (), {"dps": None})(), _pair({"X": 0.8}, {"A": 0.3}),
        {"crystals": [{"crystal_id": "c1", "perspective_support": ["P0", "P1"]}]})
    assert report == {"occurrence_id": "occ_1", "crystals": {"c1": ["P0", "P1"]},
                      "retained": {"P0": True, "P1": True}, "born": True}
