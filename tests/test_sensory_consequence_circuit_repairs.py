#!/usr/bin/env python3
"""Regression coverage for the Build 656+ follow-up (Sunni & Cael):
"what she learns does not govern her future sensory input" -- three
concrete, independently-verified gaps between a citizen's learned axis
and the rest of the representational economy.

1. Cache invalidation bug: genealogy's relevance-index cache stamps on
   (len(links), len(abilities), len(pair_stats)) alone. A learned axis
   reassignment replaces an EXISTING ability in place -- the count never
   changes, so the cache never rebuilt and kept indexing the
   representation under its stale collision signature. Reproduced
   directly: citizen earns axis B, representation_record() correctly
   reports B, but the relevance index still had it filed under axis:T
   and was absent from axis:B.

2. The missing feedback circuit: a citizen could earn axis B through
   tick_citizen_participation() while DPS routing (_dps_route_observation)
   kept stamping every NEW observation of that SAME representation with
   the static facet-level prior (T), because the specific matched node_id
   was computed by facet.observe() and then discarded before reaching DPS
   routing. What she learned about a representation never governed how
   the next encounter with it was perceived.

3. Structured live state (centroid, usage history, session breadth,
   cross-modal links, maturity, axis-evidence vector/samples) was only
   ever reachable via the transient genealogy.observe() notes payload of
   whichever tick happened to run last -- not part of the STANDING
   operand surface representation_record()/staged inquiry operands/RCRW
   actually stage from.
"""
from __future__ import annotations

from aurora_internal.aurora_sensory_crystal import (
    AXIS_EVIDENCE_MIN_SAMPLES,
    AuroraSensoryCrystal,
    SensoryClusterFacet,
    SensoryNode,
)


def _fresh_genealogy(tmp_path, name="circuit_repairs_test"):
    from aurora_internal.constraint_genealogy import ConstraintGenealogyLogger, GenealogyConfig
    return ConstraintGenealogyLogger(name, config=GenealogyConfig(), output_dir=str(tmp_path / name))


def _drifting_node(node_id="n1", domain="audio", facet="tone"):
    """Same fixture shape as test_sensory_learned_axis_participation.py's
    _promoted_node -- heavy cross-modal grounding, shaped to earn B
    against tone's T starting prior."""
    node = SensoryNode(node_id=node_id, domain=domain, facet=facet, centroid=[0.1] * 8)
    node.stage = "promoted"
    node.fitness = 0.72
    node.usage_count = 30
    node.session_count = 4
    node.confidence = 0.40
    node.cross_modal_links = ["p1", "p2", "p3", "p4"]
    return node


def _drive_to_learned_axis(facet, node):
    for _ in range(AXIS_EVIDENCE_MIN_SAMPLES + 3):
        node.fitness = min(1.0, node.fitness + 0.01)
        facet.tick_citizen_participation()


# ── 1. Cache invalidation ───────────────────────────────────────────────────

def test_exact_collision_index_reflects_learned_axis_not_stale_signature(tmp_path):
    """Covers _representation_index() (the exact primitive-signature
    collision index), NOT _representation_relevance_index() (the
    cross-family native-relevance index) -- despite this test's original
    name claiming the latter. They are two separate caches with two
    separate stamps; see
    test_cross_family_relevance_index_reflects_learned_axis_not_stale_bucket
    below for the one that actually exercises the relevance index, which
    had its own, independently-confirmed instance of this same bug."""
    genealogy = _fresh_genealogy(tmp_path)
    facet = SensoryClusterFacet("audio", "tone")
    node = _drifting_node()
    facet._nodes[node.node_id] = node
    facet._genealogy_ref = genealogy
    facet.grant_representational_citizenship(node)

    # Build the index once while the ability is still at its starting T axis.
    genealogy._representation_index([node.citizen_ability_id])
    sig_t = genealogy._collision_signature_for_item(node.citizen_ability_id)

    _drive_to_learned_axis(facet, node)
    ability = genealogy.abilities[node.citizen_ability_id]
    assert ability.axis == "B", "fixture must actually earn a new axis for this test to mean anything"

    index_after = genealogy._representation_index([node.citizen_ability_id])
    sig_b_now = genealogy._collision_signature_for_item(node.citizen_ability_id)

    # The exact confirmed regression: without the fix, the rebuilt index
    # (stamped only on counts, which never changed) would still bucket the
    # ability under its ORIGINAL signature rather than reflect axis B.
    assert node.citizen_ability_id in index_after.get(sig_b_now, []), (
        "relevance index must reflect the representation's CURRENT "
        "operational axis after an in-place learned reassignment"
    )


