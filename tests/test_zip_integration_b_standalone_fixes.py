# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Zip integration phase B (2026-07-29): 2 standalone bug fixes ported from
Sunni's uploaded operational-hardening zip, isolated from that zip's
much larger (and separately tracked) exception-instrumentation pass.

Fix 1 -- aurora_simulation_engine.py's native self-rewrite plumbing
(`_aurora_assign_target` / `_aurora_make_override`, used to install
"evolved" replacements for functions like `verify_layer7`) did not
account for `property`/`staticmethod`/`classmethod` descriptors:
- `_aurora_assign_target` did a bare `setattr(current, chain[-1], value)`.
  If the target attribute was a `property` on a class and `value` was a
  plain callable, this silently replaced the property descriptor with
  an unbound function -- any instance reading that attribute afterward
  got the raw function object instead of an invoked getter.
- `_aurora_make_override`'s wrapper only branched on `callable(original)`.
  A `property` object is not callable, so when `original` was itself a
  property, the branch was skipped entirely and `result` stayed `None`
  forever -- the original property's real value was never read.
Fixed by detecting the existing descriptor type before assigning (and
re-wrapping the new value to match it), and by giving `_override` an
explicit `isinstance(original, property)` branch that calls the
property's real `__get__`.

Fix 2 -- aurora_dimensional_systems.py eagerly imported
`aurora_evolution_stack` (plus `aurora_internal.lineage_canonical`) at
module load time to populate the genealogy bridge. This module sits on
a real boot import path (aurora_simulation_engine -> aurora_
consciousness_engine -> aurora_dimensional_systems) where importing
aurora_evolution_stack eagerly risks recursing back through aurora_
simulation_engine before its public types exist. A lazy loader,
`DimensionalSystems._ensure_genealogy_symbols()`, already existed
specifically to survive this import-order cycle and is called by every
real use site -- the eager top-level import was fully redundant with it
and carried the recursion risk the lazy path exists to avoid. Fixed by
deleting the eager import, leaving the bridge symbols `None` until the
lazy loader runs.
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import aurora_simulation_engine as ase  # noqa: E402
import aurora_dimensional_systems as ads  # noqa: E402


def _read_source(filename):
    with open(os.path.join(REPO_ROOT, filename), "r", encoding="utf-8") as f:
        return f.read()


class _HasProperty:
    _value = "original"

    @property
    def prop(self):
        return self._value


def test_assign_target_preserves_property_descriptor_on_plain_callable():
    """The exact bug: assigning a plain function over a class attribute
    that is a property must not clobber the property -- the attribute
    must remain a property afterward, and reading it through an
    instance must invoke the new getter, not return the raw function.
    Uses its own dedicated class (not the shared _HasProperty) so this
    mutation can't leak into other tests in this file."""
    class _HasPropertyLocal:
        _value = "original"

        @property
        def prop(self):
            return self._value

    ase.ZipFixTestTarget = _HasPropertyLocal
    try:
        def new_getter(self):
            return "rewritten"

        ok = ase._aurora_assign_target(["ZipFixTestTarget", "prop"], new_getter)
        assert ok is True
        assert isinstance(_HasPropertyLocal.__dict__["prop"], property), (
            "property descriptor must survive assignment, not be replaced "
            "by a bare function"
        )
        instance = _HasPropertyLocal()
        assert instance.prop == "rewritten"
    finally:
        del ase.ZipFixTestTarget


def test_assign_target_preserves_staticmethod_descriptor():
    class _HasStatic:
        @staticmethod
        def method():
            return "original"

    ase.ZipFixTestTarget2 = _HasStatic
    try:
        def new_impl():
            return "rewritten"

        ok = ase._aurora_assign_target(["ZipFixTestTarget2", "method"], new_impl)
        assert ok is True
        assert isinstance(_HasStatic.__dict__["method"], staticmethod)
        assert _HasStatic.method() == "rewritten"
    finally:
        del ase.ZipFixTestTarget2


def test_make_override_reads_a_property_original_via_get():
    """The other half of the same bug: when the ORIGINAL being wrapped
    is itself a property, the override wrapper must actually invoke its
    getter (via __get__) instead of silently treating it as not
    callable and returning None forever."""
    target_key = "zip_fix_test.prop_target"
    instance = _HasProperty()
    ase._AURORA_NATIVE_EVOLVED_ORIGINALS[target_key] = _HasProperty.__dict__["prop"]
    original_engine_lookup = ase._aurora_native_evolved_engine
    # Isolate the bug under test (property reading) from the separate
    # evolved-surface-engine reflection path, which needs its own real
    # export function wired up in globals() and is not what this fix
    # touches.
    ase._aurora_native_evolved_engine = lambda: None
    try:
        override = ase._aurora_make_override("zip_fix_test_export", target_key)
        result = override(instance)
        assert result == "original", (
            "override of a property original must read its real value "
            "via __get__, not silently return None"
        )
    finally:
        ase._aurora_native_evolved_engine = original_engine_lookup
        ase._AURORA_NATIVE_EVOLVED_ORIGINALS.pop(target_key, None)
        ase._AURORA_NATIVE_EVOLVED_LAST.pop(target_key, None)


def test_dimensional_systems_has_no_eager_evolution_stack_import():
    """Structural check: the module-level eager import block is gone --
    only the lazy loader's own (function-scoped) import survives."""
    source = _read_source("aurora_dimensional_systems.py")
    bridge_start = source.index("Evolution/Genealogy bridge")
    lazy_loader_start = source.index("_ensure_genealogy_symbols")
    module_header = source[:lazy_loader_start]
    # Between the bridge comment and the lazy loader definition, there
    # must be no top-level `from aurora_evolution_stack import` -- only
    # the inert None assignments.
    bridge_block = source[bridge_start:source.index("\n\n", bridge_start + 200)]
    assert "from aurora_evolution_stack import" not in bridge_block
    assert "GENEALOGY_AVAILABLE = False" in bridge_block


def test_dimensional_systems_lazy_loader_still_present_and_used():
    """The lazy loader this fix relies on for real functionality must
    still exist and still be the thing real call sites invoke."""
    assert hasattr(ads.DimensionalSystems, "_ensure_genealogy_symbols")
    source = _read_source("aurora_dimensional_systems.py")
    assert source.count("_ensure_genealogy_symbols()") >= 3, (
        "expected the lazy loader to still be called from its real use sites"
    )


def test_dimensional_systems_genealogy_starts_inert():
    """Import-time state: bridge symbols start None/unavailable and are
    only ever populated by the lazy loader, never at import time."""
    import importlib
    reloaded = importlib.reload(ads)
    assert reloaded.AbilityProfile is None
    assert reloaded.GENEALOGY_AVAILABLE is False
