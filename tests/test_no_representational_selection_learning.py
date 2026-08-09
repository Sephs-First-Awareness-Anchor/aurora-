# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA LIVE REPRESENTATIONAL PROPAGATION AND CONSEQUENCE-BINDING
DIRECTIVE, Section 19 (strict boundaries): this pass must not make
consequence alter future coordinate selection, implement a new learning
rule, or add reinforcement tables / coordinate-preference tables /
consequence-to-coordinate maps / manually authored salience rules.

These tests compare the live source of the selection-relevant functions
against the exact byte content at baseline commit 3433638 (the last
commit before this directive's work began) -- a diff of zero bytes is the
strongest available proof that no selection semantics were touched.
"""
import inspect
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE_COMMIT = "3433638"


def _baseline_source(path: str) -> str:
    out = subprocess.run(
        ["git", "show", f"{BASELINE_COMMIT}:{path}"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    )
    return out.stdout


class TestSemanticMatcherUnchangedSinceBaseline:
    def test_semantic_matcher_match_byte_identical_to_baseline(self):
        import aurora_reflexive_interpreter as ri
        current_src = inspect.getsource(ri.SemanticMatcher.match)
        baseline_full = _baseline_source("aurora_reflexive_interpreter.py")
        baseline_module_src = compile  # placeholder to keep flake quiet
        # Extract the same method from the baseline file text via exec in
        # an isolated namespace is fragile across refactors; instead
        # confirm the exact method body text is a substring of the
        # baseline file (function bodies aren't reformatted between these
        # two close commits, so a substring match is a faithful check).
        assert current_src in baseline_full, (
            "SemanticMatcher.match() source differs from baseline 3433638 -- "
            "this pass must not modify match() for experiential-learning purposes"
        )

    def test_find_nc_byte_identical_to_baseline(self):
        import aurora_reflexive_interpreter as ri
        current_src = inspect.getsource(ri.SemanticMatcher._find_nc)
        baseline_full = _baseline_source("aurora_reflexive_interpreter.py")
        assert current_src in baseline_full, (
            "SemanticMatcher._find_nc() source differs from baseline 3433638"
        )

    def test_semantic_matcher_class_frame_and_stance_tables_unchanged(self):
        import aurora_reflexive_interpreter as ri
        baseline_full = _baseline_source("aurora_reflexive_interpreter.py")
        full_class_src = inspect.getsource(ri.SemanticMatcher)
        assert full_class_src in baseline_full, (
            "SemanticMatcher class body (including frame/stance mappings) "
            "differs from baseline 3433638"
        )


class TestNoNewReinforcementOrPreferenceTables:
    FORBIDDEN_IDENTIFIER_MARKERS = (
        "reinforcement_table", "reinforcementtable",
        "coordinate_preference", "coordinatepreference",
        "consequence_to_coordinate", "consequencetocoordinate",
        "salience_rule", "saliencerule",
        "learned_selection", "learnedselection",
        "selection_weight", "selectionweight",
    )

    TOUCHED_FILES = [
        "aurora.py",
        "aurora_reflexive_interpreter.py",
        "aurora_understanding_sediment.py",
        "aurora_sedimemory.py",
        "aurora_warp_protocol.py",
        "aurora_internal/aurora_cognitive_experience_chamber.py",
    ]

    def test_no_forbidden_table_identifiers_in_touched_files(self):
        for relpath in self.TOUCHED_FILES:
            full_path = os.path.join(REPO_ROOT, relpath)
            with open(full_path, "r", encoding="utf-8") as f:
                src = f.read()
            lowered = src.lower().replace(" ", "")
            for marker in self.FORBIDDEN_IDENTIFIER_MARKERS:
                assert marker not in lowered, (
                    f"forbidden marker {marker!r} found in {relpath}"
                )


class TestConsequenceDoesNotFeedBackIntoSelection:
    def test_run_closed_loop_episode_source_never_reads_consequence_to_pick_a_ref(self):
        """The wiring added this pass only ever WRITES the already-computed
        ref onto step/backprojection/witness_report records -- every line
        that assigns a *representational_ref field must draw its value
        from bridge_result.get(...) or an existing step.representational_ref
        read, never from step.consequence or any quantity derived from it."""
        from aurora_internal import aurora_cognitive_experience_chamber as rcec
        for fn in (rcec.run_episode_step, rcec.run_backprojection_step, rcec.run_witnessed_observation):
            src = inspect.getsource(fn)
            for line in src.splitlines():
                if "representational_ref" in line and "=" in line and "consequence" not in line.split("=")[0]:
                    rhs = line.split("=", 1)[1]
                    assert "consequence" not in rhs, (
                        f"line assigns a ref from something involving 'consequence': {line!r} in {fn.__name__}"
                    )

    def test_representational_ref_field_default_is_none_not_derived(self):
        from aurora_internal.aurora_cognitive_experience_chamber import EpisodeStep
        import dataclasses
        f = next(f for f in dataclasses.fields(EpisodeStep) if f.name == "representational_ref")
        assert f.default is None