def test_cross_family_relevance_index_reflects_learned_axis_not_stale_bucket(tmp_path):
    """_representation_relevance_index() -- the cross-family native-
    relevance index that representation_gap_candidates() actually searches
    -- had its OWN, separate cache stamped only on
    (len(links), len(abilities), len(pair_stats)), with no reference to
    _representation_index_dirty_counter at all. mark_representation_index_
    dirty() only ever invalidated _representation_index(), the exact-
    collision index, never this one.

    Reproduced directly: a sensory citizen earns axis B via
    tick_citizen_participation() (which does call
    mark_representation_index_dirty() -- the counter genuinely climbs), yet
    _representation_relevance_index() kept the ability filed under its
    stale axis:T bucket and absent from axis:B, because an in-place ability
    replacement changes none of the three counts this cache's own stamp
    was built from. Aurora's cross-family inquiry search
    (representation_gap_candidates()) could therefore still see yesterday's
    operational identity after the representation itself had changed."""
    genealogy = _fresh_genealogy(tmp_path)
    facet = SensoryClusterFacet("audio", "tone")
    node = _drifting_node()
    facet._nodes[node.node_id] = node
    facet._genealogy_ref = genealogy
    facet.grant_representational_citizenship(node)

    relevance_before = genealogy._representation_relevance_index()
    aid = node.citizen_ability_id
    assert aid in relevance_before.get("axis:T", []), (
        "fixture sanity check: citizen must start out bucketed under its "
        "facet-prior axis"
    )

    _drive_to_learned_axis(facet, node)
    ability = genealogy.abilities[aid]
    assert ability.axis == "B", "fixture must actually earn a new axis for this test to mean anything"
    assert genealogy._representation_index_dirty_counter > 0, (
        "sanity check: the learned-axis path must have marked the index dirty"
    )

    relevance_after = genealogy._representation_relevance_index()
    assert aid in relevance_after.get("axis:B", []), (
        "cross-family relevance index must reflect the representation's "
        "CURRENT operational axis after an in-place learned reassignment"
    )
    assert aid not in relevance_after.get("axis:T", []), (
        "cross-family relevance index must not keep the representation "
        "filed under its stale, pre-learning axis bucket"
    )


def test_mark_representation_index_dirty_forces_a_rebuild(tmp_path):
    """Direct proof the dirty counter is what breaks the stale cache, not
    some other side effect of the citizenship path."""
    genealogy = _fresh_genealogy(tmp_path)
    facet = SensoryClusterFacet("audio", "tone")
    node = _drifting_node()
    facet._nodes[node.node_id] = node
    facet._genealogy_ref = genealogy
    facet.grant_representational_citizenship(node)

    genealogy._representation_index([node.citizen_ability_id])
    stamp_before = genealogy._representation_index_stamp

    # Replace the ability's content in place WITHOUT going through the
    # citizen-participation path, exactly the class of mutation the bug
    # report named ("Genealogy's cross-family relevance index is cached
    # using (links, abilities, pair_stats)... the number of abilities
    # doesn't change").
    import dataclasses
    existing = genealogy.abilities[node.citizen_ability_id]
    genealogy.abilities[node.citizen_ability_id] = dataclasses.replace(existing, axis="A")

    assert genealogy._representation_index_stamp == stamp_before, (
        "sanity check: the stamp must NOT change from the replace alone"
    )
    genealogy.mark_representation_index_dirty()
    genealogy._representation_index([node.citizen_ability_id])
    assert genealogy._representation_index_stamp != stamp_before


