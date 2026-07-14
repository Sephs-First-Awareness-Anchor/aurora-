"""
tests/test_lifecycle_catalog.py
==================================
MTSL, live-wired 2026-07-14: lifecycle_catalog.catalog_lifecycle() --
a read-only, alive/dead view unifying SemanticVariant status, Crystal
facet state, and WarpComponent trial/promoted/dissolved state, all
sourced from data that already exists (no new storage).
"""
import time

import types

from aurora_internal.dual_strata import (
    catalog_lifecycle,
    catalog_lifecycle_from_systems,
    collect_warp_hosts,
)
from aurora_internal.dual_strata.crest import Crest
from aurora_internal.dual_strata.semantic_variant_registry import SemanticVariantRegistry
from aurora_internal.dual_strata.topological_semantic_coordinator import TopologicalSemanticCoordinator
from aurora_dimensional_systems import CrystalProcessingSystem, EvolutionTracker, FacetState
from aurora_warp_protocol import WarpComponent

_AXES_CYCLE = [
    {"X": 0.5, "T": 0.5, "N": 0.7, "B": 0.5, "A": 0.3},
    {"X": 0.5, "T": 0.5, "N": 0.3, "B": 0.5, "A": 0.7},
    {"X": 0.5, "T": 0.5, "N": 0.5, "B": 0.7, "A": 0.3},
]
_CRESTS = (Crest(label="steady", intensity=0.6, axis="N"),)


def _driven_dps(n=40):
    dps = CrystalProcessingSystem(tracker=EvolutionTracker())
    coord = TopologicalSemanticCoordinator(state_dir=None)
    for i in range(n):
        coord.observe_turn(
            turn_id=f"t{i}", timestamp=time.time(), adjusted_axes=_AXES_CYCLE[i % 3],
            sub_crests=_CRESTS, dps=dps,
        )
    return dps, coord


def _fake_component(cid, gap_ref=None):
    return WarpComponent(
        component_id=cid, level="test_level", axis_profile={"I_SOUGHT": 0.7},
        parent_ids=[], name=cid, topology_gap_ref=gap_ref,
    )


# ---- empty / graceful degradation ----

def test_empty_catalog_no_dps_no_hosts():
    cat = catalog_lifecycle()
    assert cat["alive_total"] == 0
    assert cat["dead_total"] == 0
    assert cat["semantic_variants"]["alive"] == []
    assert cat["crystal_facets"]["alive"] == []
    assert cat["warp_components"]["alive"] == []


def test_none_dps_does_not_raise():
    cat = catalog_lifecycle(dps=None, warp_hosts=None)
    assert cat["alive_total"] == 0


def test_malformed_dps_does_not_raise():
    class _Bad:
        crystals = "not a dict"
    cat = catalog_lifecycle(dps=_Bad(), warp_hosts={"bad": object()})
    assert cat["alive_total"] == 0
    assert cat["dead_total"] == 0


def test_bad_warp_host_does_not_raise():
    cat = catalog_lifecycle(warp_hosts={"weird": object(), "none": None})
    assert cat["warp_components"]["alive"] == []
    assert cat["warp_components"]["dead_count"] == 0


# ---- semantic variants ----

def test_driven_dps_produces_alive_semantic_variants():
    dps, _coord = _driven_dps()
    cat = catalog_lifecycle(dps=dps)
    assert cat["semantic_variants"]["alive_count"] >= 1
    assert cat["semantic_variants"]["dead_count"] == 0
    statuses = {e["status"] for e in cat["semantic_variants"]["alive"]}
    assert statuses <= {"provisional", "reinforced", "promoted"}


def test_retired_variant_counted_as_dead():
    dps, coord = _driven_dps()
    snap = coord.latest_snapshot
    mid, tid = coord._split_variant_id(snap)
    reg = SemanticVariantRegistry(state_dir=None)
    reg.retire(dps, mid, tid, reason="test")

    cat = catalog_lifecycle(dps=dps)
    dead_ids = {e["variant_id"] for e in cat["semantic_variants"]["dead"]}
    assert any(vid and vid.endswith(tid) for vid in dead_ids)
    assert cat["semantic_variants"]["dead_count"] >= 1


def test_alive_plus_dead_variant_count_matches_total_variant_crystals():
    dps, _coord = _driven_dps()
    cat = catalog_lifecycle(dps=dps)
    variant_crystals = [c for c in dps.crystals.values() if c.concept.startswith("tensor_variant:")]
    assert cat["semantic_variants"]["alive_count"] + cat["semantic_variants"]["dead_count"] == len(variant_crystals)


# ---- crystal facets ----

def test_active_facets_are_alive():
    dps, _coord = _driven_dps()
    cat = catalog_lifecycle(dps=dps)
    assert cat["crystal_facets"]["alive_count"] >= 1
    assert all(e["state"] != "relic" for e in cat["crystal_facets"]["alive"])


def test_relic_facet_counted_as_dead():
    dps, _coord = _driven_dps()
    first_facet = next(iter(next(iter(dps.crystals.values())).facets.values()))
    first_facet.state = FacetState.RELIC

    cat = catalog_lifecycle(dps=dps)
    assert cat["crystal_facets"]["dead_count"] == 1
    assert cat["crystal_facets"]["dead"][0]["facet_id"] == first_facet.facet_id


def test_decaying_facet_is_still_alive():
    dps, _coord = _driven_dps()
    first_facet = next(iter(next(iter(dps.crystals.values())).facets.values()))
    first_facet.state = FacetState.DECAYING

    cat = catalog_lifecycle(dps=dps)
    matching = [e for e in cat["crystal_facets"]["alive"] if e["facet_id"] == first_facet.facet_id]
    assert matching and matching[0]["state"] == "decaying"


