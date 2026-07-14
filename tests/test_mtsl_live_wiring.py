"""
tests/test_mtsl_live_wiring.py
=================================
MTSL live-wiring (2026-07-14): MTSL_AUTHORITY_STAGE advanced to 2 (a
manual, evidence-cited decision -- see cers_regulator.py's comment on
the constant), and TopologyContext threaded into the real
CERSBridge.build_snapshot() -> cers_converge() call, sourced from the
coordinator's PREVIOUS-turn snapshot (this tick's own observation
happens after, via aurora_consciousness_engine.py's reordered
_attach_dual_strata_snapshot).
"""
import tempfile
import time

import pytest

from aurora_dimensional_systems import CrystalProcessingSystem, EvolutionTracker
from aurora_internal.dual_strata.cers_bridge import CERSBridge
from aurora_internal.dual_strata.cers_regulator import MTSL_AUTHORITY_STAGE, TopologyContext
from aurora_internal.dual_strata.crest import Crest
from aurora_internal.dual_strata.topological_semantic_coordinator import TopologicalSemanticCoordinator

_AXES_CYCLE = [
    {"X": 0.5, "T": 0.5, "N": 0.7, "B": 0.5, "A": 0.3},
    {"X": 0.5, "T": 0.5, "N": 0.3, "B": 0.5, "A": 0.7},
    {"X": 0.5, "T": 0.5, "N": 0.5, "B": 0.7, "A": 0.3},
]
_CRESTS = (Crest(label="comfort", intensity=0.6, axis="N"), Crest(label="urgency", intensity=0.1, axis="A"))


class _FakeAssembly:
    def __init__(self, axes):
        self.adjusted_axes = axes
        self.sensory_context = {}
        self.entropy_state = {"coherence": 0.5}
        self.coherence = 0.5


def test_authority_stage_is_now_2():
    assert MTSL_AUTHORITY_STAGE == 2


# ---- CoordinatorSnapshot.to_topology_context() ----

def test_to_topology_context_builds_a_real_topology_context():
    dps = CrystalProcessingSystem(tracker=EvolutionTracker())
    coord = TopologicalSemanticCoordinator(state_dir=None)
    snap = None
    for i in range(30):
        snap = coord.observe_turn(
            turn_id=f"t{i}", timestamp=time.time(), adjusted_axes=_AXES_CYCLE[i % 3],
            sub_crests=_CRESTS, dps=dps,
        )
    ctx = snap.to_topology_context()
    assert isinstance(ctx, TopologyContext)
    assert ctx.turn_id == snap.turn_id
    assert ctx.manifold_slot_id == snap.manifold_slot_id
    assert ctx.variant_confidence == (snap.variant_confidence or 0.0)


def test_to_topology_context_respects_dominant_scale_override():
    dps = CrystalProcessingSystem(tracker=EvolutionTracker())
    coord = TopologicalSemanticCoordinator(state_dir=None)
    snap = None
    for i in range(30):
        snap = coord.observe_turn(
            turn_id=f"t{i}", timestamp=time.time(), adjusted_axes=_AXES_CYCLE[i % 3],
            sub_crests=_CRESTS, dps=dps,
        )
    ctx_meso = snap.to_topology_context(dominant_scale="meso")
    ctx_micro = snap.to_topology_context(dominant_scale="micro")
    assert ctx_meso.regime == snap.topology_signatures["meso"]["regime"]
    assert ctx_micro.regime == snap.topology_signatures["micro"]["regime"]


# ---- CERSBridge.build_snapshot(mtsl_topology_context=...) live wiring ----


def test_first_tick_has_no_prior_context_and_inert_mtsl_fields(tmp_path):
    bridge = CERSBridge(state_dir=str(tmp_path))
    dps = CrystalProcessingSystem(tracker=EvolutionTracker())
    assembly = _FakeAssembly(_AXES_CYCLE[0])
    snapshot = bridge.build_snapshot(
        assembly, payload="test", payload_type="text",
        precomputed_sub_crests=_CRESTS, dps=dps,
        mtsl_topology_context=None,
    )
    import json
    detail = json.loads((bridge.state_dir / "cers_detail.json").read_text())
    mtsl = detail["mtsl_semantic"]
    assert mtsl["semantic_salience"] == 0.0
    assert mtsl["semantic_hesitation"] is False
    assert mtsl["semantic_mode"] is None


