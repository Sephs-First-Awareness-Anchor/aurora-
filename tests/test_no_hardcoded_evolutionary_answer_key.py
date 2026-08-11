# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA BUILD 646 GENEALOGY-TO-EVOLUTION CLOSURE DIRECTIVE, Non-Goals:
this pass must not introduce a hardcoded "good mutation" template, a
human-authored universal fitness answer key, an arbitrary trait
ontology, or a simplistic if-failure-then-mutate rule.
"""
import inspect
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

FORBIDDEN_MARKERS = (
    "trait_smarter", "trait_better", "trait_correct", "is_good_mutation",
    "correct_architecture", "universal_fitness", "fitness_answer_key",
    "hardcoded_trait", "trait_ontology", "if_failure_then_mutate",
)


class TestNoHardcodedAnswerKeyInNewAncestryBridge:
    def test_ancestry_bridge_module_has_no_forbidden_markers(self):
        import aurora_internal.aurora_evolutionary_ancestry_bridge as bridge
        src = inspect.getsource(bridge)
        lowered = src.lower().replace(" ", "")
        for marker in FORBIDDEN_MARKERS:
            assert marker.replace(" ", "") not in lowered

    def test_acquired_ancestry_fields_are_evidence_shaped_not_semantic_labels(self):
        """Every field on AcquiredAncestry must be either a raw identifier
        list, a numeric weight, or a status enum drawn from real evidence
        -- never a boolean 'is this a good change' flag."""
        import aurora_internal.aurora_evolutionary_ancestry_bridge as bridge
        import dataclasses
        fields = {f.name for f in dataclasses.fields(bridge.AcquiredAncestry)}
        forbidden_field_names = {"is_good", "is_correct", "is_smart", "quality_label", "fitness_grade"}
        assert fields.isdisjoint(forbidden_field_names)


class TestNoSimplisticFailureMutateRule:
    def test_propose_mutation_never_directly_triggers_from_a_bare_failure_check(self):
        """propose_mutation() must remain a pure request/response query --
        it must not itself contain an `if failure:` -style trigger that
        would hardcode a mutation pedagogy into the chamber."""
        import aurora_internal.aurora_code_evolution_chamber as chamber_mod
        src = inspect.getsource(chamber_mod.CodeEvolutionChamber.propose_mutation)
        # The bridge only ACQUIRES evidence -- it must never itself decide
        # to mutate based on a bare boolean failure flag.
        assert "if failure" not in src.lower().replace(" ", "")
        assert "if_failure_then_mutate" not in src.lower().replace(" ", "")


class TestNoNewFitnessOpaqueMagicNumber:
    def test_acceptance_gate_remains_the_pre_existing_decomposable_formula(self):
        """observe_mutation()'s accept/reject formula must remain
        unchanged by this pass -- still decomposable into is_relief/
        admissible_x/net_benefit/checks_passed, never collapsed into an
        opaque single score this pass introduces."""
        import aurora_internal.aurora_code_evolution_chamber as chamber_mod
        src = inspect.getsource(chamber_mod.CodeEvolutionChamber.observe_mutation)
        assert "accepted = bool(checks_passed and admissible_x and is_relief and net_benefit" in src
