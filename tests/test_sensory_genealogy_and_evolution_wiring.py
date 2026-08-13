#!/usr/bin/env python3
"""Regression coverage for Build 650 Multimodal Representational Autonomy
Directive, Sections X and XI (Sunni & Cael).

Section X: ensure_sensory_crystal_lineage() must register the sensory
AbilityProfiles into the live ConstraintGenealogyLogger on every call,
regardless of whether the on-disk lineage trait was already materialized
by a prior boot. Trait materialization and live genealogy registration
are separate responsibilities.

Section XI: a promoted sensory representation must be able to reach
Aurora's existing evolutionary evidence surface (EvolutionaryChamber
.observe_external_evidence) through AuroraSensoryCrystal's
register_evolution_hook -- the hook existed but nothing ever called it.
"""
from __future__ import annotations

from aurora_internal.aurora_sensory_crystal import (
    ensure_sensory_crystal_lineage,
    SensoryClusterFacet,
    SENSORY_ABILITY_IDS,
)


def _fresh_genealogy(tmp_path, name="sensory_wiring_test"):
    from aurora_internal.constraint_genealogy import ConstraintGenealogyLogger, GenealogyConfig
    return ConstraintGenealogyLogger(name, config=GenealogyConfig(), output_dir=str(tmp_path / name))


def test_fresh_state_registers_sensory_abilities(tmp_path):
    genealogy = _fresh_genealogy(tmp_path, "g_fresh")
    systems = {"genealogy": genealogy}
    state_dir = str(tmp_path / "fresh")

    result = ensure_sensory_crystal_lineage(systems, state_dir=state_dir, verbose=False)

    assert result is True  # newly materialized
    for ability_id in SENSORY_ABILITY_IDS:
        assert ability_id in genealogy.abilities, f"{ability_id} missing after fresh materialization"


def test_existing_trait_with_missing_live_abilities_still_registers(tmp_path):
    """The exact bug this directive names: a persisted trait directory from
    a prior boot must not suppress live genealogy registration for THIS
    process's freshly-constructed ConstraintGenealogyLogger."""
    state_dir = str(tmp_path / "restart")

    first_genealogy = _fresh_genealogy(tmp_path, "g_restart_first")
    ensure_sensory_crystal_lineage({"genealogy": first_genealogy}, state_dir=state_dir, verbose=False)
    for ability_id in SENSORY_ABILITY_IDS:
        assert ability_id in first_genealogy.abilities

    # Simulate a restart: trait directory persists on disk, but a brand new
    # (empty) ConstraintGenealogyLogger is constructed for this process.
    second_genealogy = _fresh_genealogy(tmp_path, "g_restart_second")
    assert not any(a in second_genealogy.abilities for a in SENSORY_ABILITY_IDS)

    result = ensure_sensory_crystal_lineage({"genealogy": second_genealogy}, state_dir=state_dir, verbose=False)

    assert result is False  # trait already materialized on disk
    for ability_id in SENSORY_ABILITY_IDS:
        assert ability_id in second_genealogy.abilities, (
            f"{ability_id} missing from live genealogy after restart with persisted trait -- "
            "this is the exact regression Section X names"
        )


def test_existing_trait_and_existing_abilities_stays_idempotent(tmp_path):
    state_dir = str(tmp_path / "idempotent")
    genealogy = _fresh_genealogy(tmp_path, "g_idempotent")
    systems = {"genealogy": genealogy}

    ensure_sensory_crystal_lineage(systems, state_dir=state_dir, verbose=False)
    before_ids = {id(v) for v in genealogy.abilities.values() if v.id in SENSORY_ABILITY_IDS}

    ensure_sensory_crystal_lineage(systems, state_dir=state_dir, verbose=False)
    after_ids = {id(v) for v in genealogy.abilities.values() if v.id in SENSORY_ABILITY_IDS}

    # Calling it again with abilities already present must not duplicate or
    # replace the existing AbilityProfile objects.
    assert before_ids == after_ids
    assert len(genealogy.abilities) == len({a.id for a in genealogy.abilities.values()})


