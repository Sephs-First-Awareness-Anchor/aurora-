#!/usr/bin/env python3
"""Regression coverage for the Build 654/656 follow-up (Sunni & Cael),
covering three gaps found by direct testing after the first citizenship
pass landed:

1. DPS routing (_dps_route_observation) and genealogy/evolution/
   citizenship independently held disagreeing axis tables for the same
   six sensory facets (tone/timbre/rhythm/hue/shape/motion) -- confirmed:
   hue was B in one and X in the other, motion was T vs A, tone N vs T.
   Unified onto one module-level table (SENSORY_FACET_AXIS), reconciled
   toward DPS's pre-existing, individually-reasoned mapping.

2. A node promoted before genealogy was ever wired to its facet (e.g.
   loaded from persisted state at boot) stayed permanently stranded --
   register_genealogy() only wired the reference, never backfilled
   citizenship for nodes already at stage="promoted". Confirmed against
   this build's own shipped sensory state.

3. The AbilityProfile created at citizenship grant was a frozen,
   point-in-time snapshot -- fitness/usage/cross_modal_links baked in at
   creation never changed again even as the live node kept learning.
   Confirmed directly: raise fitness after citizenship, run the real
   citizen-participation path, re-inspect the ability -- unchanged.
"""
from __future__ import annotations

from aurora_internal.aurora_sensory_crystal import (
    AuroraSensoryCrystal,
    SENSORY_FACET_AXIS,
    SensoryClusterFacet,
    SensoryNode,
    _facet_axis,
)


def _fresh_genealogy(tmp_path, name="followup_test"):
    from aurora_internal.constraint_genealogy import ConstraintGenealogyLogger, GenealogyConfig
    return ConstraintGenealogyLogger(name, config=GenealogyConfig(), output_dir=str(tmp_path / name))


def _promoted_node(node_id="n1", domain="visual", facet="hue", fitness=0.9):
    node = SensoryNode(node_id=node_id, domain=domain, facet=facet, centroid=[0.1] * 8)
    node.stage = "promoted"
    node.fitness = fitness
    node.usage_count = 999
    node.session_count = 999
    node.cross_modal_links = ["peer1"]
    return node


# ── 1. Axis unification ─────────────────────────────────────────────────────

def test_citizenship_axis_matches_dps_routing_axis_for_every_facet():
    """The exact confirmed regression: the same sensory representation must
    not hold two different primitive axis identities depending on which
    subsystem (DPS routing vs genealogy/evolution/citizenship) is asked."""
    expected = {
        "tone": "T", "timbre": "B", "rhythm": "N",
        "hue": "X", "shape": "B", "motion": "A",
    }
    for facet, axis in expected.items():
        assert SENSORY_FACET_AXIS[facet] == axis
    # _facet_axis() (used by both grant_representational_citizenship and
    # _dps_route_observation) must resolve identically regardless of which
    # domain string is passed for a given facet name.
    assert _facet_axis("visual", "hue") == "X"
    assert _facet_axis("audio", "tone") == "T"


def test_dps_route_observation_uses_the_same_unified_table(tmp_path):
    """Direct proof, not just table equality: drive an actual DPS routing
    call and confirm the stamped constraint_signature axis matches
    SENSORY_FACET_AXIS, using a minimal stand-in DPS reference."""
    class _StubCrystal:
        def __init__(self):
            self.constraint_signature = {}
        def add_facet(self, **kw): pass
        def use(self): pass
        def evolve(self): return False

    class _StubDPS:
        def __init__(self):
            self.crystal = _StubCrystal()
        def _get_or_create(self, concept):
            return self.crystal

    crystal = AuroraSensoryCrystal(state_dir=str(tmp_path))
    dps = _StubDPS()
    crystal._dps_ref = dps

    crystal._dps_route_observation("visual", "hue", confidence=0.7)

    assert "X" in dps.crystal.constraint_signature
    assert "B" not in dps.crystal.constraint_signature


# ── 2. Legacy citizen migration ─────────────────────────────────────────────

def test_migrate_legacy_citizens_backfills_already_promoted_nodes(tmp_path):
    """The exact confirmed regression: a node already at stage="promoted"
    before genealogy was ever wired (the real shape of loading persisted
    state at boot) must not stay permanently stranded."""
    genealogy = _fresh_genealogy(tmp_path)
    facet = SensoryClusterFacet("audio", "tone")
    node = _promoted_node("legacy1", "audio", "tone")
    facet._nodes[node.node_id] = node
    assert node.citizen_ability_id is None  # pre-condition: never granted

    facet._genealogy_ref = genealogy  # simulate register_genealogy's wiring only
    assert node.citizen_ability_id is None  # wiring alone must not migrate

    migrated = facet.migrate_legacy_citizens()

    assert migrated == 1
    assert node.citizen_ability_id is not None
    assert node.citizen_ability_id in genealogy.abilities


