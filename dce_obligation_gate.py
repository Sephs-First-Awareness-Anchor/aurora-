#!/usr/bin/env python3
"""
DCE OBLIGATION GATE
===================
Implements the Obligation Law from OBLIGATION_LAW.md.

Architecture:
    Subsurface  =  pressure reservoir  (holds all latent tensions)
    DCE         =  pressure gate       (this module — selects, evaluates, obligates)
    Surface     =  obligation executor (executes only what DCE authorizes)

Core truth:
    DCE does not grant permission. DCE creates obligation.
    Surface does not choose what to explore. Surface executes what must be resolved.

The three axes (all must clear — failure at one invalidates the target):
    1. Pressure Strength  — Is the tension real and meaningful? Not curiosity. Not noise.
    2. Worth              — Will resolving this change anything meaningful? Does it propagate?
    3. Context Validity   — Is this the right time to act?

Critical principle:
    Premature action is worse than delayed action.
    Premature = polluted system state.
    Delayed   = preserved integrity.

Authors: Sunni (Sir) Morningstar
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# THRESHOLDS
# ---------------------------------------------------------------------------

PRESSURE_THRESHOLD = 0.40   # Minimum pressure strength to be considered real
WORTH_THRESHOLD    = 0.35   # Minimum worth — must propagate meaningfully
CONTEXT_THRESHOLD  = 0.50   # Minimum context validity — must be right now
MAX_ACTIVE_TARGETS = 3      # DCE selects at most this many at once


# ---------------------------------------------------------------------------
# DATA STRUCTURES
# ---------------------------------------------------------------------------

@dataclass
class LatentTension:
    """
    A single unresolved element held by Subsurface.

    Most tensions stay here permanently — latency is stability, not failure.
    Only tensions that pass DCE evaluation ever become targets.
    """
    id: str
    question: str                          # The unresolved question or hypothesis
    context: str = ""                      # What produced this tension
    pressure: float = 0.0                  # 0.0–1.0: how real and meaningful is this gap
    worth: float = 0.0                     # 0.0–1.0: propagation potential of resolution
    cost: float = 0.1                      # 0.0–1.0: resource cost of acting
    context_validity: float = 1.0          # 0.0–1.0: is this the right moment
    resolution_criteria: str = ""          # What counts as resolved
    exploration_hints: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_evaluated_at: float = 0.0


@dataclass
class ObligationTarget:
    """
    A tension that passed all three DCE axes and is now an obligation for Surface.

    Surface must execute this. Not permission — obligation.
    """
    tension: LatentTension
    obligation_score: float                # Combined score that cleared the gate
    authorized_at: float = field(default_factory=time.time)
    channels: List[str] = field(default_factory=list)  # Allowed exploration channels

    @property
    def id(self) -> str:
        return self.tension.id

    @property
    def question(self) -> str:
        return self.tension.question

    @property
    def resolution_criteria(self) -> str:
        return self.tension.resolution_criteria


@dataclass
class EvaluationResult:
    """
    Detailed result of a single tension passing through the DCE gate.
    """
    tension_id: str
    authorized: bool
    pressure_score: float
    worth_score: float
    context_score: float
    cost: float
    obligation_score: float
    rejection_axis: Optional[str]          # Which axis failed, if any
    rejection_reason: str = ""


# ---------------------------------------------------------------------------
# DCE OBLIGATION GATE
# ---------------------------------------------------------------------------

class DCEObligationGate:
    """
    The only layer allowed to convert subsurface pressure into surface obligation.

    Subsurface hands the full tension reservoir here.
    DCE evaluates each tension against three axes.
    Only tensions that clear all three axes become obligations.
    Surface receives only obligations — never raw tension.

    Failure modes this prevents:
        Too permissive  → lower thresholds, Surface floods
        Too restrictive → raise thresholds, system stagnates
        Context-blind   → context_validity axis ignored
    """

    def __init__(
        self,
        pressure_threshold: float = PRESSURE_THRESHOLD,
        worth_threshold: float = WORTH_THRESHOLD,
        context_threshold: float = CONTEXT_THRESHOLD,
        max_active: int = MAX_ACTIVE_TARGETS,
    ) -> None:
        self.pressure_threshold = pressure_threshold
        self.worth_threshold = worth_threshold
        self.context_threshold = context_threshold
        self.max_active = max_active

    # ------------------------------------------------------------------
    # PUBLIC INTERFACE
    # ------------------------------------------------------------------

    def evaluate(
        self,
        tensions: List[LatentTension],
        context: Optional[dict] = None,
    ) -> Tuple[List[ObligationTarget], List[EvaluationResult]]:
        """
        Evaluate a list of latent tensions. Return only those that become obligations.

        Args:
            tensions: All latent tensions from Subsurface. Most will not pass.
            context:  Current system context — used to modulate context_validity.

        Returns:
            obligations: Tensions authorized as Surface obligations (max_active).
            evaluations: Full evaluation record for every tension evaluated.
        """
        now = time.time()
        evaluations: List[EvaluationResult] = []

        for tension in tensions:
            tension.last_evaluated_at = now
            result = self._evaluate_one(tension, context or {})
            evaluations.append(result)

        # Select only authorized tensions, sorted by obligation score descending
        authorized = [
            ObligationTarget(
                tension=t,
                obligation_score=e.obligation_score,
                channels=self._select_channels(t),
            )
            for t, e in zip(tensions, evaluations)
            if e.authorized
        ]
        authorized.sort(key=lambda o: o.obligation_score, reverse=True)

        obligations = authorized[: self.max_active]
        return obligations, evaluations

    def obligation_score(self, tension: LatentTension) -> float:
        """
        Compute the raw obligation score for a single tension.

        Score = (pressure × worth × context_validity) / max(cost, 0.01)

        All three numerator factors must independently clear their thresholds
        before the score is meaningful — this is enforced in evaluate_one.
        """
        numerator = (
            tension.pressure
            * tension.worth
            * tension.context_validity
        )
        denominator = max(tension.cost, 0.01)
        return numerator / denominator

    # ------------------------------------------------------------------
    # INTERNAL EVALUATION
    # ------------------------------------------------------------------

    def _evaluate_one(
        self,
        tension: LatentTension,
        context: dict,
    ) -> EvaluationResult:
        """
        Apply the three axes in order. First failure terminates evaluation.
        Ordered cheapest-to-most-expensive check first.
        """
        # Apply context to modulate context_validity if provided
        effective_context_validity = self._apply_context(tension, context)

        # Axis 1: Pressure Strength
        # Is this tension real and meaningful — not curiosity, not noise?
        if tension.pressure < self.pressure_threshold:
            return EvaluationResult(
                tension_id=tension.id,
                authorized=False,
                pressure_score=tension.pressure,
                worth_score=tension.worth,
                context_score=effective_context_validity,
                cost=tension.cost,
                obligation_score=0.0,
                rejection_axis="pressure_strength",
                rejection_reason=(
                    f"Pressure {tension.pressure:.2f} below threshold {self.pressure_threshold:.2f}. "
                    "Not real enough to act on."
                ),
            )

        # Axis 2: Worth
        # Will resolving this change anything meaningful? Does it propagate?
        if tension.worth < self.worth_threshold:
            return EvaluationResult(
                tension_id=tension.id,
                authorized=False,
                pressure_score=tension.pressure,
                worth_score=tension.worth,
                context_score=effective_context_validity,
                cost=tension.cost,
                obligation_score=0.0,
                rejection_axis="worth",
                rejection_reason=(
                    f"Worth {tension.worth:.2f} below threshold {self.worth_threshold:.2f}. "
                    "Resolution would not propagate meaningfully."
                ),
            )

        # Axis 3: Context Validity
        # Is this the right time? Valid target at wrong moment = distorted understanding.
        if effective_context_validity < self.context_threshold:
            return EvaluationResult(
                tension_id=tension.id,
                authorized=False,
                pressure_score=tension.pressure,
                worth_score=tension.worth,
                context_score=effective_context_validity,
                cost=tension.cost,
                obligation_score=0.0,
                rejection_axis="context_validity",
                rejection_reason=(
                    f"Context validity {effective_context_validity:.2f} below threshold "
                    f"{self.context_threshold:.2f}. Right tension, wrong moment — "
                    "acting now would create distorted understanding."
                ),
            )

        # All three axes cleared — compute final obligation score
        score = self.obligation_score(tension)
        # Override context_validity with the modulated value for score accuracy
        score = (tension.pressure * tension.worth * effective_context_validity) / max(tension.cost, 0.01)

        return EvaluationResult(
            tension_id=tension.id,
            authorized=True,
            pressure_score=tension.pressure,
            worth_score=tension.worth,
            context_score=effective_context_validity,
            cost=tension.cost,
            obligation_score=score,
            rejection_axis=None,
        )

    def _apply_context(self, tension: LatentTension, context: dict) -> float:
        """
        Modulate tension.context_validity based on current system context.

        External context can reduce validity (wrong moment) but cannot
        increase it beyond the tension's own declared validity.
        This prevents context from fabricating readiness that isn't there.
        """
        base = tension.context_validity

        # If the system is in high-load or reactive state, reduce context validity
        # for non-urgent tensions so they stay held rather than forcing through.
        system_load = float(context.get("system_load", 0.0) or 0.0)
        if system_load > 0.7 and tension.pressure < 0.75:
            base *= (1.0 - (system_load - 0.7) * 1.5)

        # If a surface turn is actively processing, deprioritize new targets
        if context.get("surface_processing", False) and tension.pressure < 0.9:
            base *= 0.6

        return max(0.0, min(1.0, base))

    def _select_channels(self, tension: LatentTension) -> List[str]:
        """
        Determine which exploration channels Surface may use for this target.
        Derived from the tension's exploration hints; defaults to all channels.
        """
        default_channels = ["ask_user", "observe", "search", "compose"]
        if tension.exploration_hints:
            return [h for h in tension.exploration_hints if h in default_channels] or default_channels
        return default_channels


# ---------------------------------------------------------------------------
# SURFACE LAW ENFORCER (thin wrapper)
# ---------------------------------------------------------------------------

class SurfaceObligationExecutor:
    """
    Surface does not initiate. Surface does not choose.
    Surface receives an obligation list and executes.

    This class enforces the Surface law at the boundary:
        - Surface may only act on DCE-authorized targets
        - Surface may not substitute judgment about what is interesting
        - Surface must not gather data unrelated to active targets

    Usage:
        gate = DCEObligationGate()
        executor = SurfaceObligationExecutor(gate)
        obligations = executor.receive(latent_tensions, context)
        for ob in obligations:
            surface_execute(ob)  # your Surface execution logic
    """

    def __init__(self, gate: DCEObligationGate) -> None:
        self._gate = gate
        self._active: List[ObligationTarget] = []

    def receive(
        self,
        tensions: List[LatentTension],
        context: Optional[dict] = None,
    ) -> List[ObligationTarget]:
        """
        Request obligations from DCE. Surface receives what was authorized.
        Surface does not see the full tension reservoir.
        Surface does not see rejection reasons.
        Surface receives only: what it must resolve.
        """
        self._active, _ = self._gate.evaluate(tensions, context)
        return list(self._active)

    @property
    def active_targets(self) -> List[ObligationTarget]:
        return list(self._active)

    def has_obligations(self) -> bool:
        return bool(self._active)
