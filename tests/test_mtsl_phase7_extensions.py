"""
tests/test_mtsl_phase7_extensions.py
=======================================
MTSL Phase 7 (2026-07-13): compact topology/semantic-variant refs on
ConstraintLink/AbilityProfile (genealogy), and topology-fingerprint
similarity recall on SediMemory (spec section 17).
"""
from aurora_internal.constraint_genealogy import AbilityProfile, ConstraintLink
from aurora_sedimemory import ConstraintVector, MemoryEvent, SediMemory
from aurora_sedimemory import topology_fingerprint_similarity
from aurora_warp_protocol import CoverageGap, WarpGenerator


# ---- ConstraintLink / AbilityProfile: additive, byte-identical when absent ----

def _link(**overrides):
    base = dict(
        id="L:test", parents=["X:FOO"], depth=1, created_at_tick=5,
        count=3, mean_relief={"X": 0.1}, mean_cost={"X": 0.05},
        mean_x_risk=0.02, stdev_relief={"X": 0.01}, dominant_relief_axis="X",
    )
    base.update(overrides)
    return ConstraintLink(**base)


def _ability(**overrides):
    base = dict(id="X:TEST", axis="X", requires=("X",), cost={"X": 0.1}, risk={"X": 0.0}, effect_tags=("t",))
    base.update(overrides)
    return AbilityProfile(**base)


def test_constraint_link_refs_default_to_none():
    link = _link()
    assert link.topology_id is None
    assert link.semantic_variant_id is None


def test_constraint_link_to_dict_omits_refs_when_absent():
    d = _link().to_dict()
    assert "topology_id" not in d
    assert "semantic_variant_id" not in d


def test_constraint_link_to_dict_includes_refs_when_present():
    d = _link(topology_id="TS:X:v1", semantic_variant_id="sv1").to_dict()
    assert d["topology_id"] == "TS:X:v1"
    assert d["semantic_variant_id"] == "sv1"


def test_ability_profile_refs_default_to_none():
    ab = _ability()
    assert ab.topology_id is None
    assert ab.semantic_variant_id is None


def test_ability_profile_to_dict_omits_refs_when_absent():
    d = _ability().to_dict()
    assert "topology_id" not in d
    assert "semantic_variant_id" not in d


def test_ability_profile_to_dict_includes_refs_when_present():
    d = _ability(topology_id="TS:X:v1", semantic_variant_id="sv1").to_dict()
    assert d["topology_id"] == "TS:X:v1"
    assert d["semantic_variant_id"] == "sv1"


def test_ability_profile_still_frozen():
    ab = _ability()
    try:
        ab.topology_id = "should not work"
        assert False, "AbilityProfile should still be frozen"
    except Exception:
        pass


# ---- SediMemory: topology-fingerprint similarity + recall_topology ----

def _fp(fingerprint_id="TS:ABN:ABN4:cf4:v1", axes_key="ABN"):
    return {"schema_version": 1, "axes_key": axes_key, "loops_key": "ABN4", "bands_key": "cf4", "fingerprint_id": fingerprint_id}


def test_similarity_exact_match_is_1():
    fp = _fp()
    assert topology_fingerprint_similarity(fp, dict(fp)) == 1.0


def test_similarity_empty_dicts_are_zero():
    assert topology_fingerprint_similarity({}, _fp()) == 0.0
    assert topology_fingerprint_similarity(_fp(), {}) == 0.0
    assert topology_fingerprint_similarity({}, {}) == 0.0


def test_similarity_partial_axes_overlap_is_below_exact_match():
    a = _fp(fingerprint_id="TS:ABN:x:cf4:v1", axes_key="ABN")
    b = _fp(fingerprint_id="TS:ABX:y:cf2:v1", axes_key="ABX")
    sim = topology_fingerprint_similarity(a, b)
    assert 0.0 < sim < 1.0


def test_similarity_disjoint_axes_is_zero():
    a = _fp(fingerprint_id="TS:AB:x:cf4:v1", axes_key="AB")
    b = _fp(fingerprint_id="TS:XT:y:cf2:v1", axes_key="XT")
    assert topology_fingerprint_similarity(a, b) == 0.0


def _cv():
    return ConstraintVector(X=0.5, T=0.5, N=0.5, B=0.5, A=0.5)


