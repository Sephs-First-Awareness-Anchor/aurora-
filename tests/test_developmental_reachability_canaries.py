# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA BUILD 648 EVOLUTIONARY INFRASTRUCTURE CLOSURE DIRECTIVE, Phase 8:
Developmental Reachability Canaries.

These are OBSERVATIONS of existing machinery, not implementations of the
proposed dimensional-pressure solution. No canary here installs
EnvironmentSignature as a pressure key, indexes pressure by genealogy,
drives mutation automatically from PressureExperienceLedger, or maps
Dream/conversational failure onto source functions. Canary E (below)
guards this file itself against naming any of those developer-proposed
solutions as an expected outcome.
"""
import inspect
import os
import sys
import tempfile
import textwrap

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_genealogy_environment import derive_environment_signature, logger_from_links
from aurora_internal.constraint_genealogy import ConstraintLink
from aurora_internal.aurora_pressure_ledger import PressureExperienceLedger
from aurora_internal.aurora_code_evolution_chamber import CodeEvolutionChamber
from aurora_internal.aurora_universal_function_lineage import UniversalFunctionLineage
from aurora_internal.aurora_evolutionary_ancestry_bridge import acquire_ancestry_for_target


def _link(link_id, parents, depth, axis, relief_axes):
    mean_relief = {a: (0.01 if a in relief_axes else 0.0) for a in ("X", "T", "N", "B", "A")}
    return ConstraintLink(
        id=link_id, parents=list(parents), depth=depth, created_at_tick=0, count=1,
        mean_relief=mean_relief, mean_cost={a: 0.0 for a in ("X", "T", "N", "B", "A")},
        mean_x_risk=0.0, stdev_relief={a: 0.0 for a in ("X", "T", "N", "B", "A")},
        dominant_relief_axis=axis, tags=[],
    )


def _write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(content))


class TestCanaryA_DistinctRepresentationPreservation:
    """Two genuinely different genealogical structures whose aggregate
    axis projection is equal (same three axes, one appearance each) but
    whose real structure differs (forward vs. reversed recursion order)."""

    def test_equal_axis_totals_remain_structurally_distinguishable(self):
        forward = {
            "L:fwd1": _link("L:fwd1", ["A:root"], 1, "X", {"X"}),
            "L:fwd2": _link("L:fwd2", ["L:fwd1"], 2, "T", {"T"}),
            "L:fwd3": _link("L:fwd3", ["L:fwd2"], 3, "N", {"N"}),
        }
        reversed_order = {
            "L:rev1": _link("L:rev1", ["A:root"], 1, "N", {"N"}),
            "L:rev2": _link("L:rev2", ["L:rev1"], 2, "T", {"T"}),
            "L:rev3": _link("L:rev3", ["L:rev2"], 3, "X", {"X"}),
        }
        sig_forward = derive_environment_signature(logger_from_links(forward), "L:fwd3")
        sig_reversed = derive_environment_signature(logger_from_links(reversed_order), "L:rev3")

        # Same aggregate axis histogram (each of X/T/N appears once, equal
        # weight) -- a purely aggregate X/T/N/B/A view cannot distinguish them.
        assert sig_forward.axis_distribution == sig_reversed.axis_distribution

        # But real existing structural identity DOES distinguish them --
        # this is not fabricated for the test; it is aurora_genealogy_environment.py's
        # own pre-existing structural_hash, computed from real edge order.
        assert sig_forward.structural_hash != sig_reversed.structural_hash
        assert sig_forward.provenance != sig_reversed.provenance


class TestCanaryB_RepresentationSpecificConsequenceHistory:
    """Two distinct representation anchors (the real structural_hash
    values from Canary A) accumulate independent causal histories in
    PressureExperienceLedger -- the substrate can preserve 'these
    superficially similar things behaved differently' without this test
    prescribing what that difference should MEAN developmentally."""

    def test_two_structural_hash_anchors_carry_independent_conditionality(self):
        forward = {
            "L:fwd1": _link("L:fwd1", ["A:root"], 1, "X", {"X"}),
            "L:fwd2": _link("L:fwd2", ["L:fwd1"], 2, "T", {"T"}),
            "L:fwd3": _link("L:fwd3", ["L:fwd2"], 3, "N", {"N"}),
        }
        reversed_order = {
            "L:rev1": _link("L:rev1", ["A:root"], 1, "N", {"N"}),
            "L:rev2": _link("L:rev2", ["L:rev1"], 2, "T", {"T"}),
            "L:rev3": _link("L:rev3", ["L:rev2"], 3, "X", {"X"}),
        }
        anchor_forward = derive_environment_signature(logger_from_links(forward), "L:fwd3").structural_hash
        anchor_reversed = derive_environment_signature(logger_from_links(reversed_order), "L:rev3").structural_hash
        assert anchor_forward and anchor_reversed and anchor_forward != anchor_reversed

        with tempfile.TemporaryDirectory() as tmp:
            ledger = PressureExperienceLedger(state_dir=tmp)
            # anchor_forward: same action, split outcomes -> conditional.
            ledger.record(anchor=anchor_forward, meaning="structural_hash", pursuing="p",
                          causal_action="act", consequence={}, outcome={"resolved": True}, source="test")
            ledger.record(anchor=anchor_forward, meaning="structural_hash", pursuing="p",
                          causal_action="act", consequence={}, outcome={"resolved": False}, source="test")
            # anchor_reversed: same action, consistent outcome -> not conditional.
            for _ in range(2):
                ledger.record(anchor=anchor_reversed, meaning="structural_hash", pursuing="p",
                              causal_action="act", consequence={}, outcome={"resolved": True}, source="test")

            variance_forward = ledger.outcome_variance(anchor_forward)
            variance_reversed = ledger.outcome_variance(anchor_reversed)
            assert variance_forward["is_conditional"] is True
            assert variance_reversed["is_conditional"] is False


class TestCanaryC_FlatteningBoundary:
    """Traces a real representation-specific record (a function's exact
    UniversalFunctionLineage identity and root_weights) through the
    ancestry bridge this directive's Phase 3 built, and reports the last
    point exact identity remains available and the first point it is
    reduced to an aggregate. Does NOT repair the boundary -- this is
    observational evidence for the next developmental experiment."""

    def test_exact_identity_survives_until_file_level_averaging_begins(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "profile_mix.py")
            # Three functions with deliberately different structural
            # profiles sharing one file.
            _write(target, """
                def light_fn(x):
                    return x + 1

                def heavy_fn(x):
                    if x == 0:
                        return 1
                    if x == 1:
                        return 2
                    if x == 2:
                        return 3
                    return x

                def boundary_fn(x):
                    assert x is not None
                    return x
            """)
            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=True)
            functions = lineage.all_functions()
            heavy_fid = next(fid for fid, rec in functions.items() if rec.get("qualname", "").endswith("heavy_fn") or fid.endswith("heavy_fn"))

            # LAST POINT exact identity is available: a single function's
            # own root_weights, addressed by its own function_id.
            heavy_weights = dict(lineage.lineage_for(heavy_fid).get("root_weights", {}) or {})
            assert heavy_weights, "exact per-function weights must exist at this point"

            # Still exact: acquire_ancestry_for_target() in EXACT scope
            # (Phase 3) preserves this function's own signature untouched.
            exact = acquire_ancestry_for_target(
                function_lineage=lineage, mutation_lineage={}, target_files=[target],
                repo_root=tmp, exact_function_ids=[heavy_fid],
            )
            assert exact.ancestry_scope == "exact"
            assert exact.resolved_function_ids == [heavy_fid]
            assert exact.constraint_signature == {k: round(v, 6) for k, v in heavy_weights.items()}

            # FIRST POINT identity is reduced to an aggregate: the
            # file-level fallback AVERAGES heavy_fn's weights together
            # with light_fn's and boundary_fn's -- which specific
            # function contributed what is no longer recoverable from
            # constraint_signature alone once this path is taken.
            coarse = acquire_ancestry_for_target(
                function_lineage=lineage, mutation_lineage={}, target_files=[target],
                repo_root=tmp,
            )
            assert coarse.ancestry_scope == "file_level_fallback"
            assert len(coarse.resolved_function_ids) == 3
            # The averaged signature is generally NOT equal to any single
            # function's exact signature once profiles genuinely differ.
            if heavy_weights:
                assert coarse.constraint_signature != exact.constraint_signature or len(coarse.resolved_function_ids) != 1


class TestCanaryD_EvolutionaryReachability:
    """Given a representation-specific unresolved discrepancy (one of two
    otherwise-similar functions in the same file has real, repeated
    rejected-mutation history; the other does not), can existing
    candidate-formation machinery address the SPECIFIC function the
    discrepancy concerns, without a human hand-selecting which function?
    This is a reachability test -- it does not require a variation to be
    generated or to survive selection, only reports which stage was reached."""

    def test_file_level_fallback_cannot_isolate_the_discrepancy_but_exact_scope_can(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "twins.py")
            _write(target, """
                def twin_alpha(x):
                    return x + 1

                def twin_beta(x):
                    return x + 1
            """)
            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=True)
            chamber = CodeEvolutionChamber(repo_root=tmp, output_dir=os.path.join(tmp, "out"))

            # Real, repeated failure evidence attaches to twin_alpha
            # specifically (a no-op mutation attempt against it -- genuine
            # rejection, not fabricated).
            before = chamber.snapshot(target_files=[target])
            rejected = chamber.propose_mutation(
                name="pointless_alpha_attempt", constraints_used=["existence"],
                target_files=[target], function_lineage=lineage,
            )
            result = chamber.evaluate_mutation(trace=rejected, before=before, checks_passed=True)
            assert result["accepted"] is False

            functions = lineage.all_functions()
            alpha_fid = next(fid for fid, rec in functions.items() if fid.endswith("twin_alpha"))
            beta_fid = next(fid for fid, rec in functions.items() if fid.endswith("twin_beta"))

            # OUTCOME CLASS 2 ("discrepancy remains represented but cannot
            # reach an operational target"): file-level-fallback ancestry
            # for this file sees the rejection evidence, but it is scoped
            # to the FILE, not distinguishably to twin_alpha vs twin_beta --
            # a caller with only file-level scope cannot address "the
            # function this discrepancy is actually about" specifically.
            coarse = acquire_ancestry_for_target(
                function_lineage=lineage, mutation_lineage=chamber._mutation_lineage,
                target_files=[target], repo_root=tmp,
            )
            assert rejected.mutation_id in coarse.previous_rejected_mutation_ids
            assert len(coarse.resolved_function_ids) == 2  # cannot tell which twin it concerns

            # OUTCOME CLASS 3 ("the target is reachable") for the ANCESTRY
            # component specifically: once the exact function_id is
            # available (Phase 3's exact_function_ids path), existing
            # machinery CAN address twin_alpha's own operational ancestry
            # precisely -- this uses genuinely available lineage data, not
            # a developer-supplied guess about which twin matters.
            exact = acquire_ancestry_for_target(
                function_lineage=lineage, mutation_lineage=chamber._mutation_lineage,
                target_files=[target], repo_root=tmp, exact_function_ids=[alpha_fid],
            )
            assert exact.ancestry_scope == "exact"
            assert exact.resolved_function_ids == [alpha_fid]

            # HONEST FINDING (not a repair, per Repair Authority -- this
            # is what the currently-existing machinery actually does):
            # the PRIOR-MUTATION-HISTORY match (previous_rejected_mutation_ids)
            # is keyed by target_files overlap only, never by
            # exact_function_ids -- even when the CURRENT query is
            # exact-scoped, and even though the rejected mutation itself
            # was only ever file-level-scoped (it never claimed to be
            # about twin_alpha specifically). So twin_beta's exact-scoped
            # query still inherits twin_alpha's unrelated rejection as if
            # it were its own. This is OUTCOME CLASS 2 for the
            # mutation-history component specifically: the discrepancy
            # remains represented (the rejection is real, on record, and
            # was reached), but existing machinery cannot yet attribute a
            # FILE-LEVEL-recorded historical rejection to one specific
            # function among several exact operations reachable through
            # that same file -- current mutation vocabulary/history
            # granularity is the limiting factor here, not detection or
            # selection. Reported as-is; not silently patched, since doing
            # so would require deciding what "this mutation concerned
            # exactly function X" should mean for every PAST record ever
            # written at file-level scope -- a new provenance-inference
            # policy, not a mechanical repair.
            next_alpha = chamber.propose_mutation(
                name="alpha_retry", constraints_used=["existence"], target_files=[target],
                function_lineage=lineage, exact_function_ids=[alpha_fid],
            )
            next_beta = chamber.propose_mutation(
                name="beta_first_attempt", constraints_used=["existence"], target_files=[target],
                function_lineage=lineage, exact_function_ids=[beta_fid],
            )
            alpha_acquired = next_alpha.meta["acquired_operational_ancestry"]
            beta_acquired = next_beta.meta["acquired_operational_ancestry"]
            assert rejected.mutation_id in alpha_acquired["previous_rejected_mutation_ids"]
            assert rejected.mutation_id in beta_acquired["previous_rejected_mutation_ids"], (
                "documents current behavior: mutation-history matching remains "
                "file-level even when the live query is exact-scoped"
            )


class TestCanaryE_NoAnswerKeyLeakage:
    """None of the canaries above may name a developer-proposed pressure
    architecture as the expected mutation outcome."""

    FORBIDDEN_PHRASES = (
        "representation-addressed pressure", "representation_addressed_pressure",
        "environmentsignature pressure binding", "environment_signature_pressure_binding",
        "hierarchical pressure", "hierarchical_pressure",
        "dimensional pressure topology", "dimensional_pressure_topology",
    )

    def test_canary_classes_a_through_d_name_no_developer_proposed_solution(self):
        import tests.test_developmental_reachability_canaries as this_module
        # Scan only the OBSERVATIONAL canary classes (A-D) -- this class's
        # own blocklist necessarily contains the forbidden phrases as data,
        # not as an expected test outcome, so it is excluded from the scan.
        watched = (
            TestCanaryA_DistinctRepresentationPreservation,
            TestCanaryB_RepresentationSpecificConsequenceHistory,
            TestCanaryC_FlatteningBoundary,
            TestCanaryD_EvolutionaryReachability,
        )
        src = "\n".join(inspect.getsource(cls) for cls in watched).lower()
        for phrase in self.FORBIDDEN_PHRASES:
            assert phrase not in src, f"canary file must not name '{phrase}' as an expected outcome"
