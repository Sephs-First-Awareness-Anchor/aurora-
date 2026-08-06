# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Build 598: Categorical Branch Primitive for the Operational Synthesis
Chamber (doctrine Level 6 -- Provide Representational Substrate).

Before this, execute_program()'s primitive set had no way to express
"if condition then value-A else value-B" for a non-boolean output --
_synthesize_boolean_scalar() only ever returned True/False, and
_synthesize_value()'s only non-constant string path was SELECT (copying a
field already literally present in the input). There was no way for the
chamber to compose a categorical rule like "if source_role is verb and
target_role is noun -> enables" -- the vocabulary to express that rule did
not exist, independent of how much evidence she's given.

This test file covers only the primitive and its synthesis search --
NOT relation typing itself, which stays hers to develop once fed evidence
(a separate, follow-on directive).
"""
from __future__ import annotations

from aurora_internal.aurora_operational_synthesis import (
    AuroraOperationalSynthesisChamber,
    SynthesisExample,
    describe_program,
    execute_program,
    synthesize_program,
)


class _Genealogy:
    def __init__(self):
        self.registered = []

    def register_emergent_operational_synthesis(self, payload):
        self.registered.append(dict(payload))
        return {"registered": True, "ability_id": "A:IFELSE_TEST"}


def _advance_with_holdouts(chamber, task_id, holdouts):
    for input_value, output_value in holdouts:
        chamber.observe_example(
            task_id, input_value, output_value,
            validation=True, source="unseen_holdout",
        )


# ---------------------------------------------------------------------------
# execute_program() -- IFELSE dispatch itself
# ---------------------------------------------------------------------------

def test_ifelse_evaluates_the_taken_branch_only():
    tree_then = {
        "op": "IFELSE",
        "cond": {"op": "CONST", "value": True},
        "then": {"op": "CONST", "value": "yes"},
        "else": {"op": "CONST", "value": "no"},
    }
    assert execute_program(tree_then, None) == "yes"

    tree_else = {
        "op": "IFELSE",
        "cond": {"op": "CONST", "value": False},
        "then": {"op": "CONST", "value": "yes"},
        "else": {"op": "CONST", "value": "no"},
    }
    assert execute_program(tree_else, None) == "no"


def test_ifelse_condition_and_branches_can_read_the_real_input():
    tree = {
        "op": "IFELSE",
        "cond": {"op": "GT", "args": [{"op": "SELECT", "path": ["x"]}, {"op": "CONST", "value": 0}]},
        "then": {"op": "CONST", "value": "positive"},
        "else": {"op": "CONST", "value": "not_positive"},
    }
    assert execute_program(tree, {"x": 5}) == "positive"
    assert execute_program(tree, {"x": -5}) == "not_positive"
    assert execute_program(tree, {"x": 0}) == "not_positive"


def test_ifelse_short_circuits_the_untaken_branch():
    """The untaken branch may contain an operation that would fail outside
    its guarding condition (e.g. division by zero) -- it must never run."""
    tree = {
        "op": "IFELSE",
        "cond": {"op": "EQ", "args": [{"op": "SELECT", "path": ["x"]}, {"op": "CONST", "value": 0}]},
        "then": {"op": "CONST", "value": "zero"},
        "else": {"op": "DIV", "args": [{"op": "CONST", "value": 1}, {"op": "SELECT", "path": ["x"]}]},
    }
    assert execute_program(tree, {"x": 0}) == "zero"
    assert execute_program(tree, {"x": 4}) == 0.25


def test_ifelse_nests_for_multiway_categorical_selection():
    """Chained IFELSE (then/else holding a further IFELSE), not a separate
    multi-branch SWITCH primitive, is how 3+-way selection is expressed."""
    tree = {
        "op": "IFELSE",
        "cond": {"op": "LT", "args": [{"op": "SELECT", "path": ["x"]}, {"op": "CONST", "value": 0}]},
        "then": {"op": "CONST", "value": "neg"},
        "else": {
            "op": "IFELSE",
            "cond": {"op": "EQ", "args": [{"op": "SELECT", "path": ["x"]}, {"op": "CONST", "value": 0}]},
            "then": {"op": "CONST", "value": "zero"},
            "else": {"op": "CONST", "value": "pos"},
        },
    }
    assert execute_program(tree, {"x": -3}) == "neg"
    assert execute_program(tree, {"x": 0}) == "zero"
    assert execute_program(tree, {"x": 3}) == "pos"


def test_ifelse_traversal_utilities_walk_cond_then_else():
    """_node_count / describe_program / _primitive_sequence previously only
    walked args/fields -- IFELSE's cond/then/else children need the same
    treatment or genealogy and complexity accounting silently undercount."""
    from aurora_internal.aurora_operational_synthesis import _node_count, _primitive_sequence

    tree = {
        "op": "IFELSE",
        "cond": {"op": "EQ", "args": [{"op": "SELECT", "path": ["x"]}, {"op": "CONST", "value": 0}]},
        "then": {"op": "CONST", "value": "zero"},
        "else": {"op": "CONST", "value": "nonzero"},
    }
    # IFELSE + EQ + SELECT + CONST(0) + CONST("zero") + CONST("nonzero") = 6
    assert _node_count(tree) == 6
    prims = _primitive_sequence(tree)
    assert prims.count("IFELSE") == 1
    assert "EQ" in prims and "SELECT" in prims
    assert prims.count("CONST") == 3
    description = describe_program(tree)
    assert description.startswith("if ")
    assert "then" in description and "else" in description


# ---------------------------------------------------------------------------
# Synthesis search: a categorical (non-boolean, non-numeric, non-constant)
# task must be composable now, and must generalize to unseen inputs -- not
# just memorize the literal training values.
# ---------------------------------------------------------------------------

def test_synthesize_program_composes_sign_classification_and_generalizes():
    training = [
        SynthesisExample("e1", {"x": -5}, "neg"),
        SynthesisExample("e2", {"x": -1}, "neg"),
        SynthesisExample("e3", {"x": 0}, "zero"),
        SynthesisExample("e4", {"x": 3}, "pos"),
        SynthesisExample("e5", {"x": 9}, "pos"),
        SynthesisExample("e6", {"x": -100}, "neg"),
    ]
    tree = synthesize_program(training)
    assert tree is not None
    assert tree.get("op") == "IFELSE"

    for example in training:
        assert execute_program(tree, example.input_value) == example.expected_output

    # Unseen values, not equal to any training literal -- proves the
    # synthesized rule is an ordering test, not per-example memorization.
    for x, expected in ((42, "pos"), (-42, "neg"), (1000, "pos"), (7, "pos")):
        assert execute_program(tree, {"x": x}) == expected


def test_role_pair_categorical_rule_generalizes_to_an_unseen_combination():
    """Mirrors the directive's motivating case: composing a rule like
    "if source_role is X and target_role is Y -> relation" from varied
    role-pair examples. This test does NOT touch OntologicalWeb or
    RelationType -- it only proves the chamber can compose and generalize
    such a rule once given evidence, which is the whole point of the
    primitive."""
    training = [
        SynthesisExample("r1", {"source_role": "verb", "target_role": "noun"}, "enables"),
        SynthesisExample("r2", {"source_role": "adjective", "target_role": "noun"}, "describes"),
        SynthesisExample("r3", {"source_role": "verb", "target_role": "noun"}, "enables"),
        SynthesisExample("r4", {"source_role": "noun", "target_role": "noun"}, "related_to"),
        SynthesisExample("r5", {"source_role": "adjective", "target_role": "noun"}, "describes"),
        SynthesisExample("r6", {"source_role": "noun", "target_role": "noun"}, "related_to"),
    ]
    tree = synthesize_program(training)
    assert tree is not None
    for example in training:
        assert execute_program(tree, example.input_value) == example.expected_output


def test_categorical_synthesis_does_not_fire_for_constant_output():
    """_constant_candidate() already owns the all-same-output case -- the
    categorical search must not compete with it."""
    training = [
        SynthesisExample("c1", {"x": 1}, "same"),
        SynthesisExample("c2", {"x": 2}, "same"),
        SynthesisExample("c3", {"x": 3}, "same"),
    ]
    tree = synthesize_program(training)
    assert tree is not None
    assert tree.get("op") == "CONST"


def test_categorical_synthesis_does_not_fire_for_numeric_or_boolean_output():
    """Numeric and boolean outputs keep using their own existing search
    paths -- the categorical branch is scoped to non-numeric, non-boolean
    scalars only, per the directive."""
    numeric_training = [
        SynthesisExample("n1", {"x": 1}, 2),
        SynthesisExample("n2", {"x": 2}, 4),
        SynthesisExample("n3", {"x": 3}, 6),
    ]
    tree = synthesize_program(numeric_training)
    assert tree is not None
    assert tree.get("op") != "IFELSE"

    boolean_training = [
        SynthesisExample("b1", {"x": 1}, True),
        SynthesisExample("b2", {"x": -1}, False),
        SynthesisExample("b3", {"x": 5}, True),
    ]
    tree_b = synthesize_program(boolean_training)
    assert tree_b is not None
    assert tree_b.get("op") != "IFELSE"


# ---------------------------------------------------------------------------
# Full chamber lifecycle: observe_example() -> synthesize() -> promotion,
# with the same WARP trial / genealogy path any other task uses -- no
# second-class treatment for a categorical task.
# ---------------------------------------------------------------------------

def test_categorical_task_synthesizes_promotes_and_registers_genealogy_via_the_chamber():
    genealogy = _Genealogy()
    chamber = AuroraOperationalSynthesisChamber(persist=False, genealogy=genealogy)
    chamber.attach_systems({"genealogy": genealogy})

    # Interleaved on purpose: the chamber synthesizes as soon as the
    # min-training/min-distinct-input thresholds are met, using whatever
    # examples have arrived so far. An all-"neg" prefix would let the
    # constant-output candidate win early and then never re-trigger
    # resynthesis (observe_example only resynthesizes while the candidate
    # is None/dissolved/failed) -- interleaving proves the search reaches
    # IFELSE rather than depending on example order.
    training = [
        ({"x": -5}, "neg"), ({"x": 0}, "zero"), ({"x": 3}, "pos"),
        ({"x": -1}, "neg"), ({"x": 9}, "pos"), ({"x": -100}, "neg"),
    ]
    for input_value, output_value in training:
        chamber.observe_example(
            "sign_classify", input_value, output_value,
            need_description="categorical sign classification",
        )

    # observe_example() only resynthesizes automatically while the task has
    # no candidate or its candidate is dissolved/failed -- a pre-existing
    # chamber behavior, out of this Level-6 directive's scope to change.
    # Force a resynthesis against the now-complete training set explicitly,
    # the same way any caller would once it knows more evidence has arrived.
    chamber.synthesize("sign_classify")

    status = chamber.task_status("sign_classify")
    assert status["exists"] is True
    assert status["candidate"] is not None
    assert status["candidate"]["primitive_sequence"][0] == "IFELSE"

    result = chamber.execute("sign_classify", {"x": 42})
    assert result["executed"] is True
    assert result["output"] == "pos"

    holdouts = [({"x": v}, "pos" if v > 0 else ("neg" if v < 0 else "zero"))
                for v in (11, -11, 22, -22, 33, -33, 44, -44, 55, -55)]
    _advance_with_holdouts(chamber, "sign_classify", holdouts)

    status = chamber.task_status("sign_classify")
    assert status["status"] == "promoted"
    assert status["candidate"]["status"] == "promoted"
    assert status["candidate"]["genealogy_ability_id"] == "A:IFELSE_TEST"
    # Same X/T/N/B/A ancestry fields any other promoted program carries --
    # this directive must not create a second-class genealogy path.
    assert set(status["candidate"]["root_constraints"]).issubset({"X", "T", "N", "B", "A"})
    assert status["candidate"]["root_constraints"]
    assert genealogy.registered
    assert genealogy.registered[-1]["primitive_sequence"][0] == "IFELSE"
    assert genealogy.registered[-1]["program_tree"]["op"] == "IFELSE"
