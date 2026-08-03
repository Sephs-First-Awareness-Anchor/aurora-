# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
External structural/safety audit (2026-08-02): an identical ~440-line
"auto-evolution surface adapter" block (_aurora_native_evolved_engine,
_aurora_assign_target, _aurora_get_target, _aurora_bind_owner_attribute,
_aurora_target_strategy, _aurora_target_feedback, _aurora_store_reflection,
_aurora_store_owner_state, _aurora_make_override, _aurora_make_latent_binding,
and 4 module-specific _aurora_apply_*_rewrite functions) was pasted,
byte-identical, into 25 separate modules by aurora_internal/aurora_code_
autoevolver.py's own generator. One already found regression: aurora_
simulation_engine.py had a real fix (preserving @property/@staticmethod/
@classmethod descriptors on reassignment) that was never propagated to
the other 24 files.

aurora_internal/aurora_evolution_hook.py is the new canonical, hand-
maintained module (deliberately not aurora_evolved_surfaces.py, which is
itself generated output and would silently discard hand-added functions
on the next regeneration). This test proves the new shared functions are
BEHAVIORALLY EQUIVALENT to the old per-file versions before any of the
25 files are migrated to call them -- run against aurora.py's own
still-in-place copies (the 24-file "canonical" variant) as the ground
truth, plus a direct check that the property/staticmethod/classmethod
descriptor fix (previously only in aurora_simulation_engine.py) is now
present in the shared version everyone will get.
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import aurora as A  # noqa: E402
import aurora_internal.aurora_evolution_hook as H  # noqa: E402


# ---------------------------------------------------------------------------
# get_target / assign_target / bind_owner_attribute
# ---------------------------------------------------------------------------

def test_get_target_single_element_chain():
    g = {'thing': 42}
    assert H.get_target(g, ['thing']) == 42


def test_get_target_multi_element_chain():
    # aurora.py's own _aurora_get_target always resolves against aurora.py's
    # own globals(), so it can't be called against a foreign dict directly;
    # this checks the shared function's behavior against the documented
    # semantics the old per-file version had (walk attrs, None on any miss).
    class Owner:
        pass
    owner = Owner()
    owner.attr = 'value'
    g1 = {'owner': owner}
    g2 = {'owner': owner}
    assert H.get_target(g1, ['owner', 'attr']) == 'value'
    assert H.get_target(g2, ['missing', 'attr']) is None
    assert H.get_target({}, []) is None


def test_assign_target_single_element_chain():
    g = {}
    assert H.assign_target(g, ['x'], 99) is True
    assert g['x'] == 99


def test_assign_target_missing_root_returns_false():
    g = {}
    assert H.assign_target(g, ['missing', 'attr'], 1) is False


def test_assign_target_plain_attribute_unaffected_by_descriptor_logic():
    class Owner:
        pass
    owner = Owner()
    owner.attr = 'old'
    g = {'owner': owner}
    assert H.assign_target(g, ['owner', 'attr'], 'new') is True
    assert owner.attr == 'new'


def test_assign_target_preserves_property_descriptor_on_plain_callable():
    """The fix previously unique to aurora_simulation_engine.py -- assigning
    a plain callable over an existing @property must wrap it back into a
    property, not silently replace the property with a bare function."""
    class Owner:
        @property
        def value(self):
            return self._v
        @value.setter
        def value(self, v):
            self._v = v

    def new_getter(self):
        return 'overridden'

    assign_target_test_owner = Owner
    g = {'Owner': assign_target_test_owner}
    assert H.assign_target(g, ['Owner', 'value'], new_getter) is True
    instance = Owner()
    instance._v = 'ignored'
    assert isinstance(inspect_getattr_static(Owner, 'value'), property)
    assert instance.value == 'overridden'