def test_mark_representation_index_dirty_also_forces_relevance_index_rebuild(tmp_path):
    """Same proof as above, for _representation_relevance_index(). Both
    caches share the single _representation_index_dirty_counter -- one
    dirty call must invalidate both, since a caller has no way to know in
    advance which index a downstream query will consult."""
    genealogy = _fresh_genealogy(tmp_path)
    facet = SensoryClusterFacet("audio", "tone")
    node = _drifting_node()
    facet._nodes[node.node_id] = node
    facet._genealogy_ref = genealogy
    facet.grant_representational_citizenship(node)

    genealogy._representation_relevance_index()
    stamp_before = genealogy._representation_relevance_stamp

    import dataclasses
    existing = genealogy.abilities[node.citizen_ability_id]
    genealogy.abilities[node.citizen_ability_id] = dataclasses.replace(existing, axis="A")

    assert genealogy._representation_relevance_stamp == stamp_before, (
        "sanity check: the stamp must NOT change from the replace alone"
    )
    genealogy.mark_representation_index_dirty()
    genealogy._representation_relevance_index()
    assert genealogy._representation_relevance_stamp != stamp_before


# ── 2. Learned axis feeds back into future DPS routing for that node ───────

def test_dps_routing_uses_the_specific_nodes_learned_axis(tmp_path):
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

    genealogy = _fresh_genealogy(tmp_path)
    crystal = AuroraSensoryCrystal(state_dir=str(tmp_path / "crystal_state"))
    crystal.register_genealogy(genealogy)
    dps = _StubDPS()
    crystal._dps_ref = dps

    facet = crystal._audio["tone"]
    node = _drifting_node("n1", "audio", "tone")
    facet._nodes[node.node_id] = node
    facet.grant_representational_citizenship(node)
    _drive_to_learned_axis(facet, node)
    assert genealogy.abilities[node.citizen_ability_id].axis == "B"

    # A FRESH observation of the SAME representation (real DPS routing
    # call, node_id passed through as observe_frame() now does).
    crystal._dps_route_observation("audio", "tone", 0.7, node_id=node.node_id)

    # The exact confirmed regression: without the fix, this always stamped
    # tone's static facet-level prior (T), regardless of what genealogy
    # had already learned about this specific representation.
    assert "B" in dps.crystal.constraint_signature
    assert "T" not in dps.crystal.constraint_signature


def test_dps_routing_falls_back_to_facet_prior_for_a_node_with_no_citizenship(tmp_path):
    """A brand-new / not-yet-promoted node has no citizen_ability_id --
    routing must fall back exactly as before this fix, not crash or guess."""
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

    crystal._dps_route_observation("audio", "tone", 0.7, node_id="not-a-real-node")
    assert "T" in dps.crystal.constraint_signature  # tone's SENSORY_FACET_AXIS prior


def test_observe_frame_passes_matched_node_id_through_to_dps_routing(tmp_path, monkeypatch):
    """End-to-end: observe_frame() must not discard the node_id
    facet.observe() already computed."""
    genealogy = _fresh_genealogy(tmp_path)
    crystal = AuroraSensoryCrystal(state_dir=str(tmp_path / "crystal_state2"))
    crystal.register_genealogy(genealogy)

    captured = []
    monkeypatch.setattr(
        crystal, "_dps_route_observation",
        lambda domain, facet_name, confidence, node_id="": captured.append((domain, facet_name, node_id)),
    )
    crystal._dps_ref = object()  # non-None so the (monkeypatched) call fires

    audio_20d = [0.0] * 20
    vision_57d = [0.0] * 57
    # Give the tone facet a genuinely distinguishable signal so observe()
    # matches/creates a real node rather than the all-zero early-return.
    # Tone reads index 6 (harmonicity) + 8:20 (chroma) -- AUDIO_FACET_INDICES.
    audio_20d[6] = 0.8
    crystal.observe_frame(audio_20d, vision_57d, session_id="s1")

    tone_calls = [c for c in captured if c[1] == "tone"]
    assert tone_calls, "tone facet must have routed an observation"
    assert tone_calls[0][2], "node_id must be a non-empty matched node id, not silently dropped"


