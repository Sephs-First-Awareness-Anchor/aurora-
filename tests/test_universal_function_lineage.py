from __future__ import annotations

from pathlib import Path

from aurora_internal.aurora_universal_function_lineage import UniversalFunctionLineage
from aurora_internal.lineage_canonical import constraints_for_operation


ROOT = Path(__file__).resolve().parents[1]


def _lineage() -> UniversalFunctionLineage:
    return UniversalFunctionLineage(repo_root=str(ROOT), auto_build=False, persist=False)


def test_manifest_covers_every_scanned_executable_function() -> None:
    lineage = _lineage()
    surfaces, _file_hashes, errors = lineage._scan_surfaces()
    assert not errors
    assert lineage.status()["function_count"] == len(surfaces)
    assert lineage.status()["named_function_count"] == sum(1 for row in surfaces.values() if row.kind != "lambda")
    assert lineage.status()["lambda_count"] == sum(1 for row in surfaces.values() if row.kind == "lambda")


def test_every_function_traces_to_a_foundational_constraint() -> None:
    lineage = _lineage()
    report = lineage.verify()
    assert report["valid"] is True
    assert report["coverage_rate"] == 1.0
    assert report["orphan_count"] == 0
    assert report["missing_parent_count"] == 0
    assert report["bad_root_path_count"] == 0


def test_parentage_is_multi_parent_and_cross_module_not_domain_partitioned() -> None:
    lineage = _lineage()
    status = lineage.status()
    assert status["domain_taxonomy_used_for_parentage"] is False
    assert status["multi_parent_functions"] > 100
    assert status["cross_module_parent_edges"] > 100
    assert status["max_generation"] >= 2


def test_live_response_and_slot_binding_have_real_ancestry() -> None:
    lineage = _lineage()
    live = lineage.lineage_for("aurora._run_live_response_turn")
    bind = lineage.lineage_for(
        "aurora_expression_perception.SentenceComposer._bind_slot_from_frame"
    )
    assert live["lineage_kind"] in {"composite", "co_evolved_composite"}
    assert live["functional_parents"]
    assert live["root_paths"]
    assert bind["functional_parents"]
    assert any("infer_word_role" in parent for parent in bind["functional_parents"])
    assert "B" in bind["traceable_roots"]


def test_canonical_constraint_lookup_uses_universal_index() -> None:
    constraints = constraints_for_operation(
        "aurora_expression_perception.SentenceComposer._bind_slot_from_frame"
    )
    assert "boundary" in constraints
    assert constraints


def test_genealogy_can_attach_and_query_function_lineage() -> None:
    lineage = _lineage()

    class FakeGenealogy:
        def __init__(self) -> None:
            self.bound = None

        def attach_function_lineage(self, value):
            self.bound = value
            return True

    genealogy = FakeGenealogy()
    assert lineage.attach_genealogy(genealogy) is True
    assert genealogy.bound is lineage


def test_recursive_surfaces_are_coevolution_not_cyclic_parentage() -> None:
    lineage = _lineage()
    coevolved = [
        row for row in lineage.all_functions().values()
        if row.get("co_evolved_with")
    ]
    assert coevolved
    for row in coevolved[:100]:
        peers = set(row.get("co_evolved_with", []) or [])
        parents = set(row.get("parents", []) or [])
        assert not peers.intersection(parents)
        assert row.get("root_paths")