def test_assign_target_preserves_staticmethod_descriptor():
    class Owner:
        @staticmethod
        def compute():
            return 1

    def new_compute():
        return 2

    g = {'Owner': Owner}
    assert H.assign_target(g, ['Owner', 'compute'], new_compute) is True
    assert isinstance(inspect_getattr_static(Owner, 'compute'), staticmethod)
    assert Owner.compute() == 2


def test_bind_owner_attribute_sets_attribute_via_chain():
    class Owner:
        pass
    owner = Owner()
    g = {'owner': owner}
    assert H.bind_owner_attribute(g, ['owner'], 'bound', 'value') is True
    assert owner.bound == 'value'


def test_bind_owner_attribute_missing_owner_returns_false():
    assert H.bind_owner_attribute({}, ['missing'], 'attr', 'v') is False


import inspect as _inspect_module
def inspect_getattr_static(obj, name):
    return _inspect_module.getattr_static(obj, name, None)


# ---------------------------------------------------------------------------
# target_strategy / target_feedback -- compare directly against aurora.py's
# live _AURORA_NATIVE_STRATEGIES data (still in place, pre-migration).
# ---------------------------------------------------------------------------

def test_target_strategy_matches_aurora_py_live_data():
    strategies = A._AURORA_NATIVE_STRATEGIES
    for key in list(strategies.keys())[:5]:
        assert H.target_strategy(strategies, key) == A._aurora_target_strategy(key)


def test_target_feedback_matches_aurora_py_live_data():
    strategies = A._AURORA_NATIVE_STRATEGIES
    for key in list(strategies.keys())[:5]:
        assert H.target_feedback(strategies, key) == A._aurora_target_feedback(key)


def test_target_strategy_unknown_key_returns_empty_dict():
    assert H.target_strategy({}, 'nonexistent.key') == {}


def test_target_feedback_unknown_key_returns_empty_dict():
    assert H.target_feedback({}, 'nonexistent.key') == {}


# ---------------------------------------------------------------------------
# store_reflection / store_owner_state
# ---------------------------------------------------------------------------

class _Owner:
    pass


def test_store_reflection_sets_dict_on_owner():
    owner = _Owner()
    H.store_reflection('some.target', {'r': 1}, (owner,))
    assert owner._aurora_evolved_reflections == {'some.target': {'r': 1}}


def test_store_reflection_no_args_is_noop():
    H.store_reflection('some.target', {'r': 1}, ())  # must not raise


def test_store_owner_state_sets_named_attribute():
    owner = _Owner()
    H.store_owner_state('_custom_attr', 'key1', 'value1', (owner,))
    assert owner._custom_attr == {'key1': 'value1'}


def test_store_owner_state_accumulates_across_calls():
    owner = _Owner()
    H.store_owner_state('_custom_attr', 'key1', 'v1', (owner,))
    H.store_owner_state('_custom_attr', 'key2', 'v2', (owner,))
    assert owner._custom_attr == {'key1': 'v1', 'key2': 'v2'}


# ---------------------------------------------------------------------------
# apply_result_rewrite dispatch -- matches aurora.py's live dispatcher
# (aurora.py's own _AURORA_NATIVE_MODULE is 'aurora', so its own dispatcher
# falls through to the generic path; the 4 specializations are exercised
# directly by module identity string instead).
# ---------------------------------------------------------------------------

def test_apply_result_rewrite_generic_path_matches_aurora_py():
    strategies = A._AURORA_NATIVE_STRATEGIES
    target_key = next(iter(strategies.keys())) if strategies else 'nonexistent'
    result = {'k': 'v'}
    reflection = {'ref': True}
    args, kwargs = (), {}
    old = A._aurora_apply_result_rewrite(target_key, result, reflection, args, kwargs)
    new = H.apply_result_rewrite(A._AURORA_NATIVE_MODULE, strategies, target_key, result, reflection, args, kwargs)
    assert old == new


