# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA DREAM SUBSTRATE... DIRECTIVE, Sections 57-64: no native producer
for sub_law_c/sub_law_d/col_law_c/col_law_d was found among this pass's
own additions (crystal facets, rich fail stream, Dream substrate). No
mapping/lookup table/semantic assignment was invented to force M2,1/M2,2
production. SemanticMatcher and D3 boundaries remain intact.
"""
import inspect
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

INTERMEDIATE_FIELDS = ("sub_law_c", "sub_law_d", "col_law_c", "col_law_d")

NEW_MODULES_THIS_PASS = [
    "aurora_dream_substrate",
    "aurora_dream_new_experience_canary",
]


class TestNoNewProducerIntroducedByThisPass:
    def test_new_modules_never_reference_intermediate_field_names(self):
        for modname in NEW_MODULES_THIS_PASS:
            module = __import__(modname)
            src = inspect.getsource(module)
            for field in INTERMEDIATE_FIELDS:
                assert field not in src, f"{modname} references {field} -- unexpected new producer surface"

    def test_fail_stream_event_shape_has_no_representational_fields(self):
        import aurora_dream_trainer as dt
        fields = {f.name for f in __import__("dataclasses").fields(dt.FailStreamEvent)}
        assert fields.isdisjoint(set(INTERMEDIATE_FIELDS))

    def test_dream_fragment_shape_has_no_representational_fields(self):
        import aurora_dream_substrate as ds
        fields = {f.name for f in __import__("dataclasses").fields(ds.DreamFragment)}
        assert fields.isdisjoint(set(INTERMEDIATE_FIELDS))

    def test_understanding_contract_edits_do_not_reference_intermediate_fields(self):
        from aurora_internal.aurora_understanding_contract import RuntimeUnderstandingContract
        src = inspect.getsource(RuntimeUnderstandingContract._record_pre_outcome_fail_if_applicable)
        for field in INTERMEDIATE_FIELDS:
            assert field not in src


class TestProducerMapIsHonest:
    def test_producer_map_json_is_valid_and_declares_absence(self):
        path = os.path.join(REPO_ROOT, "aurora_intermediate_coordinate_producer_map.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["conclusion"] == "NATIVE_INTERMEDIATE_RESOLUTION_MECHANISM_ABSENT"
        assert data["action_taken"] == "None. No mapping, lookup table, semantic assignment, reward table, or coordinate preference was invented. The absence is reported, not patched, per Section 63."

    def test_every_intermediate_field_is_classified(self):
        path = os.path.join(REPO_ROOT, "aurora_intermediate_coordinate_producer_map.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        classified_fields = {entry["field"] for entry in data["field_classification"]}
        assert classified_fields == {
            "nc_law_c", "nc_dim", "nc_target",
            "sub_law_c", "sub_law_d", "col_law_c", "col_law_d",
        }
        allowed_statuses = {
            "NATIVELY_OBSERVED", "INDEPENDENTLY_SELECTED", "DERIVED", "PINNED",
            "DEFAULTED", "MEMORY_RECOVERED", "PRESSURE_RESOLVED",
            "RELATION_RESOLVED", "UNRESOLVED", "NO_PRODUCER",
        }
        for entry in data["field_classification"]:
            assert entry["status"] in allowed_statuses


class TestSemanticMatcherBoundaryHeldThroughThisAudit:
    def test_semantic_matcher_still_byte_identical_to_baseline(self):
        import subprocess
        import aurora_reflexive_interpreter as ri

        out = subprocess.run(
            ["git", "show", "3433638:aurora_reflexive_interpreter.py"],
            cwd=REPO_ROOT, capture_output=True, text=True, check=True,
        )
        baseline_src = out.stdout
        current_src = inspect.getsource(ri.SemanticMatcher)
        assert current_src in baseline_src


class TestNoD3ArtifactFromThisAudit:
    def test_no_d3_markers_in_producer_map(self):
        """Identifier-shaped markers only -- the report is explicitly
        allowed to discuss, in plain English, that 390,625/625x625 was
        NOT created (same convention as
        tests/test_representational_conservation_negative_guards.py's
        FORBIDDEN_DEPTH3_MARKERS, which excludes the prose phrase for the
        identical reason)."""
        path = os.path.join(REPO_ROOT, "aurora_intermediate_coordinate_producer_map.json")
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        lowered = text.lower().replace(" ", "")
        for marker in ("thirddegree", "depth_three", "depth3", "48828125", "30517578125"):
            assert marker not in lowered
        assert "was created" in text.lower()  # discussed explicitly, in the negative

    def test_manifold_directory_still_has_exactly_125_files(self):
        import glob
        manifold_dir = os.path.join(REPO_ROOT, "aurora_manifold_directory")
        files = glob.glob(os.path.join(manifold_dir, "*", "*.json"))
        assert len(files) == 125
