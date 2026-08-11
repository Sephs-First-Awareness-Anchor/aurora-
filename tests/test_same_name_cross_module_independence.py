# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA BUILD 648 EVOLUTIONARY INFRASTRUCTURE CLOSURE DIRECTIVE, Phase 5:
same-named functions in different modules must remain independently
addressable and independently selected -- an accepted mutation to one
must never automatically mutate the other merely because the names
match. UniversalFunctionLineage already keys functions by
module-qualified identity (never bare name), so this is regression
protection against that guarantee being silently broken, not new
machinery. Where real call/inheritance genealogy DOES connect two
same-named functions across modules, that relationship must remain
visible as ordinary evidence -- never as a trigger for automatic
propagation, and each context keeps its own independent
consequence-grounded selection.
"""
import os
import sys
import tempfile
import textwrap

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_internal.aurora_code_evolution_chamber import CodeEvolutionChamber
from aurora_internal.aurora_universal_function_lineage import UniversalFunctionLineage


def _write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(content))


class TestSameNameDifferentModulesRemainSeparateIdentities:
    def test_two_modules_each_define_process_as_distinct_function_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(os.path.join(tmp, "moda.py"), "def process(x):\n    return x + 1\n")
            _write(os.path.join(tmp, "modb.py"), "def process(x):\n    return x - 1\n")
            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=True)

            process_fids = [fid for fid in lineage.all_functions() if fid.endswith(".process") or fid.endswith(":process")]
            # At minimum, two DISTINCT identities exist for the same bare name.
            functions = lineage.all_functions()
            moda_fid = next(fid for fid, rec in functions.items() if rec.get("file") == "moda.py")
            modb_fid = next(fid for fid, rec in functions.items() if rec.get("file") == "modb.py")
            assert moda_fid != modb_fid
            assert functions[moda_fid]["qualname"] != "" or functions[moda_fid]["module"] != functions[modb_fid]["module"]
            assert functions[moda_fid]["module"] != functions[modb_fid]["module"]


class TestAcceptedMutationDoesNotAutoPropagateAcrossSameNamedModules:
    def test_accepting_a_mutation_in_moda_leaves_modb_byte_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            moda = os.path.join(tmp, "moda.py")
            modb = os.path.join(tmp, "modb.py")
            complex_body = "def process(x):\n" + "".join(
                f"    if x == {i}:\n        x = x + {i}\n" for i in range(30)
            ) + "    return x\n"
            _write(moda, complex_body)
            _write(modb, complex_body)  # deliberately identical content + identical name
            modb_original = complex_body

            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=True)
            chamber = CodeEvolutionChamber(repo_root=tmp, output_dir=os.path.join(tmp, "out"))

            before = chamber.snapshot(target_files=[moda])
            trace = chamber.propose_mutation(
                name="simplify_moda", constraints_used=["energy", "boundary"],
                target_files=[moda], function_lineage=lineage,
            )
            _write(moda, "def process(x):\n    return x\n")
            result = chamber.evaluate_mutation(trace=trace, before=before, checks_passed=True)
            assert result["accepted"] is True

            # modb was never named as a target -- it must be completely
            # untouched, despite having an identically-named, originally
            # identically-bodied function.
            with open(modb, "r", encoding="utf-8") as f:
                assert f.read() == modb_original

            lineage.rebuild()
            modb_fid = next(fid for fid, rec in lineage.all_functions().items() if rec.get("file") == "modb.py")
            moda_fid = next(fid for fid, rec in lineage.all_functions().items() if rec.get("file") == "moda.py")
            # Their post-mutation source hashes must now differ -- moda
            # changed, modb structurally did not.
            assert lineage.lineage_for(moda_fid)["source_hash"] != lineage.lineage_for(modb_fid)["source_hash"]


class TestRealGenealogyConnectionRemainsEvidenceOnlyNeverAutoPropagation:
    def test_cross_module_call_relationship_is_visible_but_does_not_trigger_propagation(self):
        with tempfile.TemporaryDirectory() as tmp:
            # modb.process is REALLY called by moda.wrapper -- a genuine
            # existing genealogy relationship (Requirement per Phase 5:
            # "if existing real call/inheritance genealogy connects them,
            # preserve that relationship as evidence only").
            _write(os.path.join(tmp, "modb.py"), "def process(x):\n    return x + 1\n")
            _write(os.path.join(tmp, "moda.py"), "from modb import process\n\ndef wrapper(x):\n    return process(x) * 2\n")

            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=True)
            chamber = CodeEvolutionChamber(repo_root=tmp, output_dir=os.path.join(tmp, "out"))

            functions = lineage.all_functions()
            modb_process_fid = next(fid for fid, rec in functions.items() if rec.get("file") == "modb.py")
            wrapper_fid = next(fid for fid, rec in functions.items() if rec.get("file") == "moda.py" and "wrapper" in fid)

            # The real call relationship IS visible as evidence.
            wrapper_parents = {p.get("function_id") for p in lineage.parents_of(wrapper_fid)}
            assert modb_process_fid in wrapper_parents

            # But mutating moda.py (the caller) must never write to modb.py.
            modb_path = os.path.join(tmp, "modb.py")
            with open(modb_path, "r", encoding="utf-8") as f:
                modb_original = f.read()
            before = chamber.snapshot(target_files=[os.path.join(tmp, "moda.py")])
            trace = chamber.propose_mutation(
                name="mutate_wrapper", constraints_used=["energy"],
                target_files=[os.path.join(tmp, "moda.py")], function_lineage=lineage,
            )
            _write(os.path.join(tmp, "moda.py"), "from modb import process\n\ndef wrapper(x):\n    return process(x)\n")
            chamber.evaluate_mutation(trace=trace, before=before, checks_passed=True)
            with open(modb_path, "r", encoding="utf-8") as f:
                assert f.read() == modb_original
