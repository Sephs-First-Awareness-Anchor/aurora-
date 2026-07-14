# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_internal/dual_strata/perturbation_probe.py
=====================================================
PerturbationProbe — MTSL Phase 6 (2026-07-13), spec section 8/18.

Occlusion/clamp/delay experiments run ONLY against a copied, replayed
shadow state -- never the live TopologyTracker or
SemanticVariantRegistry. The constructor takes plain TopologyFrame
instances (already side-effect-free plain data by construction --
see topology_frame.py's own docstring: "Plain data only: no live
system references") and defensively asserts they really are that
type, not some live object masquerading as one. TopologyFrame's own
field types (Dict[str, float], str, float, Tuple[str, ...],
Optional[str]) structurally cannot hold a live registry/system
reference, so the isinstance check IS the guarantee -- there is no
live path to check for beyond confirming the type.

FIX-A012 (Simulated Evidence Authority Leak): every PerturbationResult
this module produces is meant to be recorded via
SemanticVariantRegistry.record_simulated_evidence(source="dream"|
"classroom", ...) -- lower authority than lived evidence, stored in
its own facet, never alone sufficient to promote a variant. This
module itself never writes to any registry; it only computes results
a caller chooses to record. Nothing here mutates the frames it was
constructed with, and every perturbed replay runs through a brand-new
TopologyTracker (via from_frames) that is discarded after use --
never the tracker the live turn loop owns.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .topology_frame import AXES, TopologyFrame
from .topology_tracker import TopologySignature, TopologyTracker, WINDOW_SCALES

PERTURBATION_TYPES = ("occlusion", "clamp", "delay")


class LiveReferenceError(TypeError):
    """Raised when the constructor is handed something that isn't a
    plain, already-detached TopologyFrame -- the one hard guarantee
    this module makes."""


def _assert_plain_frames(frames: Sequence[Any]) -> Tuple[TopologyFrame, ...]:
    checked: List[TopologyFrame] = []
    for f in frames:
        if not isinstance(f, TopologyFrame):
            raise LiveReferenceError(
                f"PerturbationProbe requires plain TopologyFrame instances, got {type(f)!r}"
            )
        checked.append(f)
    return tuple(checked)


@dataclass(frozen=True)
class PerturbationResult:
    perturbation_type: str
    axis: str
    parameter: Optional[float]                     # clamp value, delay lag (frames), or None for occlusion
    baseline_signatures: Dict[str, Dict[str, Any]]  # scale -> TopologySignature.to_dict()
    perturbed_signatures: Dict[str, Dict[str, Any]]
    circulation_fraction_delta: Dict[str, float]    # scale -> perturbed - baseline
    regime_changed: Dict[str, bool]                 # scale -> whether the regime label differs

    def to_dict(self) -> Dict[str, Any]:
        return {
            "perturbation_type": self.perturbation_type,
            "axis": self.axis,
            "parameter": self.parameter,
            "baseline_signatures": self.baseline_signatures,
            "perturbed_signatures": self.perturbed_signatures,
            "circulation_fraction_delta": self.circulation_fraction_delta,
            "regime_changed": self.regime_changed,
        }

    def summary_note(self) -> str:
        """Short, human-readable note -- suitable as the `note` passed
        to SemanticVariantRegistry.record_simulated_evidence()."""
        shifted = [scale for scale, changed in self.regime_changed.items() if changed]
        if shifted:
            return f"{self.perturbation_type}({self.axis}) shifted regime at: {', '.join(shifted)}"
        return f"{self.perturbation_type}({self.axis}) did not shift regime at any scale"


def _replay(frames: Sequence[TopologyFrame]) -> Dict[str, TopologySignature]:
    tracker = TopologyTracker.from_frames(frames)
    return tracker.signatures()


def _rebuild_frame(frame: TopologyFrame, new_cv: Dict[str, float], new_prev_cv: Dict[str, float]) -> TopologyFrame:
    """A perturbed frame with a new constraint_vector AND a new
    previous_vector, with delta/crest/trough/active-fields/creation/
    dissipation recomputed honestly from them via
    TopologyFrame.from_vectors -- never hand-edited independently, which
    would desync the frame's own internal consistency and would be a
    second implementation of derivation logic topology_frame.py already
    owns as the single source of truth.

    previous_vector MUST be the perturbed sequence's own preceding
    constraint_vector, not the original frame's previous_vector field --
    otherwise an axis that never actually moved (e.g. occluding an axis
    that was already constant at 0.5 every frame) reads as a fake -0.5
    delta on the FIRST perturbed frame only, because "current" would be
    perturbed while "previous" stayed at the stale original value.
    Callers are responsible for threading this correctly through the
    sequence (see occlude/clamp/delay below)."""
    return TopologyFrame.from_vectors(
        turn_id=frame.turn_id,
        timestamp=frame.timestamp,
        constraint_vector=new_cv,
        previous_vector=new_prev_cv,
        manifold_slot_id=frame.manifold_slot_id,
        base_meaning_form=frame.base_meaning_form,
        ivm_phase=frame.ivm_phase,
        context_family=frame.context_family,
        schema_version=frame.schema_version,
    )


class PerturbationProbe:
    """Constructed once per copied frame sequence; each experiment
    method (occlude/clamp/delay) is a pure computation returning a new
    PerturbationResult -- calling any of them repeatedly with the same
    arguments always returns an equivalent result, and none of them
    mutate the frames this probe was built from."""

    def __init__(self, frames: Sequence[TopologyFrame]) -> None:
        self._frames = _assert_plain_frames(frames)
        self._baseline: Optional[Dict[str, TopologySignature]] = None

    @property
    def frame_count(self) -> int:
        return len(self._frames)

    def _baseline_signatures(self) -> Dict[str, TopologySignature]:
        if self._baseline is None:
            self._baseline = _replay(self._frames)
        return self._baseline

    def _build_chained_perturbation(self, axis: str, value_at: Any) -> List[TopologyFrame]:
        """Shared chaining logic: value_at(i) returns the perturbed
        axis value for frame i. Each frame's previous_vector is built
        from the PRECEDING frame's own perturbed constraint_vector (or,
        for frame 0, the original previous_vector with this axis
        overridden to value_at(0) -- consistent with "nothing before
        the sequence changed due to this axis either"), never the
        original frame's stale previous_vector field. This is what
        makes deltas on every OTHER axis exactly as they were in the
        unperturbed replay -- only this one axis's contribution to flow
        actually changes."""
        perturbed_frames: List[TopologyFrame] = []
        prev_cv = dict(self._frames[0].previous_vector) if self._frames else {a: 0.0 for a in AXES}
        prev_cv[axis] = value_at(0)
        for i, f in enumerate(self._frames):
            cv = dict(f.constraint_vector)
            cv[axis] = value_at(i)
            perturbed_frames.append(_rebuild_frame(f, cv, prev_cv))
            prev_cv = cv
        return perturbed_frames

    def occlude(self, axis: str) -> PerturbationResult:
        """Hide this axis's pressure entirely (held at 0.0 for every
        frame) and observe how the topology reorganizes without it."""
        if axis not in AXES:
            raise ValueError(f"unknown axis: {axis!r}")
        perturbed_frames = self._build_chained_perturbation(axis, lambda i: 0.0)
        return self._compare("occlusion", axis, None, perturbed_frames)

    def clamp(self, axis: str, value: float) -> PerturbationResult:
        """Fix this axis at a constant value across every frame."""
        if axis not in AXES:
            raise ValueError(f"unknown axis: {axis!r}")
        clipped = max(0.0, min(1.0, float(value)))
        perturbed_frames = self._build_chained_perturbation(axis, lambda i: clipped)
        return self._compare("clamp", axis, clipped, perturbed_frames)

    def delay(self, axis: str, lag: int) -> PerturbationResult:
        """Shift this axis's value series back by `lag` frames (frame i
        sees the value that axis had at frame max(0, i - lag)),
        desynchronizing it from the other four axes without touching
        their own timing."""
        if axis not in AXES:
            raise ValueError(f"unknown axis: {axis!r}")
        if lag < 0:
            raise ValueError("lag must be >= 0")
        series = [f.constraint_vector.get(axis, 0.0) for f in self._frames]
        perturbed_frames = self._build_chained_perturbation(axis, lambda i: series[max(0, i - lag)])
        return self._compare("delay", axis, float(lag), perturbed_frames)

    def _compare(
        self, perturbation_type: str, axis: str, parameter: Optional[float],
        perturbed_frames: Sequence[TopologyFrame],
    ) -> PerturbationResult:
        baseline = self._baseline_signatures()
        perturbed = _replay(perturbed_frames)
        circ_delta: Dict[str, float] = {}
        regime_changed: Dict[str, bool] = {}
        for scale in WINDOW_SCALES:
            b = baseline.get(scale)
            p = perturbed.get(scale)
            if b is None or p is None:
                continue
            circ_delta[scale] = round(p.circulation_fraction - b.circulation_fraction, 4)
            regime_changed[scale] = (p.regime != b.regime)
        return PerturbationResult(
            perturbation_type=perturbation_type,
            axis=axis,
            parameter=parameter,
            baseline_signatures={s: sig.to_dict() for s, sig in baseline.items()},
            perturbed_signatures={s: sig.to_dict() for s, sig in perturbed.items()},
            circulation_fraction_delta=circ_delta,
            regime_changed=regime_changed,
        )


def record_probe_evidence(
    registry: Any,
    dps: Any,
    result: PerturbationResult,
    *,
    manifold_slot_id: str,
    topology_id: str,
    source: str,
) -> Any:
    """Thin, tested connector between a PerturbationResult and
    SemanticVariantRegistry.record_simulated_evidence() -- the storage
    side of FIX-A012 that Phase 2 already built. `registry` is a
    SemanticVariantRegistry instance (typed Any here to avoid this
    module importing semantic_variant_registry.py, which would invert
    the natural producer/consumer direction). Returns whatever
    record_simulated_evidence() returns (None if the target variant
    doesn't exist yet -- this never creates one).

    Deliberately NOT called from anywhere in this module: wiring a live
    dream/classroom call site to actually invoke a perturbation
    experiment and record its result is a separate, deeper integration
    task deferred out of this phase's scope (see the directive-amendment
    note in this module's own commit message for the exact hook points
    identified in aurora_quantum_dream_substrate.py,
    aurora_dream_trainer.py, and aurora_classroom.py) -- this function
    is the ready-to-call bridge a future phase's live wiring would use.
    """
    if registry is None or not hasattr(registry, "record_simulated_evidence"):
        return None
    return registry.record_simulated_evidence(
        dps, manifold_slot_id, topology_id,
        source=source, note=result.summary_note(),
    )