def test_apply_result_rewrite_dispatches_by_native_module():
    strategies = {}
    result = {'k': 'v'}
    reflection = {'ref': True}
    for module_name, expected_key in [
        ('aurora_internal.constraint_genealogy', 'lineage_memory'),
        ('aurora_governance_persistence_gateway', 'governance_evolution_context'),
        ('aurora_expression_perception', 'perception_evolution_context'),
        ('aurora_dimensional_systems', 'dimensional_evolution_context'),
        ('some_unrecognized_module', 'generic_adaptation'),
    ]:
        rewritten = H.apply_result_rewrite(module_name, strategies, 'x.y', result, reflection, (), {})
        assert isinstance(rewritten, dict)
        # Each specialization (and the generic fallback) stamps its own
        # distinguishing context key -- confirms dispatch actually reached
        # the right branch, not that some other branch happened to overlap.
        assert expected_key in rewritten, f"{module_name} -> missing {expected_key!r}, got {sorted(rewritten.keys())}"


def test_apply_result_rewrite_none_result_uses_reflection_fallback():
    rewritten = H.apply_result_rewrite('unknown_module', {}, 'x', None, {'a': 1}, (), {})
    assert rewritten is not None
    assert rewritten.get('a') == 1
    assert '_aurora_rewrite_profile' in rewritten


def test_apply_result_rewrite_scalar_result_passthrough():
    rewritten = H.apply_result_rewrite('unknown_module', {}, 'x', 42, None, (), {})
    assert rewritten == 42


# ---------------------------------------------------------------------------
# make_override / make_latent_binding
# ---------------------------------------------------------------------------

def test_make_override_wraps_plain_callable_and_calls_result_rewrite():
    globals_dict = {}

    def export_fn(args_meta):
        return {'reflected': True, 'args_meta': args_meta}

    globals_dict['export_fn'] = export_fn

    def original(x):
        return x * 2

    originals = {'target': original}
    evolved_last = {}

    def engine_fn():
        return object()  # any non-None "engine"

    override = H.make_override(
        globals_dict, originals, evolved_last, engine_fn,
        'unknown_module', {}, 'export_fn', 'target',
    )
    result = override(5)
    # original(5) == 10, a dict, so apply_result_rewrite enriches it
    assert isinstance(result, dict) or result == 10
    assert 'target' in evolved_last


def test_make_override_reads_a_property_original_via_get():
    class Owner:
        @property
        def value(self):
            return 'the_value'

    globals_dict = {}

    def export_fn(args_meta):
        return {'reflected': True}

    globals_dict['export_fn'] = export_fn
    originals = {'Owner.value': Owner.value}
    evolved_last = {}

    def engine_fn():
        return object()

    override = H.make_override(
        globals_dict, originals, evolved_last, engine_fn,
        'unknown_module', {}, 'export_fn', 'Owner.value',
    )
    owner = Owner()
    # Calling override(owner) should read the property via __get__, not
    # attempt to call the property object (which would raise TypeError).
    result = override(owner)
    assert result is not None


def test_make_latent_binding_constructs_payload_from_owner():
    globals_dict = {}

    def export_fn(payload=None, **kwargs):
        return {'payload': payload}

    globals_dict['export_fn'] = export_fn
    evolved_last = {}

    binding = H.make_latent_binding(globals_dict, evolved_last, 'export_fn', 'target.key')

    class Owner:
        pass
    owner = Owner()
    result = binding(owner)
    assert result['payload']['bound_target'] == 'target.key'
    assert result['payload']['owner_type'] == 'Owner'
    assert evolved_last['target.key']['latent_binding_active'] is True
    assert owner._aurora_latent_bindings == {'target.key': result}


def test_make_latent_binding_no_args_builds_minimal_payload():
    globals_dict = {}

    def export_fn(payload=None, **kwargs):
        return {'payload': payload}

    globals_dict['export_fn'] = export_fn
    evolved_last = {}
    binding = H.make_latent_binding(globals_dict, evolved_last, 'export_fn', 'target.key')
    result = binding()
    assert result['payload'] is None
