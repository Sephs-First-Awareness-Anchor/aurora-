# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA BUILD 646 GENEALOGY-TO-EVOLUTION CLOSURE DIRECTIVE, Phase 0 /
Phase 16 Category A: a universal genealogy manifest is valid only when it
corresponds to the executable source tree it claims to represent.
Internal graph consistency alone is insufficient -- a stale-but-coherent
manifest must not verify as valid.

Uses a small synthetic repo fixture rather than Aurora's own ~9,100-
function tree, so this suite stays fast (a real-repo rebuild takes
~40-50s; a synthetic 2-3-file repo takes well under a second).
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


def _small_repo(tmp: str) -> None:
    _write(os.path.join(tmp, "alpha.py"), """
        def root_x():
            return 1

        def uses_root_x():
            return root_x() + 1
    """)
    _write(os.path.join(tmp, "beta.py"), """
        def root_boundary():
            return "b"
    """)


class TestCurrentManifestVerifiesSuccessfully:
    def test_freshly_built_manifest_is_valid_and_current(self):
        with tempfile.TemporaryDirectory() as tmp:
            _small_repo(tmp)
            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=True)
            report = lineage.verify()
            assert report["internally_coherent"] is True
            assert report["source_current"] is True
            assert report["valid"] is True
            assert report["freshness"]["missing_from_manifest_count"] == 0
            assert report["freshness"]["obsolete_in_manifest_count"] == 0


class TestAddingAFunctionMakesTheManifestStale:
    def test_new_function_after_persist_is_detected_as_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            _small_repo(tmp)
            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=True)
            assert lineage.verify()["source_current"] is True

            # Add a new function to the already-scanned source tree without
            # telling this lineage instance -- simulates a code change that
            # happened after the manifest was generated.
            with open(os.path.join(tmp, "alpha.py"), "a", encoding="utf-8") as f:
                f.write("\n\ndef newly_added_function():\n    return 42\n")

            # Reload the SAME persisted manifest (fresh instance, as a
            # restarted process would) -- it must now detect staleness.
            reloaded = UniversalFunctionLineage(repo_root=tmp, auto_build=False, persist=False)
            report = reloaded.verify()
            assert report["source_current"] is False
            assert report["valid"] is False
            assert report["freshness"]["missing_from_manifest_count"] >= 1
            assert any("newly_added_function" in fid for fid in report["freshness"]["missing_from_manifest"])


class TestRemovingAFunctionMakesTheManifestStale:
    def test_removed_function_is_detected_as_obsolete(self):
        with tempfile.TemporaryDirectory() as tmp:
            _small_repo(tmp)
            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=True)
            assert lineage.verify()["source_current"] is True

            _write(os.path.join(tmp, "alpha.py"), """
                def root_x():
                    return 1
            """)  # uses_root_x() removed

            reloaded = UniversalFunctionLineage(repo_root=tmp, auto_build=False, persist=False)
            report = reloaded.verify()
            assert report["source_current"] is False
            assert report["freshness"]["obsolete_in_manifest_count"] >= 1
            assert any("uses_root_x" in fid for fid in report["freshness"]["obsolete_in_manifest"])


class TestChangedStructureMakesTheManifestStale:
    def test_changed_call_relationship_flips_source_manifest_hash(self):
        """A structurally relevant edit (changing what a function calls,
        without renaming it) changes the owning file's digest and
        therefore the aggregate source_manifest_hash -- detectable even
        though the function count itself doesn't change."""
        with tempfile.TemporaryDirectory() as tmp:
            _small_repo(tmp)
            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=True)
            before_hash = lineage.status()["source_manifest_hash"]

            _write(os.path.join(tmp, "alpha.py"), """
                def root_x():
                    return 1

                def uses_root_x():
                    return root_x() * 2
            """)  # same function names, different body/ancestry-relevant content

            reloaded = UniversalFunctionLineage(repo_root=tmp, auto_build=False, persist=False)
            report = reloaded.verify()
            assert report["freshness"]["current_source_manifest_hash"] != before_hash
            assert report["freshness"]["changed_file_count"] >= 1
            assert report["source_current"] is False


class TestVerifyOnlyRejectsStaleSourceCorrespondence:
    def test_verify_only_semantics_reject_stale_manifest(self):
        """Mirrors scripts/compile_universal_function_lineage.py's
        --verify-only path: auto_build=False (load only, no rebuild),
        then verify()."""
        with tempfile.TemporaryDirectory() as tmp:
            _small_repo(tmp)
            UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=True)

            with open(os.path.join(tmp, "beta.py"), "a", encoding="utf-8") as f:
                f.write("\n\ndef another_new_one():\n    return 7\n")

            verify_only = UniversalFunctionLineage(repo_root=tmp, auto_build=False, persist=False)
            result = {"status": verify_only.status(), "verification": verify_only.verify()}
            exit_code = 0 if result["verification"].get("valid") else 1
            assert exit_code == 1
            assert result["verification"]["internally_coherent"] is True
            assert result["verification"]["source_current"] is False


class TestBootDoesNotExposeStaleGenealogyAsAuthoritative:
    def test_auto_build_true_rebuilds_when_persisted_manifest_is_stale(self):
        """This is the exact boot-authority scenario (Requirement 0.4):
        a persisted-but-stale manifest must not be silently treated as
        current just because it loaded without error."""
        with tempfile.TemporaryDirectory() as tmp:
            _small_repo(tmp)
            UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=True)

            with open(os.path.join(tmp, "alpha.py"), "a", encoding="utf-8") as f:
                f.write("\n\ndef boot_time_addition():\n    return 99\n")

            # auto_build=True is exactly what aurora.py's boot_aurora() uses.
            booted = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=True)
            report = booted.verify()
            assert report["valid"] is True
            assert report["source_current"] is True
            assert any("boot_time_addition" in fid for fid in booted.all_functions())

    def test_auto_build_false_never_rebuilds_even_when_stale(self):
        """auto_build=False callers (e.g. --verify-only, or an inspection
        tool that must not silently mutate the persisted manifest) must
        still see the stale, unrebuilt state -- confirms the freshness fix
        did not remove the ability to inspect staleness without repairing it."""
        with tempfile.TemporaryDirectory() as tmp:
            _small_repo(tmp)
            UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=True)
            with open(os.path.join(tmp, "alpha.py"), "a", encoding="utf-8") as f:
                f.write("\n\ndef should_not_trigger_rebuild():\n    return 1\n")

            inspected = UniversalFunctionLineage(repo_root=tmp, auto_build=False, persist=False)
            assert "should_not_trigger_rebuild" not in str(inspected.all_functions().keys())
            assert inspected.verify()["source_current"] is False


class TestRebuildReturnsCompleteValidCoverage:
    def test_rebuild_after_staleness_yields_full_coverage_and_zero_orphans(self):
        with tempfile.TemporaryDirectory() as tmp:
            _small_repo(tmp)
            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=True)
            with open(os.path.join(tmp, "beta.py"), "a", encoding="utf-8") as f:
                f.write("\n\ndef fresh_addition():\n    return 3\n")

            status = lineage.rebuild()
            report = lineage.verify()
            assert report["valid"] is True
            assert report["coverage_rate"] == 1.0
            assert report["orphan_count"] == 0
            assert status["function_count"] == report["function_count"]
