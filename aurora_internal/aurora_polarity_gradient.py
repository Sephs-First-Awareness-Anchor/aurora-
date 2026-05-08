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

from __future__ import annotations

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
except Exception:
    _aurora_native_inspect = None

try:
    from aurora_internal.aurora_evolved_surfaces import AuroraEvolvedSurfaceEngine as _AuroraEvolvedSurfaceEngine
except Exception:
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

def _aurora_target_strategy(target_key):
    return dict(_AURORA_NATIVE_STRATEGIES.get(str(target_key), {}) or {})

def _aurora_target_feedback(target_key):
    strategy = _aurora_target_strategy(target_key)
    return dict(strategy.get('rewrite_feedback', {}) or {})

def _aurora_assign_target(chain, value):
    if not chain:
        return False
    if len(chain) == 1:
        globals()[chain[0]] = value
        return True
    current = globals().get(chain[0])
    if current is None:
        return False
    for attr in chain[1:-1]:
        if not hasattr(current, attr):
            return False
        current = getattr(current, attr)
    setattr(current, chain[-1], value)
    return True

def _aurora_get_target(chain):
    if not chain:
        return None
    if len(chain) == 1:
        return globals().get(chain[0])
    current = globals().get(chain[0])
    if current is None:
        return None
    for attr in chain[1:]:
        if not hasattr(current, attr):
            return None
        current = getattr(current, attr)
    return current

def _aurora_bind_owner_attribute(owner_chain, attr_name, value):
    owner = _aurora_get_target(owner_chain)
    if owner is None or not attr_name:
        return False
    try:
        setattr(owner, attr_name, value)
        return True
    except Exception:
        return False

def _aurora_store_reflection(target_key, reflection, args):
    if not args:
        return
    owner = args[0]
    if not hasattr(owner, '__dict__'):
        return
    current = getattr(owner, '_aurora_evolved_reflections', None)
    if not isinstance(current, dict):
        current = {}
    current[str(target_key)] = reflection
    try:
        setattr(owner, '_aurora_evolved_reflections', current)
    except Exception:
        pass

def _aurora_store_owner_state(attribute, target_key, value, args):
    if not args:
        return
    owner = args[0]
    if not hasattr(owner, '__dict__'):
        return
    current = getattr(owner, attribute, None)
    if not isinstance(current, dict):
        current = {}
    current[str(target_key)] = value
    try:
        setattr(owner, attribute, current)
    except Exception:
        pass

