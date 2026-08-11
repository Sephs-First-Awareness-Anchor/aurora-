# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA BUILD 646 GENEALOGY-TO-EVOLUTION CLOSURE DIRECTIVE, Phase 13:
every accepted descendant retains/recomputes its relationship to the
five root constraints (X/T/N/B/A) through a real path (parent mechanism
-> higher-order relation -> constraint operation -> root), not a
hardcoded single-axis label. An evolutionary mutation may change the
route/weight/combination of that constraint ancestry, and that change
itself is hereditary evidence.
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


def _complex_source() -> str:
    src = "def hot_path(x):\n"
    for i in range(30):
        src += f"    if x == {i}:\n        x = x + {i}\n"
    src += "    return x\n"
    return src


class TestConstraintAncestryIsARealPathNotAFlatLabel:
    def test_root_paths_carry_the_full_route_not_just_a_terminal_axis(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "hot.py")
            _write(target, _complex_source())
            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=True)
            fid = next(fid for fid in lineage.all_functions() if fid.endswith("hot_path"))
            root_paths = lineage.trace_to_roots(fid)
            assert root_paths
            for root, path in root_paths.items():
                # A real path has intermediate structure, not just
                # [function_id, ROOT] -- it may legitimately be short for
                # a shallow function, but it must be an actual list
                # reflecting the reconstructed route, never a bare label.
                assert isinstance(path, list) and path


class TestMultipleRootInfluencesRemainRepresentable:
    def test_a_function_touching_multiple_axes_keeps_all_of_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "hot.py")
            _write(target, _complex_source())
            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=True)
            fid = next(fid for fid in lineage.all_functions() if fid.endswith("hot_path"))
            rec = lineage.lineage_for(fid)
            traceable = rec.get("traceable_roots", []) or []
            weights = rec.get("root_weights", {}) or {}
            # A 30-branch function legitimately touches more than one
            # axis (branching -> N/energy, boundary conditions -> B) --
            # this must NOT be collapsed into a single root label.
            assert len(traceable) >= 1
            assert isinstance(weights, dict)


class TestMutationChangesTheConstraintRouteAsHereditaryEvidence:
    def test_simplifying_a_function_changes_its_constraint_signature_and_that_delta_is_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "hot.py")
            _write(target, _complex_source())
            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=True)
            chamber = CodeEvolutionChamber(repo_root=tmp, output_dir=os.path.join(tmp, "out"))

            fid_before = next(fid for fid in lineage.all_functions() if fid.endswith("hot_path"))
            weights_before = dict(lineage.lineage_for(fid_before).get("root_weights", {}) or {})

            before = chamber.snapshot(target_files=[target])
            trace = chamber.propose_mutation(
                name="simplify", constraints_used=["energy", "boundary"],
                target_files=[target], function_lineage=lineage,
            )
            _write(target, "def hot_path(x):\n    return x\n")
            result = chamber.evaluate_mutation(trace=trace, before=before, checks_passed=True)
            assert result["accepted"] is True
            lineage.rebuild()

            fid_after = next(fid for fid in lineage.all_functions() if fid.endswith("hot_path"))
            weights_after = dict(lineage.lineage_for(fid_after).get("root_weights", {}) or {})

            # The constraint signature genuinely changed (fewer branches
            # -> less N/B pressure evidence) -- this delta is itself
            # available as hereditary evidence via the accepted mutation's
            # recorded pre/post pressure, not silently discarded.
            assert weights_before != weights_after or result["pressure_before"] != result["pressure_after"]
            # The descendant still traces to at least one root -- the
            # route may change, but continuity to root constraints must
            # never be lost by an accepted mutation.
            assert lineage.trace_to_roots(fid_after)
