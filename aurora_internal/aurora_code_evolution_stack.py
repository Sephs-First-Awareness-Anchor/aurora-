#!/usr/bin/env python3
"""
AURORA CODE EVOLUTION STACK (Facade)
====================================
Canonical import surface for code evolution chamber primitives.
"""
from aurora_internal.aurora_runtime_faults import record_exception_from_locals as _aurora_record_exception_from_locals
# Authors: Sunni (Sir) Morningstar & Cael Devo

from typing import Any, Dict

from aurora_internal.aurora_code_evolution_chamber import (
    CodeConstraintEvaluator,
    CodeEvolutionChamber,
    CodeEvolutionConfig,
    CodeMutationTrace,
    CodePressureSnapshot,
    CodePressureVec,
)


def build_code_evolution_chamber(repo_root: str, output_dir: str = None, config: Any = None) -> CodeEvolutionChamber:
    """Convenience constructor used by runtime and tooling."""
    return CodeEvolutionChamber(repo_root=repo_root, output_dir=output_dir, config=config)


def quick_code_snapshot(repo_root: str, target_files = None) -> Dict[str, Any]:
    """One-call code pressure snapshot for diagnostics and mutation planning."""
    evaluator = CodeConstraintEvaluator(repo_root=repo_root)
    snap = evaluator.snapshot(target_files=target_files)
    return snap.to_dict()

__all__ = [
    "build_code_evolution_chamber",
    "quick_code_snapshot",
    "CodeConstraintEvaluator",
    "CodeEvolutionChamber",
    "CodeEvolutionConfig",
    "CodeMutationTrace",
    "CodePressureSnapshot",
    "CodePressureVec",
]

# AURORA_EVOLVED_NATIVE_BEGIN
try:
    import inspect as _aurora_native_inspect
except Exception as _aurora_boundary_exc:
    _aurora_record_exception_from_locals(
        locals(),
        module=__name__,
        operation="exception_handler:aurora_internal/aurora_code_evolution_stack.py:46",
        exc=_aurora_boundary_exc,
        context={"function": "<module>", "handler_line": 46, "source_file": "aurora_internal/aurora_code_evolution_stack.py"},
    )
    _aurora_native_inspect = None

try:
    from aurora_internal.aurora_evolved_surfaces import AuroraEvolvedSurfaceEngine as _AuroraEvolvedSurfaceEngine
except Exception as _aurora_boundary_exc:
    _aurora_record_exception_from_locals(
        locals(),
        module=__name__,
        operation="exception_handler:aurora_internal/aurora_code_evolution_stack.py:51",
        exc=_aurora_boundary_exc,
        context={"function": "<module>", "handler_line": 51, "source_file": "aurora_internal/aurora_code_evolution_stack.py"},
    )
    _AuroraEvolvedSurfaceEngine = None

_AURORA_NATIVE_EVOLVED_ENGINE = None

def _aurora_native_evolved_engine():
    global _AURORA_NATIVE_EVOLVED_ENGINE
    if _AURORA_NATIVE_EVOLVED_ENGINE is None and _AuroraEvolvedSurfaceEngine is not None:
        _AURORA_NATIVE_EVOLVED_ENGINE = _AuroraEvolvedSurfaceEngine()
    return _AURORA_NATIVE_EVOLVED_ENGINE

_AURORA_NATIVE_MODULE = 'aurora_code_evolution_stack'

