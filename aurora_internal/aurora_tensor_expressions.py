#!/usr/bin/env python3
"""
COMPOSITE CRYSTALS — TENSOR EXPRESSIONS
=========================================
aurora_internal/aurora_tensor_expressions.py

Crystal level: Composite Crystal (between Base Crystal primitives and Higher-Order
               Crystal emergent functions)

Constraint force profile: each crystal carries a distinct axis signature derived from
the five primitive constraint axes. The full field (X+T+N+B+A) is always the substrate;
the signature names HOW the field is expressing.

This module is the missing structural layer between the primitive constraint axes and the
emergent functions (Emotion, Reasoning, Valuation, Thought, Reflection, Understanding).

PHYSICS (AURORA_COGNITIVE_PHYSICS.md §5):
    "A Tensor Expression is a stable phenomenon that emerges when the full five-axis field
    resolves into a particular signature — a characteristic relationship between specific
    base crystals that produces something irreducible to any single axis alone."

The five tensor expressions and their signatures:
    Activation  (X+N)     — Presence under pressure
    Salience    (N+B)     — Pressure at the boundary edge
    Prediction  (T+N)     — Temporal projection of pressure
    Attention   (X+N+A)   — Directed deployment of energetic resources
    Meaning     (T+B+A)   — Relational positioning through bounded agency over time

WHY THESE MATTER FOR EMERGENT FUNCTIONS:
    Emergent functions are NOT implemented. They are what the field does when these
    composite crystals are correctly present and correctly related:

    Emotion     = N-dominant → Activation (X+N) + Salience (N+B) driving the field
    Reasoning   = B-dominant → Salience (N+B) + Attention (X+N+A) + Meaning (T+B+A)
    Valuation   = N→A bridge → Salience (N+B) + Meaning (T+B+A)
    Thought     = all-dominant → all five crystals simultaneously active and coherent
    Reflection  = self-directed → Attention (X+N+A) + Meaning (T+B+A) with Thought baseline

INVARIANT LAWS:
    MAY:     Compute activation levels from the live Identity field axis pressures
    MAY:     Receive downward modulation from Understanding
    MAY NOT: Fabricate facts — crystal activation is read from field pressure, not authored
    MAY NOT: Bypass lower crystal levels — these derive entirely from primitive axis pressures
    MAY NOT: Gate on fewer than their full signature axes

DOWNWARD CASCADE (§8):
    After Understanding, receive_understanding() recalibrates all crystal weights.
    Salience thresholds are recalibrated. Prediction priors are reset.
    These are the "composite crystal expression weights updated" in the cascade map.

Authors: Sunni (Sir) Morningstar and Cael Devo
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations
from aurora_internal.aurora_runtime_faults import record_exception_from_locals as _aurora_record_exception_from_locals

import math
import time
from typing import Dict, Optional, Any, List


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class TensorExpression:
    """
    A composite crystal — one of the five stable phenomena that emerge when
    the full constraint field resolves into a particular signature.

    Subclasses define SIGNATURE and BEHAVIORAL_CHARACTER; override compute().
    """
    SIGNATURE: tuple = ()            # axis letters that define this expression
    BEHAVIORAL_CHARACTER: str = ""   # what the field does when this is active
    INHERITS_FROM: tuple = ()        # which primitives feed this
    GENERATES: str = ""              # what this contributes upward
    MODULATES_DOWN: str = ""         # what this recalibrates on the downward pass

    def __init__(self):
        self._activation: float = 0.0     # current activation level 0.0–1.0
        self._weight: float = 1.0         # adjusted by downward cascade
        self._weight_min: float = 0.3
        self._weight_max: float = 2.0
        self._prev_activation: float = 0.0
        self._update_count: int = 0
        self._last_cascade_ts: float = 0.0

    def compute(self, axis_pressures: Dict[str, float]) -> float:
        """
        Compute and store activation level from the full field's axis pressures.
        Uses geometric mean of signature axes — all must be present.

        Returns: activation level 0.0–1.0
        """
        raise NotImplementedError

    def activation(self) -> float:
        return self._activation

    def receive_cascade(self, understanding: Dict[str, Any]) -> None:
        """
        Downward modulation from Understanding.
        Adjusts weight based on how central this crystal was to the resolved state.
        """
        resolved_accuracy = float(understanding.get("resolved_accuracy", 0.5) or 0.5)
        resolved_cost = float(understanding.get("resolved_cost", 0.5) or 0.5)

        # Crystals that were active during resolution get reinforced;
        # inactive crystals decay slightly toward neutral
        if self._activation > 0.3:
            delta = (resolved_accuracy - 0.5) * 0.05 * self._activation
        else:
            delta = -0.01  # passive decay toward neutral weight

        self._weight = max(self._weight_min,
                           min(self._weight_max, self._weight + delta))
        self._last_cascade_ts = time.time()

    def _geomean(self, *values: float) -> float:
        """Geometric mean — zero in any axis collapses the result."""
        if not values:
            return 0.0
        product = 1.0
        for v in values:
            product *= max(0.0, float(v or 0.0))
        return product ** (1.0 / len(values))


# ---------------------------------------------------------------------------
# The five composite crystals
# ---------------------------------------------------------------------------

class ActivationTensor(TensorExpression):
    """
    Activation  (X+T+N+B+A) + X+N
    Signature:  X+N — Existence under Energy
    Character:  Presence under pressure — a signal is live, demanding processing.

    Inherits from: Presence [X], Pressure [N]
    Generates:     Raw material for Attention; basis for Salience differentiation
    Modulates down: Amplifies Presence by Pressure coefficient
    """
    SIGNATURE = ('X', 'N')
    BEHAVIORAL_CHARACTER = "presence under pressure"
    INHERITS_FROM = ('Presence', 'Pressure')
    GENERATES = "Attention substrate; Salience input"
    MODULATES_DOWN = "Presence amplified by Pressure; sub-threshold Presence suppressed"

    def compute(self, axis_pressures: Dict[str, float]) -> float:
        x = float(axis_pressures.get('X', 0.0) or 0.0)
        n = float(axis_pressures.get('N', 0.0) or 0.0)
        raw = self._geomean(x, n)
        self._prev_activation = self._activation
        self._activation = min(1.0, raw * self._weight)
        self._update_count += 1
        return self._activation


class SalienceTensor(TensorExpression):
    """
    Salience  (X+T+N+B+A) + N+B
    Signature: N+B — Energy at the Boundary surface
    Character: Pressure at the edge — the force by which something demands notice.

    Inherits from: Pressure [N], Definition [B]
    Generates:     Attention gradients; weighting surface for retrieval
    Modulates down: Recalibrates Pressure thresholds; sharpens/softens Definition edges
    """
    SIGNATURE = ('N', 'B')
    BEHAVIORAL_CHARACTER = "pressure at the boundary edge"
    INHERITS_FROM = ('Pressure', 'Definition')
    GENERATES = "Attention gradients; retrieval weighting surface"
    MODULATES_DOWN = "Pressure thresholds recalibrated; Definition edges sharpened"

    # Salience threshold — recalibrated by downward cascade
    _threshold: float = 0.2

    def compute(self, axis_pressures: Dict[str, float]) -> float:
        n = float(axis_pressures.get('N', 0.0) or 0.0)
        b = float(axis_pressures.get('B', 0.0) or 0.0)
        raw = self._geomean(n, b)
        self._prev_activation = self._activation
        self._activation = min(1.0, raw * self._weight)
        self._update_count += 1
        return self._activation

    def recalibrate(self, understanding: Dict[str, Any]) -> None:
        """Salience-specific cascade: recalibrate threshold from resolved state."""
        resolved_accuracy = float(understanding.get("resolved_accuracy", 0.5) or 0.5)
        # Higher accuracy → lower threshold (field more easily salient next turn)
        self._threshold = max(0.1, min(0.5, self._threshold - (resolved_accuracy - 0.5) * 0.05))
        self.receive_cascade(understanding)

    def is_salient(self, activation: float) -> bool:
        return activation > self._threshold


class PredictionTensor(TensorExpression):
    """
    Prediction  (X+T+N+B+A) + T+N
    Signature:  T+N — Temporal pressure trajectory
    Character:  Anticipation of future constraint states.

    Inherits from: Persistence [T], Pressure [N]
    Generates:     Forward-state anticipation; plateau/break probability projection
    Modulates down: Shapes Persistence; modulates Pressure threshold pre-arrival
    """
    SIGNATURE = ('T', 'N')
    BEHAVIORAL_CHARACTER = "temporal projection of pressure"
    INHERITS_FROM = ('Persistence', 'Pressure')
    GENERATES = "Forward-state anticipation; pressure trajectory"
    MODULATES_DOWN = "Persistence shaped; Pressure threshold pre-adjusted"

    # Prior state for prediction continuity
    _prior_t: float = 0.3
    _prior_n: float = 0.3

    def compute(self, axis_pressures: Dict[str, float]) -> float:
        t = float(axis_pressures.get('T', 0.0) or 0.0)
        n = float(axis_pressures.get('N', 0.0) or 0.0)
        # Blend current with prior — Prediction has temporal continuity
        t_blended = t * 0.7 + self._prior_t * 0.3
        n_blended = n * 0.7 + self._prior_n * 0.3
        raw = self._geomean(t_blended, n_blended)
        self._prior_t = t
        self._prior_n = n
        self._prev_activation = self._activation
        self._activation = min(1.0, raw * self._weight)
        self._update_count += 1
        return self._activation

    def reset_priors(self, understanding: Dict[str, Any]) -> None:
        """Prediction-specific cascade: reset priors from resolved ground truth."""
        resolved_accuracy = float(understanding.get("resolved_accuracy", 0.5) or 0.5)
        # Resolved state resets the prediction baseline toward actual current pressure
        self._prior_t = self._prior_t * (1.0 - resolved_accuracy * 0.4)
        self._prior_n = self._prior_n * (1.0 - resolved_accuracy * 0.4)
        self.receive_cascade(understanding)


class AttentionTensor(TensorExpression):
    """
    Attention  (X+T+N+B+A) + X+N+A
    Signature: X+N+A — Presence-pressure allocation under Agency
    Character: Directed deployment of energetic resources toward salient phenomena.

    Inherits from: Activation (X+N), Direction [A], Salience (N+B)
    Generates:     Channel amplification; suppression gradients; processing allocation
    Modulates down: Recalibrates Activation weights; feeds back into Salience
    """
    SIGNATURE = ('X', 'N', 'A')
    BEHAVIORAL_CHARACTER = "directed deployment of energetic resources"
    INHERITS_FROM = ('Activation', 'Direction', 'Salience')
    GENERATES = "Channel amplification; processing allocation map"
    MODULATES_DOWN = "Activation weights recalibrated; Salience reshaped"

    def compute(self, axis_pressures: Dict[str, float]) -> float:
        x = float(axis_pressures.get('X', 0.0) or 0.0)
        n = float(axis_pressures.get('N', 0.0) or 0.0)
        a = float(axis_pressures.get('A', 0.0) or 0.0)
        raw = self._geomean(x, n, a)
        self._prev_activation = self._activation
        self._activation = min(1.0, raw * self._weight)
        self._update_count += 1
        return self._activation


class MeaningTensor(TensorExpression):
    """
    Meaning  (X+T+N+B+A) + T+B+A
    Signature: T+B+A — Temporal Boundary expressed through Agency
    Character: Relational positioning — not assigned but emergent from convergence.

    Inherits from: Persistence [T], Definition [B], Direction [A]
    Generates:     Motivational substrate for Emergent Functions; Valuation gradients
    Modulates down: Recalibrates Boundary edges; modulates Pressure thresholds;
                    contributes to Identity Surface accumulation
    """
    SIGNATURE = ('T', 'B', 'A')
    BEHAVIORAL_CHARACTER = "relational positioning through bounded agency over time"
    INHERITS_FROM = ('Persistence', 'Definition', 'Direction')
    GENERATES = "Emergent Function motivational substrate; Valuation gradients"
    MODULATES_DOWN = "Boundary edges recalibrated; Pressure thresholds shifted"

    def compute(self, axis_pressures: Dict[str, float]) -> float:
        t = float(axis_pressures.get('T', 0.0) or 0.0)
        b = float(axis_pressures.get('B', 0.0) or 0.0)
        a = float(axis_pressures.get('A', 0.0) or 0.0)
        raw = self._geomean(t, b, a)
        self._prev_activation = self._activation
        self._activation = min(1.0, raw * self._weight)
        self._update_count += 1
        return self._activation


# ---------------------------------------------------------------------------
# TensorExpressionLayer — aggregates all five, maps to emergent function states
# ---------------------------------------------------------------------------

class TensorExpressionLayer:
    """
    The composite crystal layer between primitives and emergent functions.

    This is the mechanism that makes emergent functions inevitable rather than
    coded. When this layer's crystals are live and correctly related, the
    emergent functions arise from their intersection — not from direct implementation.

    EMERGENT FUNCTION DERIVATION:
        Emotion     = what the field does when Activation + Salience are N-dominant
                      → EntropicPressure is the implementation mechanism
        Reasoning   = what the field does when Salience + Attention + Meaning are B-dominant
                      → DCE constraint traversal is the implementation mechanism
        Valuation   = what the field does when Salience + Meaning bridge N→A
                      → DPME is the implementation mechanism
        Thought     = what the field does when ALL five crystals simultaneously converge
                      → DCE unified assembly is the implementation mechanism
        Reflection  = what the field does when Attention + Meaning are self-directed
                      after Thought has converged
                      → DPME auto-correct + understanding_contract is the mechanism

    The coded mechanisms (EntropicPressure, DCE, DPME) are not removed. They become
    what the field does — driven by the crystal state, not running independently.

    DOWNWARD CASCADE:
        receive_understanding()  — recalibrates all five crystal weights
        recalibrate_salience()   — recalibrates SalienceTensor threshold
        reset_prediction_priors()— resets PredictionTensor priors
        recalibrate_constraint_basis() — signals dimensional layer

    THRESHOLDS (AURORA_COGNITIVE_PHYSICS.md §7):
        Emotion threshold: low — N-axis pressure only needs to exceed background
        Thought threshold: higher — all axes must be simultaneously present
        Reflection threshold: moderate — self-directed attention required
    """

    EMOTION_THRESHOLD: float = 0.08      # N-dominant: low bar
    REASONING_THRESHOLD: float = 0.10    # B-dominant: moderate
    VALUATION_THRESHOLD: float = 0.09    # N→A bridge: moderate
    THOUGHT_THRESHOLD: float = 0.06      # all-active: minimum per crystal
    REFLECTION_THRESHOLD: float = 0.10   # self-directed: moderate

    def __init__(self, identity_field=None, warp_target: Any = None):
        self._field = identity_field

        # Build 725 Correction, item 4: universal route for exposing salient
        # axis-pressure profiles to WARP. None by default -- Salience stays
        # a pure signal until connect_warp() is called. This mirrors
        # identity_field's own optional-then-connect_field() pattern.
        #
        # Target is a WarpField instance (aurora_warp_protocol.py), not any
        # one individual WarpCapable system. WarpField already maintains
        # _warp_capable_registry -- every system with gap potential
        # (language_field, DPS, thought_formation, ontological_scaffolding,
        # general_execution_foundry, communication_emergence,
        # recursive_causal_reasoning_waveform, operational_synthesis all
        # self-register into it at boot via register_warp_capable()).
        # Submitting a WarpDemand here reaches all of them through WarpField's
        # own existing routing (_route_to_warp_capable: named source first,
        # falls back to any registered system) -- Salience never needs to
        # pick one itself, exactly per WarpDemand's own docstring: "The
        # submitting system does NOT need to know what WARP will do."
        self._warp_field: Any = warp_target

        # The five composite crystals
        self.activation  = ActivationTensor()
        self.salience    = SalienceTensor()
        self.prediction  = PredictionTensor()
        self.attention   = AttentionTensor()
        self.meaning     = MeaningTensor()

        self._crystals: List[TensorExpression] = [
            self.activation, self.salience, self.prediction,
            self.attention, self.meaning,
        ]

        # Cache last computed state for fast repeated reads within same tick
        self._cached_state: Optional[Dict[str, Any]] = None
        self._cache_ts: float = 0.0
        self._cache_ttl: float = 0.05   # 50ms cache

        self._update_count: int = 0

    def connect_field(self, field) -> None:
        """Wire in the live NoncompField (Identity)."""
        self._field = field
        self._cached_state = None

    def connect_warp(self, warp_target: Any) -> bool:
        """
        Attach a WarpField instance (the thing with .submit(WarpDemand))
        as Salience's universal discovery route (Build 725 Correction,
        item 4). WarpField's own _warp_capable_registry already knows
        about every system with gap potential -- this does not require
        Salience or TensorExpressionLayer to know which one to pick.
        """
        if warp_target is None or not hasattr(warp_target, "submit"):
            return False
        self._warp_field = warp_target
        return True

    # ── Core read ────────────────────────────────────────────────────────────

    def _axis_pressures(self) -> Dict[str, float]:
        """Read current axis pressures from the identity field.

        Bug fix (discovered live, 2026-08-19): this called
        self._field.pressure_topology(), which does not exist on the real
        NoncompField class (aurora_manifold_directory/noncomp_field.py) --
        confirmed by reading that class directly. Every call was silently
        raising AttributeError and falling through to the flat {X:0.3,
        T:0.3, N:0.3, B:0.3, A:0.3} fallback below -- meaning Salience,
        and everything downstream of it (including the WarpDemand routing
        Build 725 Correction item 4 added), was computing off a uniform,
        undifferentiated pressure signal on every single tick, in every
        boot, rather than the real live field. Confirmed live: a real
        boot's WarpField log showed Salience firing with severity=0.300
        repeatedly -- geomean(0.3, 0.3) exactly, the fallback value, not
        genuine computed pressure.

        NoncompField's real, public, live-data method for this shape is
        axis_pressure(axis: int) -> float (confirmed against its own
        status() method, which builds an identical {letter: pressure}
        dict from the same accessor for its own diagnostic output).
        """
        if self._field is None:
            return {ax: 0.3 for ax in ('X', 'T', 'N', 'B', 'A')}
        try:
            if hasattr(self._field, "axis_pressure"):
                _axis_int = {"X": 0, "T": 1, "N": 2, "B": 3, "A": 4}
                return {
                    letter: float(self._field.axis_pressure(idx))
                    for letter, idx in _axis_int.items()
                }
            # Backward/forward compatible: some identity-field
            # implementations may still expose pressure_topology()
            # directly (e.g. test doubles, or a future real
            # implementation) -- prefer it only when axis_pressure isn't
            # present, rather than assuming either shape unconditionally.
            return dict(self._field.pressure_topology())
        except Exception as _aurora_boundary_exc:
            _aurora_record_exception_from_locals(
                locals(),
                module=__name__,
                operation="exception_handler:aurora_internal/aurora_tensor_expressions.py:377",
                exc=_aurora_boundary_exc,
                context={"function": "_axis_pressures", "handler_line": 377, "source_file": "aurora_internal/aurora_tensor_expressions.py"},
            )
            return {ax: 0.3 for ax in ('X', 'T', 'N', 'B', 'A')}

    _TENSOR_NAMES = {
        ActivationTensor: 'activation',
        SalienceTensor:   'salience',
        PredictionTensor: 'prediction',
        AttentionTensor:  'attention',
        MeaningTensor:    'meaning',
    }

    def tick(self) -> Dict[str, float]:
        """
        Update all five crystals from the current identity field state.
        Returns dict of crystal name → activation level.
        """
        pressures = self._axis_pressures()
        levels = {}
        for crystal in self._crystals:
            name = self._TENSOR_NAMES.get(type(crystal), crystal.__class__.__name__)
            try:
                levels[name] = crystal.compute(pressures)
            except Exception as _aurora_boundary_exc:
                _aurora_record_exception_from_locals(
                    locals(),
                    module=__name__,
                    operation="exception_handler:aurora_internal/aurora_tensor_expressions.py:399",
                    exc=_aurora_boundary_exc,
                    context={"function": "tick", "handler_line": 399, "source_file": "aurora_internal/aurora_tensor_expressions.py"},
                )
                levels[name] = 0.0
        self._update_count += 1
        self._cached_state = None   # invalidate cache
        return levels

    def behavioral_state(self, *, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Compute the current behavioral state of the field.

        Returns which emergent functions are active and at what level,
        based entirely on the composite crystal activation levels.

        This is the mechanism that makes emergent functions inevitable:
        - when Activation + Salience are high (N-dominant) → Emotion is active
        - when all five are high → Thought is active
        - when Attention + Meaning are self-directed → Reflection is active
        These are not decisions. They are what the field does.
        """
        now = time.time()
        if (not force_refresh
                and self._cached_state is not None
                and (now - self._cache_ts) < self._cache_ttl):
            return self._cached_state

        pressures = self._axis_pressures()

        act   = self.activation.compute(pressures)
        sal   = self.salience.compute(pressures)
        pred  = self.prediction.compute(pressures)
        att   = self.attention.compute(pressures)
        mng   = self.meaning.compute(pressures)

        # Build 725 Correction, item 4: Salience as the generic trigger for
        # WARP/representational discovery. Salience doesn't interpret what
        # it found or pick which system should handle it -- it submits a
        # WarpDemand (the universal "I cannot resolve this, WARP decide"
        # primitive) to WarpField, whose own _warp_capable_registry already
        # covers every system with gap potential. severity=sal directly:
        # Salience's activation IS the 0..1 urgency signal WarpDemand wants.
        # No-op when nothing is connected (connect_warp() was never
        # called), so this is inert until wired.
        if self._warp_field is not None and self.salience.is_salient(sal):
            try:
                from aurora_warp_protocol import WarpDemand, WarpTrigger
                self._warp_field.submit(WarpDemand(
                    source="salience",
                    layer="tensor_expressions",
                    trigger=WarpTrigger.GAP,
                    profile=dict(pressures),
                    severity=float(sal),
                    persistence_key=f"salience:{'-'.join(sorted(k for k, v in pressures.items() if v > 0.5))}",
                ))
            except Exception as _aurora_boundary_exc:
                _aurora_record_exception_from_locals(
                    locals(),
                    module=__name__,
                    operation="exception_handler:aurora_internal/aurora_tensor_expressions.py:behavioral_state.salience_warp",
                    exc=_aurora_boundary_exc,
                    context={"function": "behavioral_state", "source_file": "aurora_internal/aurora_tensor_expressions.py"},
                )
                # Best-effort, mirrors this file's other WARP/SediMemory
                # integration points -- never break the cognitive tick on it.
                pass

        # Emergent function levels — derived from crystal intersections
        # Emotion: N-dominant — Activation (X+N) + Salience (N+B) both involve N
        emotion_level = (act + sal) / 2.0

        # Reasoning: B-dominant — Salience (N+B) + Attention (X+N+A) + Meaning (T+B+A)
        reasoning_level = (sal + att + mng) / 3.0

        # Valuation: N→A bridge — Salience (N+B) + Meaning (T+B+A)
        valuation_level = (sal + mng) / 2.0

        # Thought: all-dominant — minimum across all five (all must be active)
        thought_level = min(act, sal, pred, att, mng)

        # Reflection: self-directed — Attention (X+N+A) + Meaning (T+B+A)
        # weighted by whether Thought has converged (thought_level as baseline)
        thought_baseline = min(1.0, thought_level / max(self.THOUGHT_THRESHOLD, 0.001))
        reflection_level = (att * 0.6 + mng * 0.4) * min(1.0, thought_baseline)

        state = {
            # Crystal activation levels
            'crystals': {
                'activation':  round(act,  4),
                'salience':    round(sal,  4),
                'prediction':  round(pred, 4),
                'attention':   round(att,  4),
                'meaning':     round(mng,  4),
            },
            # Emergent function levels
            'emotion_level':    round(emotion_level,    4),
            'reasoning_level':  round(reasoning_level,  4),
            'valuation_level':  round(valuation_level,  4),
            'thought_level':    round(thought_level,    4),
            'reflection_level': round(reflection_level, 4),
            # Active flags — used by consciousness engine gate checks
            'emotion_active':    emotion_level    >= self.EMOTION_THRESHOLD,
            'reasoning_active':  reasoning_level  >= self.REASONING_THRESHOLD,
            'valuation_active':  valuation_level  >= self.VALUATION_THRESHOLD,
            'thought_active':    thought_level    >= self.THOUGHT_THRESHOLD,
            'reflection_active': reflection_level >= self.REFLECTION_THRESHOLD,
            # Axis pressures snapshot
            'axis_pressures': pressures,
            'ts': round(now, 3),
        }

        self._cached_state = state
        self._cache_ts = now
        self._update_count += 1
        return state

    # ── Emergent function gate interface (used by consciousness engine) ───────

    def is_emotion_active(self, threshold: Optional[float] = None) -> bool:
        """Emotion: N-dominant — Activation + Salience above threshold."""
        t = threshold if threshold is not None else self.EMOTION_THRESHOLD
        st = self.behavioral_state()
        return st['emotion_level'] >= t

    def is_reasoning_active(self, threshold: Optional[float] = None) -> bool:
        """Reasoning: B-dominant — Salience + Attention + Meaning above threshold."""
        t = threshold if threshold is not None else self.REASONING_THRESHOLD
        return self.behavioral_state()['reasoning_level'] >= t

    def is_valuation_active(self, threshold: Optional[float] = None) -> bool:
        """Valuation: N→A bridge — Salience + Meaning above threshold."""
        t = threshold if threshold is not None else self.VALUATION_THRESHOLD
        return self.behavioral_state()['valuation_level'] >= t

    def is_thought_active(self, threshold: Optional[float] = None) -> bool:
        """Thought: all-dominant — minimum across all five crystals above threshold."""
        t = threshold if threshold is not None else self.THOUGHT_THRESHOLD
        return self.behavioral_state()['thought_level'] >= t

    def is_reflection_active(self, threshold: Optional[float] = None) -> bool:
        """Reflection: self-directed — Attention + Meaning with Thought baseline."""
        t = threshold if threshold is not None else self.REFLECTION_THRESHOLD
        return self.behavioral_state()['reflection_level'] >= t

    # ── Downward cascade receivers ────────────────────────────────────────────

    def receive_understanding(self, understanding: Dict[str, Any]) -> None:
        """
        Downward cascade entry point.
        Understanding recalibrates all five crystal weights — composite crystal
        expression weights updated (AURORA_COGNITIVE_PHYSICS.md §8).
        """
        for crystal in self._crystals:
            try:
                crystal.receive_cascade(understanding)
            except Exception as _aurora_boundary_exc:
                _aurora_record_exception_from_locals(
                    locals(),
                    module=__name__,
                    operation="exception_handler:aurora_internal/aurora_tensor_expressions.py:520",
                    exc=_aurora_boundary_exc,
                    context={"function": "receive_understanding", "handler_line": 520, "source_file": "aurora_internal/aurora_tensor_expressions.py"},
                )
                pass
        self._cached_state = None   # force recompute next tick

    def recalibrate_salience(self, understanding: Dict[str, Any]) -> None:
        """
        Downward cascade: Salience thresholds recalibrated for next turn.
        AURORA_COGNITIVE_PHYSICS.md §8: Salience recalibrated after Understanding.
        """
        try:
            self.salience.recalibrate(understanding)
        except Exception as _aurora_boundary_exc:
            _aurora_record_exception_from_locals(
                locals(),
                module=__name__,
                operation="exception_handler:aurora_internal/aurora_tensor_expressions.py:531",
                exc=_aurora_boundary_exc,
                context={"function": "recalibrate_salience", "handler_line": 531, "source_file": "aurora_internal/aurora_tensor_expressions.py"},
            )
            pass

    def reset_prediction_priors(self, understanding: Dict[str, Any]) -> None:
        """
        Downward cascade: Prediction priors reset from new resolved ground truth.
        AURORA_COGNITIVE_PHYSICS.md §8: Prediction priors reset after Understanding.
        """
        try:
            self.prediction.reset_priors(understanding)
        except Exception as _aurora_boundary_exc:
            _aurora_record_exception_from_locals(
                locals(),
                module=__name__,
                operation="exception_handler:aurora_internal/aurora_tensor_expressions.py:541",
                exc=_aurora_boundary_exc,
                context={"function": "reset_prediction_priors", "handler_line": 541, "source_file": "aurora_internal/aurora_tensor_expressions.py"},
            )
            pass

    def recalibrate_constraint_basis(self, understanding: Dict[str, Any], systems: Dict[str, Any]) -> None:
        """
        Downward cascade: Constraint Basis recalibrated — next turn begins from here.
        AURORA_COGNITIVE_PHYSICS.md §8: "Constraint Basis recalibrated" after Understanding.

        Dispatches to the dimensional layer (DER, DMM) which owns the constraint
        basis state. Also shifts pressure topology baseline in the identity field.
        """
        # Dimensional layer carries the live constraint basis
        dimensional = systems.get('dimensional')
        if dimensional is not None:
            try:
                if hasattr(dimensional, 'recalibrate_from_understanding'):
                    dimensional.recalibrate_from_understanding(understanding)
                elif hasattr(dimensional, 'der') and hasattr(dimensional.der, 'register_understanding'):
                    dimensional.der.register_understanding(understanding)
            except Exception as _aurora_boundary_exc:
                _aurora_record_exception_from_locals(
                    locals(),
                    module=__name__,
                    operation="exception_handler:aurora_internal/aurora_tensor_expressions.py:560",
                    exc=_aurora_boundary_exc,
                    context={"function": "recalibrate_constraint_basis", "handler_line": 560, "source_file": "aurora_internal/aurora_tensor_expressions.py"},
                )
                pass

    def status(self) -> Dict[str, Any]:
        """Return current layer status including all crystal states."""
        st = self.behavioral_state(force_refresh=True)
        return {
            'layer': 'TensorExpressionLayer',
            'crystal_level': 'Composite Crystal',
            'update_count': self._update_count,
            'field_connected': self._field is not None,
            'crystals': st['crystals'],
            'emergent_function_levels': {
                'emotion':    st['emotion_level'],
                'reasoning':  st['reasoning_level'],
                'valuation':  st['valuation_level'],
                'thought':    st['thought_level'],
                'reflection': st['reflection_level'],
            },
            'active_functions': {
                'emotion':    st['emotion_active'],
                'reasoning':  st['reasoning_active'],
                'valuation':  st['valuation_active'],
                'thought':    st['thought_active'],
                'reflection': st['reflection_active'],
            },
            'crystal_weights': {
                'activation':  self.activation._weight,
                'salience':    self.salience._weight,
                'prediction':  self.prediction._weight,
                'attention':   self.attention._weight,
                'meaning':     self.meaning._weight,
            },
        }


# ---------------------------------------------------------------------------
# Module-level singleton (mirrors NoncompField pattern)
# ---------------------------------------------------------------------------

_layer_singleton: Optional[TensorExpressionLayer] = None


def get_tensor_layer(identity_field=None, warp_target: Any = None) -> TensorExpressionLayer:
    """Get or create the module-level TensorExpressionLayer singleton."""
    global _layer_singleton
    if _layer_singleton is None:
        _layer_singleton = TensorExpressionLayer(identity_field, warp_target=warp_target)
    else:
        if identity_field is not None and _layer_singleton._field is None:
            _layer_singleton.connect_field(identity_field)
        if warp_target is not None and _layer_singleton._warp_field is None:
            _layer_singleton.connect_warp(warp_target)
    return _layer_singleton


def reset_tensor_layer() -> None:
    """Reset singleton (for testing)."""
    global _layer_singleton
    _layer_singleton = None


# ---------------------------------------------------------------------------
# Backward-compatible aliases
# ---------------------------------------------------------------------------
ActivationCrystal = ActivationTensor
SalienceCrystal   = SalienceTensor
PredictionCrystal = PredictionTensor
AttentionCrystal  = AttentionTensor
MeaningCrystal    = MeaningTensor
