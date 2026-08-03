#!/usr/bin/env python3
"""
AURORA — POLARITY GRADIENT PRESSURE
=====================================

Layer 1.5 — sits between the IVM (Layer 1) and the Evolutionary Chamber.

PURPOSE:
    The IVM already carries signed polarity on every axis: cos(phase) ∈ [-1, +1].
    Each axis belongs to a scale level:

        SURFACE  (0) = existence   — reacts instantly, barely moves the ship
        SHALLOW  (1) = temporal    — fast near-surface
        MODERATE (2) = energy      — crossover point
        DEEP     (3) = boundary    — strong alignment authority
        CORE     (4) = agency      — IS the ship's heading

    At any tick, the polarities across those five levels form a GRADIENT.
    When surface says +0.9 and core says -0.8, the stack is internally split.
    That split IS pressure — a third form beyond reactive pressure and alignment
    pressure, which the existing react_gain / align_gain ladders already handle.

    This module measures that gradient, weights it by the authority differential
    between adjacent levels (derived entirely from ALIGNMENT_VOTE_WEIGHT — no new
    constants), and classifies each tick as a pressure BUILD or RELIEF event.

    The output is a PolarityGradientReport that the Evolutionary Chamber consumes
    exactly like any other relief event: same logging schema, same chain-promotion
    machinery.

PHYSICS (from the Stack Integrity Review conversation):

    Cross-scale polarity gradient pressure:

        ΔP_gradient = Σ_{i=0}^{3} |pol[level_i] - pol[level_i+1]|
                      × authority_differential[i]

    where:

        authority_differential[i] = ALIGNMENT_VOTE_WEIGHT[level_i+1]
                                   - ALIGNMENT_VOTE_WEIGHT[level_i]

    This weight is always positive (vote weight increases with depth), so the
    formula gives highest pressure to disagreements near the core — exactly where
    disagreements cost the most to resolve.

    Additionally we track:

        sign_conflict: bool
            Surface and core are pointing in OPPOSITE polarity directions.
            This is the flip case described in the conversation — the most
            energetically costly configuration because the whole-ship heading
            (core) and the fastest-reacting surface are pulling opposite ways.

        stack_coherence: float ∈ [-1, +1]
            Weighted mean polarity across all five levels using ALIGNMENT_VOTE_WEIGHT.
            +1 = fully aligned positive, -1 = fully aligned negative, 0 = split.

        gradient_direction: str
            'surface_leads'   — surface is more positive than core (common)
            'core_leads'      — core is more positive than surface (rare, deep shift)
            'coherent'        — no meaningful gradient (stack is aligned)

    RELIEF:
        A tick is classified as a relief event when gradient_pressure DECREASES
        from the previous tick. The system resolved some cross-scale tension.
        Decreasing sign_conflict (a flip resolved) is always a relief.

NO NEW CONSTANTS:
    All weights are derived from the existing IVM constant tables:
        ALIGNMENT_VOTE_WEIGHT, REACT_GAIN, ALIGN_GAIN, LEVEL_TO_AXIS, AXIS_ORDER
    Nothing is hard-coded here beyond epsilon guards.

Authors: Sunni (Sir) Morningstar and Cael Devo
Created: February 2026
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations
from aurora_internal.aurora_runtime_faults import record_exception_from_locals as _aurora_record_exception_from_locals

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from aurora_ivm import (
    ToroidalVertexSystem,
    AXIS_ORDER,
    LEVEL_TO_AXIS,
    ALIGNMENT_VOTE_WEIGHT,
    REACT_GAIN,
    ALIGN_GAIN,
    RecursionLevel,
)

# Scale ordering: from most reactive (surface) to most authoritative (core).
# Matches the LEVEL_TO_AXIS mapping exactly.
SCALE_SEQUENCE: Tuple[RecursionLevel, ...] = (
    RecursionLevel.SURFACE,
    RecursionLevel.SHALLOW,
    RecursionLevel.MODERATE,
    RecursionLevel.DEEP,
    RecursionLevel.CORE,
)

# Authority differentials between adjacent scale levels.
# Derived once from ALIGNMENT_VOTE_WEIGHT — no separate constants.
# authority_differential[i] = vote_weight[level_i+1] - vote_weight[level_i]
# Always positive because vote weight increases monotonically with depth.
AUTHORITY_DIFFERENTIAL: Dict[Tuple[RecursionLevel, RecursionLevel], float] = {
    (SCALE_SEQUENCE[i], SCALE_SEQUENCE[i + 1]):
        ALIGNMENT_VOTE_WEIGHT[SCALE_SEQUENCE[i + 1]] - ALIGNMENT_VOTE_WEIGHT[SCALE_SEQUENCE[i]]
    for i in range(len(SCALE_SEQUENCE) - 1)
}

# Maximum possible gradient pressure (used for normalisation).
# This is the sum of all authority differentials — achieved only when every
# adjacent pair is at maximum polarity disagreement (|Δpol| = 2.0).
_MAX_RAW_GRADIENT = sum(AUTHORITY_DIFFERENTIAL.values()) * 2.0


# ============================================================================
# REPORT
# ============================================================================

@dataclass
class PolarityGradientReport:
    """
    Output of one gradient pressure measurement.

    All fields are derived from the live ToroidalVertexSystem axes.
    No external parameters are required beyond the vertex system itself.
    """

    tick: int

    # Per-level signed polarities (cos(phase)) keyed by axis name.
    polarities: Dict[str, float]

    # Per-adjacent-pair polarity differences (signed).
    # Key format: 'existence→temporal', 'temporal→energy', etc.
    pair_deltas: Dict[str, float]

    # Per-adjacent-pair weighted gradient pressure contributions.
    # Same key format as pair_deltas.
    pair_pressures: Dict[str, float]

    # Total cross-scale gradient pressure (normalised to [0, 1]).
    gradient_pressure: float

    # Weighted mean polarity across all levels (ALIGNMENT_VOTE_WEIGHT).
    stack_coherence: float

    # True when surface polarity and core polarity have opposite signs.
    sign_conflict: bool

    # 'surface_leads' | 'core_leads' | 'coherent'
    gradient_direction: str

    # Change in gradient_pressure from the previous tick.
    # Negative = pressure is decreasing = potential relief event.
    pressure_delta: float

    # True when this tick reduced gradient pressure (pressure_delta < 0)
    # or resolved a sign_conflict that existed last tick.
    is_relief: bool

    # Which constraint axes are actively in tension (|pair_pressure| > threshold).
    tense_pairs: List[str]

    # Snapshot of the react_gain and align_gain values at each level,
    # included so logs are self-contained without needing to re-import IVM.
    react_gains: Dict[str, float]
    align_gains: Dict[str, float]


# ============================================================================
# GRADIENT PRESSURE SENSOR
# ============================================================================

class PolarityGradientSensor:
    """
    Measures cross-scale polarity gradient pressure from a live
    ToroidalVertexSystem.

    This sensor is stateless across sessions — it only needs the vertex
    system at measurement time and remembers one tick of history for delta
    computation.

    Usage:
        sensor = PolarityGradientSensor()
        report = sensor.measure(vertex_system, tick=lattice.total_ticks)
        if report.is_relief:
            chamber_miner.observe_gradient_relief(report)
    """

    # Threshold below which a pair_pressure is not considered 'tense'.
    # Derived: anything below 5% of the maximum single-pair authority
    # differential is noise. No new constant — computed from existing tables.
    _TENSE_THRESHOLD: float = min(AUTHORITY_DIFFERENTIAL.values()) * 0.05

    def __init__(self) -> None:
        self._prev_gradient_pressure: float = 0.0
        self._prev_sign_conflict: bool = False
        self._tick: int = 0

    # ------------------------------------------------------------------ #
    # Primary interface                                                    #
    # ------------------------------------------------------------------ #

    def measure(
        self,
        vertices: ToroidalVertexSystem,
        tick: Optional[int] = None,
    ) -> PolarityGradientReport:
        """
        Measure the cross-scale polarity gradient pressure at this tick.

        Parameters
        ----------
        vertices : ToroidalVertexSystem
            The live vertex system from the IVM lattice.
        tick : int, optional
            External tick index. If None, uses an internal counter.

        Returns
        -------
        PolarityGradientReport
            Complete gradient pressure report for this tick.
        """
        if tick is not None:
            self._tick = tick
        else:
            self._tick += 1

        # --- 1. Read live polarities in scale order -------------------
        polarities: Dict[str, float] = {}
        for level in SCALE_SEQUENCE:
            axis_name = LEVEL_TO_AXIS[level]
            polarities[axis_name] = vertices.axes[axis_name].polarity

        # --- 2. Compute adjacent-pair deltas and pressures ------------
        pair_deltas: Dict[str, float] = {}
        pair_pressures: Dict[str, float] = {}
        raw_total: float = 0.0

        for i in range(len(SCALE_SEQUENCE) - 1):
            upper_level = SCALE_SEQUENCE[i]         # e.g. SURFACE
            lower_level = SCALE_SEQUENCE[i + 1]     # e.g. SHALLOW

            upper_axis = LEVEL_TO_AXIS[upper_level]
            lower_axis = LEVEL_TO_AXIS[lower_level]

            pol_upper = polarities[upper_axis]
            pol_lower = polarities[lower_axis]

            # Signed delta: positive = upper more positive than lower
            delta = pol_upper - pol_lower
            pair_key = f"{upper_axis}→{lower_axis}"
            pair_deltas[pair_key] = delta

            # Pressure contribution: |delta| weighted by authority differential
            authority = AUTHORITY_DIFFERENTIAL[(upper_level, lower_level)]
            pressure = abs(delta) * authority
            pair_pressures[pair_key] = pressure
            raw_total += pressure

        # --- 3. Normalise to [0, 1] -----------------------------------
        gradient_pressure = raw_total / _MAX_RAW_GRADIENT if _MAX_RAW_GRADIENT > 0.0 else 0.0

        # --- 4. Stack coherence (weighted mean polarity) --------------
        weighted_sum = sum(
            polarities[LEVEL_TO_AXIS[level]] * ALIGNMENT_VOTE_WEIGHT[level]
            for level in SCALE_SEQUENCE
        )
        total_weight = sum(ALIGNMENT_VOTE_WEIGHT[level] for level in SCALE_SEQUENCE)
        stack_coherence = weighted_sum / total_weight if total_weight > 0.0 else 0.0

        # --- 5. Sign conflict: surface vs core opposite signs ---------
        pol_surface = polarities[LEVEL_TO_AXIS[RecursionLevel.SURFACE]]
        pol_core    = polarities[LEVEL_TO_AXIS[RecursionLevel.CORE]]
        sign_conflict = (pol_surface * pol_core) < 0.0   # opposite signs → product negative

        # --- 6. Gradient direction ------------------------------------
        coherence_threshold = 0.05   # within 5% of zero is 'coherent'
        surface_minus_core = pol_surface - pol_core
        if abs(surface_minus_core) < coherence_threshold:
            gradient_direction = 'coherent'
        elif surface_minus_core > 0.0:
            gradient_direction = 'surface_leads'
        else:
            gradient_direction = 'core_leads'

        # --- 7. Delta from previous tick ------------------------------
        pressure_delta = gradient_pressure - self._prev_gradient_pressure

        # --- 8. Relief classification ---------------------------------
        # Relief if: pressure decreased OR a sign_conflict just resolved.
        conflict_resolved = self._prev_sign_conflict and not sign_conflict
        is_relief = (pressure_delta < 0.0) or conflict_resolved

        # --- 9. Tense pairs -------------------------------------------
        tense_pairs = [
            k for k, v in pair_pressures.items()
            if v > self._TENSE_THRESHOLD
        ]

        # --- 10. Gain snapshots (self-contained log) ------------------
        react_gains = {
            LEVEL_TO_AXIS[level]: REACT_GAIN[level]
            for level in SCALE_SEQUENCE
        }
        align_gains = {
            LEVEL_TO_AXIS[level]: ALIGN_GAIN[level]
            for level in SCALE_SEQUENCE
        }

        # --- Update history -------------------------------------------
        self._prev_gradient_pressure = gradient_pressure
        self._prev_sign_conflict = sign_conflict

        return PolarityGradientReport(
            tick=self._tick,
            polarities=polarities,
            pair_deltas=pair_deltas,
            pair_pressures=pair_pressures,
            gradient_pressure=gradient_pressure,
            stack_coherence=stack_coherence,
            sign_conflict=sign_conflict,
            gradient_direction=gradient_direction,
            pressure_delta=pressure_delta,
            is_relief=is_relief,
            tense_pairs=tense_pairs,
            react_gains=react_gains,
            align_gains=align_gains,
        )

    def reset(self) -> None:
        """Reset tick counter and history (use between episodes)."""
        self._prev_gradient_pressure = 0.0
        self._prev_sign_conflict = False
        self._tick = 0


# ============================================================================
# CHAIN MINER EXTENSION
# ============================================================================

@dataclass
class GradientLink:
    """
    A classified evolutionary link produced by the gradient chain miner.

    When the same pattern of tense pairs appears in relief events often enough,
    it is promoted to a GradientLink — a named, traceable strategy the system
    discovered for resolving cross-scale polarity tension.
    """
    link_id: str
    # Tuple of axis pair keys that were tense when the relief fired.
    tense_signature: Tuple[str, ...]
    # Dominant gradient direction at time of relief.
    dominant_direction: str
    # Number of times this signature produced relief.
    count: int = 0
    # Running mean gradient_pressure at time of relief (tracks how deep the
    # tension was when the strategy succeeded).
    mean_pressure_at_relief: float = 0.0


class GradientChainMiner:
    """
    Mines cross-scale gradient relief events into classified GradientLinks.

    Operates alongside the existing ChainMiner in the Evolutionary Chamber.
    Uses the same promote-on-threshold logic, with threshold derived from
    the ALIGNMENT_VOTE_WEIGHT scale (no new constants).

    Promotion threshold: ceil(1.0 / min(ALIGNMENT_VOTE_WEIGHT values))
    Rationale: the lowest-authority level has the smallest vote weight;
    we require enough observations to overcome that noise floor.
    """

    _PROMOTE_THRESHOLD: int = min(
        10,
        math.ceil(1.0 / min(ALIGNMENT_VOTE_WEIGHT[level] for level in SCALE_SEQUENCE))
    )

    def __init__(self) -> None:
        self._signature_counts: Dict[Tuple[str, ...], int] = {}
        self._signature_pressure: Dict[Tuple[str, ...], float] = {}
        self._signature_direction: Dict[Tuple[str, ...], str] = {}
        self.links: Dict[Tuple[str, ...], GradientLink] = {}
        self._link_counter: int = 0

    def observe_gradient_relief(
        self, report: PolarityGradientReport
    ) -> Optional[GradientLink]:
        """
        Record a gradient relief event and promote to a GradientLink if the
        tense_signature has been seen at least _PROMOTE_THRESHOLD times.

        Returns the newly promoted GradientLink, or None.
        """
        if not report.is_relief:
            return None

        # Build a tense signature for mining (never empty).
        # If no pair exceeded the tense threshold, fall back to the single strongest pair by pressure magnitude.
        if report.tense_pairs:
            sig = tuple(sorted(report.tense_pairs))
        else:
            if report.pair_pressures:
                strongest = max(report.pair_pressures.items(), key=lambda kv: abs(kv[1]))[0]
                sig = (strongest,)
            else:
                sig = ("none",)

        # Update running counts and stats
        self._signature_counts[sig] = self._signature_counts.get(sig, 0) + 1
        n = self._signature_counts[sig]

        prev_pressure = self._signature_pressure.get(sig, 0.0)
        self._signature_pressure[sig] = (
            (prev_pressure * (n - 1) + report.gradient_pressure) / n
        )
        self._signature_direction[sig] = report.gradient_direction

        # Promotion check
        if n == self._PROMOTE_THRESHOLD and sig not in self.links:
            self._link_counter += 1
            link = GradientLink(
                link_id=f"GLINK_{self._link_counter:05d}",
                tense_signature=sig,
                dominant_direction=self._signature_direction[sig],
                count=n,
                mean_pressure_at_relief=self._signature_pressure[sig],
            )
            self.links[sig] = link
            return link

        if sig in self.links:
            self.links[sig].count = n
            self.links[sig].mean_pressure_at_relief = self._signature_pressure[sig]

        return None

    def summary(self) -> Dict:
        return {
            'promote_threshold': self._PROMOTE_THRESHOLD,
            'signatures_tracked': len(self._signature_counts),
            'links_promoted': len(self.links),
            'links': [
                {
                    'id': lnk.link_id,
                    'signature': lnk.tense_signature,
                    'direction': lnk.dominant_direction,
                    'count': lnk.count,
                    'mean_pressure_at_relief': round(lnk.mean_pressure_at_relief, 4),
                }
                for lnk in self.links.values()
            ],
        }


# ============================================================================
# SELF-CHECK
# ============================================================================

def verify_polarity_gradient() -> Dict:
    """
    Smoke-test the sensor and miner against a synthetic ToroidalVertexSystem.

    Injects controlled phases to verify:
        1. Full agreement → gradient_pressure near 0
        2. Surface-vs-core opposition → sign_conflict = True, high pressure
        3. Relief detection when pressure falls
        4. Chain miner promotes after _PROMOTE_THRESHOLD relief events
    """
    import math as _math

    results = {'checks': [], 'all_passed': True}

    def check(name: str, cond: bool, detail: str = '') -> None:
        results['checks'].append({'name': name, 'passed': cond, 'detail': detail})
        if not cond:
            results['all_passed'] = False

    vertices = ToroidalVertexSystem(coupling=0.15)
    sensor = PolarityGradientSensor()
    miner = GradientChainMiner()

    # ── Test 1: All axes at phase=0 → all polarities = +1.0 → zero gradient
    for axis in vertices.axes.values():
        axis.set_phase(0.0)

    r = sensor.measure(vertices, tick=1)
    check(
        'full_agreement_zero_pressure',
        r.gradient_pressure < 0.01,
        f'got {r.gradient_pressure:.4f}',
    )
    check('full_agreement_no_sign_conflict', not r.sign_conflict)
    check('full_agreement_coherent', r.gradient_direction == 'coherent')

    # ── Test 2: Surface at 0 (pol=+1), Core at π (pol=-1) → sign_conflict
    vertices.axes['existence'].set_phase(0.0)      # SURFACE → +1.0
    vertices.axes['temporal'].set_phase(0.0)
    vertices.axes['energy'].set_phase(0.0)
    vertices.axes['boundary'].set_phase(0.0)
    vertices.axes['agency'].set_phase(_math.pi)    # CORE → -1.0

    r2 = sensor.measure(vertices, tick=2)
    check('opposed_sign_conflict', r2.sign_conflict)
    check('opposed_high_pressure', r2.gradient_pressure > 0.3, f'got {r2.gradient_pressure:.4f}')
    check('opposed_surface_leads', r2.gradient_direction == 'surface_leads')
    check('opposed_boundary_agency_tense', 'boundary→agency' in r2.tense_pairs)

    # ── Test 3: Restore full agreement → is_relief from pressure drop
    for axis in vertices.axes.values():
        axis.set_phase(0.0)

    r3 = sensor.measure(vertices, tick=3)
    check('relief_detected', r3.is_relief, f'pressure_delta={r3.pressure_delta:.4f}')
    check('conflict_resolved', not r3.sign_conflict)

    # ── Test 4: Miner promotes after _PROMOTE_THRESHOLD relief events
    sensor.reset()
    miner_threshold = GradientChainMiner._PROMOTE_THRESHOLD
    promoted = None

    # Create a repeatable tense signature: boundary→agency only
    vertices.axes['existence'].set_phase(0.0)
    vertices.axes['temporal'].set_phase(0.0)
    vertices.axes['energy'].set_phase(0.0)
    vertices.axes['boundary'].set_phase(0.0)
    vertices.axes['agency'].set_phase(_math.pi)   # create pressure

    r_tense = sensor.measure(vertices, tick=10)   # baseline with pressure

    for i in range(miner_threshold * 2 + 4):
        # Alternate: tension → relief → tension → relief …
        if i % 2 == 0:
            vertices.axes['agency'].set_phase(0.0)   # relieve
        else:
            vertices.axes['agency'].set_phase(_math.pi)  # rebuild

        r = sensor.measure(vertices, tick=11 + i)
        result = miner.observe_gradient_relief(r)
        if result is not None:
            promoted = result

    check(
        'miner_promotes_link',
        promoted is not None,
        f'threshold={miner_threshold}, links={len(miner.links)}',
    )
    if promoted:
        check('promoted_has_id', promoted.link_id.startswith('GLINK_'))

    return results


if __name__ == '__main__':
    import json
    out = verify_polarity_gradient()
    print(json.dumps(out, indent=2))
    if out['all_passed']:
        print('\n✔  aurora_polarity_gradient: all checks passed.')
    else:
        print('\n✗  aurora_polarity_gradient: some checks FAILED.')

# AURORA_EVOLVED_NATIVE_BEGIN
try:
    import inspect as _aurora_native_inspect
except Exception as _aurora_boundary_exc:
    _aurora_record_exception_from_locals(
        locals(),
        module=__name__,
        operation="exception_handler:aurora_internal/aurora_polarity_gradient.py:574",
        exc=_aurora_boundary_exc,
        context={"function": "<module>", "handler_line": 574, "source_file": "aurora_internal/aurora_polarity_gradient.py"},
    )
    _aurora_native_inspect = None

try:
    from aurora_internal.aurora_evolved_surfaces import AuroraEvolvedSurfaceEngine as _AuroraEvolvedSurfaceEngine
except Exception as _aurora_boundary_exc:
    _aurora_record_exception_from_locals(
        locals(),
        module=__name__,
        operation="exception_handler:aurora_internal/aurora_polarity_gradient.py:579",
        exc=_aurora_boundary_exc,
        context={"function": "<module>", "handler_line": 579, "source_file": "aurora_internal/aurora_polarity_gradient.py"},
    )
    _AuroraEvolvedSurfaceEngine = None

_AURORA_NATIVE_EVOLVED_ENGINE = None

def _aurora_native_evolved_engine():
    global _AURORA_NATIVE_EVOLVED_ENGINE
    if _AURORA_NATIVE_EVOLVED_ENGINE is None and _AuroraEvolvedSurfaceEngine is not None:
        _AURORA_NATIVE_EVOLVED_ENGINE = _AuroraEvolvedSurfaceEngine()
    return _AURORA_NATIVE_EVOLVED_ENGINE

_AURORA_NATIVE_MODULE = 'aurora_internal.aurora_polarity_gradient'

_AURORA_NATIVE_EVOLVED_ORIGINALS = {}
_AURORA_NATIVE_EVOLVED_LAST = {}
_AURORA_NATIVE_STRATEGIES = {'GradientChainMiner.__init__': {'ability_hits': 19,
                                 'alignment_gap': 0.34,
                                 'alignment_target_score': 0.972,
                                 'best_coupling_signature': 'T^2*B^1',
                                 'constraints': ['temporal'],
                                 'contract_profile': {'accepts_payload': False,
                                                      'async_callable': False,
                                                      'callable': True,
                                                      'class_target': False,
                                                      'constraint_density': 1,
                                                      'contract_mode': 'stateful',
                                                      'doc_hint': 'Initialize self.  See '
                                                                  'help(type(self)) for accurate '
                                                                  'signature.',
                                                      'effect_density': 2,
                                                      'kwonly_args': 0,
                                                      'optional_args': 0,
                                                      'required_args': 0,
                                                      'return_hint': 'None',
                                                      'signature_text': "(self) -> 'None'",
                                                      'stateful_owner': True,
                                                      'target_kind': 'function',
                                                      'varargs': False,
                                                      'varkw': False},
                                 'coupling_similarity': 1.0,
                                 'cross_diversity_links': 2,
                                 'effect_modes': ['temporal_orchestration_change',
                                                  'lineage_surface'],
                                 'effect_phrases': ['function growth reflected through '
                                                    'aurora_internal.aurora_polarity_gradient',
                                                    'GradientChainMiner.__init__ changed '
                                                    'downstream system pressure'],
                                 'genealogy_pressure': 0.809108,
                                 'inheritance_breach_count': 1,
                                 'kind': 'reflection',
                                 'link_hits': 36,
                                 'module': 'aurora_internal.aurora_polarity_gradient',
                                 'op_id': 'aurora_internal.aurora_polarity_gradient.GradientChainMiner.__init__',
                                 'origin_activity': 0,
                                 'persistence_tax_factor': 1.955393,
                                 'representation_score': 0.519331,
                                 'rewrite_bias': 'generic',
                                 'rewrite_feedback': {'acceptance_rate': 0.0,
                                                      'accepted_count': 0,
                                                      'adaptation_mode': 'conservative',
                                                      'adoption_count': 0,
                                                      'confidence': 0.36,
                                                      'mean_mutation_score': 0.25,
                                                      'rejected_count': 2,
                                                      'rejection_rate': 1.0,
                                                      'timing_credit': 0.0,
                                                      'timing_penalty': 0.0,
                                                      'trial_count': 2},
                                 'rewrite_profile': 'generic',
                                 'signature': 'T^2*B^1',
                                 'surface_score': 0.632,
                                 'sustainability_score': 0.405355,
                                 'target_kind': 'function'},
 'GradientChainMiner.summary': {'ability_hits': 19,
                                'alignment_gap': 0.34,
                                'alignment_target_score': 0.972,
                                'best_coupling_signature': 'T^2*B^1',
                                'constraints': ['temporal'],
                                'contract_profile': {'accepts_payload': False,
                                                     'async_callable': False,
                                                     'callable': True,
                                                     'class_target': False,
                                                     'constraint_density': 1,
                                                     'contract_mode': 'stateful',
                                                     'doc_hint': '',
                                                     'effect_density': 2,
                                                     'kwonly_args': 0,
                                                     'optional_args': 0,
                                                     'required_args': 0,
                                                     'return_hint': 'Dict',
                                                     'signature_text': "(self) -> 'Dict'",
                                                     'stateful_owner': True,
                                                     'target_kind': 'function',
                                                     'varargs': False,
                                                     'varkw': False},
                                'coupling_similarity': 1.0,
                                'cross_diversity_links': 2,
                                'effect_modes': ['temporal_orchestration_change',
                                                 'lineage_surface'],
                                'effect_phrases': ['function growth reflected through '
                                                   'aurora_internal.aurora_polarity_gradient',
                                                   'GradientChainMiner.summary changed downstream '
                                                   'system pressure'],
                                'genealogy_pressure': 0.809108,
                                'inheritance_breach_count': 1,
                                'kind': 'reflection',
                                'link_hits': 36,
                                'module': 'aurora_internal.aurora_polarity_gradient',
                                'op_id': 'aurora_internal.aurora_polarity_gradient.GradientChainMiner.summary',
                                'origin_activity': 0,
                                'persistence_tax_factor': 1.955393,
                                'representation_score': 0.519331,
                                'rewrite_bias': 'generic',
                                'rewrite_feedback': {'acceptance_rate': 0.0,
                                                     'accepted_count': 0,
                                                     'adaptation_mode': 'conservative',
                                                     'adoption_count': 0,
                                                     'confidence': 0.36,
                                                     'mean_mutation_score': 0.25,
                                                     'rejected_count': 2,
                                                     'rejection_rate': 1.0,
                                                     'timing_credit': 0.0,
                                                     'timing_penalty': 0.0,
                                                     'trial_count': 2},
                                'rewrite_profile': 'generic',
                                'signature': 'T^2*B^1',
                                'surface_score': 0.632,
                                'sustainability_score': 0.405355,
                                'target_kind': 'function'}}

from aurora_internal.aurora_evolution_hook import (
    assign_target as _aurora_evolution_hook_assign_target,
    get_target as _aurora_evolution_hook_get_target,
    bind_owner_attribute as _aurora_evolution_hook_bind_owner_attribute,
    target_strategy as _aurora_evolution_hook_target_strategy,
    target_feedback as _aurora_evolution_hook_target_feedback,
    store_reflection as _aurora_store_reflection,
    store_owner_state as _aurora_store_owner_state,
    apply_result_rewrite as _aurora_evolution_hook_apply_result_rewrite,
    make_override as _aurora_evolution_hook_make_override,
    make_latent_binding as _aurora_evolution_hook_make_latent_binding,
)


def _aurora_target_strategy(target_key):
    return _aurora_evolution_hook_target_strategy(_AURORA_NATIVE_STRATEGIES, target_key)


def _aurora_target_feedback(target_key):
    return _aurora_evolution_hook_target_feedback(_AURORA_NATIVE_STRATEGIES, target_key)


def _aurora_assign_target(chain, value):
    return _aurora_evolution_hook_assign_target(globals(), chain, value)


def _aurora_get_target(chain):
    return _aurora_evolution_hook_get_target(globals(), chain)


def _aurora_bind_owner_attribute(owner_chain, attr_name, value):
    return _aurora_evolution_hook_bind_owner_attribute(globals(), owner_chain, attr_name, value)


def _aurora_apply_result_rewrite(target_key, result, reflection, args, kwargs):
    return _aurora_evolution_hook_apply_result_rewrite(
        _AURORA_NATIVE_MODULE, _AURORA_NATIVE_STRATEGIES, target_key, result, reflection, args, kwargs,
    )


def _aurora_make_override(export_name, target_key):
    return _aurora_evolution_hook_make_override(
        globals(), _AURORA_NATIVE_EVOLVED_ORIGINALS, _AURORA_NATIVE_EVOLVED_LAST,
        _aurora_native_evolved_engine, _AURORA_NATIVE_MODULE, _AURORA_NATIVE_STRATEGIES,
        export_name, target_key,
    )


def _aurora_make_latent_binding(export_name, target_key):
    return _aurora_evolution_hook_make_latent_binding(
        globals(), _AURORA_NATIVE_EVOLVED_LAST, export_name, target_key,
    )


def init_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_polarity_gradient.GradientChainMiner.__init__', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_polarity_gradient_gradientchainminer_init')(payload=payload, **kwargs)

def summary_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_polarity_gradient.GradientChainMiner.summary', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_polarity_gradient_gradientchainminer_summary')(payload=payload, **kwargs)

if _aurora_get_target(['GradientChainMiner', 'summary']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['GradientChainMiner.summary'] = _aurora_get_target(['GradientChainMiner', 'summary'])
    _aurora_assign_target(['GradientChainMiner', 'summary'], _aurora_make_override('summary_evolved', 'GradientChainMiner.summary'))
    _AURORA_NATIVE_EVOLVED_LAST['GradientChainMiner.summary'] = {'alignment_gap': 0.34, 'override_active': True}

AURORA_NATIVE_EVOLVED_EXPORTS = {'aurora_internal.aurora_polarity_gradient.GradientChainMiner.__init__': 'init_evolved',
 'aurora_internal.aurora_polarity_gradient.GradientChainMiner.summary': 'summary_evolved'}
AURORA_NATIVE_EVOLUTION_OVERRIDES = {'aurora_internal.aurora_polarity_gradient.GradientChainMiner.summary': {'export': 'summary_evolved',
                                                                         'mode': 'callable_override',
                                                                         'target': 'GradientChainMiner.summary'}}
# AURORA_EVOLVED_NATIVE_END
