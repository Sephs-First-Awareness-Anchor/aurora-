# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA BUILD 648 EVOLUTIONARY INFRASTRUCTURE CLOSURE DIRECTIVE, Phase 4:
AuroraRuntime.code_autoevolve_once() previously staged a before-snapshot
over only the caller-supplied target_files, then let
CodeAutoEvolver.apply_operator() run -- and for native_surface_projection
specifically, the real update set (derived from operation descriptors
via _build_native_projection_updates()) can touch files beyond that
target. evaluate_mutation() then measured "after" using the ORIGINAL
target_files, so any pressure change in the extra touched files never
entered the accept/reject decision -- a mutation could receive fitness
credit for something never actually measured.

This proves the repair at the real AuroraRuntime.code_autoevolve_once()
call site (not a reimplementation): a genuinely-booted runtime (steerer-
backed, since code_simulate_mutation() requires a real steerer) with
its code_chamber/_code_autoevolver redirected to an isolated synthetic
repo so no real repository file is touched. CodeAutoEvolver.apply_operator/
plan_operator are stubbed only to make WHICH files change deterministic
(exercising the operator_key="native_surface_projection" label this
phase is named for) -- the runtime's own new planning/reconciliation/
escape-detection logic runs for real and unstubbed.

Expensive (one real boot) -- kept to a single focused test.
"""
import os
import shutil
import sys
import tempfile
import textwrap
from unittest.mock import patch

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_runtime import AuroraRuntime
from aurora_internal.aurora_code_evolution_chamber import CodeEvolutionChamber
from aurora_internal.aurora_code_autoevolver import CodeAutoEvolver


def _write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(content))


def test_every_changed_file_participates_in_fitness_scope_or_mutation_is_rejected():
    scratch = tempfile.mkdtemp(prefix="aurora_build648_p4_")
    boot_scratch = tempfile.mkdtemp(prefix="aurora_build648_p4_boot_")
    try:
        primary = os.path.join(scratch, "aurora_internal", "aurora_evolved_surfaces.py")
        escaped_file = os.path.join(scratch, "aurora_internal", "unplanned_module.py")
        _write(primary, "def hot_fn(x):\n" + "".join(
            f"    if x == {i}:\n        x = x + {i}\n" for i in range(30)
        ) + "    return x\n")
        _write(escaped_file, "def untouched_fn(x):\n    return x\n")

        runtime = AuroraRuntime(
            state_dir=os.path.join(boot_scratch, "aurora_state"),
            output_dir=os.path.join(boot_scratch, "aurora_runtime_output"),
        )
        runtime.boot(verbose=False)
        assert runtime.code_chamber is not None and runtime._code_autoevolver is not None

        # Redirect the runtime's evolution machinery to the isolated
        # synthetic repo -- the real boot above is only needed for a real
        # steerer; no real repository file is touched by this test.
        runtime.code_chamber = CodeEvolutionChamber(
            repo_root=scratch, output_dir=os.path.join(scratch, "out"),
        )
        runtime._code_autoevolver = CodeAutoEvolver(repo_root=scratch)

        def _stub_plan_operator(self, operator_key, target_files):
            return [primary]  # plan only ever anticipates the primary file

        def _stub_apply_operator(self, operator_key, target_files):
            with open(primary, "r", encoding="utf-8") as f:
                primary_original = f.read()
            with open(escaped_file, "r", encoding="utf-8") as f:
                escaped_original = f.read()
            # Genuine relief on the planned file...
            with open(primary, "w", encoding="utf-8") as f:
                f.write("def hot_fn(x):\n    return x\n")
            # ...but ALSO touches a file the plan never anticipated.
            with open(escaped_file, "w", encoding="utf-8") as f:
                f.write("def untouched_fn(x):\n    return x + 999\n")
            return {
                "operator_key": operator_key,
                "changed_files": [primary, escaped_file],
                "change_count": 2,
                "backups": {primary: primary_original, escaped_file: escaped_original},
                "details": [], "rejected": [], "rejected_count": 0,
            }

        with patch.object(CodeAutoEvolver, "plan_operator", _stub_plan_operator), \
             patch.object(CodeAutoEvolver, "apply_operator", _stub_apply_operator):
            result = runtime.code_autoevolve_once(
                operator_key="native_surface_projection",
                target_files=[primary],
                chain_ticks=5, episodes=0, turns=1,
            )

        # The escape must be detected and reported...
        assert escaped_file in result["escaped_plan_scope"] or \
            os.path.abspath(escaped_file) in result["escaped_plan_scope"]
        # ...and the mutation must NOT be silently accepted on the
        # strength of the planned file's real relief while the escaped
        # file's change went unmeasured.
        assert result["final"]["accepted"] is False
        # Because valid before/after evidence was unavailable for the
        # escaped file, both files must be rolled back -- not just the
        # unplanned one -- since accepting a partial, half-measured state
        # would itself be fabricating an untested combination.
        with open(primary, "r", encoding="utf-8") as f:
            assert "for i in range(30)" not in f.read()  # sanity: real content, not a stub artifact
        with open(escaped_file, "r", encoding="utf-8") as f:
            assert f.read() == "def untouched_fn(x):\n    return x\n"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
        shutil.rmtree(boot_scratch, ignore_errors=True)


def test_actual_changed_files_within_plan_are_reconciled_and_measured():
    """Contrast case: when the actual change stays within the planned
    scope, evaluation must reconcile to (and correctly measure) the real
    changed files, not merely the originally-requested target -- and a
    genuine relief must be able to survive."""
    scratch = tempfile.mkdtemp(prefix="aurora_build648_p4b_")
    boot_scratch = tempfile.mkdtemp(prefix="aurora_build648_p4b_boot_")
    try:
        primary = os.path.join(scratch, "aurora_internal", "aurora_evolved_surfaces.py")
        companion = os.path.join(scratch, "aurora_internal", "companion_module.py")
        _write(primary, "def hot_fn(x):\n" + "".join(
            f"    if x == {i}:\n        x = x + {i}\n" for i in range(30)
        ) + "    return x\n")
        _write(companion, "def companion_fn(x):\n    return x\n")

        runtime = AuroraRuntime(
            state_dir=os.path.join(boot_scratch, "aurora_state"),
            output_dir=os.path.join(boot_scratch, "aurora_runtime_output"),
        )
        runtime.boot(verbose=False)
        runtime.code_chamber = CodeEvolutionChamber(
            repo_root=scratch, output_dir=os.path.join(scratch, "out"),
        )
        runtime._code_autoevolver = CodeAutoEvolver(repo_root=scratch)

        def _stub_plan_operator(self, operator_key, target_files):
            return [primary, companion]  # plan anticipates BOTH

        def _stub_apply_operator(self, operator_key, target_files):
            with open(primary, "r", encoding="utf-8") as f:
                primary_original = f.read()
            with open(primary, "w", encoding="utf-8") as f:
                f.write("def hot_fn(x):\n    return x\n")
            return {
                "operator_key": operator_key,
                "changed_files": [primary],  # companion planned but not actually touched
                "change_count": 1,
                "backups": {primary: primary_original},
                "details": [], "rejected": [], "rejected_count": 0,
            }

        with patch.object(CodeAutoEvolver, "plan_operator", _stub_plan_operator), \
             patch.object(CodeAutoEvolver, "apply_operator", _stub_apply_operator):
            result = runtime.code_autoevolve_once(
                operator_key="native_surface_projection",
                target_files=[primary],
                chain_ticks=5, episodes=0, turns=1,
            )

        assert result["escaped_plan_scope"] == []
        assert result["final"]["accepted"] is True
        with open(primary, "r", encoding="utf-8") as f:
            assert f.read() == "def hot_fn(x):\n    return x\n"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
        shutil.rmtree(boot_scratch, ignore_errors=True)
