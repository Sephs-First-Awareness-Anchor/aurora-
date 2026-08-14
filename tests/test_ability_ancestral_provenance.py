#!/usr/bin/env python3
"""Regression coverage for AbilityProfile.origin_axis (Sunni & Cael,
"Autonomous Development Integrity" pass, blocker 5): immutable ancestral
grounding kept structurally distinct from mutable operational/proxy state
(current .axis, consequence_profile, structured_state).

Formalizes what sensory citizenship's "initial_axis:" effect_tag already
did informally -- this is the typed, structural version of the same
guarantee, verified directly rather than assumed.
"""
from __future__ import annotations

import dataclasses

from aurora_internal.constraint_genealogy import (
    AXES,
    AbilityProfile,
    ConstraintGenealogyLogger,
    GenealogyConfig,
    _augment_ability_profile_with_origin,
)


def _fresh_genealogy(tmp_path, name="provenance_test"):
    return ConstraintGenealogyLogger(name, config=GenealogyConfig(), output_dir=str(tmp_path / name))


def test_origin_axis_is_stamped_on_first_augmentation_pass():
    raw = AbilityProfile(
        id="B:ENCAPSULATE", axis="B", requires=("B",),
        cost={a: 0.0 for a in AXES}, risk={a: 0.0 for a in AXES},
        effect_tags=(), notes="",
    )
    assert raw.origin_axis is None, "sanity check: not yet stamped"
    augmented = _augment_ability_profile_with_origin(raw)
    assert augmented.origin_axis == "B"


def test_origin_axis_survives_a_learned_axis_reassignment():
    """The frozen-dataclass replace() contract this depends on: replacing
    .axis must NOT disturb origin_axis, since nothing passes it."""
    ability = _augment_ability_profile_with_origin(AbilityProfile(
        id="T:SENSORY_REPR_x", axis="T", requires=("T",),
        cost={a: 0.0 for a in AXES}, risk={a: 0.0 for a in AXES},
        effect_tags=(), notes="",
    ))
    assert ability.origin_axis == "T"
    relearned = dataclasses.replace(ability, axis="B", requires=("B",))
    assert relearned.origin_axis == "T", "origin_axis must survive a learned axis reassignment untouched"
    assert relearned.axis == "B"


def test_reaugmenting_an_already_learned_ability_does_not_overwrite_origin_axis():
    """The exact restart-triggered drift this blocker fixes: without
    reading ap.origin_axis first, a second pass through
    _augment_ability_profile_with_origin (e.g. on every restart via
    normalize_ability_origins()) would recompute origin/lineage tags from
    the CURRENT (already-learned) axis instead of preserving the true
    birth axis."""
    born = _augment_ability_profile_with_origin(AbilityProfile(
        id="T:SENSORY_REPR_y", axis="T", requires=("T",),
        cost={a: 0.0 for a in AXES}, risk={a: 0.0 for a in AXES},
        effect_tags=(), notes="",
    ))
    assert born.origin_axis == "T"

    learned = dataclasses.replace(born, axis="B", requires=("B",))
    re_augmented = _augment_ability_profile_with_origin(learned)
    assert re_augmented.origin_axis == "T", (
        "a second augmentation pass after a learned reassignment must NOT "
        "overwrite origin_axis with the current (post-learning) axis"
    )
    assert re_augmented.axis == "B", "the current operational axis is untouched by this same pass"


def test_ability_provenance_view_separates_ancestral_from_operational():
    ability = _augment_ability_profile_with_origin(AbilityProfile(
        id="T:SENSORY_REPR_z", axis="T", requires=("T",),
        cost={a: 0.001 for a in AXES}, risk={a: 0.0 for a in AXES},
        effect_tags=("tag",), notes="",
    ))
    learned = dataclasses.replace(
        ability, axis="B", requires=("B",),
        consequence_profile={"effect": {a: 0.1 for a in AXES}, "samples": 5, "confidence": 0.5},
    )
    view = learned.ability_provenance_view()
    assert view["ancestral"]["origin_axis"] == "T"
    assert view["ancestral"]["id"] == learned.id
    assert view["operational"]["axis"] == "B"
    assert view["operational"]["consequence_profile"]["samples"] == 5
    # Mutating the returned dicts must not touch the ability itself.
    view["operational"]["axis"] = "N"
    assert learned.axis == "B"


