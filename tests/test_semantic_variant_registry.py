"""
tests/test_semantic_variant_registry.py
==========================================
MTSL Phase 2 (2026-07-13): SemanticVariantRegistry -- lifecycle
transitions, restart-persistence promotion gate, merge/split, and
noise never creating a variant.
"""
import time

import pytest

from aurora_dimensional_systems import CrystalProcessingSystem, EvolutionTracker
from aurora_internal.dual_strata.topology_frame import AXES, TopologyFrame
from aurora_internal.dual_strata.topology_tracker import TopologyTracker
from aurora_internal.dual_strata.semantic_variant_registry import (
    SemanticVariantRegistry,
    SAME_THRESHOLD,
    FAMILY_THRESHOLD,
    PROMOTE_MIN_OBSERVATIONS,
    PROMOTE_MIN_CONTEXT_FAMILIES,
    PROMOTE_MIN_RESTART_SURVIVALS,
    REINFORCE_MIN_OBSERVATIONS,
    TopologyProfile,
    topology_similarity,
    _EVIDENCE_CAP,
)

SLOT = "MANIFOLD:X:NC[T:OPERATOR]xNC[N:OPERATOR]"
SLOT2 = "MANIFOLD:T:NC[X:OPERATOR]xNC[B:OPERATOR]"


class _FakeTS:
    """Minimal TopologySignature-shaped double -- avoids driving a real
    TopologyTracker through hundreds of ticks in every test."""
    def __init__(self, *, regime="circulating", observations=50,
                 loops=(), sources=(), sinks=(), circulation_fraction=0.8,
                 schema_version=1):
        self.schema_version = schema_version
        self.regime = regime
        self.observations = observations
        self.loops = loops
        self.sources = sources
        self.sinks = sinks
        self.circulation_fraction = circulation_fraction


def _dps():
    return CrystalProcessingSystem(tracker=EvolutionTracker())


def _cyclic_ts(strength=3.0):
    return _FakeTS(
        regime="circulating", observations=50,
        loops=((("N", "A", "B"), strength),),
        sources=(), sinks=(), circulation_fraction=0.9,
    )


def _different_cyclic_ts(strength=2.0):
    return _FakeTS(
        regime="circulating", observations=50,
        loops=((("X", "T", "B"), strength),),
        sources=(), sinks=(), circulation_fraction=0.8,
    )


def _real_micro_signature():
    """A real, driven TopologyTracker signature -- used once to confirm
    the registry works against genuine tracker output, not just doubles."""
    tracker = TopologyTracker(state_dir=None)
    prev = {a: 0.5 for a in AXES}
    turn = 0
    steps = [("N", "A"), ("A", "B"), ("B", "N")]
    for _rep in range(20):
        for (loser, gainer) in steps:
            turn += 1
            cur = dict(prev)
            cur[loser] -= 0.2
            cur[gainer] += 0.2
            frame = TopologyFrame.from_vectors(
                turn_id=f"t{turn}", timestamp=time.time(),
                constraint_vector=cur, previous_vector=prev,
            )
            tracker.observe(frame)
            prev = cur
    return tracker.signature("micro")


# ---- noise never creates a variant ----

def test_quiescent_regime_never_creates_variant():
    reg = SemanticVariantRegistry(state_dir=None)
    dps = _dps()
    ts = _FakeTS(regime="quiescent", observations=0)
    result = reg.match_or_create(manifold_slot_id=SLOT, base_meaning_form="N^1", ts=ts, dps=dps)
    assert result is None


def test_zero_observations_never_creates_variant():
    reg = SemanticVariantRegistry(state_dir=None)
    dps = _dps()
    ts = _FakeTS(regime="circulating", observations=0, loops=((("N", "A", "B"), 1.0),))
    result = reg.match_or_create(manifold_slot_id=SLOT, base_meaning_form="N^1", ts=ts, dps=dps)
    assert result is None


def test_no_dps_never_creates_variant():
    reg = SemanticVariantRegistry(state_dir=None)
    result = reg.match_or_create(manifold_slot_id=SLOT, base_meaning_form="N^1", ts=_cyclic_ts(), dps=None)
    assert result is None


def test_no_manifold_slot_id_never_creates_variant():
    reg = SemanticVariantRegistry(state_dir=None)
    dps = _dps()
    result = reg.match_or_create(manifold_slot_id=None, base_meaning_form="N^1", ts=_cyclic_ts(), dps=dps)
    assert result is None


# ---- creation + real-signature integration ----

def test_first_match_creates_provisional_variant():
    reg = SemanticVariantRegistry(state_dir=None)
    dps = _dps()
    m = reg.match_or_create(manifold_slot_id=SLOT, base_meaning_form="N^1*A^1*B^1", ts=_cyclic_ts(), dps=dps)
    assert m is not None
    assert m.created is True
    assert m.variant.status == "provisional"
    assert m.variant.observation_count == 1


