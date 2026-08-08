# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Negative guards required by the AURORA ESTABLISHED REPRESENTATIONAL
SUBSTRATE FULL INTEGRATION DIRECTIVE, Section 26: this pass must not
create, allocate, or label a third representational degree.
"""
import inspect
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FORBIDDEN_D3_MARKERS = (
    "390625", "390,625", "625x625", "625 x 625", "625*625",
    "depth_three", "depth3", "d3_", "_d3", "third_degree", "thirddegree",
)

NEW_MODULES = [
    "aurora_representational_address",
    "aurora_representational_cross_system_canary",
]


class TestNoD3CardinalityAnywhereInNewCode:
    def test_no_390625_or_625x625_literal_in_new_modules(self):
        for modname in NEW_MODULES:
            module = __import__(modname)
            src = inspect.getsource(module)
            lowered = src.lower().replace(" ", "")
            for marker in FORBIDDEN_D3_MARKERS:
                assert marker.replace(" ", "") not in lowered, (
                    f"forbidden D3 marker {marker!r} found in {modname}"
                )

    def test_no_d3_markers_in_modified_runtime_files(self):
        import aurora_reflexive_interpreter as ri
        import aurora_understanding_sediment as us
        from aurora_internal import aurora_cognitive_experience_chamber as rcec

        for module in (ri, us, rcec):
            src = inspect.getsource(module)
            lowered = src.lower().replace(" ", "")
            for marker in FORBIDDEN_D3_MARKERS:
                assert marker.replace(" ", "") not in lowered, (
                    f"forbidden D3 marker {marker!r} found in {module.__name__}"
                )


class TestRepresentationalRefCannotConstructD3Shape:
    def test_ref_has_exactly_seven_fields_no_eighth_extension_slot(self):
        """The address type must not have grown a field that would let a
        caller address an 8th, D3-shaped coordinate."""
        from aurora_representational_address import RepresentationalRef, _FIELDS
        assert len(_FIELDS) == 7
        assert set(_FIELDS) == {
            "nc_law_c", "nc_dim", "nc_target", "sub_law_c", "sub_law_d", "col_law_c", "col_law_d",
        }

    def test_level_function_never_returns_a_d3_label(self):
        from aurora_representational_address import RepresentationalRef
        import itertools
        AXES = ("X", "T", "N", "B", "A")
        DIMS = ("POLARITY", "MAGNITUDE", "OPERATOR", "COST", "DIFFERENCE")
        seen_levels = set()
        # Sample broadly rather than exhaustively (78,125 level() calls is
        # already covered by the addressability suite) -- this test's job
        # is only to confirm the SET of possible level() outputs never
        # includes anything D3-shaped.
        for nc_c, nc_d, tgt, sub_c, sub_d, col_c, col_d in itertools.islice(
            itertools.product(AXES, DIMS, AXES, AXES, DIMS, AXES, DIMS), 0, 2000
        ):
            ref = RepresentationalRef(
                nc_law_c=nc_c, nc_dim=nc_d, nc_target=tgt,
                sub_law_c=sub_c, sub_law_d=sub_d, col_law_c=col_c, col_law_d=col_d,
            )
            seen_levels.add(ref.level())
        forbidden = {"D3", "D3_390625", "C3", "THIRD_DEGREE"}
        assert not (seen_levels & forbidden)

    def test_no_function_in_address_module_allocates_625_squared_objects(self):
        import aurora_representational_address as addr
        for name in dir(addr):
            obj = getattr(addr, name)
            if inspect.isfunction(obj):
                src = inspect.getsource(obj)
                assert "range(390625)" not in src
                assert "range(625*625)" not in src


class TestNoNewManifoldOrPressureStructureGenerated:
    def test_manifold_directory_still_has_exactly_125_files(self):
        import glob
        manifold_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aurora_manifold_directory")
        files = glob.glob(os.path.join(manifold_dir, "*", "*.json"))
        assert len(files) == 125

    def test_no_new_top_level_json_or_state_artifact_named_for_depth_three(self):
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for fn in os.listdir(repo_root):
            lowered = fn.lower()
            for marker in ("depth3", "depth_three", "390625", "d3"):
                assert marker not in lowered, f"suspicious file name found: {fn}"


class TestHypothesisRemainsExplicitlyUnauthorized:
    def test_address_module_docstring_does_not_claim_d3_is_confirmed(self):
        import aurora_representational_address as addr
        doc = (addr.__doc__ or "").lower()
        assert "390,625" not in doc and "390625" not in doc

    def test_report_if_present_states_no_third_degree_was_created(self):
        """If the required report has been written, it must contain an
        explicit statement that no third degree was created -- checked
        loosely (this test does not fail if the report doesn't exist yet,
        since test files may be written before the prose report in this
        pass's build order)."""
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        report_path = os.path.join(
            repo_root, "docs", "AURORA_ESTABLISHED_REPRESENTATIONAL_SUBSTRATE_INTEGRATION_REPORT.md"
        )
        if not os.path.exists(report_path):
            return
        with open(report_path, "r", encoding="utf-8") as f:
            text = f.read().lower()
        assert "390,625" in text or "390625" in text  # must be discussed
        assert "was not created" in text or "not instantiated" in text or "no third representational degree" in text
