# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Canonical evolution-hook engine.

External structural/safety audit (2026-08-02): an identical ~440-line
"auto-evolution surface adapter" block (_aurora_native_evolved_engine,
_aurora_assign_target, _aurora_get_target, _aurora_bind_owner_attribute,
_aurora_target_strategy, _aurora_target_feedback, _aurora_store_reflection,
_aurora_store_owner_state, _aurora_make_override, _aurora_make_latent_binding,
and 4 module-specific _aurora_apply_*_rewrite functions of which only ONE
is ever reachable in any given file) had been pasted into 25 separate
modules by aurora_internal/aurora_code_autoevolver.py's own code generator
(_native_wrapper_block). One evolutionary mechanism wearing 25 identical
coats, not 25 independent ones -- and the risk that framing warns about
had already manifested: aurora_simulation_engine.py had picked up a real
fix (preserving @property/@staticmethod/@classmethod descriptors when a
target gets reassigned, in both _aurora_assign_target and
_aurora_make_override) that was never propagated to the other 24 files,
which would silently strip such a descriptor if code evolution ever
reassigned one of their targets.

This module is that one canonical engine. Deliberately NOT placed in
aurora_internal/aurora_evolved_surfaces.py -- that file is itself
generated output ("Do not hand-edit generated methods; regenerate
through the code autoevolver", per its own docstring) produced by
CodeAutoEvolver._module_template(), and a full regeneration would
silently discard anything hand-added there.

Each of the 25 (now migrated) call sites keeps exactly the state that is
genuinely per-module -- _AURORA_NATIVE_MODULE (identity string),
_AURORA_NATIVE_STRATEGIES (this module's own target metadata, the "each
subsystem contributing target metadata... and its specialized rewrite
strategy" the audit asked for), _AURORA_NATIVE_EVOLVED_ORIGINALS/_LAST
(mutable per-target state), and its own globals() -- and delegates the
actual mechanism to the functions below via thin one-line wrappers.
_aurora_native_evolved_engine() itself (a 5-line lazy singleton getter)
was left untouched per file rather than migrated: parameterizing a
`global` rebind across 25 files for 5 lines of code was not worth the
added indirection.
"""
from __future__ import annotations

import inspect
from typing import Any, Callable, Dict, List, Optional

from aurora_internal.aurora_runtime_faults import record_exception_from_locals as _aurora_record_exception_from_locals


# ---------------------------------------------------------------------------
# Target resolution -- operates on a caller-supplied globals() dict so target
# resolution/assignment happens in the CALLING module's own namespace, not
# this shared module's. Passing globals() explicitly (rather than calling
# the builtin globals() in here, which would resolve against this module's
# own namespace) is what keeps this centralization behavior-preserving.
# ---------------------------------------------------------------------------

def assign_target(globals_dict: Dict[str, Any], chain: List[str], value: Any) -> bool:
    """Canonical target assignment. Preserves @property/@staticmethod/
    @classmethod descriptors on the existing target when reassigning --
    the fix that previously existed only in aurora_simulation_engine.py,
    now the one shared behavior everywhere."""
    if not chain:
        return False
    if len(chain) == 1:
        globals_dict[chain[0]] = value
        return True
    current = globals_dict.get(chain[0])
    if current is None:
        return False
    for attr in chain[1:-1]:
        if not hasattr(current, attr):
            return False
        current = getattr(current, attr)
    attr_name = chain[-1]
    descriptor = inspect.getattr_static(current, attr_name, None)
    if isinstance(descriptor, property) and not isinstance(value, property):
        if callable(value):
            value = property(value, descriptor.fset, descriptor.fdel, descriptor.__doc__)
        else:
            value = property(lambda _instance, _value=value: _value, descriptor.fset, descriptor.fdel, descriptor.__doc__)
    elif isinstance(descriptor, staticmethod) and not isinstance(value, staticmethod):
        value = staticmethod(value) if callable(value) else descriptor
    elif isinstance(descriptor, classmethod) and not isinstance(value, classmethod):
        value = classmethod(value) if callable(value) else descriptor
    setattr(current, attr_name, value)
    return True


def get_target(globals_dict: Dict[str, Any], chain: List[str]) -> Any:
    if not chain:
        return None
    if len(chain) == 1:
        return globals_dict.get(chain[0])
    current = globals_dict.get(chain[0])
    if current is None:
        return None
    for attr in chain[1:]:
        if not hasattr(current, attr):
            return None
        current = getattr(current, attr)
    return current


def bind_owner_attribute(globals_dict: Dict[str, Any], owner_chain: List[str], attr_name: str, value: Any) -> bool:
    owner = get_target(globals_dict, owner_chain)
    if owner is None or not attr_name:
        return False
    try:
        setattr(owner, attr_name, value)
        return True
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(),
            module=__name__,
            operation="exception_handler:aurora_internal/aurora_evolution_hook.py:bind_owner_attribute",
            exc=_aurora_boundary_exc,
            context={"function": "bind_owner_attribute", "source_file": "aurora_internal/aurora_evolution_hook.py"},
        )
        return False


# ---------------------------------------------------------------------------
# Target metadata lookups -- `strategies` is the caller's own
# _AURORA_NATIVE_STRATEGIES dict: per-module target metadata, genuinely not
# shareable data, passed in explicitly rather than centralized.
# ---------------------------------------------------------------------------

def target_strategy(strategies: Dict[str, Any], target_key: Any) -> Dict[str, Any]:
    return dict(strategies.get(str(target_key), {}) or {})


def target_feedback(strategies: Dict[str, Any], target_key: Any) -> Dict[str, Any]:
    return dict(target_strategy(strategies, target_key).get('rewrite_feedback', {}) or {})


# ---------------------------------------------------------------------------
# Owner-instance state -- mutates args[0] (the bound method's own owner
# object) directly. Fully generic: no per-module state involved at all.
# ---------------------------------------------------------------------------

def store_reflection(target_key: Any, reflection: Any, args: tuple) -> None:
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
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(),
            module=__name__,
            operation="exception_handler:aurora_internal/aurora_evolution_hook.py:store_reflection",
            exc=_aurora_boundary_exc,
            context={"function": "store_reflection", "source_file": "aurora_internal/aurora_evolution_hook.py"},
        )


def store_owner_state(attribute: str, target_key: Any, value: Any, args: tuple) -> None:
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
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(),
            module=__name__,
            operation="exception_handler:aurora_internal/aurora_evolution_hook.py:store_owner_state",
            exc=_aurora_boundary_exc,
            context={"function": "store_owner_state", "source_file": "aurora_internal/aurora_evolution_hook.py"},
        )


# ---------------------------------------------------------------------------
# Specialized rewrite strategies -- each subsystem's own rewrite behavior.
# Parameterized on `strategies` (that module's _AURORA_NATIVE_STRATEGIES)
# rather than closing over a module global, so these stay pure functions.
# ---------------------------------------------------------------------------

def apply_constraint_genealogy_rewrite(strategies: Dict[str, Any], target_key: Any, result: Any,
                                        reflection: Any, args: tuple, kwargs: dict) -> Any:
    strategy = target_strategy(strategies, target_key)
    feedback = target_feedback(strategies, target_key)
    bias = str(strategy.get('rewrite_bias', 'lineage_memory') or 'lineage_memory')
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    effect_modes = list(strategy.get('effect_modes', []) or [])
    store_reflection(target_key, reflection, args)
    store_owner_state('_aurora_genealogy_strategy', target_key, strategy, args)
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
    store_owner_state(
        '_aurora_genealogy_scalar_observations',
        target_key,
        {'result': result, 'strategy': strategy, 'reflection': reflection},
        args,
    )
    return result


def apply_governance_rewrite(strategies: Dict[str, Any], target_key: Any, result: Any,
                              reflection: Any, args: tuple, kwargs: dict) -> Any:
    strategy = target_strategy(strategies, target_key)
    feedback = target_feedback(strategies, target_key)
    bias = str(strategy.get('rewrite_bias', 'governance_routing') or 'governance_routing')
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    effect_modes = list(strategy.get('effect_modes', []) or [])
    store_reflection(target_key, reflection, args)
    store_owner_state('_aurora_governance_strategy', target_key, strategy, args)
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
    store_owner_state(
        '_aurora_governance_evolution_state',
        target_key,
        {'result': result, 'strategy': strategy, 'reflection': reflection},
        args,
    )
    return result


def apply_perception_rewrite(strategies: Dict[str, Any], target_key: Any, result: Any,
                              reflection: Any, args: tuple, kwargs: dict) -> Any:
    strategy = target_strategy(strategies, target_key)
    feedback = target_feedback(strategies, target_key)
    bias = str(strategy.get('rewrite_bias', 'perceptual_synthesis') or 'perceptual_synthesis')
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    effect_modes = list(strategy.get('effect_modes', []) or [])
    store_reflection(target_key, reflection, args)
    store_owner_state('_aurora_perception_strategy', target_key, strategy, args)
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
    store_owner_state(
        '_aurora_perception_evolution_state',
        target_key,
        {'result': result, 'strategy': strategy, 'reflection': reflection},
        args,
    )
    return result


def apply_dimensional_rewrite(strategies: Dict[str, Any], target_key: Any, result: Any,
                               reflection: Any, args: tuple, kwargs: dict) -> Any:
    strategy = target_strategy(strategies, target_key)
    feedback = target_feedback(strategies, target_key)
    bias = str(strategy.get('rewrite_bias', 'dimensional_balancing') or 'dimensional_balancing')
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    effect_modes = list(strategy.get('effect_modes', []) or [])
    store_reflection(target_key, reflection, args)
    store_owner_state('_aurora_dimensional_strategy', target_key, strategy, args)
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
    store_owner_state(
        '_aurora_dimensional_evolution_state',
        target_key,
        {'result': result, 'strategy': strategy, 'reflection': reflection},
        args,
    )
    return result


def apply_result_rewrite(native_module: str, strategies: Dict[str, Any], target_key: Any, result: Any,
                          reflection: Any, args: tuple, kwargs: dict) -> Any:
    """Dispatches to one of the 4 specializations by module identity, or a
    generic fallback -- the same design each of the 25 files already had,
    just no longer with all 4 branches (3 of which can never fire in any
    given module) pasted alongside the one that's actually reachable."""
    if native_module == 'aurora_internal.constraint_genealogy':
        return apply_constraint_genealogy_rewrite(strategies, target_key, result, reflection, args, kwargs)
    if native_module == 'aurora_governance_persistence_gateway':
        return apply_governance_rewrite(strategies, target_key, result, reflection, args, kwargs)
    if native_module == 'aurora_expression_perception':
        return apply_perception_rewrite(strategies, target_key, result, reflection, args, kwargs)
    if native_module == 'aurora_dimensional_systems':
        return apply_dimensional_rewrite(strategies, target_key, result, reflection, args, kwargs)
    store_reflection(target_key, reflection, args)
    strategy = target_strategy(strategies, target_key)
    feedback = target_feedback(strategies, target_key)
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
        store_owner_state(
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


# ---------------------------------------------------------------------------
# Override / latent-binding construction.
# ---------------------------------------------------------------------------

def make_override(globals_dict: Dict[str, Any], originals: Dict[str, Any], evolved_last: Dict[str, Any],
                   native_evolved_engine_fn: Callable[[], Any], native_module: str,
                   strategies: Dict[str, Any], export_name: str, target_key: Any) -> Callable:
    """Preserves @property originals (reads via the descriptor protocol
    rather than trying to call a property object) -- the fix that
    previously existed only in aurora_simulation_engine.py."""
    original = originals.get(target_key)

    def _override(*args, **kwargs):
        result = None
        if isinstance(original, property):
            if args:
                result = original.__get__(args[0], type(args[0]))
        elif callable(original):
            result = original(*args, **kwargs)
        engine = native_evolved_engine_fn()
        reflection = {
            'available': False,
            'reason': 'evolved_surface_engine_unavailable',
            'target': target_key,
        }
        if engine is not None:
            reflection = globals_dict[export_name]({'args_len': len(args), 'kwargs_keys': sorted(kwargs.keys())})
        evolved_last[target_key] = reflection
        rewritten = apply_result_rewrite(native_module, strategies, target_key, result, reflection, args, kwargs)
        if rewritten is not None:
            return rewritten
        if result is not None:
            return result
        return reflection

    _override.__name__ = str(target_key).split('.')[-1]
    _override.__qualname__ = _override.__name__
    if isinstance(original, property):
        _override.__doc__ = original.__doc__
    elif callable(original):
        _override.__doc__ = getattr(original, '__doc__', None)
        _override.__wrapped__ = original
        try:
            _override.__signature__ = inspect.signature(original)
        except Exception as _aurora_boundary_exc:
            _aurora_record_exception_from_locals(
                locals(),
                module=__name__,
                operation="exception_handler:aurora_internal/aurora_evolution_hook.py:make_override",
                exc=_aurora_boundary_exc,
                context={"function": "make_override", "source_file": "aurora_internal/aurora_evolution_hook.py"},
            )
    return _override


def make_latent_binding(globals_dict: Dict[str, Any], evolved_last: Dict[str, Any],
                         export_name: str, target_key: Any) -> Callable:
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
        result = globals_dict[export_name](payload=payload, **kwargs)
        evolved_last[target_key] = {'latent_binding_active': True, 'last_result_type': type(result).__name__}
        if args:
            store_owner_state('_aurora_latent_bindings', target_key, result, args)
        return result

    _binding.__name__ = str(target_key).split('.')[-1]
    _binding.__qualname__ = _binding.__name__
    _binding.__doc__ = f'Latent evolved binding for {target_key}'
    _binding._aurora_latent_binding_target = target_key
    return _binding