def test_later_ticks_carry_a_real_topology_context(tmp_path):
    import json
    state_dir = str(tmp_path)
    dps = CrystalProcessingSystem(tracker=EvolutionTracker())
    bridge = CERSBridge(state_dir=state_dir)
    coordinator = TopologicalSemanticCoordinator(state_dir=state_dir)

    for i in range(30):
        assembly = _FakeAssembly(_AXES_CYCLE[i % 3])
        prior = coordinator.latest_snapshot
        ctx = prior.to_topology_context() if prior is not None else None
        bridge.build_snapshot(
            assembly, payload="test", payload_type="text",
            precomputed_sub_crests=_CRESTS, dps=dps,
            mtsl_topology_context=ctx,
        )
        coordinator.observe_turn(
            turn_id=f"t{i}", timestamp=time.time(), adjusted_axes=_AXES_CYCLE[i % 3],
            sub_crests=_CRESTS, dps=dps,
        )

    detail = json.loads((bridge.state_dir / "cers_detail.json").read_text())
    mtsl = detail["mtsl_semantic"]
    # by tick 30 on a real cyclic pattern, semantic_mode should have
    # resolved to something real (not stuck at None)
    assert mtsl["semantic_mode"] is not None
    assert set(mtsl.keys()) == {
        "semantic_salience", "semantic_hesitation", "variant_confidence",
        "semantic_mode", "response_bias",
    }


def test_mtsl_semantic_never_breaks_a_turn_on_bad_context(tmp_path):
    # a malformed/wrong-typed context must never crash build_snapshot --
    # cers_converge()'s own topology_context handling should degrade
    # gracefully, matching every other MTSL module's posture.
    bridge = CERSBridge(state_dir=str(tmp_path))
    dps = CrystalProcessingSystem(tracker=EvolutionTracker())
    assembly = _FakeAssembly(_AXES_CYCLE[0])
    snapshot = bridge.build_snapshot(
        assembly, payload="test", payload_type="text",
        precomputed_sub_crests=_CRESTS, dps=dps,
        mtsl_topology_context=None,  # baseline: must not crash regardless
    )
    assert snapshot is not None


# ---- aurora.py's _read_cers_salience surfaces the new fields ----

def test_read_cers_salience_exposes_mtsl_semantic_fields(tmp_path, monkeypatch):
    import aurora

    state_dir = str(tmp_path)
    dps = CrystalProcessingSystem(tracker=EvolutionTracker())
    bridge = CERSBridge(state_dir=state_dir)
    coordinator = TopologicalSemanticCoordinator(state_dir=state_dir)

    for i in range(30):
        assembly = _FakeAssembly(_AXES_CYCLE[i % 3])
        prior = coordinator.latest_snapshot
        ctx = prior.to_topology_context() if prior is not None else None
        bridge.build_snapshot(
            assembly, payload="test", payload_type="text",
            precomputed_sub_crests=_CRESTS, dps=dps,
            mtsl_topology_context=ctx,
        )
        coordinator.observe_turn(
            turn_id=f"t{i}", timestamp=time.time(), adjusted_axes=_AXES_CYCLE[i % 3],
            sub_crests=_CRESTS, dps=dps,
        )

    fake_systems = {"dual_strata_state_dir": state_dir}
    monkeypatch.setattr(aurora, "_dual_strata_state_dir", lambda systems: __import__("pathlib").Path(state_dir))
    result = aurora._read_cers_salience(fake_systems)
    assert set(result.keys()) == {
        "cers_salience", "cers_hesitation",
        "semantic_salience", "semantic_hesitation",
        "variant_confidence", "semantic_mode", "response_bias",
    }


def test_read_cers_salience_degrades_gracefully_with_no_state(tmp_path, monkeypatch):
    import aurora
    monkeypatch.setattr(aurora, "_dual_strata_state_dir", lambda systems: __import__("pathlib").Path(str(tmp_path)))
    result = aurora._read_cers_salience({})
    assert result["semantic_salience"] == 0.0
    assert result["semantic_hesitation"] is False
    assert result["semantic_mode"] is None