_AURORA_NATIVE_EVOLVED_ORIGINALS = {}
_AURORA_NATIVE_EVOLVED_LAST = {}
_AURORA_NATIVE_STRATEGIES = {'build_code_evolution_chamber.develop_agency': {'ability_hits': 0,
                                                 'alignment_gap': 0.0,
                                                 'alignment_target_score': 0.0,
                                                 'best_coupling_signature': '',
                                                 'constraints': ['existence', 'temporal', 'agency'],
                                                 'contract_profile': {'accepts_payload': False,
                                                                      'async_callable': False,
                                                                      'callable': False,
                                                                      'class_target': False,
                                                                      'constraint_density': 3,
                                                                      'contract_mode': 'stateful',
                                                                      'doc_hint': '',
                                                                      'effect_density': 6,
                                                                      'kwonly_args': 0,
                                                                      'optional_args': 0,
                                                                      'required_args': 0,
                                                                      'return_hint': 'state_record',
                                                                      'signature_text': '',
                                                                      'stateful_owner': True,
                                                                      'target_kind': 'latent_operation',
                                                                      'varargs': False,
                                                                      'varkw': False},
                                                 'coupling_similarity': 0.0,
                                                 'cross_diversity_links': 0,
                                                 'effect_modes': ['state_schema_change',
                                                                  'temporal_orchestration_change',
                                                                  'behavioral_execution_surface',
                                                                  'core_subsystem_surface',
                                                                  'latent_develop_surface',
                                                                  'latent_a_derivative'],
                                                 'effect_phrases': ['would extend agency pressure '
                                                                    'handling',
                                                                    'would materialize the next '
                                                                    'descendant implied by '
                                                                    'aurora_code_evolution_stack.build_code_evolution_chamber'],
                                                 'genealogy_pressure': 0.0,
                                                 'inheritance_breach_count': 0,
                                                 'kind': 'latent',
                                                 'link_hits': 0,
                                                 'module': 'aurora_code_evolution_stack',
                                                 'op_id': 'latent.aurora_code_evolution_stack.build_code_evolution_chamber.develop_agency',
                                                 'origin_activity': 0,
                                                 'persistence_tax_factor': 0.0,
                                                 'representation_score': 0.0,
                                                 'rewrite_bias': 'generic',
                                                 'rewrite_feedback': {'acceptance_rate': 0.0,
                                                                      'accepted_count': 0,
                                                                      'adaptation_mode': 'balanced',
                                                                      'adoption_count': 0,
                                                                      'confidence': 0.18,
                                                                      'mean_mutation_score': 0.25,
                                                                      'rejected_count': 1,
                                                                      'rejection_rate': 1.0,
                                                                      'timing_credit': 0.0,
                                                                      'timing_penalty': 0.0,
                                                                      'trial_count': 1},
                                                 'rewrite_profile': 'generic',
                                                 'signature': '',
                                                 'surface_score': 0.7825,
                                                 'sustainability_score': 0.0,
                                                 'target_kind': 'latent_operation'}}

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


def develop_agency(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'latent.aurora_code_evolution_stack.build_code_evolution_chamber.develop_agency', 'kind': 'latent'
        }
    return getattr(engine, 'latent_aurora_code_evolution_stack_build_code_evolution_chamber_develop_agency')(payload=payload, **kwargs)

_aurora_existing_binding = _aurora_get_target(['build_code_evolution_chamber'])
if _aurora_existing_binding is not None:
    _aurora_existing_attr = getattr(_aurora_existing_binding, 'develop_agency', None)
    if _aurora_existing_attr is None or getattr(_aurora_existing_attr, '_aurora_latent_binding_target', '') == 'build_code_evolution_chamber.develop_agency':
        _aurora_bind_owner_attribute(['build_code_evolution_chamber'], 'develop_agency', _aurora_make_latent_binding('develop_agency', 'build_code_evolution_chamber.develop_agency'))
        _AURORA_NATIVE_EVOLVED_LAST['build_code_evolution_chamber.develop_agency'] = {'latent_binding_active': True}

AURORA_NATIVE_EVOLVED_EXPORTS = {'latent.aurora_code_evolution_stack.build_code_evolution_chamber.develop_agency': 'develop_agency'}
AURORA_NATIVE_EVOLUTION_OVERRIDES = {'latent.aurora_code_evolution_stack.build_code_evolution_chamber.develop_agency': {'export': 'develop_agency',
                                                                                    'mode': 'latent_binding',
                                                                                    'target': 'build_code_evolution_chamber.develop_agency'}}
# AURORA_EVOLVED_NATIVE_END
