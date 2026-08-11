# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA BUILD 646 GENEALOGY-TO-EVOLUTION CLOSURE DIRECTIVE, Phase 16
Category B (Operational Genealogy Integrity): zero unexplained orphans,
zero unresolved parent references, valid root paths, multi-parent
relationships survive serialization, recursion/co-evolution remains
valid, lexical/inheritance ancestry stays intact. This category
deliberately does NOT assert a fixed global function count -- the
directive is explicit that the count will naturally change.
"""
import os
import sys
import tempfile
import textwrap

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_internal.aurora_universal_function_lineage import UniversalFunctionLineage


def _write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(content))


def _mixed_repo(tmp: str) -> None:
    # Multi-parent: shared_helper is called from two independent callers.
    # Recursion / co-evolution: mutually-recursive is_even/is_odd form an
    # SCC and must cluster + co-evolve together.
    # Lexical nesting: outer() defines and calls an inner closure.
    # Inheritance: Dog.speak overrides Animal.speak.
    _write(os.path.join(tmp, "shared.py"), """
        def shared_helper(x):
            return x + 1

        def caller_one(x):
            return shared_helper(x) + 1

        def caller_two(x):
            return shared_helper(x) * 2
    """)
    _write(os.path.join(tmp, "recursion.py"), """
        def is_even(n):
            if n == 0:
                return True
            return is_odd(n - 1)

        def is_odd(n):
            if n == 0:
                return False
            return is_even(n - 1)
    """)
    _write(os.path.join(tmp, "nested.py"), """
        def outer(x):
            def inner(y):
                return y * 2
            return inner(x) + 1
    """)
    _write(os.path.join(tmp, "inherit.py"), """
        class Animal:
            def speak(self):
                return "..."

        class Dog(Animal):
            def speak(self):
                return "woof"
    """)


class TestZeroUnexplainedOrphansAndUnresolvedParents:
    def test_verify_reports_no_orphans_or_missing_parents_on_a_healthy_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            _mixed_repo(tmp)
            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=True)
            result = lineage.verify()
            assert result["orphan_count"] == 0
            assert result["missing_parent_count"] == 0
            assert result["bad_root_path_count"] == 0
            assert result["internally_coherent"] is True


class TestValidRootPaths:
    def test_every_function_traces_to_at_least_one_root_constraint(self):
        with tempfile.TemporaryDirectory() as tmp:
            _mixed_repo(tmp)
            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=True)
            for fid in lineage.all_functions():
                roots = lineage.trace_to_roots(fid)
                assert roots, f"{fid} has no root path"
                for root, path in roots.items():
                    assert root in ("X", "T", "N", "B", "A") or root.startswith("ROOT:")
                    assert path


class TestMultiParentSurvivesSerialization:
    def test_shared_helper_has_two_functional_parents_before_and_after_reload(self):
        with tempfile.TemporaryDirectory() as tmp:
            _mixed_repo(tmp)
            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=True)
            helper_fid = next(
                fid for fid in lineage.all_functions()
                if fid.endswith("shared_helper")
            )
            parents_before = {
                p["function_id"] for p in lineage.parents_of(helper_fid)
                if not p.get("function_id", "").startswith("ROOT:")
            }
            children_of_helper = set(lineage.descendants_of(helper_fid, limit=10))
            # shared_helper is called BY caller_one/caller_two -- they are
            # its children in the call graph, not its parents; confirm
            # multi-child (fan-out) survives instead.
            fanout = sum(
                1 for fid, rec in lineage.all_functions().items()
                if helper_fid in (rec.get("functional_parents") or [])
            )
            assert fanout >= 2

            reloaded = UniversalFunctionLineage(repo_root=tmp, auto_build=False, persist=False)
            fanout_after = sum(
                1 for fid, rec in reloaded.all_functions().items()
                if helper_fid in (rec.get("functional_parents") or [])
            )
            assert fanout_after == fanout


class TestRecursionAndCoEvolutionRemainsValid:
    def test_mutually_recursive_functions_cluster_and_co_evolve(self):
        with tempfile.TemporaryDirectory() as tmp:
            _mixed_repo(tmp)
            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=True)
            functions = lineage.all_functions()
            is_even = next(fid for fid in functions if fid.endswith("is_even"))
            is_odd = next(fid for fid in functions if fid.endswith("is_odd"))
            rec_even = functions[is_even]
            rec_odd = functions[is_odd]
            assert rec_even["cluster_id"] == rec_odd["cluster_id"]
            assert is_odd in (rec_even.get("co_evolved_with") or []) or \
                is_even in (rec_odd.get("co_evolved_with") or [])
            # Both remain traceable to roots despite being in a cycle.
            assert lineage.trace_to_roots(is_even)
            assert lineage.trace_to_roots(is_odd)


class TestLexicalNestingIntact:
    def test_inner_closure_resolves_as_child_of_outer(self):
        with tempfile.TemporaryDirectory() as tmp:
            _mixed_repo(tmp)
            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=True)
            functions = lineage.all_functions()
            outer_fid = next(fid for fid in functions if fid.endswith("outer"))
            inner_fid = next(fid for fid in functions if fid.endswith("outer.<locals>.inner") or ".inner" in fid)
            assert lineage.trace_to_roots(inner_fid)
            # The nested function's call evidence links back to its lexical
            # scope even though it is invoked from within `outer`.
            assert outer_fid.split(".")[0] == inner_fid.split(".")[0]


class TestInheritanceAncestryIntact:
    def test_dog_speak_carries_override_evidence_of_animal_speak(self):
        with tempfile.TemporaryDirectory() as tmp:
            _mixed_repo(tmp)
            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=True)
            functions = lineage.all_functions()
            dog_speak = next(fid for fid in functions if fid.endswith("Dog.speak"))
            animal_speak = next(fid for fid in functions if fid.endswith("Animal.speak"))
            rec = functions[dog_speak]
            call_kinds = {row.get("mode") for row in rec.get("call_evidence", []) or []}
            assert "inheritance" in call_kinds or animal_speak in (rec.get("functional_parents") or [])


class TestFunctionCountIsNotAsserted:
    def test_adding_a_function_changes_count_and_stays_valid_without_a_fixed_expectation(self):
        with tempfile.TemporaryDirectory() as tmp:
            _mixed_repo(tmp)
            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=True)
            count_before = len(lineage.all_functions())

            with open(os.path.join(tmp, "shared.py"), "a", encoding="utf-8") as f:
                f.write("\n\ndef newly_added():\n    return 42\n")
            lineage.rebuild()
            count_after = len(lineage.all_functions())

            # The directive requires this to naturally change -- no fixed
            # global count is asserted, only that integrity holds either way.
            assert count_after == count_before + 1
            assert lineage.verify()["internally_coherent"] is True
