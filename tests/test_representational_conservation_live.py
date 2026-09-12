#!/usr/bin/env python3
"""
Representational conservation fence for live System-B transformations.

These tests deliberately target the places where a representation is compacted
or merged into a new native shape.  The rule is not "copy every field into
every descendant".  The rule is narrower:

    A lossy transform must leave enough native ancestry that the source
    representation remains recoverable.

Existing mechanisms already do this elsewhere (PropositionFrame keeps its
source representation, genealogy keeps parent representation descriptors,
vision clusters keep members).  These tests fence the live gaps found in the
2026-09-12 representational-conservation pass.

Authors: Sunni (Sir) Morningstar & Ceph
"""
from __future__ import annotations

import os

# Keep import-time optional subsystems from turning this focused fence into a
# full boot.  These flags do not alter the native transform methods under test.
os.environ.setdefault("AURORA_SKIP_OETS_IMPORTS", "1")
os.environ.setdefault("AURORA_SKIP_LANG_IMPORTS", "1")
os.environ.setdefault("AURORA_SKIP_HARDWARE_IMPORTS", "1")

import aurora_expression_perception as aep
from aurora_hardware_io import SensoryConcept, SensoryConceptMemory
from foundational_contract import ExistenceMode


def _native_energy_to_shard(cascade, channels):
    """Exercise the native transform even when an evolved surface is installed."""
    originals = getattr(aep, "_AURORA_NATIVE_EVOLVED_ORIGINALS", {}) or {}
    fn = originals.get("ImpressionCascade.energy_to_shard")
    if fn is None:
        fn = aep.ImpressionCascade.energy_to_shard
    return fn(cascade, channels, ExistenceMode.TRANSIENT)


def test_energy_to_shard_preserves_the_channel_packet_it_compacted():
    cascade = aep.ImpressionCascade()
    channels = {"curiosity": 0.7, "fear": 0.2, "joy": 0.1}

    shard = _native_energy_to_shard(cascade, channels)

    assert isinstance(shard, aep.EmotionShard)
    assert getattr(shard, "source_channels", None) == channels
    # Conservation must be a snapshot, not an alias to caller-owned state.
    channels["curiosity"] = 0.0
    assert shard.source_channels["curiosity"] == 0.7


def test_bounded_seed_compression_returns_a_relic_with_resolvable_ancestry():
    cascade = aep.ImpressionCascade()
    seeds = [
        aep.ImpressionSeed(
            seed_id=f"seed_{idx}",
            dominant_emotion=emotion,
            shard_ids=[f"shard_{idx}"],
            centroid_valence=valence,
            reliability=reliability,
        )
        for idx, (emotion, valence, reliability) in enumerate(
            (
                ("curiosity", 0.55, 0.72),
                ("curiosity", 0.60, 0.68),
                ("trust", 0.45, 0.64),
            )
        )
    ]
    for seed in seeds:
        cascade.seeds[seed.seed_id] = seed

    # The existing mode boundary remains load-bearing.
    assert cascade.seeds_to_relic(
        [seed.seed_id for seed in seeds], ExistenceMode.PERSISTENT
    ) is None

    relic = cascade.seeds_to_relic(
        [seed.seed_id for seed in seeds], ExistenceMode.BOUNDED
    )

    assert isinstance(relic, aep.GhostRelic)
    assert relic.relic_id in cascade.relics
    assert set(relic.seed_ids) == {seed.seed_id for seed in seeds}
    # Every recorded parent must still resolve to the intact representation
    # that was compacted, rather than merely to a flattened theme/score.
    assert all(seed_id in cascade.seeds for seed_id in relic.seed_ids)


def test_sensory_concept_merge_preserves_absorbed_concept_identity_and_round_trips():
    memory = SensoryConceptMemory("visual")
    target = SensoryConcept(
        concept_id="concept_target",
        modality="visual",
        label="person",
        centroid=[0.2, 0.3],
        times_matched=3,
    )
    source = SensoryConcept(
        concept_id="concept_source",
        modality="visual",
        label="sunny",
        centroid=[0.25, 0.35],
        times_matched=2,
    )
    # Model a source that already had ancestry of its own.  A merge must not
    # preserve only the immediate parent and amputate the earlier lineage.
    source.source_concept_ids = ["concept_grandparent"]

    merged = memory._merge_concepts(target, source)

    source_ids = set(getattr(merged, "source_concept_ids", []) or [])
    assert "concept_source" in source_ids
    assert "concept_grandparent" in source_ids

    restored = SensoryConcept.from_dict(merged.to_dict())
    restored_ids = set(getattr(restored, "source_concept_ids", []) or [])
    assert source_ids == restored_ids
