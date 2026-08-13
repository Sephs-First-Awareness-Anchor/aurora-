#!/usr/bin/env python3
"""Regression coverage for Build 654 (Sunni & Cael): sensory representations
becoming citizens of the genealogy/Difference/inquiry/RCRW/evolution
economy, not merely evidence that feeds someone else's promotion.

Confirmed architectural finding this closes: a promoted SensoryNode had no
RepresentationalRef, no durable/re-derivable genealogy identity (only a
one-shot, time-hashed "code_evolution"-tagged ability fossil via
register_code_evolution_outcome, which also mislabeled a perceptual
concept's provenance), and never appeared in any trace passed to
genealogy.observe() -- so it could be passively discovered as a counterpart
by something ELSE's search, but could never itself seed a
collision/gap search, accumulate PairStats, or be traced to by RCRW.

Also covers two real, independently-confirmed bugs found while auditing
the promotion path in order to build this: SensoryClusterFacet never
initialized self._evolution_hook (AttributeError the moment any node
reached the promotion gate) and AuroraSensoryCrystal.register_evolution_hook
only ever set the hook on the crystal object, never propagating it to
child facets, so the documented boot-time wiring API never actually
reached the code that reads it.
"""
from __future__ import annotations

from aurora_internal.aurora_sensory_crystal import (
    AuroraSensoryCrystal,
    SensoryClusterFacet,
    SensoryNode,
    sensory_citizen_ability_id,
    sensory_representational_ref,
)
from aurora_representational_address import RepresentationalRef


def _fresh_genealogy(tmp_path, name="citizenship_test"):
    from aurora_internal.constraint_genealogy import ConstraintGenealogyLogger, GenealogyConfig
    return ConstraintGenealogyLogger(name, config=GenealogyConfig(), output_dir=str(tmp_path / name))


def _promotable_node(node_id="n1", domain="visual", facet="hue"):
    node = SensoryNode(node_id=node_id, domain=domain, facet=facet, centroid=[0.1] * 8)
    node.stage = "concept"
    node.fitness = 0.9
    node.usage_count = 999
    node.session_count = 999
    node.cross_modal_links = ["peer1"]
    return node


# ── Bug 1: SensoryClusterFacet never initialized _evolution_hook ───────────

def test_fresh_facet_has_evolution_hook_attribute_without_crashing():
    """The exact confirmed regression: a fresh SensoryClusterFacet raised
    AttributeError inside tick_advanced_promotion() the moment any node
    reached the promotion gate, because __init__ never set the attribute
    the method unconditionally reads."""
    facet = SensoryClusterFacet("visual", "hue")
    assert hasattr(facet, "_evolution_hook")
    assert facet._evolution_hook is None
    facet._nodes["n1"] = _promotable_node()
    promoted = facet.tick_advanced_promotion()  # must not raise
    assert promoted == ["n1"]


# ── Bug 2: crystal-level register_evolution_hook never reached facets ──────

def test_register_evolution_hook_propagates_to_child_facets(tmp_path):
    crystal = AuroraSensoryCrystal(state_dir=str(tmp_path))
    received = []
    crystal.register_evolution_hook(lambda evidence: received.append(evidence))

    for facet in list(crystal._audio.values()) + list(crystal._visual.values()):
        assert facet._evolution_hook is not None

    facet = crystal._visual["hue"]
    facet._nodes["n1"] = _promotable_node()
    facet.tick_advanced_promotion()
    assert len(received) == 1
    assert received[0]["event"] == "sensory_promotion"


# ── Citizenship: addressability ─────────────────────────────────────────────

def test_sensory_representational_ref_is_d1_level_and_stable():
    ref = sensory_representational_ref("visual", "hue")
    assert isinstance(ref, RepresentationalRef)
    assert ref.level() == "D1_25"
    assert ref.nc_law_c == "X"  # hue's mapped axis (unified with DPS routing)
    # Same (domain, facet) always resolves to the same ref -- addressable,
    # not regenerated arbitrarily each call.
    assert ref.encode() == sensory_representational_ref("visual", "hue").encode()


def test_citizen_ability_id_is_stable_per_node_not_time_hashed():
    aid1 = sensory_citizen_ability_id("visual", "hue", "same-node-id")
    aid2 = sensory_citizen_ability_id("visual", "hue", "same-node-id")
    assert aid1 == aid2, "the same node must always resolve to the same ability id"
    aid_other = sensory_citizen_ability_id("visual", "hue", "different-node-id")
    assert aid_other != aid1