def test_register_genealogy_backfills_legacy_citizens_across_all_facets(tmp_path):
    """End-to-end at the crystal level, mirroring the real boot sequence:
    load persisted state (nodes already "promoted"), then wire genealogy."""
    crystal = AuroraSensoryCrystal(state_dir=str(tmp_path / "crystal"))
    genealogy = _fresh_genealogy(tmp_path, "crystal_g")

    tone_node = _promoted_node("t1", "audio", "tone")
    rhythm_node = _promoted_node("r1", "audio", "rhythm")
    crystal._audio["tone"]._nodes["t1"] = tone_node
    crystal._audio["rhythm"]._nodes["r1"] = rhythm_node

    migrated = crystal.register_genealogy(genealogy)

    assert migrated == 2
    assert tone_node.citizen_ability_id in genealogy.abilities
    assert rhythm_node.citizen_ability_id in genealogy.abilities


def test_migrate_legacy_citizens_is_idempotent(tmp_path):
    genealogy = _fresh_genealogy(tmp_path)
    facet = SensoryClusterFacet("visual", "shape")
    node = _promoted_node("n1", "visual", "shape")
    facet._nodes[node.node_id] = node
    facet._genealogy_ref = genealogy

    first = facet.migrate_legacy_citizens()
    second = facet.migrate_legacy_citizens()

    assert first == 1
    assert second == 0  # already has a citizen id; nothing left to migrate


def test_migrate_legacy_citizens_skips_non_promoted_nodes(tmp_path):
    genealogy = _fresh_genealogy(tmp_path)
    facet = SensoryClusterFacet("visual", "motion")
    node = _promoted_node("n1", "visual", "motion")
    node.stage = "concept"  # not yet promoted
    facet._nodes[node.node_id] = node
    facet._genealogy_ref = genealogy

    migrated = facet.migrate_legacy_citizens()

    assert migrated == 0
    assert node.citizen_ability_id is None


# ── 3. Live state carried into the ability itself ───────────────────────────

def test_tick_citizen_participation_refreshes_ability_with_current_state(tmp_path):
    """The exact confirmed regression: raise fitness after citizenship,
    run the real citizen-participation path, and the ability's OWN fields
    (not just the observe() event) must reflect the new state."""
    genealogy = _fresh_genealogy(tmp_path)
    facet = SensoryClusterFacet("visual", "motion")
    node = _promoted_node("n1", "visual", "motion", fitness=0.60)
    facet._nodes[node.node_id] = node
    facet._genealogy_ref = genealogy
    facet.grant_representational_citizenship(node)

    ability_before = genealogy.abilities[node.citizen_ability_id]
    assert "sensory_fitness:0.600" in ability_before.effect_tags

    node.fitness = 0.95
    reported = facet.tick_citizen_participation()

    assert reported == 1
    ability_after = genealogy.abilities[node.citizen_ability_id]
    assert "sensory_fitness:0.950" in ability_after.effect_tags
    assert "sensory_fitness:0.600" not in ability_after.effect_tags
    assert "usage=999" in ability_after.notes
    assert "fitness=0.950" in ability_after.notes


def test_tick_citizen_participation_includes_live_state_in_observe_notes(tmp_path, monkeypatch):
    """Confirm the notes dict passed INTO genealogy.observe() itself
    (not just the ability afterward) carries the live centroid/fitness/
    usage/cross_modal_links snapshot -- intercept the real call rather than
    inferring it from a side effect."""
    genealogy = _fresh_genealogy(tmp_path)
    facet = SensoryClusterFacet("audio", "rhythm")
    node = _promoted_node("n1", "audio", "rhythm", fitness=0.70)
    node.centroid = [0.5, 0.25, 0.1]
    facet._nodes[node.node_id] = node
    facet._genealogy_ref = genealogy
    facet.grant_representational_citizenship(node)

    captured = {}
    orig_observe = genealogy.observe

    def _spy_observe(*args, **kwargs):
        captured.update(kwargs)
        return orig_observe(*args, **kwargs)

    monkeypatch.setattr(genealogy, "observe", _spy_observe)

    node.fitness = 0.80
    facet.tick_citizen_participation()

    live_state = captured["notes"]["live_state"]
    assert live_state["centroid"] == [0.5, 0.25, 0.1]
    assert live_state["fitness"] == 0.80
    assert live_state["usage_count"] == 999
    assert live_state["cross_modal_links"] == ["peer1"]
