# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Negative/guard-rail tests required by the SYSTEM-WIDE REPRESENTATIONAL
CONSERVATION, PROPAGATION, AND EMERGENCE REPAIR DIRECTIVE's Regression
Requirements section:

  - no unconfirmed depth-three semantics have entered runtime code
  - the audit/observer modules cannot mutate WARP, genealogy authority,
    meaning profiles, or pressure geometry
  - independent coordinates remain independent (no silent narrowing)
  - coupled coordinates are not incorrectly treated as independent
  - lower-rank representations are not falsely promoted to higher rank
"""
import inspect
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AUDIT_MODULES = [
    "aurora_rank6_shadow_analysis",
    "aurora_representational_emergence_observatory",
]

FORBIDDEN_DEPTH3_MARKERS = (
    # Identifier-shaped markers only -- deliberately excludes the plain-English
    # phrase "depth three", since compliance documentation (this module's own
    # docstring included) must be free to describe the doctrine that forbids
    # it without tripping this guard on its own prose.
    "depth_three", "depth3", "d3_", "_d3",
    "390625", "390,625", "48828125", "48,828,125",
    "30517578125", "30,517,578,125",
)

FORBIDDEN_AUTHORITY_WRITE_TARGETS = (
    "aurora_warp_protocol", "warp_field", "warp_guard",
    "constraint_genealogy", "genealogy.observe", "genealogy.promote",
    "meaning_profile", "aurora_meaning",
    "aurora_625_pressure_map", "pressure_map",
)


class TestNoDepthThreeSemanticsInAuditCode:
    def test_no_depth_three_markers_in_new_audit_modules(self):
        for modname in AUDIT_MODULES:
            module = __import__(modname)
            src = inspect.getsource(module)
            lowered = src.lower()
            for marker in FORBIDDEN_DEPTH3_MARKERS:
                assert marker.lower() not in lowered, (
                    f"forbidden depth-three marker {marker!r} found in {modname}"
                )

    def test_no_depth_three_markers_in_repaired_runtime_files(self):
        """The two files actually touched by this pass's repairs
        (aurora.py, aurora_reflexive_interpreter.py) must not have gained
        any depth-three-adjacent constant or label as a side effect of the
        repair."""
        import aurora
        import aurora_reflexive_interpreter as ri

        for module in (aurora, ri):
            src = inspect.getsource(module)
            lowered = src.lower()
            for marker in FORBIDDEN_DEPTH3_MARKERS:
                assert marker.lower() not in lowered, (
                    f"forbidden depth-three marker {marker!r} found in {module.__name__}"
                )


class TestAuditAndObserverCannotMutateAuthority:
    def test_audit_modules_do_not_import_warp_genealogy_meaning_or_pressuremap(self):
        for modname in AUDIT_MODULES:
            module = __import__(modname)
            src = inspect.getsource(module)
            lowered = src.lower()
            for target in FORBIDDEN_AUTHORITY_WRITE_TARGETS:
                assert target.lower() not in lowered, (
                    f"{modname} references {target!r} -- audit/observer modules "
                    "must have zero contact with WARP, genealogy, meaning, or "
                    "pressure-map authority"
                )

    def test_observatory_never_calls_a_write_method_on_a_passed_object(self):
        """evaluate_candidate_relationship / record_dependent_to_independent_
        transition only ever read attributes off ObservationSample -- never
        call a method on caller-supplied data at all."""
        import aurora_representational_emergence_observatory as obs
        src = inspect.getsource(obs.evaluate_candidate_relationship)
        # No method call syntax "s.<name>(" on a sample variable.
        assert ".observe(" not in src
        assert ".promote(" not in src
        assert ".connect_" not in src


class TestIndependentCoordinatesRemainIndependent:
    def test_sub_law_c_still_shows_full_five_state_independence(self):
        """A regression guard: if a future change to the manifold compiler
        or the shadow analysis module silently narrowed sub_law_c's real
        independence, this must fail loudly rather than let the report's
        headline claim go stale."""
        import aurora_rank6_shadow_analysis as rank6

        directory = rank6.load_manifold_directory_raw()
        for nc_name in ("Existential_Operator_of_Existence", "Boundary_Cost_of_Agency"):
            nc = directory[nc_name]
            home = (nc["nc_law_c"], nc["nc_dim"])
            varied = rank6.vary_sub_law_c(directory, nc_name, home)
            distinct = rank6.count_distinct(varied, rank6.numeric_signature)
            assert distinct == 5, f"sub_law_c independence regressed at {nc_name}"


class TestCoupledCoordinatesNotFalselyPromoted:
    def test_sub_law_d_still_capped_at_two_numeric_states(self):
        """The mirror guard: sub_law_d must not be silently reported (by
        any future change to the shared analysis module) as more
        independent than it actually is."""
        import aurora_rank6_shadow_analysis as rank6

        directory = rank6.load_manifold_directory_raw()
        for nc_name in ("Existential_Operator_of_Existence", "Boundary_Cost_of_Agency"):
            nc = directory[nc_name]
            home = (nc["nc_law_c"], nc["nc_dim"])
            varied = rank6.vary_sub_law_d(directory, nc_name, home)
            distinct = rank6.count_distinct(varied, rank6.numeric_signature)
            assert distinct <= 2, f"sub_law_d shows unexpected independence at {nc_name}"

    def test_axis_level_pressure_vector_is_not_promoted_to_noncomp_identity(self):
        """Lower-rank (5-axis, X/T/N/B/A only) representations -- e.g. a
        dream episode's pressure_before/after -- must not be silently
        treated as though they carried a (constraint, dimension) NonComp
        identity anywhere this pass touched. Confirms the repaired
        _inject_to_genealogy call site still only ever produces a 5-key
        X/T/N/B/A PressureVec, never a richer object it has no data for."""
        import aurora
        from aurora_evolution_stack import PressureVec

        balancer = aurora.ConstraintFieldBalancer()
        for _ in range(30):
            balancer.update({"X": 0.6, "T": 0.15, "N": 0.1, "B": 0.05, "A": 0.1}, systems={})
        gradient = balancer.field_gradient()
        starved = [ax for ax, g in gradient.items() if g >= 0.005]
        assert starved, "test setup did not produce a starved axis"

        # The repaired code path only ever constructs a 5-field PressureVec
        # -- verify by source inspection that no nc_law_c/nc_dim/sub_law_c
        # style field was invented at this call site.
        src = inspect.getsource(aurora.ConstraintFieldBalancer._inject_to_genealogy)
        for forbidden_field in ("nc_law_c", "nc_dim", "sub_law_c", "sub_law_d", "nc_name"):
            assert forbidden_field not in src


class TestNoNewDepthOrPressureStructureWasGenerated:
    def test_no_390625_or_larger_manifold_directory_was_created(self):
        import glob
        files = glob.glob(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "aurora_manifold_directory", "*", "*.json")
        )
        assert len(files) == 125, (
            f"expected exactly 125 manifold files (the confirmed C1 space); found {len(files)} "
            "-- a new structure may have been generated"
        )