# ── Citizenship: granted at promotion, honestly tagged, re-derivable ───────

def test_grant_representational_citizenship_registers_honest_ability(tmp_path):
    genealogy = _fresh_genealogy(tmp_path)
    facet = SensoryClusterFacet("visual", "hue")
    facet._genealogy_ref = genealogy
    node = _promotable_node()
    facet._nodes[node.node_id] = node

    aid = facet.grant_representational_citizenship(node)

    assert aid is not None
    assert aid in genealogy.abilities
    assert node.citizen_ability_id == aid
    assert node.representational_ref is not None
    ability = genealogy.abilities[aid]
    assert "sensory_representation" in ability.effect_tags
    assert f"sensory_node_id:{node.node_id}" in ability.effect_tags
    # Ancestral/modal grounding must be honest, never disguised as a code
    # mutation the way register_code_evolution_outcome's fossil is tagged.
    assert "code_evolution" not in ability.effect_tags
    assert any(t.startswith("representational_ref:") for t in ability.effect_tags)


def test_grant_representational_citizenship_is_idempotent(tmp_path):
    genealogy = _fresh_genealogy(tmp_path)
    facet = SensoryClusterFacet("visual", "hue")
    facet._genealogy_ref = genealogy
    node = _promotable_node()
    facet._nodes[node.node_id] = node

    aid_first = facet.grant_representational_citizenship(node)
    ability_count_after_first = len(genealogy.abilities)
    aid_second = facet.grant_representational_citizenship(node)

    assert aid_first == aid_second
    assert len(genealogy.abilities) == ability_count_after_first


def test_tick_advanced_promotion_grants_citizenship_when_genealogy_wired(tmp_path):
    genealogy = _fresh_genealogy(tmp_path)
    facet = SensoryClusterFacet("visual", "hue")
    facet._genealogy_ref = genealogy
    node = _promotable_node()
    facet._nodes[node.node_id] = node

    facet.tick_advanced_promotion()

    assert node.stage == "promoted"
    assert node.citizen_ability_id is not None
    assert node.citizen_ability_id in genealogy.abilities


def test_tick_advanced_promotion_without_genealogy_still_promotes_safely():
    """No genealogy wired (_genealogy_ref stays None) must not block or
    crash ordinary promotion -- citizenship is additive, not a new
    dependency the existing promotion gate now requires."""
    facet = SensoryClusterFacet("visual", "hue")
    node = _promotable_node()
    facet._nodes[node.node_id] = node

    facet.tick_advanced_promotion()

    assert node.stage == "promoted"
    assert node.citizen_ability_id is None


# ── Citizenship: interaction with other representations ────────────────────

def test_promoted_citizen_is_discoverable_by_an_unrelated_search(tmp_path):
    """The confirmed mechanism: representation_collision_candidates()/
    representation_gap_candidates() build their search index from
    genealogy.abilities/links directly (_representation_index), seeded
    only by the caller's own active items. Registering the sensory
    ability durably in genealogy.abilities is what makes it reachable at
    all -- prove it end-to-end against the real index builder, not just
    against genealogy.abilities' dict membership."""
    from aurora_internal.constraint_genealogy import AbilityProfile

    genealogy = _fresh_genealogy(tmp_path)
    facet = SensoryClusterFacet("visual", "hue")
    facet._genealogy_ref = genealogy
    node = _promotable_node()
    facet._nodes[node.node_id] = node
    aid = facet.grant_representational_citizenship(node)

    # An unrelated ability on the SAME axis, sharing the citizen's
    # collision signature, registered independently (simulating some
    # other subsystem's own representation).
    other_id = "B:UNRELATED_OTHER"
    genealogy.abilities[other_id] = AbilityProfile(
        id=other_id, axis="B", requires=("B",),
        cost={a: 0.001 for a in ("X", "T", "N", "B", "A")},
        risk={a: 0.0 for a in ("X", "T", "N", "B", "A")},
        effect_tags=("other_representation",), notes="unrelated",
    )

    index = genealogy._representation_index([other_id])
    signature = genealogy._collision_signature_for_item(aid)
    assert aid in index.get(signature, []), (
        "the sensory citizen ability must be reachable as a counterpart "
        "when an unrelated active item searches for collisions"
    )


# ── Citizenship: ongoing consequence-observation ────────────────────────────

