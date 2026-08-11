# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA BUILD 648 EVOLUTIONARY INFRASTRUCTURE CLOSURE DIRECTIVE, Phase 0:
a normal AuroraRuntime.boot() must populate a real, source-current
UniversalFunctionLineage on the stack, and stage_code_mutation() must
actually exercise the Build 646 evolutionary ancestry bridge through
that connection -- without the test manually injecting a lineage
object. boot_stack() previously never set systems.function_lineage at
all, so getattr(self.systems, "function_lineage", None) always saw
None in production even though the bridge itself was fully functional
when supplied a lineage object directly.

This also incidentally exercises a second, closely-related repair:
AuroraRuntime's own CodeEvolutionChamber import previously named a
module ("aurora_code_evolution_stack") that does not exist anywhere in
this repository, so CodeEvolutionChamber (and everything derived from
it, including runtime.code_chamber) was always None after a normal
boot -- the entire runtime code-mutation transaction path was
unreachable in production regardless of the lineage-wiring gap. Both
are required for stage_code_mutation() to run at all.

Booting real Aurora is expensive -- this file intentionally contains a
single focused test, not a matrix.
"""
import os
import shutil
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_runtime import AuroraRuntime


def test_boot_populates_source_current_lineage_and_bridge_executes_unassisted():
    scratch = tempfile.mkdtemp(prefix="aurora_rw648_boot_")
    state_dir = os.path.join(scratch, "aurora_state")
    output_dir = os.path.join(scratch, "aurora_runtime_output")
    try:
        runtime = AuroraRuntime(state_dir=state_dir, output_dir=output_dir)
        runtime.boot(verbose=False)

        # 1. A real, non-null UniversalFunctionLineage is on the stack.
        lineage = runtime.systems.function_lineage
        assert lineage is not None
        assert hasattr(lineage, "verify")

        # 2. It is source-current (Build 646's freshness repair), not a
        # stale or partially-built object silently treated as authoritative.
        verification = lineage.verify()
        assert verification["source_current"] is True
        assert verification["internally_coherent"] is True

        # 3. runtime.code_chamber is real (the import-path repair) --
        # without this, stage_code_mutation() cannot run at all.
        assert runtime.code_chamber is not None

        # 4. stage_code_mutation() -- called with NO explicit parent_ids
        # and no manually-injected lineage object -- must exercise the
        # ancestry bridge on its own, via the connection this phase
        # repairs. Target a real, small, harmless-to-restage file.
        target = os.path.join(REPO_ROOT, "aurora_internal", "aurora_code_autoevolver.py")
        staged = runtime.stage_code_mutation(
            name="build648_connection_probe",
            operator_key="__nonexistent_probe_operator__",
            target_files=[target],
        )
        pending_trace = runtime._code_pending[staged["mutation_id"]]["trace"]
        assert pending_trace.meta.get("acquired_operational_ancestry") is not None
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