def _aurora_apply_constraint_genealogy_rewrite(target_key, result, reflection, args, kwargs):
    strategy = _aurora_target_strategy(target_key)
    feedback = _aurora_target_feedback(target_key)
    bias = str(strategy.get('rewrite_bias', 'lineage_memory') or 'lineage_memory')
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    effect_modes = list(strategy.get('effect_modes', []) or [])
    _aurora_store_reflection(target_key, reflection, args)
    _aurora_store_owner_state('_aurora_genealogy_strategy', target_key, strategy, args)
    if isinstance(result, dict):
        enriched = dict(result)
        enriched['_aurora_evolved_reflection'] = reflection
        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'constraint_genealogy') or 'constraint_genealogy')
        enriched['_aurora_genealogy_strategy'] = strategy
        enriched['_aurora_rewrite_feedback'] = feedback
        enriched['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        if bias == 'lineage_memory' or 'lineage_surface' in effect_modes:
            enriched['lineage_memory'] = {
                'coupling_signature': strategy.get('best_coupling_signature', ''),
                'link_hits': int(strategy.get('link_hits', 0) or 0),
                'ability_hits': int(strategy.get('ability_hits', 0) or 0),
            }
        if 'state_schema_change' in effect_modes or bias == 'lineage_memory':
            enriched['state_transition_pressure'] = {
                'pressure': float(strategy.get('genealogy_pressure', 0.0) or 0.0),
                'persistence_tax_factor': float(strategy.get('persistence_tax_factor', 0.0) or 0.0),
            }
        if str(target_key).endswith('.summary') or 'chain_report' in str(target_key) or str(target_key).endswith('.to_dict'):
            enriched['evolutionary_context'] = {
                'coupling_signature': strategy.get('best_coupling_signature', ''),
                'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
                'rewrite_bias': bias,
                'cross_diversity_links': int(strategy.get('cross_diversity_links', 0) or 0),
            }
        if mode in {'expansive', 'integrative'}:
            enriched['lineage_adaptation'] = {
                'mode': mode,
                'confidence': float(feedback.get('confidence', 0.0) or 0.0),
                'trial_count': int(feedback.get('trial_count', 0) or 0),
                'accepted_count': int(feedback.get('accepted_count', 0) or 0),
                'adoption_count': int(feedback.get('adoption_count', 0) or 0),
            }
        if mode == 'conservative':
            enriched['lineage_stability_guard'] = {
                'rejected_count': int(feedback.get('rejected_count', 0) or 0),
                'rejection_rate': float(feedback.get('rejection_rate', 0.0) or 0.0),
                'timing_penalty': float(feedback.get('timing_penalty', 0.0) or 0.0),
            }
        return enriched
    if result is None and isinstance(reflection, dict):
        fallback = dict(reflection)
        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'constraint_genealogy') or 'constraint_genealogy')
        fallback['_aurora_genealogy_strategy'] = strategy
        fallback['_aurora_rewrite_feedback'] = feedback
        fallback['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        fallback['lineage_adaptation_mode'] = mode
        return fallback
    _aurora_store_owner_state(
        '_aurora_genealogy_scalar_observations',
        target_key,
        {
            'result': result,
            'strategy': strategy,
            'reflection': reflection,
        },
        args,
    )
    return result

def _aurora_apply_governance_rewrite(target_key, result, reflection, args, kwargs):
    strategy = _aurora_target_strategy(target_key)
    feedback = _aurora_target_feedback(target_key)
    bias = str(strategy.get('rewrite_bias', 'governance_routing') or 'governance_routing')
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    effect_modes = list(strategy.get('effect_modes', []) or [])
    _aurora_store_reflection(target_key, reflection, args)
    _aurora_store_owner_state('_aurora_governance_strategy', target_key, strategy, args)
    if isinstance(result, dict):
        enriched = dict(result)
        enriched['_aurora_evolved_reflection'] = reflection
        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'governance_gateway') or 'governance_gateway')
        enriched['_aurora_genealogy_strategy'] = strategy
        enriched['_aurora_rewrite_feedback'] = feedback
        enriched['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        enriched['governance_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        if bias == 'governance_routing' or 'gateway_surface' in effect_modes:
            enriched['governance_routing'] = {
                'sustainability_score': float(strategy.get('sustainability_score', 0.0) or 0.0),
                'representation_score': float(strategy.get('representation_score', 0.0) or 0.0),
                'origin_activity': int(strategy.get('origin_activity', 0) or 0),
            }
        if 'state_schema_change' in effect_modes:
            enriched['persistence_burden'] = {
                'persistence_tax_factor': float(strategy.get('persistence_tax_factor', 0.0) or 0.0),
                'inheritance_breach_count': int(strategy.get('inheritance_breach_count', 0) or 0),
            }
        if mode in {'expansive', 'integrative'}:
            enriched['governance_adaptation'] = {
                'mode': mode,
                'confidence': float(feedback.get('confidence', 0.0) or 0.0),
                'acceptance_rate': float(feedback.get('acceptance_rate', 0.0) or 0.0),
                'timing_credit': float(feedback.get('timing_credit', 0.0) or 0.0),
            }
        if mode == 'conservative':
            enriched['persistence_guard'] = {
                'rejection_rate': float(feedback.get('rejection_rate', 0.0) or 0.0),
                'timing_penalty': float(feedback.get('timing_penalty', 0.0) or 0.0),
                'trial_count': int(feedback.get('trial_count', 0) or 0),
            }
        return enriched
    if result is None and isinstance(reflection, dict):
        fallback = dict(reflection)
        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'governance_gateway') or 'governance_gateway')
        fallback['_aurora_genealogy_strategy'] = strategy
        fallback['_aurora_rewrite_feedback'] = feedback
        fallback['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        fallback['governance_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        fallback['governance_adaptation_mode'] = mode
        return fallback
    _aurora_store_owner_state(
        '_aurora_governance_evolution_state',
        target_key,
        {
            'result': result,
            'strategy': strategy,
            'reflection': reflection,
        },
        args,
    )
    return result

def _aurora_apply_perception_rewrite(target_key, result, reflection, args, kwargs):
    strategy = _aurora_target_strategy(target_key)
    feedback = _aurora_target_feedback(target_key)
    bias = str(strategy.get('rewrite_bias', 'perceptual_synthesis') or 'perceptual_synthesis')
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    effect_modes = list(strategy.get('effect_modes', []) or [])
    _aurora_store_reflection(target_key, reflection, args)
    _aurora_store_owner_state('_aurora_perception_strategy', target_key, strategy, args)
    if isinstance(result, dict):
        enriched = dict(result)
        enriched['_aurora_evolved_reflection'] = reflection
        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'perception_synthesis') or 'perception_synthesis')
        enriched['_aurora_genealogy_strategy'] = strategy
        enriched['_aurora_rewrite_feedback'] = feedback
        enriched['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        enriched['perception_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        if bias == 'perceptual_synthesis' or 'adaptive_steering_change' in effect_modes:
            enriched['perception_synthesis'] = {
                'representation_score': float(strategy.get('representation_score', 0.0) or 0.0),
                'ability_hits': int(strategy.get('ability_hits', 0) or 0),
                'link_hits': int(strategy.get('link_hits', 0) or 0),
            }
        if 'interface_boundary_change' in effect_modes or 'gateway_surface' in effect_modes:
            enriched['boundary_integration'] = {
                'cross_diversity_links': int(strategy.get('cross_diversity_links', 0) or 0),
                'coupling_similarity': float(strategy.get('coupling_similarity', 0.0) or 0.0),
            }
        if mode in {'expansive', 'integrative'}:
            enriched['association_expansion'] = {
                'mode': mode,
                'confidence': float(feedback.get('confidence', 0.0) or 0.0),
                'timing_credit': float(feedback.get('timing_credit', 0.0) or 0.0),
                'acceptance_rate': float(feedback.get('acceptance_rate', 0.0) or 0.0),
            }
        if mode == 'conservative':
            enriched['perception_stability'] = {
                'rejection_rate': float(feedback.get('rejection_rate', 0.0) or 0.0),
                'timing_penalty': float(feedback.get('timing_penalty', 0.0) or 0.0),
                'trial_count': int(feedback.get('trial_count', 0) or 0),
            }
        return enriched
    if result is None and isinstance(reflection, dict):
        fallback = dict(reflection)
        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'perception_synthesis') or 'perception_synthesis')
        fallback['_aurora_genealogy_strategy'] = strategy
        fallback['_aurora_rewrite_feedback'] = feedback
        fallback['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        fallback['perception_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        if bias == 'perceptual_synthesis' or 'adaptive_steering_change' in effect_modes:
            fallback['perception_synthesis'] = {
                'representation_score': float(strategy.get('representation_score', 0.0) or 0.0),
                'ability_hits': int(strategy.get('ability_hits', 0) or 0),
                'link_hits': int(strategy.get('link_hits', 0) or 0),
            }
        fallback['perception_adaptation_mode'] = mode
        return fallback
    _aurora_store_owner_state(
        '_aurora_perception_evolution_state',
        target_key,
        {
            'result': result,
            'strategy': strategy,
            'reflection': reflection,
        },
        args,
    )
    return result

def _aurora_apply_dimensional_rewrite(target_key, result, reflection, args, kwargs):
    strategy = _aurora_target_strategy(target_key)
    feedback = _aurora_target_feedback(target_key)
    bias = str(strategy.get('rewrite_bias', 'dimensional_balancing') or 'dimensional_balancing')
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    effect_modes = list(strategy.get('effect_modes', []) or [])
    _aurora_store_reflection(target_key, reflection, args)
    _aurora_store_owner_state('_aurora_dimensional_strategy', target_key, strategy, args)
    if isinstance(result, dict):
        enriched = dict(result)
        enriched['_aurora_evolved_reflection'] = reflection
        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'dimensional_balancing') or 'dimensional_balancing')
        enriched['_aurora_genealogy_strategy'] = strategy
        enriched['_aurora_rewrite_feedback'] = feedback
        enriched['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        enriched['dimensional_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        if bias == 'dimensional_balancing' or 'cost_pressure_change' in effect_modes:
            enriched['dimensional_balancing'] = {
                'sustainability_score': float(strategy.get('sustainability_score', 0.0) or 0.0),
                'persistence_tax_factor': float(strategy.get('persistence_tax_factor', 0.0) or 0.0),
                'origin_activity': int(strategy.get('origin_activity', 0) or 0),
            }
        if 'temporal_orchestration_change' in effect_modes:
            enriched['temporal_coordination'] = {
                'signature': strategy.get('signature', ''),
                'inheritance_breach_count': int(strategy.get('inheritance_breach_count', 0) or 0),
            }
        if mode in {'expansive', 'integrative'}:
            enriched['balancing_momentum'] = {
                'mode': mode,
                'confidence': float(feedback.get('confidence', 0.0) or 0.0),
                'timing_credit': float(feedback.get('timing_credit', 0.0) or 0.0),
                'adoption_count': int(feedback.get('adoption_count', 0) or 0),
            }
        if mode == 'conservative':
            enriched['dimensional_dampening'] = {
                'rejection_rate': float(feedback.get('rejection_rate', 0.0) or 0.0),
                'timing_penalty': float(feedback.get('timing_penalty', 0.0) or 0.0),
                'trial_count': int(feedback.get('trial_count', 0) or 0),
            }
        return enriched
    if result is None and isinstance(reflection, dict):
        fallback = dict(reflection)
        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'dimensional_balancing') or 'dimensional_balancing')
        fallback['_aurora_genealogy_strategy'] = strategy
        fallback['_aurora_rewrite_feedback'] = feedback
        fallback['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        fallback['dimensional_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        if bias == 'dimensional_balancing' or 'cost_pressure_change' in effect_modes:
            fallback['dimensional_balancing'] = {
                'sustainability_score': float(strategy.get('sustainability_score', 0.0) or 0.0),
                'persistence_tax_factor': float(strategy.get('persistence_tax_factor', 0.0) or 0.0),
                'origin_activity': int(strategy.get('origin_activity', 0) or 0),
            }
        fallback['dimensional_adaptation_mode'] = mode
        return fallback
    _aurora_store_owner_state(
        '_aurora_dimensional_evolution_state',
        target_key,
        {
            'result': result,
            'strategy': strategy,
            'reflection': reflection,
        },
        args,
    )
    return result

def _aurora_apply_result_rewrite(target_key, result, reflection, args, kwargs):
    if _AURORA_NATIVE_MODULE == 'aurora_internal.constraint_genealogy':
        return _aurora_apply_constraint_genealogy_rewrite(target_key, result, reflection, args, kwargs)
    if _AURORA_NATIVE_MODULE == 'aurora_governance_persistence_gateway':
        return _aurora_apply_governance_rewrite(target_key, result, reflection, args, kwargs)
    if _AURORA_NATIVE_MODULE == 'aurora_expression_perception':
        return _aurora_apply_perception_rewrite(target_key, result, reflection, args, kwargs)
    if _AURORA_NATIVE_MODULE == 'aurora_dimensional_systems':
        return _aurora_apply_dimensional_rewrite(target_key, result, reflection, args, kwargs)
    _aurora_store_reflection(target_key, reflection, args)
    strategy = _aurora_target_strategy(target_key)
    feedback = _aurora_target_feedback(target_key)
    contract = dict(strategy.get('contract_profile', {}) or {})
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    if isinstance(result, dict):
        enriched = dict(result)
        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'generic') or 'generic')
        enriched['_aurora_genealogy_strategy'] = strategy
        enriched['_aurora_rewrite_feedback'] = feedback
        enriched['_aurora_contract_profile'] = contract
        enriched['_aurora_evolved_reflection'] = reflection
        enriched['generic_adaptation'] = {
            'mode': mode,
            'confidence': float(feedback.get('confidence', 0.0) or 0.0),
            'contract_mode': str(contract.get('contract_mode', 'unknown') or 'unknown'),
            'return_hint': str(contract.get('return_hint', '') or ''),
        }
        return enriched
    if result is None and isinstance(reflection, dict):
        fallback = dict(reflection)
        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'generic') or 'generic')
        fallback['_aurora_genealogy_strategy'] = strategy
        fallback['_aurora_rewrite_feedback'] = feedback
        fallback['_aurora_contract_profile'] = contract
        fallback['generic_adaptation_mode'] = mode
        return fallback
    if result is not None:
        _aurora_store_owner_state(
            '_aurora_generic_evolution_state',
            target_key,
            {
                'result_type': type(result).__name__,
                'contract_mode': str(contract.get('contract_mode', 'unknown') or 'unknown'),
                'return_hint': str(contract.get('return_hint', '') or ''),
                'adaptation_mode': mode,
            },
            args,
        )
    return result