def test_memory_event_topology_fingerprint_defaults_empty():
    event = MemoryEvent.create(content={"k": "v"}, constraint_vector=_cv())
    assert event.topology_fingerprint == {}


def test_deposited_fragments_carry_the_event_fingerprint():
    sed = SediMemory()
    fp = _fp()
    event = MemoryEvent.create(content={"k": "v"}, constraint_vector=_cv())
    event.topology_fingerprint = dict(fp)
    n = sed._ingest(event)
    assert n > 0
    frags = sed.recall_event(event.event_id)
    assert frags
    assert all(f.topology_fingerprint.get("fingerprint_id") == fp["fingerprint_id"] for f in frags)


def test_recall_topology_finds_exact_match_only():
    sed = SediMemory()
    fp = _fp()
    unrelated_fp = _fp(fingerprint_id="TS:XT:z:cf0:v1", axes_key="XT")

    event_a = MemoryEvent.create(content={"k": "a"}, constraint_vector=_cv())
    event_a.topology_fingerprint = dict(fp)
    sed._ingest(event_a)

    event_b = MemoryEvent.create(content={"k": "b"}, constraint_vector=_cv())
    event_b.topology_fingerprint = dict(unrelated_fp)
    sed._ingest(event_b)

    event_c = MemoryEvent.create(content={"k": "c"}, constraint_vector=_cv())  # no fingerprint at all
    sed._ingest(event_c)

    results = sed.recall_topology(fp, min_similarity=0.99)
    assert results
    assert all(r.event_id == event_a.event_id for r in results)


def test_recall_topology_empty_query_returns_nothing():
    sed = SediMemory()
    event = MemoryEvent.create(content={"k": "v"}, constraint_vector=_cv())
    event.topology_fingerprint = dict(_fp())
    sed._ingest(event)
    assert sed.recall_topology({}, min_similarity=0.5) == []


def test_recall_topology_respects_min_similarity_threshold():
    sed = SediMemory()
    a = _fp(fingerprint_id="TS:ABN:x:cf4:v1", axes_key="ABN")
    b = _fp(fingerprint_id="TS:ABX:y:cf2:v1", axes_key="ABX")  # partial overlap with a

    event_a = MemoryEvent.create(content={"k": "a"}, constraint_vector=_cv())
    event_a.topology_fingerprint = dict(a)
    sed._ingest(event_a)

    partial_sim = topology_fingerprint_similarity(a, b)
    assert 0.0 < partial_sim < 1.0

    loose = sed.recall_topology(b, min_similarity=max(0.0, partial_sim - 0.01))
    strict = sed.recall_topology(b, min_similarity=min(1.0, partial_sim + 0.2))
    assert len(loose) >= len(strict)


# ---- WARP: topology_gap_ref is provenance only, never a promotion shortcut ----

def _gap(**overrides):
    base = dict(
        axis_profile={"X": 0.8, "T": 0.2, "N": 0.5, "B": 0.3, "A": 0.6},
        best_coverage=0.5, closest_ids=["comp1", "comp2"], closest_profiles=[{}, {}],
        is_sixth_axis_candidate=False, source="test", gap_tick=1,
    )
    base.update(overrides)
    return CoverageGap(**base)


def test_generate_without_topology_gap_ref_defaults_to_none():
    comp = WarpGenerator().generate(_gap(), level="test_level")
    assert comp is not None
    assert comp.topology_gap_ref is None


def test_generate_with_topology_gap_ref_tags_the_component():
    comp = WarpGenerator().generate(_gap(), level="test_level", topology_gap_ref="TS:ABN:v1")
    assert comp is not None
    assert comp.topology_gap_ref == "TS:ABN:v1"


def test_topology_gap_ref_never_bypasses_the_promotion_gate():
    comp = WarpGenerator().generate(_gap(), level="test_level", topology_gap_ref="TS:ABN:v1")
    assert comp.promoted is False
    assert comp.trial_tick == 0
    assert comp.trial_score_ema == 0.0


def test_sixth_axis_anomaly_returns_none_regardless_of_topology_gap_ref():
    anomaly_gap = _gap(
        axis_profile={"X": 0.1}, best_coverage=0.1, closest_ids=[], closest_profiles=[],
        is_sixth_axis_candidate=True,
    )
    assert WarpGenerator().generate(anomaly_gap, level="test_level", topology_gap_ref="TS:X:v1") is None