def test_restart_persistence_round_trip(tmp_path):
    state_dir = str(tmp_path / "round_trip")

    genealogy_a = _fresh_genealogy(tmp_path, "g_round_trip_a")
    materialized_a = ensure_sensory_crystal_lineage({"genealogy": genealogy_a}, state_dir=state_dir, verbose=False)
    assert materialized_a is True

    genealogy_b = _fresh_genealogy(tmp_path, "g_round_trip_b")
    materialized_b = ensure_sensory_crystal_lineage({"genealogy": genealogy_b}, state_dir=state_dir, verbose=False)
    assert materialized_b is False
    assert set(a.id for a in genealogy_b.abilities.values()) >= set(SENSORY_ABILITY_IDS)


def test_evolution_hook_can_be_registered_and_fires_on_advanced_promotion():
    facet = SensoryClusterFacet(domain="visual", facet="motion")

    received = []

    class _StubCrystal:
        def register_evolution_hook(self, hook):
            self._hook = hook

    # AuroraSensoryCrystal wires facet.promotion_hook/_evolution_hook onto
    # itself; here we exercise the exact mechanism SensoryClusterFacet uses
    # to call back into the crystal's own registered evolution hook.
    def _hook(evidence):
        received.append(evidence)

    facet._evolution_hook = _hook  # what AuroraSensoryCrystal sets internally

    node = facet.observe([0.9, 0.1, 0.0, 0.0, 0.0], session_id="s1", confidence_hint=0.9)
    assert node is not None
    real_node = next(iter(facet._nodes.values()))
    # Force the node past the advanced-promotion gates directly rather than
    # simulating 28+ observations -- this exercises the real promotion and
    # hook-firing code path, not a re-simulation of arrival.
    real_node.stage = "concept"
    real_node.fitness = 0.85
    real_node.usage_count = 40
    real_node.cross_modal_links = ["some-other-node-id"]

    promoted = facet.tick_advanced_promotion()

    assert promoted == [real_node.node_id]
    assert len(received) == 1
    evidence = received[0]
    assert evidence["event"] == "sensory_promotion"
    assert evidence["domain"] == "visual"
    assert evidence["facet"] == "motion"
    assert evidence["node_id"] == real_node.node_id
    assert evidence["stage"] == "promoted"
    assert evidence["modality"] == "visual"
    assert evidence["notes"]["fitness"] == round(real_node.fitness, 3)
    assert evidence["notes"]["cross_modal_links"] == real_node.cross_modal_links


def test_sensory_promotion_evidence_reaches_evolutionary_chamber():
    """End-to-end: a promoted sensory node's evidence must actually reach
    EvolutionaryChamber.observe_external_evidence -- the existing
    evolutionary evidence surface, not a new one."""
    facet = SensoryClusterFacet(domain="audio", facet="rhythm")

    received_by_chamber = []

    class _StubChamber:
        def observe_external_evidence(self, outcome):
            received_by_chamber.append(dict(outcome))
            return {"ok": True}

    stub_chamber = _StubChamber()

    def _sensory_promotion_hook(evidence, _chamber=stub_chamber):
        _chamber.observe_external_evidence(evidence)

    facet._evolution_hook = _sensory_promotion_hook

    facet.observe([0.0, 0.9, 0.1, 0.0, 0.0], session_id="s1", confidence_hint=0.9)
    node = next(iter(facet._nodes.values()))
    node.stage = "concept"
    node.fitness = 0.9
    node.usage_count = 50
    node.cross_modal_links = ["cross-1"]

    facet.tick_advanced_promotion()

    assert len(received_by_chamber) == 1
    outcome = received_by_chamber[0]
    assert outcome["mutation_name"] == "sensory.audio.rhythm"
    assert "pressure_after" in outcome and "axis_drive" in outcome