def test_ability_provenance_view_degrades_honestly_for_abilities_predating_the_field():
    """An ability persisted before origin_axis existed has origin_axis ==
    None -- the view must fall back to current .axis rather than fabricate
    a birth record it doesn't actually have."""
    legacy = AbilityProfile(
        id="X:LEGACY", axis="X", requires=("X",),
        cost={a: 0.0 for a in AXES}, risk={a: 0.0 for a in AXES},
        effect_tags=(), notes="",
    )
    assert legacy.origin_axis is None
    view = legacy.ability_provenance_view()
    assert view["ancestral"]["origin_axis"] == "X"


def test_origin_axis_round_trips_through_to_dict():
    ability = _augment_ability_profile_with_origin(AbilityProfile(
        id="B:ROUND_TRIP", axis="B", requires=("B",),
        cost={a: 0.0 for a in AXES}, risk={a: 0.0 for a in AXES},
        effect_tags=(), notes="",
    ))
    d = ability.to_dict()
    assert d["origin_axis"] == "B"

    restored = AbilityProfile(
        id=d["id"], axis=d["axis"], requires=tuple(d["requires"]),
        cost=d["cost"], risk=d["risk"], effect_tags=tuple(d["effect_tags"]), notes=d["notes"],
        origin_axis=d.get("origin_axis"),
    )
    assert restored.origin_axis == "B"


def test_aurora_runtime_restore_preserves_origin_axis(tmp_path):
    import json

    genealogy = _fresh_genealogy(tmp_path)
    genealogy.abilities["B:A"] = _augment_ability_profile_with_origin(AbilityProfile(
        id="B:A", axis="B", requires=("B",),
        cost={a: 0.0 for a in AXES}, risk={a: 0.0 for a in AXES},
        effect_tags=(), notes="",
    ))
    # Simulate a learned reassignment happening before the restart.
    genealogy.abilities["B:A"] = dataclasses.replace(genealogy.abilities["B:A"], axis="N", requires=("N",))
    assert genealogy.abilities["B:A"].origin_axis == "B"

    output_dir = str(tmp_path / "provenance_test")
    abilities_path = f"{output_dir}/{genealogy.cfg.ABILITIES_FILE}"
    with open(abilities_path, "w", encoding="utf-8") as fh:
        json.dump({aid: ab.to_dict() for aid, ab in genealogy.abilities.items()}, fh)

    from aurora_runtime import _restore_genealogy_state

    restarted = ConstraintGenealogyLogger("provenance_test_2", config=GenealogyConfig(), output_dir=output_dir)
    _restore_genealogy_state(restarted, output_dir=output_dir)
    restored = restarted.abilities["B:A"]
    assert restored.origin_axis == "B", "origin_axis must survive a full persist/restore/normalize round trip"
    assert restored.axis == "N", "the learned reassignment must also survive, unconfused with ancestry"


def test_real_sensory_citizen_origin_axis_survives_learned_reassignment(tmp_path):
    """Real integration proof, not just synthetic AbilityProfile
    manipulation: a genuine sensory citizen's origin_axis (stamped at
    grant_representational_citizenship(), the one construction site that
    doesn't route through _augment_ability_profile_with_origin) must
    survive tick_citizen_participation() earning it a new operational
    axis."""
    from aurora_internal.aurora_sensory_crystal import AXIS_EVIDENCE_MIN_SAMPLES, SensoryClusterFacet, SensoryNode

    genealogy = _fresh_genealogy(tmp_path)
    facet = SensoryClusterFacet("audio", "tone")
    node = SensoryNode(node_id="n1", domain="audio", facet="tone", centroid=[0.1] * 8)
    node.stage = "promoted"
    node.fitness = 0.72
    node.usage_count = 30
    node.session_count = 4
    node.confidence = 0.40
    node.cross_modal_links = ["p1", "p2", "p3", "p4"]
    facet._nodes[node.node_id] = node
    facet._genealogy_ref = genealogy
    facet.grant_representational_citizenship(node)

    ability = genealogy.abilities[node.citizen_ability_id]
    assert ability.origin_axis == "T"

    for _ in range(AXIS_EVIDENCE_MIN_SAMPLES + 3):
        node.fitness = min(1.0, node.fitness + 0.01)
        facet.tick_citizen_participation()

    ability = genealogy.abilities[node.citizen_ability_id]
    assert ability.axis != "T", "fixture sanity check: the axis really did get relearned"
    assert ability.origin_axis == "T", "ancestral grounding must not move just because operational identity did"