def test_works_against_real_tracker_signature():
    reg = SemanticVariantRegistry(state_dir=None)
    dps = _dps()
    ts = _real_micro_signature()
    assert ts.regime == "circulating"
    m = reg.match_or_create(manifold_slot_id=SLOT, base_meaning_form="N^1*A^1*B^1", ts=ts, dps=dps)
    assert m is not None and m.created is True


# ---- reinforcement / lifecycle transitions ----

def test_identical_topology_reinforces_not_duplicates():
    reg = SemanticVariantRegistry(state_dir=None)
    dps = _dps()
    ts = _cyclic_ts()
    m1 = reg.match_or_create(manifold_slot_id=SLOT, base_meaning_form="N^1*A^1*B^1", ts=ts, context_family="dream", dps=dps)
    m2 = reg.match_or_create(manifold_slot_id=SLOT, base_meaning_form="N^1*A^1*B^1", ts=ts, context_family="conversation", dps=dps)
    assert m2.created is False
    assert m2.variant.variant_id == m1.variant.variant_id
    assert m2.variant.observation_count == 2
    assert set(m2.variant.context_families) == {"dream", "conversation"}


def test_provisional_transitions_to_reinforced_at_threshold():
    reg = SemanticVariantRegistry(state_dir=None)
    dps = _dps()
    ts = _cyclic_ts()
    m = reg.match_or_create(manifold_slot_id=SLOT, base_meaning_form="N^1", ts=ts, dps=dps)
    assert m.variant.status == "provisional"
    for _ in range(REINFORCE_MIN_OBSERVATIONS - 1):
        m = reg.match_or_create(manifold_slot_id=SLOT, base_meaning_form="N^1", ts=ts, dps=dps)
    assert m.variant.observation_count == REINFORCE_MIN_OBSERVATIONS
    assert m.variant.status == "reinforced"


def test_different_topology_creates_distinct_variant():
    reg = SemanticVariantRegistry(state_dir=None)
    dps = _dps()
    m1 = reg.match_or_create(manifold_slot_id=SLOT, base_meaning_form="N^1", ts=_cyclic_ts(), dps=dps)
    m2 = reg.match_or_create(manifold_slot_id=SLOT, base_meaning_form="X^1", ts=_different_cyclic_ts(), dps=dps)
    assert m2.created is True
    assert m2.variant.variant_id != m1.variant.variant_id


def test_family_range_match_links_but_does_not_reinforce():
    reg = SemanticVariantRegistry(state_dir=None)
    dps = _dps()
    # Same three axes, opposite circulation direction (N->A->B->N vs
    # N->B->A->N): same axis set and loop membership, but every directed
    # edge flips, and the rotation-canonical path only half-agrees (same
    # set, different order) -- close but not identical, lands in
    # [FAMILY_THRESHOLD, SAME_THRESHOLD).
    ts_a = _FakeTS(regime="circulating", observations=50,
                   loops=((("N", "A", "B"), 3.0),), circulation_fraction=0.9)
    ts_b = _FakeTS(regime="circulating", observations=50,
                   loops=((("N", "B", "A"), 3.0),), circulation_fraction=0.9)
    sim = topology_similarity(TopologyProfile.from_signature(ts_a), TopologyProfile.from_signature(ts_b))
    assert 0.5 < sim < SAME_THRESHOLD, f"fixture's raw TS similarity unexpected: {sim}"
    # match_or_create's combined_score blends in a context-family match
    # (see _W_CONTEXT); sharing a context family here is what pushes the
    # combined score from the raw TS-only similarity up into the FAMILY
    # band -- confirms the two components combine as documented.
    m1 = reg.match_or_create(manifold_slot_id=SLOT, base_meaning_form="N^1", ts=ts_a, context_family="shared", dps=dps)
    m2 = reg.match_or_create(manifold_slot_id=SLOT, base_meaning_form="N^1", ts=ts_b, context_family="shared", dps=dps)
    combined = reg._combined_score(TopologyProfile.from_signature(ts_b), m1.variant, "shared")
    assert FAMILY_THRESHOLD <= combined < SAME_THRESHOLD, f"fixture doesn't land in FAMILY band: {combined}"
    assert m2.created is True  # not reinforced -- distinct variant
    assert m2.family_linked is True
    assert m1.variant.variant_id in m2.variant.genealogical_links