# ---- WARP components ----

def test_trial_component_is_alive():
    dps, _coord = _driven_dps()
    comp = _fake_component("trial1", gap_ref="TS:abc")
    dps._warp_trials[comp.component_id] = comp

    cat = catalog_lifecycle(dps=dps, warp_hosts={"dps": dps})
    entries = [e for e in cat["warp_components"]["alive"] if e["component_id"] == "trial1"]
    assert entries and entries[0]["lifecycle"] == "trial"
    assert entries[0]["topology_gap_ref"] == "TS:abc"


def test_promoted_component_is_alive():
    dps, _coord = _driven_dps()
    comp = _fake_component("promoted1")
    comp.promoted = True
    dps._warp_promoted[comp.component_id] = comp

    cat = catalog_lifecycle(dps=dps, warp_hosts={"dps": dps})
    entries = [e for e in cat["warp_components"]["alive"] if e["component_id"] == "promoted1"]
    assert entries and entries[0]["lifecycle"] == "promoted"


def test_dissolved_count_is_reported_as_dead():
    dps, _coord = _driven_dps()
    dps._warp_dissolved_count = 3

    cat = catalog_lifecycle(dps=dps, warp_hosts={"dps": dps})
    assert cat["warp_components"]["dead_count"] == 3
    assert "dead_note" in cat["warp_components"]


def test_warp_evaluate_trials_dissolve_path_increments_counter():
    # real dissolve path (not a hand-set counter) -- proves the mixin's
    # own evaluate_warp_trials() increments _warp_dissolved_count when a
    # trial fails to clear PROMOTION_SCORE by TRIAL_TICKS.
    dps, _coord = _driven_dps()
    comp = _fake_component("doomed")
    dps._warp_trials[comp.component_id] = comp
    assert dps._warp_dissolved_count == 0

    from aurora_warp_protocol import TRIAL_TICKS
    for _ in range(TRIAL_TICKS + 1):
        dps.evaluate_warp_trials()

    assert "doomed" not in dps._warp_trials
    assert dps._warp_dissolved_count >= 1
    cat = catalog_lifecycle(dps=dps, warp_hosts={"dps": dps})
    assert cat["warp_components"]["dead_count"] >= 1


def test_multiple_warp_hosts_are_merged():
    dps, _coord = _driven_dps()
    comp_a = _fake_component("a1")
    comp_b = _fake_component("b1")
    dps._warp_trials[comp_a.component_id] = comp_a

    other_dps, _c2 = _driven_dps(n=1)
    other_dps._warp_trials[comp_b.component_id] = comp_b

    cat = catalog_lifecycle(warp_hosts={"dps": dps, "other": other_dps})
    hosts_seen = {e["host"] for e in cat["warp_components"]["alive"]}
    assert hosts_seen == {"dps", "other"}


# ---- totals ----

def test_totals_are_sums_of_sections():
    dps, _coord = _driven_dps()
    comp = _fake_component("t1")
    dps._warp_trials[comp.component_id] = comp
    dps._warp_dissolved_count = 2

    cat = catalog_lifecycle(dps=dps, warp_hosts={"dps": dps})
    expected_alive = (
        cat["semantic_variants"]["alive_count"]
        + cat["crystal_facets"]["alive_count"]
        + cat["warp_components"]["alive_count"]
    )
    expected_dead = (
        cat["semantic_variants"]["dead_count"]
        + cat["crystal_facets"]["dead_count"]
        + cat["warp_components"]["dead_count"]
    )
    assert cat["alive_total"] == expected_alive
    assert cat["dead_total"] == expected_dead


def test_generated_at_is_a_real_timestamp():
    before = time.time()
    cat = catalog_lifecycle()
    after = time.time()
    assert before <= cat["generated_at"] <= after


# ---- collect_warp_hosts / catalog_lifecycle_from_systems ----

def test_collect_warp_hosts_empty_systems_does_not_raise():
    assert collect_warp_hosts({}) == {}
    assert collect_warp_hosts(None) == {}


def test_collect_warp_hosts_finds_dps_off_dimensional():
    dps, _coord = _driven_dps()
    fake_dimensional = types.SimpleNamespace(dps=dps)
    hosts = collect_warp_hosts({"dimensional": fake_dimensional})
    assert hosts.get("dps") is dps


def test_collect_warp_hosts_finds_sibling_top_level_hosts():
    perception = object()
    language_field = object()
    thought_braid = object()
    hosts = collect_warp_hosts({
        "perception": perception,
        "language_field": language_field,
        "_thought_braid": thought_braid,
    })
    assert hosts["perception"] is perception
    assert hosts["language_field"] is language_field
    assert hosts["thought_braid"] is thought_braid


def test_collect_warp_hosts_skips_absent_optional_hosts():
    hosts = collect_warp_hosts({"dimensional": types.SimpleNamespace(dps=None)})
    assert hosts == {}


def test_catalog_lifecycle_from_systems_end_to_end():
    dps, _coord = _driven_dps()
    comp = _fake_component("sys1")
    dps._warp_trials[comp.component_id] = comp
    fake_dimensional = types.SimpleNamespace(dps=dps)

    cat = catalog_lifecycle_from_systems({"dimensional": fake_dimensional})
    assert cat["semantic_variants"]["alive_count"] >= 1
    entries = [e for e in cat["warp_components"]["alive"] if e["component_id"] == "sys1"]
    assert entries and entries[0]["host"] == "dps"


def test_catalog_lifecycle_from_systems_empty_does_not_raise():
    assert catalog_lifecycle_from_systems({}) is not None
    assert catalog_lifecycle_from_systems(None) is not None
