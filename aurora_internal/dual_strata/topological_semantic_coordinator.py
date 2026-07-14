# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_internal/dual_strata/topological_semantic_coordinator.py
===================================================================
TopologicalSemanticCoordinator — MTSL Phase 3 (2026-07-13), spec
section 6.4. The single runtime entry for topology/SV observation:
build frame -> tick tracker once -> produce multi-scale TS -> match/
create SV -> expose one immutable snapshot. Owns the legacy
ToroidalCirculationLayer too (FIX-A011: "applies retroactively to
ToroidalCirculationLayer once the coordinator lands") -- callers no
longer tick TCL themselves.

NO AUTHORITY: like semantic_variant_registry.py, this module observes
and records. It never decides meaning, salience, or response (Phase
4/5). record_turn_outcome() is exposed plumbing only -- nothing in
this module or its Phase 3 wiring calls it; deciding what counts as a
positive/negative outcome is explicitly out of this phase's scope.

DIRECTIVE AMENDMENT (section 11: deviations the live code forces must
be logged, not silently absorbed). The directive's section 6 prose
says "wire into aurora.py inside the existing CERS shadow pass...and
into aurora_consciousness_engine.py as a reader of the same snapshot."
Tracing the actual call graph shows the opposite assignment is what
the real code requires:

    gw._synthesize() (aurora_governance_persistence_gateway.py)
      -> self.consciousness.process(.... )                    [FIRST]
           -> ConsciousnessEngine._attach_dual_strata_snapshot()
              already computes adjusted_axes/sub_crests for its OWN
              CERSBridge tick right here.
      -> returns `synthesis` with .assembly set
    aurora.py's _refresh_live_dual_strata_runtime(systems, synthesis=synthesis, ...)
      runs SECOND, on that SAME assembly.                      [SECOND]

_attach_dual_strata_snapshot (aurora_consciousness_engine.py) runs
first on every turn and already has fresh adjusted_axes/sub_crests in
scope -- it is the OBSERVER (calls observe_turn()). aurora.py's
_refresh_live_dual_strata_runtime runs second on the identical
assembly -- it is the READER (reads latest_snapshot, never
re-observes). This is the reverse of the directive's prose but the
only assignment that actually satisfies "neither observes flow
independently" against the real call graph. Single-observer law is
enforced structurally here (only one call site ever calls
observe_turn()), not just by the turn_id idempotency check --observe()
was also verified to still return False on a same-turn_id repeat
call, so a caller that DID additionally invoke observe_turn() a second
time this same turn would still be safely absorbed.

Two more scope-limited deviations, also logged here rather than
silently absorbed:

  - ivm_phase (TopologyFrame field, P3 observation firewall) has no
    reliable source at this wiring point without deeper plumbing this
    phase didn't have budget for. Left {} (never fabricated) --
    matches the existing "skip, never fake" degradation convention.
  - The "Understanding contract" extension (distinguishing "don't
    understand topic" / "understand base, not this organization" /
    "two plausible organizations") is implemented here as
    understanding_classification() rather than as a change to
    aurora_understanding_contract.py's live RuntimeUnderstandingContract
    class -- that file is foundational and already has real callers;
    editing it was judged higher-risk than this phase's budget
    justified. The classification is fully computed and available on
    every CoordinatorSnapshot; wiring it into the contract's own
    stored state is left for a future phase.
"""
from __future__ import annotations

import json
import os
import sys
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Deque, Dict, Optional, Sequence, Tuple

from .cers_tensor_locator import resolve_pressure_coordinate
from .semantic_variant_registry import SemanticVariantRegistry, SemanticVariantMatch
from .topology_frame import AXES, TopologyFrame
from .topology_tracker import TopologyTracker, WINDOW_SCALES

SHADOW_COMPARISON_FILENAME = "mtsl_shadow_comparison.jsonl"

# Which multi-scale window drives semantic-variant matching. micro is too
# tick-noisy, developmental too slow to ever produce a fresh match within a
# session; meso is the balance point. First-pass choice, not spec-pinned.
_SV_MATCH_SCALE = "meso"

_BASE_MEANING_FLOOR = 0.5  # axis activation floor for deriving a BMF from adjusted_axes


def _get_tcl_class():
    """Lazy import of the repo-root toroidal circulation module, same
    sys.path pattern cers_tensor_locator.py uses for
    aurora_constraint_manifold_router -- avoids an import-time
    dependency from this self-contained package on repo-root modules."""
    try:
        _core = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
        if _core not in sys.path:
            sys.path.insert(0, _core)
        from aurora_toroidal_circulation import ToroidalCirculationLayer
        return ToroidalCirculationLayer
    except Exception:
        return None


def _get_meaning_evolution():
    try:
        from ..aurora_meaning_evolution import canonical_signature, rank_meaning_profiles
        return canonical_signature, rank_meaning_profiles
    except Exception:
        return None, None


@dataclass(frozen=True)
class CoordinatorSnapshot:
    schema_version: int
    turn_id: str
    timestamp: float
    fresh_observation: bool
    manifold_slot_id: Optional[str]
    base_meaning_form: Optional[str]
    topology_signatures: Dict[str, Dict[str, Any]]     # scale -> TopologySignature.to_dict()
    dominant_scale: str
    semantic_variant_id: Optional[str]
    semantic_variant_status: Optional[str]
    variant_confidence: Optional[float]
    variant_created: bool
    variant_match_score: Optional[float]
    toroidal_signature: Dict[str, Any]                  # legacy TCL's own ToroidalSignature.to_dict()
    understanding_classification: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "turn_id": self.turn_id,
            "timestamp": self.timestamp,
            "fresh_observation": self.fresh_observation,
            "manifold_slot_id": self.manifold_slot_id,
            "base_meaning_form": self.base_meaning_form,
            "topology_signatures": self.topology_signatures,
            "dominant_scale": self.dominant_scale,
            "semantic_variant_id": self.semantic_variant_id,
            "semantic_variant_status": self.semantic_variant_status,
            "variant_confidence": self.variant_confidence,
            "variant_created": self.variant_created,
            "variant_match_score": self.variant_match_score,
            "toroidal_signature": self.toroidal_signature,
            "understanding_classification": self.understanding_classification,
        }


SCHEMA_VERSION = 1


def _derive_base_meaning_form(adjusted_axes: Dict[str, float], canonical_signature) -> str:
    if canonical_signature is None:
        return "0"
    active = [ax for ax in AXES if float(adjusted_axes.get(ax, 0.0) or 0.0) >= _BASE_MEANING_FLOOR]
    return canonical_signature(active)


def _classify_understanding(
    *,
    base_forms: Sequence[Dict[str, Any]],
    variant_match: Optional[SemanticVariantMatch],
    ts_regime: str,
) -> str:
    """Three-way distinction the directive's understanding-contract
    extension (spec 14) asks for, computed but not (yet) wired into
    aurora_understanding_contract.py's own stored state -- see the
    module docstring's directive-amendment note."""
    if not base_forms:
        return "no_topic"
    if variant_match is None:
        return "base_only"
    if variant_match.family_linked:
        return "ambiguous_organization"
    return "resolved"


class TopologicalSemanticCoordinator:
    """Single runtime entry for topology/SV observation. Idempotent by
    turn_id (single-observer law): a repeat call with the same turn_id
    returns the cached latest_snapshot rather than re-observing."""

    def __init__(self, state_dir: Optional[str] = None) -> None:
        self._state_dir = str(state_dir) if state_dir else None
        self._tracker = TopologyTracker(state_dir=self._state_dir)
        self._registry = SemanticVariantRegistry(state_dir=self._state_dir)
        _TCL = _get_tcl_class()
        self._tcl = None
        if _TCL is not None:
            try:
                self._tcl = _TCL(state_dir=self._state_dir)
                if self._tcl.stats().get("observations", 0) == 0:
                    self._tcl.seed_from_surface_log()
            except Exception:
                self._tcl = None
        self._tcl_class = _TCL

        self.last_observed_turn_id: Optional[str] = None
        self.latest_snapshot: Optional[CoordinatorSnapshot] = None
        self._last_adjusted_axes: Dict[str, float] = {}
        self._observation_log: Deque[Dict[str, Any]] = deque(maxlen=200)

        self._shadow_log_path = (
            os.path.join(self._state_dir, SHADOW_COMPARISON_FILENAME) if self._state_dir else None
        )

    # ── audit ──

    @property
    def observation_count(self) -> int:
        return len(self._observation_log)

    @property
    def double_observation_rate(self) -> float:
        """Fraction of observe_turn() calls that were a repeat of the
        already-cached turn_id (idempotency absorbed a would-be double
        tick) rather than a genuinely fresh turn. 0.0 in the intended
        wiring (exactly one call site ever calls observe_turn())."""
        if not self._observation_log:
            return 0.0
        repeats = sum(1 for e in self._observation_log if not e.get("fresh", True))
        return round(repeats / len(self._observation_log), 4)

    # ── observation (single call site: ConsciousnessEngine._attach_dual_strata_snapshot) ──

    def observe_turn(
        self,
        *,
        turn_id: str,
        timestamp: float,
        adjusted_axes: Dict[str, float],
        sub_crests: Sequence[Any] = (),
        context_family: Optional[str] = None,
        dps: Any = None,
    ) -> CoordinatorSnapshot:
        if turn_id and turn_id == self.last_observed_turn_id and self.latest_snapshot is not None:
            self._observation_log.append({"turn_id": turn_id, "fresh": False, "ts": time.time()})
            return self.latest_snapshot

        adjusted_axes = dict(adjusted_axes or {})
        canonical_signature, rank_meaning_profiles = _get_meaning_evolution()

        coord = None
        try:
            coord = resolve_pressure_coordinate(adjusted_axes, tuple(sub_crests or ()))
        except Exception:
            coord = None
        manifold_slot_id = coord.slot_id if coord is not None else None
        base_meaning_form = _derive_base_meaning_form(adjusted_axes, canonical_signature)

        frame = TopologyFrame.from_vectors(
            turn_id=turn_id,
            timestamp=timestamp,
            constraint_vector=adjusted_axes,
            previous_vector=self._last_adjusted_axes,
            manifold_slot_id=manifold_slot_id,
            base_meaning_form=base_meaning_form,
            ivm_phase={},  # never fabricated -- see module docstring
            context_family=context_family,
        )
        self._tracker.observe(frame)
        try:
            self._tracker.save()
        except Exception:
            pass

        toroidal_signature: Dict[str, Any] = {}
        if self._tcl is not None:
            try:
                intensity = self._tcl_class.intensity_from_crests(tuple(sub_crests or ()))
                self._tcl.observe(intensity)
                self._tcl.save()
                toroidal_signature = self._tcl.current_signature().to_dict()
            except Exception:
                toroidal_signature = {}

        signatures = self._tracker.signatures()
        ts_for_matching = signatures.get(_SV_MATCH_SCALE)

        variant_match: Optional[SemanticVariantMatch] = None
        if manifold_slot_id is not None and dps is not None:
            try:
                variant_match = self._registry.match_or_create(
                    manifold_slot_id=manifold_slot_id,
                    base_meaning_form=base_meaning_form,
                    ts=ts_for_matching,
                    context_family=context_family,
                    dps=dps,
                )
            except Exception:
                variant_match = None
        if variant_match is not None:
            try:
                self._registry.save_index()
            except Exception:
                pass

        base_forms = []
        if rank_meaning_profiles is not None:
            try:
                base_forms = rank_meaning_profiles(adjusted_axes)
            except Exception:
                base_forms = []

        understanding = _classify_understanding(
            base_forms=base_forms,
            variant_match=variant_match,
            ts_regime=(ts_for_matching.regime if ts_for_matching is not None else "quiescent"),
        )

        snapshot = CoordinatorSnapshot(
            schema_version=SCHEMA_VERSION,
            turn_id=turn_id,
            timestamp=timestamp,
            fresh_observation=True,
            manifold_slot_id=manifold_slot_id,
            base_meaning_form=base_meaning_form,
            topology_signatures={scale: sig.to_dict() for scale, sig in signatures.items()},
            dominant_scale=_SV_MATCH_SCALE,
            semantic_variant_id=(variant_match.variant.variant_id if variant_match else None),
            semantic_variant_status=(variant_match.variant.status if variant_match else None),
            variant_confidence=(variant_match.variant.confidence if variant_match else None),
            variant_created=bool(variant_match.created) if variant_match else False,
            variant_match_score=(variant_match.score if variant_match else None),
            toroidal_signature=toroidal_signature,
            understanding_classification=understanding,
        )

        self.last_observed_turn_id = turn_id
        self.latest_snapshot = snapshot
        self._last_adjusted_axes = adjusted_axes
        self._observation_log.append({"turn_id": turn_id, "fresh": True, "ts": time.time()})

        self._log_shadow_comparison(base_forms=base_forms, snapshot=snapshot)

        return snapshot

    # ── meaning shadow (computed + logged only, never authoritative) ──

    def _log_shadow_comparison(self, *, base_forms: Sequence[Dict[str, Any]], snapshot: CoordinatorSnapshot) -> None:
        if not self._shadow_log_path:
            return
        dominant_base_form = dict(base_forms[0]) if base_forms else {}
        entry = {
            "ts": snapshot.timestamp,
            "turn_id": snapshot.turn_id,
            "base_forms": [dict(f) for f in base_forms],
            "dominant_base_form": dominant_base_form,
            "semantic_variants": (
                [snapshot.semantic_variant_id] if snapshot.semantic_variant_id else []
            ),
            "dominant_semantic_variant": snapshot.semantic_variant_id,
            "variant_confidence": snapshot.variant_confidence,
            "semantic_ambiguity": snapshot.understanding_classification == "ambiguous_organization",
            "agrees_base_vs_variant": bool(
                dominant_base_form.get("signature") == snapshot.base_meaning_form
            ) if dominant_base_form else None,
        }
        try:
            os.makedirs(self._state_dir, exist_ok=True)
            with open(self._shadow_log_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, sort_keys=True) + "\n")
        except Exception:
            pass

    # ── post-turn outcome plumbing (no authority: nothing calls this yet) ──

    def record_turn_outcome(self, *, positive: bool, dps: Any = None) -> Optional[Any]:
        """Route an outcome judgment to the last-matched semantic
        variant. Exposed plumbing only -- deciding what counts as a
        positive/negative outcome is Phase 4/5's job, not this
        coordinator's. Nothing in Phase 3's wiring calls this."""
        snap = self.latest_snapshot
        if snap is None or snap.manifold_slot_id is None or snap.semantic_variant_id is None or dps is None:
            return None
        # semantic_variant_id is "<manifold_slot_id>:<topology_id>", but
        # manifold_slot_id itself contains ":" (e.g. "MANIFOLD:X:NC[...]xNC[...]"),
        # so split off only the trailing topology_id by removing the known
        # manifold_slot_id prefix rather than a naive split(":")[-1].
        prefix = f"{snap.manifold_slot_id}:"
        if not snap.semantic_variant_id.startswith(prefix):
            return None
        topology_id = snap.semantic_variant_id[len(prefix):]
        return self._registry.record_outcome(dps, snap.manifold_slot_id, topology_id, positive=positive)