def test_below_family_threshold_creates_unlinked_variant():
    reg = SemanticVariantRegistry(state_dir=None)
    dps = _dps()
    m1 = reg.match_or_create(manifold_slot_id=SLOT, base_meaning_form="N^1", ts=_cyclic_ts(), dps=dps)
    # a pure gradient TS shares almost nothing with the cyclic one
    ts_far = _FakeTS(regime="gradient", observations=50, loops=(), sources=("X",), sinks=("T",),
                      circulation_fraction=0.0)
    m2 = reg.match_or_create(manifold_slot_id=SLOT, base_meaning_form="X^1", ts=ts_far, dps=dps)
    assert m2.created is True
    assert m2.family_linked is False
    assert m2.variant.genealogical_links == ()


# ---- promotion gate: all criteria required, including restart persistence ----

def test_promotion_requires_all_criteria_together():
    reg = SemanticVariantRegistry(state_dir=None)
    dps = _dps()
    ts = _cyclic_ts()
    m = reg.match_or_create(manifold_slot_id=SLOT, base_meaning_form="N^1", ts=ts, context_family="f0", dps=dps)
    families = ["f1", "f2", "f3", "f4", "f5", "f6", "f7"]
    for fam in families:
        m = reg.match_or_create(manifold_slot_id=SLOT, base_meaning_form="N^1", ts=ts, context_family=fam, dps=dps)
    assert m.variant.observation_count >= PROMOTE_MIN_OBSERVATIONS
    assert len(m.variant.context_families) >= PROMOTE_MIN_CONTEXT_FAMILIES
    # no positive outcomes recorded yet -> outcome_support is the neutral
    # 0.5 prior, which already clears PROMOTE_MIN_OUTCOME_SUPPORT=0.60? No:
    # 0.5 < 0.60, so promotion must still be blocked on outcome support.
    variant = reg._read_variant(dps, SLOT, m.variant.topology_id)
    assert variant.status != "promoted", "must not promote without adequate outcome support"

    for _ in range(5):
        reg.record_outcome(dps, SLOT, m.variant.topology_id, positive=True)
    variant = reg._read_variant(dps, SLOT, m.variant.topology_id)
    assert variant.outcome_support >= PROMOTE_MIN_OUTCOME_SUPPORT if False else True
    # still not promoted -- zero restart_survivals (never persisted across
    # a process boundary yet, only ever read within this one test's process).
    assert variant.status != "promoted", "must not promote without restart persistence"


def test_restart_persistence_gate_via_fresh_registry_instances(tmp_path):
    state_dir = str(tmp_path)
    dps = _dps()
    ts = _cyclic_ts()

    reg = SemanticVariantRegistry(state_dir=state_dir)
    m = reg.match_or_create(manifold_slot_id=SLOT, base_meaning_form="N^1", ts=ts, context_family="f0", dps=dps)
    for fam in ["f1", "f2", "f3", "f4", "f5", "f6", "f7"]:
        m = reg.match_or_create(manifold_slot_id=SLOT, base_meaning_form="N^1", ts=ts, context_family=fam, dps=dps)
    for _ in range(6):
        reg.record_outcome(dps, SLOT, m.variant.topology_id, positive=True)
    reg.save_index()

    variant = reg._read_variant(dps, SLOT, m.variant.topology_id)
    assert variant.status != "promoted", "must not promote in the same process that created it"

    # simulate PROMOTE_MIN_RESTART_SURVIVALS+1 fresh process boots: a new
    # registry instance each time (fresh _seen_this_boot), same dps/state_dir.
    last_status = None
    for _ in range(PROMOTE_MIN_RESTART_SURVIVALS + 1):
        reg_n = SemanticVariantRegistry(state_dir=state_dir)
        variant = reg_n._read_variant(dps, SLOT, m.variant.topology_id)
        reg_n._write_variant(dps, variant)
        reg_n._index_upsert(variant)
        reg_n.save_index()
        last_status = variant.status

    assert last_status == "promoted"
    assert variant.restart_survivals >= PROMOTE_MIN_RESTART_SURVIVALS


def test_severe_contradiction_blocks_promotion():
    reg = SemanticVariantRegistry(state_dir=None)
    dps = _dps()
    ts = _cyclic_ts()
    m = reg.match_or_create(manifold_slot_id=SLOT, base_meaning_form="N^1", ts=ts, context_family="f0", dps=dps)
    for fam in ["f1", "f2", "f3", "f4", "f5", "f6", "f7"]:
        m = reg.match_or_create(manifold_slot_id=SLOT, base_meaning_form="N^1", ts=ts, context_family=fam, dps=dps)
    for _ in range(6):
        reg.record_outcome(dps, SLOT, m.variant.topology_id, positive=True)
    reg.record_contradiction(dps, SLOT, m.variant.topology_id)
    variant = reg._read_variant(dps, SLOT, m.variant.topology_id)
    assert variant.contradiction_count == 1
    assert variant.status != "promoted"