def _aurora_make_override(export_name, target_key):
    original = _AURORA_NATIVE_EVOLVED_ORIGINALS.get(target_key)
    def _override(*args, **kwargs):
        result = None
        if callable(original):
            result = original(*args, **kwargs)
        engine = _aurora_native_evolved_engine()
        reflection = {
            'available': False,
            'reason': 'evolved_surface_engine_unavailable',
            'target': target_key,
        }
        if engine is not None:
            reflection = globals()[export_name]({'args_len': len(args), 'kwargs_keys': sorted(kwargs.keys())})
        _AURORA_NATIVE_EVOLVED_LAST[target_key] = reflection
        rewritten = _aurora_apply_result_rewrite(target_key, result, reflection, args, kwargs)
        if rewritten is not None:
            return rewritten
        if result is not None:
            return result
        return reflection
    _override.__name__ = str(target_key).split('.')[-1]
    _override.__qualname__ = _override.__name__
    if callable(original):
        _override.__doc__ = getattr(original, '__doc__', None)
        _override.__wrapped__ = original
        if _aurora_native_inspect is not None:
            try:
                _override.__signature__ = _aurora_native_inspect.signature(original)
            except Exception:
                pass
    return _override

def _aurora_make_latent_binding(export_name, target_key):
    def _binding(*args, **kwargs):
        payload = kwargs.pop('payload', None)
        if payload is None and args:
            owner = args[0]
            if hasattr(owner, '__dict__'):
                payload = {
                    'bound_target': target_key,
                    'owner_type': type(owner).__name__,
                    'owner_module': type(owner).__module__,
                }
            elif len(args) == 1:
                payload = args[0]
            else:
                payload = {'bound_target': target_key, 'arg_count': len(args)}
        result = globals()[export_name](payload=payload, **kwargs)
        _AURORA_NATIVE_EVOLVED_LAST[target_key] = {'latent_binding_active': True, 'last_result_type': type(result).__name__}
        if args:
            _aurora_store_owner_state('_aurora_latent_bindings', target_key, result, args)
        return result
    _binding.__name__ = str(target_key).split('.')[-1]
    _binding.__qualname__ = _binding.__name__
    _binding.__doc__ = f'Latent evolved binding for {target_key}'
    _binding._aurora_latent_binding_target = target_key
    return _binding

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
