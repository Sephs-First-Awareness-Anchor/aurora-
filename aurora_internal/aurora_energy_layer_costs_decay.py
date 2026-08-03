
"""
aurora_energy_layer_costs_decay.py

Layered energy accounting with scale-conversion + decay/inheritance.

Design intent (Sunni spec):
- "Energy should multiply as it transfers the scale" -> this is scale-unit conversion.
- When a higher-k layer can't "hold" (goes negative / unstable), it decays downward and
  the next cheaper layer inherits that energy with conversion: E_to += E_from * (k_from/k_to).

This module is written to be drop-in friendly:
- If aurora_noncomp_registry.REGISTRY exists, we read k values from it.
- Otherwise we fall back to canonical constants: X=1, T=4, N=10, B=40, A=150.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations
from aurora_internal.aurora_runtime_faults import record_exception_from_locals as _aurora_record_exception_from_locals

from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Tuple

# --- Constraint enum import (fallback-safe) -----------------------------------
try:
    from foundational_contract import Constraint  # type: ignore
except Exception as _aurora_boundary_exc:
    _aurora_record_exception_from_locals(
        locals(),
        module=__name__,
        operation="exception_handler:aurora_internal/aurora_energy_layer_costs_decay.py:26",
        exc=_aurora_boundary_exc,
        context={"function": "<module>", "handler_line": 26, "source_file": "aurora_internal/aurora_energy_layer_costs_decay.py"},
    )
    try:
        from aurora_internal.aurora_noncomp_registry import Constraint  # type: ignore
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(),
            module=__name__,
            operation="exception_handler:aurora_internal/aurora_energy_layer_costs_decay.py:29",
            exc=_aurora_boundary_exc,
            context={"function": "<module>", "handler_line": 29, "source_file": "aurora_internal/aurora_energy_layer_costs_decay.py"},
        )
        # Minimal fallback (stringy)
        class Constraint:  # type: ignore
            X = "X"
            T = "T"
            N = "N"
            B = "B"
            A = "A"

# --- Registry import (optional) ----------------------------------------------
try:
    from aurora_internal.aurora_noncomp_registry import REGISTRY  # type: ignore
except Exception as _aurora_boundary_exc:
    _aurora_record_exception_from_locals(
        locals(),
        module=__name__,
        operation="exception_handler:aurora_internal/aurora_energy_layer_costs_decay.py:41",
        exc=_aurora_boundary_exc,
        context={"function": "<module>", "handler_line": 41, "source_file": "aurora_internal/aurora_energy_layer_costs_decay.py"},
    )
    REGISTRY = None  # type: ignore


DEFAULT_K: Dict[object, float] = {
    getattr(Constraint, "X"): 1.0,
    getattr(Constraint, "T"): 4.0,
    getattr(Constraint, "N"): 10.0,
    getattr(Constraint, "B"): 40.0,
    getattr(Constraint, "A"): 150.0,
}

# Most-expensive -> cheapest. This is the decay cascade order.
DEFAULT_CASCADE = [
    getattr(Constraint, "A"),
    getattr(Constraint, "B"),
    getattr(Constraint, "N"),
    getattr(Constraint, "T"),
    getattr(Constraint, "X"),
]


def k_of(c: object) -> float:
    """
    Scale factor k for a constraint/layer. Higher k = more expensive/deeper units.
    """
    if REGISTRY is not None:
        try:
            # Many builds use REGISTRY.operator(c).k
            op = REGISTRY.operator(c)
            if hasattr(op, "k"):
                return float(op.k)
        except Exception as _aurora_boundary_exc:
            _aurora_record_exception_from_locals(
                locals(),
                module=__name__,
                operation="exception_handler:aurora_internal/aurora_energy_layer_costs_decay.py:73",
                exc=_aurora_boundary_exc,
                context={"function": "k_of", "handler_line": 73, "source_file": "aurora_internal/aurora_energy_layer_costs_decay.py"},
            )
            pass
    return float(DEFAULT_K.get(c, 1.0))


def convert_units(amount: float, c_from: object, c_to: object) -> float:
    """
    Convert energy amount from layer c_from units into c_to units.

    Inheritance/decay rule:
      E_to += E_from * (k_from / k_to)

    So collapsing from expensive -> cheaper expands "usable" units, because cheaper units
    are smaller denominations.
    """
    k_from = k_of(c_from)
    k_to = k_of(c_to)
    if k_to <= 0:
        return 0.0
    return float(amount) * (k_from / k_to)


@dataclass
class LayerEnergyAccountant:
    """
    Holds per-layer energy pools in their own units, with decay cascade.

    Key invariants:
    - Pools are kept non-negative by cascading deficits downward.
    - If a layer is short (negative after withdrawals/maintenance), it is set to 0 and
      its deficit is pushed into the next cheaper layer by converting units.
    - You can treat this as the canonical "energy substrate" and then define higher-level
      semantics (intake, burn, budget, etc.) on top.

    Notes:
    - This does NOT invent energy. It's unit conversion + redistribution.
    - If you want global conservation, choose one canonical unit (e.g., N) and only store
      canonical internally; this module stores native per-layer units on purpose, because
      your spec wants scale to be operational.
    """

    pools: Dict[object, float]
    cascade: Tuple[object, ...] = tuple(DEFAULT_CASCADE)
    eps: float = 1e-12

    @classmethod
    def new(cls, initial: Optional[Dict[object, float]] = None,
            cascade: Optional[Iterable[object]] = None) -> "LayerEnergyAccountant":
        pools = {c: 0.0 for c in DEFAULT_CASCADE}
        if initial:
            for c, v in initial.items():
                pools[c] = float(v)
        cas = tuple(cascade) if cascade is not None else tuple(DEFAULT_CASCADE)
        return cls(pools=pools, cascade=cas)

    # --- basic access ---------------------------------------------------------
    def get(self, c: object) -> float:
        return float(self.pools.get(c, 0.0))

    def set(self, c: object, v: float) -> None:
        self.pools[c] = float(v)

    def add(self, c: object, dv: float) -> None:
        self.pools[c] = float(self.pools.get(c, 0.0)) + float(dv)

    # --- deposit / withdraw ---------------------------------------------------
    def deposit(self, c: object, amount: float) -> None:
        if amount <= 0:
            return
        self.add(c, amount)

    def withdraw(self, c: object, amount: float) -> float:
        """
        Withdraw up to `amount` from layer c. If insufficient, will zero that layer and
        push the remaining deficit down the cascade via conversion.

        Returns the amount successfully withdrawn in the *requested layer's units*.
        """
        if amount <= 0:
            return 0.0

        before = self.get(c)
        if before >= amount:
            self.set(c, before - amount)
            return float(amount)

        # not enough -> take all, then cascade deficit
        taken = before
        deficit = amount - before
        self.set(c, 0.0)

        # cascade the deficit downward: c -> next cheaper -> ...
        self._cascade_deficit(from_layer=c, deficit_in_from_units=deficit)
        return float(taken)

    # --- maintenance / decay --------------------------------------------------
    def apply_maintenance(self, costs: Dict[object, float]) -> None:
        """
        Subtract per-layer maintenance/burn, then normalize pools via decay cascade.
        costs: {Constraint: cost_in_that_layer_units}
        """
        for c, cost in costs.items():
            if cost == 0:
                continue
            self.add(c, -float(cost))
        self.normalize()

    def normalize(self) -> None:
        """
        Ensure no layer is negative by cascading any deficits down toward cheaper layers.
        """
        # Walk in expensive->cheaper order; push deficits down.
        cas = list(self.cascade)
        for i, c in enumerate(cas[:-1]):  # last layer has nowhere cheaper to push
            v = self.get(c)
            if v >= -self.eps:
                # clamp tiny negatives
                if v < 0:
                    self.set(c, 0.0)
                continue

            deficit = -v
            self.set(c, 0.0)
            self._cascade_deficit(from_layer=c, deficit_in_from_units=deficit)

        # Clamp any tiny negative at the cheapest layer
        last = cas[-1]
        v_last = self.get(last)
        if v_last < 0:
            self.set(last, 0.0)

    def _cascade_deficit(self, from_layer: object, deficit_in_from_units: float) -> None:
        """
        Push deficit from `from_layer` down to next cheaper layers by converting units.
        This models: layer couldn't hold -> decay -> next inherits the load.
        """
        if deficit_in_from_units <= 0:
            return

        cas = list(self.cascade)
        if from_layer not in cas:
            # unknown layer: treat as cheapest; eat deficit
            return

        idx = cas.index(from_layer)
        remaining_deficit = float(deficit_in_from_units)

        # We push the *need* downward. At each step, we remove from the next layer to pay it.
        for j in range(idx + 1, len(cas)):
            c_to = cas[j]
            # Convert remaining deficit into c_to units (how much c_to must cover)
            need_to = convert_units(remaining_deficit, cas[j - 1], c_to) if j == idx + 1 else convert_units(remaining_deficit, cas[j - 1], c_to)

            available = self.get(c_to)
            if available >= need_to:
                self.set(c_to, available - need_to)
                return

            # consume all available and continue pushing leftover further down
            self.set(c_to, 0.0)
            leftover_to = need_to - available

            # Now leftover_to is in c_to units; treat that as the new deficit from c_to
            remaining_deficit = float(leftover_to)

        # If we reach here, cheapest layer couldn't cover it. Deficit is effectively dropped (system collapse).
        return

    # --- inheritance (positive spill) -----------------------------------------
    def spill_down(self, c_from: object, amount_from: float, c_to: object) -> None:
        """
        Move *positive* energy downward with conversion:
        take `amount_from` from c_from, add converted amount into c_to.
        """
        if amount_from <= 0:
            return
        actual = min(self.get(c_from), float(amount_from))
        if actual <= 0:
            return
        self.set(c_from, self.get(c_from) - actual)
        self.add(c_to, convert_units(actual, c_from, c_to))

    # --- diagnostics ----------------------------------------------------------
    def snapshot(self) -> Dict[str, float]:
        """
        Human-readable snapshot. Keys like 'X','T','N','B','A' if available.
        """
        out: Dict[str, float] = {}
        for c in self.cascade:
            name = getattr(c, "name", None)
            if name is None:
                name = str(c)
            out[str(name)] = self.get(c)
        return out


# Convenience factory, matching common loader expectations
def make_energy_accountant(initial: Optional[Dict[object, float]] = None,
                           cascade: Optional[Iterable[object]] = None) -> LayerEnergyAccountant:
    return LayerEnergyAccountant.new(initial=initial, cascade=cascade)

# AURORA_EVOLVED_NATIVE_BEGIN
try:
    import inspect as _aurora_native_inspect
except Exception as _aurora_boundary_exc:
    _aurora_record_exception_from_locals(
        locals(),
        module=__name__,
        operation="exception_handler:aurora_internal/aurora_energy_layer_costs_decay.py:277",
        exc=_aurora_boundary_exc,
        context={"function": "<module>", "handler_line": 277, "source_file": "aurora_internal/aurora_energy_layer_costs_decay.py"},
    )
    _aurora_native_inspect = None

try:
    from aurora_internal.aurora_evolved_surfaces import AuroraEvolvedSurfaceEngine as _AuroraEvolvedSurfaceEngine
except Exception as _aurora_boundary_exc:
    _aurora_record_exception_from_locals(
        locals(),
        module=__name__,
        operation="exception_handler:aurora_internal/aurora_energy_layer_costs_decay.py:282",
        exc=_aurora_boundary_exc,
        context={"function": "<module>", "handler_line": 282, "source_file": "aurora_internal/aurora_energy_layer_costs_decay.py"},
    )
    _AuroraEvolvedSurfaceEngine = None

_AURORA_NATIVE_EVOLVED_ENGINE = None

def _aurora_native_evolved_engine():
    global _AURORA_NATIVE_EVOLVED_ENGINE
    if _AURORA_NATIVE_EVOLVED_ENGINE is None and _AuroraEvolvedSurfaceEngine is not None:
        _AURORA_NATIVE_EVOLVED_ENGINE = _AuroraEvolvedSurfaceEngine()
    return _AURORA_NATIVE_EVOLVED_ENGINE

_AURORA_NATIVE_MODULE = 'aurora_internal.aurora_energy_layer_costs_decay'

_AURORA_NATIVE_EVOLVED_ORIGINALS = {}
_AURORA_NATIVE_EVOLVED_LAST = {}
_AURORA_NATIVE_STRATEGIES = {'Constraint': {'ability_hits': 19,
                'alignment_gap': 0.0,
                'alignment_target_score': 0.921,
                'best_coupling_signature': 'N^2*B^2',
                'constraints': ['energy', 'boundary'],
                'contract_profile': {'accepts_payload': True,
                                     'async_callable': False,
                                     'callable': True,
                                     'class_target': True,
                                     'constraint_density': 2,
                                     'contract_mode': 'stateless',
                                     'doc_hint': 'The five fundamental constraints.',
                                     'effect_density': 3,
                                     'kwonly_args': 4,
                                     'optional_args': 5,
                                     'required_args': 1,
                                     'return_hint': 'boundary_record',
                                     'signature_text': '(value, names=None, *, module=None, '
                                                       'qualname=None, type=None, start=1)',
                                     'stateful_owner': False,
                                     'target_kind': 'class',
                                     'varargs': False,
                                     'varkw': False},
                'coupling_similarity': 1.0,
                'cross_diversity_links': 4,
                'effect_modes': ['cost_pressure_change',
                                 'interface_boundary_change',
                                 'class_lineage_surface'],
                'effect_phrases': ['class growth reflected through '
                                   'aurora_internal.aurora_energy_layer_costs_decay',
                                   'Constraint changed downstream system pressure'],
                'genealogy_pressure': 0.79846,
                'inheritance_breach_count': 1,
                'kind': 'reflection',
                'link_hits': 38,
                'module': 'aurora_internal.aurora_energy_layer_costs_decay',
                'op_id': 'aurora_internal.aurora_energy_layer_costs_decay.Constraint',
                'origin_activity': 0,
                'persistence_tax_factor': 1.422994,
                'representation_score': 0.480407,
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
                'signature': 'N^2*B^2',
                'surface_score': 0.921,
                'sustainability_score': 0.498642,
                'target_kind': 'class'}}

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


def constraint_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_energy_layer_costs_decay.Constraint', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_energy_layer_costs_decay_constraint')(payload=payload, **kwargs)

if _aurora_get_target(['Constraint']) is not None:
    setattr(_aurora_get_target(['Constraint']), 'evolved_reflection', staticmethod(constraint_evolved))
    setattr(_aurora_get_target(['Constraint']), '_aurora_alignment_gap', 0.0)
    setattr(_aurora_get_target(['Constraint']), '_aurora_alignment_target_score', 0.921)

AURORA_NATIVE_EVOLVED_EXPORTS = {'aurora_internal.aurora_energy_layer_costs_decay.Constraint': 'constraint_evolved'}
AURORA_NATIVE_EVOLUTION_OVERRIDES = {'aurora_internal.aurora_energy_layer_costs_decay.Constraint': {'export': 'constraint_evolved',
                                                                'mode': 'class_reflection_hook',
                                                                'target': 'Constraint'}}
# AURORA_EVOLVED_NATIVE_END