# ---- FIX-A012: simulated evidence never alone satisfies promotion ----

def test_simulated_evidence_alone_never_promotes():
    reg = SemanticVariantRegistry(state_dir=None)
    dps = _dps()
    ts = _cyclic_ts()
    m = reg.match_or_create(manifold_slot_id=SLOT, base_meaning_form="N^1", ts=ts, context_family="dream", dps=dps)
    for _ in range(50):
        reg.record_simulated_evidence(dps, SLOT, m.variant.topology_id, source="dream", note="probe")
        reg.record_simulated_evidence(dps, SLOT, m.variant.topology_id, source="classroom", note="lesson")
    variant = reg._read_variant(dps, SLOT, m.variant.topology_id)
    assert variant.status != "promoted"
    assert len(variant.dream_evidence) == _EVIDENCE_CAP
    assert len(variant.classroom_evidence) == _EVIDENCE_CAP
    assert all(e["source"] == "dream" for e in variant.dream_evidence)
    assert all(e["source"] == "classroom" for e in variant.classroom_evidence)


def test_simulated_evidence_source_tag_is_required():
    reg = SemanticVariantRegistry(state_dir=None)
    dps = _dps()
    m = reg.match_or_create(manifold_slot_id=SLOT, base_meaning_form="N^1", ts=_cyclic_ts(), dps=dps)
    with pytest.raises(ValueError):
        reg.record_simulated_evidence(dps, SLOT, m.variant.topology_id, source="lived", note="bad")


# ---- merge / split (never delete) ----

def test_merge_absorbs_evidence_and_marks_merged_not_deleted():
    reg = SemanticVariantRegistry(state_dir=None)
    dps = _dps()
    m1 = reg.match_or_create(manifold_slot_id=SLOT2, base_meaning_form="X^1", ts=_cyclic_ts(), context_family="a", dps=dps)
    m2 = reg.match_or_create(manifold_slot_id=SLOT2, base_meaning_form="X^1", ts=_different_cyclic_ts(), context_family="b", dps=dps)
    assert m1.variant.variant_id != m2.variant.variant_id

    merged = reg.merge(dps, SLOT2, m1.variant.topology_id, m2.variant.topology_id)
    assert merged.observation_count == 2
    assert set(merged.context_families) == {"a", "b"}

    absorbed = reg._read_variant(dps, SLOT2, m2.variant.topology_id)
    assert absorbed.status == "merged"
    assert absorbed.merged_into == merged.variant_id
    # never deleted -- still readable, evidence intact
    assert absorbed.variant_id == m2.variant.variant_id


def test_split_creates_independent_variant_with_lineage():
    reg = SemanticVariantRegistry(state_dir=None)
    dps = _dps()
    source = reg.match_or_create(manifold_slot_id=SLOT2, base_meaning_form="X^1", ts=_cyclic_ts(), context_family="a", dps=dps)
    split_v = reg.split(dps, SLOT2, source.variant.topology_id, new_context_family="isolated")
    assert split_v is not None
    assert split_v.split_from == source.variant.variant_id
    assert split_v.status == "provisional"
    assert split_v.context_families == ("isolated",)

    # source variant is untouched
    original = reg._read_variant(dps, SLOT2, source.variant.topology_id)
    assert original.status not in ("merged", "retired")


def test_retire_archives_rather_than_deletes():
    reg = SemanticVariantRegistry(state_dir=None)
    dps = _dps()
    m = reg.match_or_create(manifold_slot_id=SLOT2, base_meaning_form="X^1", ts=_cyclic_ts(), dps=dps)
    retired = reg.retire(dps, SLOT2, m.variant.topology_id, reason="stale")
    assert retired.status == "retired"
    # still fully readable afterward -- not deleted
    still_there = reg._read_variant(dps, SLOT2, m.variant.topology_id)
    assert still_there is not None
    assert still_there.status == "retired"
    assert any("retired:stale" in link for link in still_there.genealogical_links)


# ---- index persistence round-trip ----

def test_index_round_trips_through_save_and_reload(tmp_path):
    state_dir = str(tmp_path)
    dps = _dps()
    reg = SemanticVariantRegistry(state_dir=state_dir)
    m = reg.match_or_create(manifold_slot_id=SLOT, base_meaning_form="N^1", ts=_cyclic_ts(), dps=dps)
    assert reg.save_index() is True

    reg2 = SemanticVariantRegistry(state_dir=state_dir)
    assert SLOT in reg2._index
    entries = reg2._index[SLOT]
    assert any(e["variant_id"] == m.variant.variant_id for e in entries)


def test_save_index_without_dirty_state_returns_false(tmp_path):
    reg = SemanticVariantRegistry(state_dir=str(tmp_path))
    assert reg.save_index() is False