def test_tick_citizen_participation_reports_fitness_movement_via_observe(tmp_path):
    genealogy = _fresh_genealogy(tmp_path)
    facet = SensoryClusterFacet("visual", "hue")
    facet._genealogy_ref = genealogy
    node = _promotable_node()
    facet._nodes[node.node_id] = node
    node.stage = "promoted"  # citizenship is only ever granted at this stage
    facet.grant_representational_citizenship(node)

    tick_before = genealogy.tick_count
    node.fitness = min(1.0, node.fitness + 0.05)  # genuine forward movement

    reported = facet.tick_citizen_participation()

    assert reported == 1
    assert genealogy.tick_count == tick_before + 1
    assert node._last_citizen_fitness == node.fitness


def test_tick_citizen_participation_skips_idle_citizens(tmp_path):
    """A promoted node whose fitness has not moved since its last citizen
    tick produces no consequence -- it is not re-reported just because a
    session ended."""
    genealogy = _fresh_genealogy(tmp_path)
    facet = SensoryClusterFacet("visual", "hue")
    facet._genealogy_ref = genealogy
    node = _promotable_node()
    facet._nodes[node.node_id] = node
    node.stage = "promoted"  # citizenship is only ever granted at this stage
    facet.grant_representational_citizenship(node)

    tick_before = genealogy.tick_count
    reported = facet.tick_citizen_participation()

    assert reported == 0
    assert genealogy.tick_count == tick_before


def test_tick_citizen_participation_reports_regression_not_just_improvement(tmp_path):
    """A fitness regression is real consequence too and must not be
    silently dropped or clamped away."""
    genealogy = _fresh_genealogy(tmp_path)
    facet = SensoryClusterFacet("visual", "hue")
    facet._genealogy_ref = genealogy
    node = _promotable_node()
    facet._nodes[node.node_id] = node
    node.stage = "promoted"  # citizenship is only ever granted at this stage
    facet.grant_representational_citizenship(node)

    node.fitness = max(0.0, node.fitness - 0.10)
    reported = facet.tick_citizen_participation()

    assert reported == 1


# ── Crystal-level wiring ────────────────────────────────────────────────────

def test_crystal_register_genealogy_propagates_to_all_facets(tmp_path):
    crystal = AuroraSensoryCrystal(state_dir=str(tmp_path / "crystal_state"))
    genealogy = _fresh_genealogy(tmp_path, "crystal_genealogy")

    crystal.register_genealogy(genealogy)

    for facet in list(crystal._audio.values()) + list(crystal._visual.values()):
        assert facet._genealogy_ref is genealogy


def test_crystal_tick_citizen_participation_aggregates_across_facets(tmp_path):
    crystal = AuroraSensoryCrystal(state_dir=str(tmp_path / "crystal_state2"))
    genealogy = _fresh_genealogy(tmp_path, "crystal_genealogy2")
    crystal.register_genealogy(genealogy)

    hue_node = _promotable_node("hn1", "visual", "hue")
    tone_node = _promotable_node("tn1", "audio", "tone")
    hue_node.stage = "promoted"
    tone_node.stage = "promoted"
    crystal._visual["hue"]._nodes["hn1"] = hue_node
    crystal._audio["tone"]._nodes["tn1"] = tone_node
    crystal._visual["hue"].grant_representational_citizenship(hue_node)
    crystal._audio["tone"].grant_representational_citizenship(tone_node)
    hue_node.fitness = min(1.0, hue_node.fitness + 0.05)
    tone_node.fitness = min(1.0, tone_node.fitness + 0.05)

    total = crystal.tick_citizen_participation()

    assert total == 2


# ── Persistence round-trip ──────────────────────────────────────────────────

def test_representational_ref_and_citizen_ability_id_survive_save_load(tmp_path):
    genealogy = _fresh_genealogy(tmp_path, "persist_genealogy")
    facet = SensoryClusterFacet("visual", "hue")
    facet._genealogy_ref = genealogy
    node = _promotable_node()
    facet._nodes[node.node_id] = node
    node.stage = "promoted"  # citizenship is only ever granted at this stage
    facet.grant_representational_citizenship(node)

    d = node.to_dict()
    assert d["representational_ref"] == node.representational_ref
    assert d["citizen_ability_id"] == node.citizen_ability_id

    reloaded = SensoryNode.from_dict(d)
    assert reloaded.representational_ref == node.representational_ref
    assert reloaded.citizen_ability_id == node.citizen_ability_id