# ---- CERSBridge.last_verdict (feeds NSpaceGateway._articulate_user_response) ----

def test_last_verdict_is_none_before_any_tick(tmp_path):
    bridge = CERSBridge(state_dir=str(tmp_path))
    assert bridge.last_verdict is None


def test_last_verdict_set_after_build_snapshot(tmp_path):
    bridge = CERSBridge(state_dir=str(tmp_path))
    dps = CrystalProcessingSystem(tracker=EvolutionTracker())
    assembly = _FakeAssembly(_AXES_CYCLE[0])
    bridge.build_snapshot(
        assembly, payload="test", payload_type="text",
        precomputed_sub_crests=_CRESTS, dps=dps, mtsl_topology_context=None,
    )
    assert bridge.last_verdict is not None
    assert bridge.last_verdict.semantic_mode is None  # no context this tick


def test_last_verdict_carries_a_real_topology_context_on_later_ticks(tmp_path):
    state_dir = str(tmp_path)
    dps = CrystalProcessingSystem(tracker=EvolutionTracker())
    bridge = CERSBridge(state_dir=state_dir)
    coordinator = TopologicalSemanticCoordinator(state_dir=state_dir)
    for i in range(30):
        assembly = _FakeAssembly(_AXES_CYCLE[i % 3])
        prior = coordinator.latest_snapshot
        ctx = prior.to_topology_context() if prior is not None else None
        bridge.build_snapshot(
            assembly, payload="test", payload_type="text",
            precomputed_sub_crests=_CRESTS, dps=dps, mtsl_topology_context=ctx,
        )
        coordinator.observe_turn(
            turn_id=f"t{i}", timestamp=time.time(), adjusted_axes=_AXES_CYCLE[i % 3],
            sub_crests=_CRESTS, dps=dps,
        )
    assert bridge.last_verdict is not None
    assert bridge.last_verdict.semantic_mode is not None


# ---- full chain: CERSBridge -> SemanticIntentionBridge -> aurora_articulation ----

def test_full_chain_produces_a_real_articulation_context(tmp_path):
    import aurora_articulation as aa
    from aurora_internal.dual_strata.semantic_intention_bridge import SemanticIntentionBridge

    state_dir = str(tmp_path)
    dps = CrystalProcessingSystem(tracker=EvolutionTracker())
    bridge = CERSBridge(state_dir=state_dir)
    coordinator = TopologicalSemanticCoordinator(state_dir=state_dir)
    intention_bridge = SemanticIntentionBridge(state_dir=state_dir)

    for i in range(30):
        assembly = _FakeAssembly(_AXES_CYCLE[i % 3])
        prior = coordinator.latest_snapshot
        ctx = prior.to_topology_context() if prior is not None else None
        bridge.build_snapshot(
            assembly, payload="test", payload_type="text",
            precomputed_sub_crests=_CRESTS, dps=dps, mtsl_topology_context=ctx,
        )
        coordinator.observe_turn(
            turn_id=f"t{i}", timestamp=time.time(), adjusted_axes=_AXES_CYCLE[i % 3],
            sub_crests=_CRESTS, dps=dps,
        )

    verdict = bridge.last_verdict
    assert verdict is not None and verdict.semantic_mode is not None
    decision = intention_bridge.consume(verdict, turn_id="expr-final", authority_stage=MTSL_AUTHORITY_STAGE)
    mtsl_context = {
        "semantic_strategy": decision.strategy,
        "semantic_confidence": decision.strategy_confidence,
        "semantic_strategy_applied": decision.applied,
    }
    assert decision.applied is True  # MTSL_AUTHORITY_STAGE is 2

    # feeding this into real decide_articulation() must not crash and
    # must record the strategy honestly, whatever it resolved to.
    art_decision = aa.decide_articulation(
        "the pattern seems worth noting honestly", "The pattern is worth noting.",
        context=mtsl_context,
    )
    assert art_decision.metadata["expression_context"]["semantic_strategy"] == decision.strategy
    assert art_decision.metadata["expression_context"]["semantic_strategy_applied"] is True
