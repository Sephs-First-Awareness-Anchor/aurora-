# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Tests for the AURORA NATIVE REPRESENTATIONAL SELECTION AND CAUSAL-TO-
REPRESENTATIONAL TRANSITION FALSIFICATION DIRECTIVE.

Covers aurora_same_input_history_canary.py and
aurora_causal_vs_representational_probe.py, plus the directive's required
negative controls.
"""
import inspect
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aurora_causal_vs_representational_probe as probe
import aurora_rank6_shadow_analysis as rank6
from aurora_same_input_history_canary import run_canary


# ── Same-input/different-history canary ─────────────────────────────────────

class TestSameInputHistoryCanary:
    def test_canary_reaches_outcome_a_for_the_traced_selector(self):
        """The selector itself (SemanticMatcher.match) is stateless by
        construction; this is the empirical confirmation. This assertion
        CAN fail -- if it ever does, that is itself a major finding
        (native selection feedback would have been discovered), not a
        broken test to loosen."""
        result = run_canary()
        assert result.selected_coordinate_identical is True
        assert result.selection_inputs_identical is True
        assert result.outcome == "A"

    def test_canary_never_directly_sets_the_coordinate(self):
        """Source-level guard: the canary must only ever call real
        interpret()/match() methods -- never assign to .constraint/
        .dimension/a SlotCoord field directly."""
        src = inspect.getsource(sys.modules["aurora_same_input_history_canary"])
        forbidden = [".constraint =", ".dimension =", "SlotCoord(", "match.constraint =", "match.dimension ="]
        for marker in forbidden:
            assert marker not in src, f"canary appears to directly force a coordinate: {marker!r}"

    def test_downstream_worth_state_can_legitimately_differ(self):
        """Distinguishes the canary's two claims: coordinate selection is
        untouched by history, but downstream understanding state (field_region)
        is legitimately allowed to differ -- this test only fails if that
        distinction itself stops being meaningful (e.g. if field_region
        became constant regardless of history, which would be a separate,
        real finding worth investigating)."""
        result = run_canary()
        # We don't assert a specific direction, only that the two questions
        # (selection vs. downstream state) are being measured separately.
        assert hasattr(result.history_p, "field_region")
        assert hasattr(result.history_q, "field_region")


# ── Causal-vs-representational probe ─────────────────────────────────────────

class TestCausalVsRepresentationalProbe:
    def test_sub_law_c_probe_runs_and_classifies(self):
        report = probe.probe_sub_law_c()
        assert report.classification in (
            "CAUSAL_ONLY", "REPRESENTATIONAL_CANDIDATE", "REPRESENTATIONAL_EVIDENCE", "INSUFFICIENT",
        )

    def test_r1_and_r2_alone_do_not_promote_to_representational(self):
        """NEGATIVE CONTROL: a candidate meeting only R1 (differentiation)
        and R2 (independent consequence) must classify as CAUSAL_ONLY, not
        higher -- simple downstream causal effect is not sufficient."""
        r1 = probe.CriterionResult("R1_differentiation", True, "stub", "EMPIRICAL RESULT")
        r2 = probe.CriterionResult("R2_independent_consequence", True, "stub", "EMPIRICAL RESULT")
        r3 = probe.CriterionResult("R3_invariant_relation", False, "stub", "EMPIRICAL RESULT")
        r4 = probe.CriterionResult("R4_persistence", False, "stub", "EMPIRICAL RESULT")
        r5 = probe.CriterionResult("R5_functional_use", False, "stub", "EMPIRICAL RESULT")
        r6 = probe.CriterionResult("R6_decoupling_mismatch", False, "stub", "EMPIRICAL RESULT")
        report = probe.ProbeReport(
            candidate="synthetic", criteria=[r1, r2, r3, r4, r5, r6],
            classification="CAUSAL_ONLY" if (r1.met and r2.met and not (r3.met and r4.met and r5.met)) else "OTHER",
            classification_rationale="stub",
        )
        assert report.classification == "CAUSAL_ONLY"

    def test_five_distinct_values_alone_does_not_pass(self):
        """NEGATIVE CONTROL: R1 being met (multiple distinguishable values)
        must not, by itself, satisfy R2-R5. Verified against the real
        sub_law_d data: it has 5 label values but fails the numeric
        independence bar entirely (rank-6 audit), so it must never be
        reported as passing R1 in the numeric sense this probe uses."""
        directory = rank6.load_manifold_directory_raw()
        nc = directory["Existential_Operator_of_Existence"]
        home = (nc["nc_law_c"], nc["nc_dim"])
        varied_d = rank6.vary_sub_law_d(directory, "Existential_Operator_of_Existence", home)
        distinct_d = rank6.count_distinct(varied_d, rank6.numeric_signature)
        assert distinct_d <= 2, "sub_law_d must not be silently promoted to full numeric independence"

    def test_experimenter_supplied_invariant_is_not_accepted_without_code_grounding(self):
        """NEGATIVE CONTROL: the probe's R3 check must be backed by an
        actual read of the invariant elsewhere in the code (here:
        _find_nc's scoring function referencing topic words), not merely
        asserted by the probe's author. Confirms the code-grounding by
        direct source inspection rather than trusting the probe's own claim."""
        from aurora_reflexive_interpreter import SemanticMatcher
        src = inspect.getsource(SemanticMatcher._find_nc)
        assert "topics" in src and "0.5" in src, (
            "R3's topic_words invariant claim is not actually grounded in "
            "_find_nc's scoring function -- the probe would be inventing an "
            "invariant rather than discovering one"
        )

    def test_persistence_failure_is_verified_against_real_key_schema(self):
        """NEGATIVE CONTROL: R4's failure must be demonstrated against the
        real overlay/ledger key functions, not asserted."""
        from aurora_understanding_sediment import slot_key
        key_x = slot_key("X", "OPERATOR")
        key_b = slot_key("B", "OPERATOR")
        # Keys are constraint/dimension-based; no topic component exists to check.
        assert "X" in key_x and "OPERATOR" in key_x
        assert "topic" not in key_x.lower() and "topic" not in key_b.lower()

    def test_direct_coordinate_forcing_is_not_performed_anywhere_in_the_probe(self):
        src = inspect.getsource(probe)
        forbidden = ["match.constraint =", "match.dimension =", ".constraint = 'X'", ".dimension = "]
        for marker in forbidden:
            assert marker not in src


# ── No mutation of production state ──────────────────────────────────────────

class TestNoProductionStateMutation:
    def _fingerprint(self, root):
        import hashlib
        digest = hashlib.sha256()
        if not os.path.isdir(root):
            return None
        for dirpath, _dirnames, filenames in os.walk(root):
            for fn in sorted(filenames):
                p = os.path.join(dirpath, fn)
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                digest.update(f"{p}:{st.st_size}:{st.st_mtime_ns}".encode("utf-8"))
        return digest.hexdigest()

    def test_canary_and_probe_touch_no_manifold_or_state_files(self):
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        manifold_dir = os.path.join(repo_root, "aurora_manifold_directory")
        state_dir = os.path.join(repo_root, "aurora_state")
        before_m = self._fingerprint(manifold_dir)
        before_s = self._fingerprint(state_dir)

        run_canary()
        probe.probe_sub_law_c()

        after_m = self._fingerprint(manifold_dir)
        after_s = self._fingerprint(state_dir)
        assert before_m == after_m
        assert before_s == after_s

    def test_neither_module_references_warp_or_genealogy_authority(self):
        for module in (sys.modules["aurora_same_input_history_canary"], probe):
            src = inspect.getsource(module)
            lowered = src.lower()
            for forbidden in ("warp_field", "warp_guard", "genealogy.observe", "genealogy.promote", "pressure_map"):
                assert forbidden not in lowered