# ── 3. Structured live state on the standing operand surface ───────────────

def test_structured_state_is_on_the_standing_representation_record(tmp_path):
    genealogy = _fresh_genealogy(tmp_path)
    facet = SensoryClusterFacet("visual", "hue")
    node = SensoryNode(node_id="n1", domain="visual", facet="hue", centroid=[0.3, 0.4, 0.5])
    node.stage = "promoted"
    node.fitness = 0.8
    node.usage_count = 20
    node.session_count = 3
    node.cross_modal_links = ["peer1"]
    facet._nodes[node.node_id] = node
    facet._genealogy_ref = genealogy
    facet.grant_representational_citizenship(node)

    # representation_record() is the standing, queryable operand surface --
    # not a transient per-event log entry.
    record = genealogy.representation_record(node.citizen_ability_id)
    assert record is not None
    structured = record["operational_effect"].get("structured_state")
    assert structured is not None, (
        "structured live state must be reachable from the STANDING intact "
        "representation surface, not only genealogy.observe()'s notes"
    )
    assert structured["centroid"] == [0.3, 0.4, 0.5]
    assert structured["usage_count"] == 20
    assert structured["session_count"] == 3
    assert structured["cross_modal_links"] == ["peer1"]


def test_structured_state_refreshes_on_each_citizen_participation_tick(tmp_path):
    genealogy = _fresh_genealogy(tmp_path)
    facet = SensoryClusterFacet("visual", "hue")
    node = SensoryNode(node_id="n1", domain="visual", facet="hue", centroid=[0.1] * 4)
    node.stage = "promoted"
    node.fitness = 0.5
    facet._nodes[node.node_id] = node
    facet._genealogy_ref = genealogy
    facet.grant_representational_citizenship(node)

    node.fitness = 0.9
    node.centroid = [0.9, 0.9, 0.9, 0.9]
    facet.tick_citizen_participation()

    record = genealogy.representation_record(node.citizen_ability_id)
    structured = record["operational_effect"]["structured_state"]
    assert structured["fitness"] == 0.9
    assert structured["centroid"] == [0.9, 0.9, 0.9, 0.9]


def test_structured_state_survives_persistence_round_trip(tmp_path):
    from aurora_internal.constraint_genealogy import AbilityProfile

    ability = AbilityProfile(
        id="B:TEST", axis="B", requires=("B",),
        cost={a: 0.001 for a in ("X", "T", "N", "B", "A")},
        risk={a: 0.0 for a in ("X", "T", "N", "B", "A")},
        effect_tags=("sensory_representation",),
        notes="test",
        structured_state={"centroid": [0.1, 0.2], "usage_count": 5},
    )
    d = ability.to_dict()
    assert d["structured_state"] == {"centroid": [0.1, 0.2], "usage_count": 5}

    # Round-trip through the real persistence restore path.
    import json
    from aurora_runtime import _restore_genealogy_state
    from aurora_internal.constraint_genealogy import ConstraintGenealogyLogger, GenealogyConfig

    out_dir = tmp_path / "persist_test"
    out_dir.mkdir()
    genealogy = ConstraintGenealogyLogger("persist_test", config=GenealogyConfig(), output_dir=str(out_dir))
    genealogy.abilities["B:TEST"] = ability
    abilities_path = out_dir / getattr(genealogy.cfg, "ABILITIES_FILE", "abilities.json")
    with open(abilities_path, "w", encoding="utf-8") as fh:
        json.dump({"B:TEST": ability.to_dict()}, fh)

    fresh = ConstraintGenealogyLogger("persist_test_2", config=GenealogyConfig(), output_dir=str(out_dir))
    fresh.abilities = {}
    _restore_genealogy_state(fresh, str(out_dir))
    assert fresh.abilities["B:TEST"].structured_state == {"centroid": [0.1, 0.2], "usage_count": 5}
