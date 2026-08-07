# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Categorical Condition Search Admissibility Repair.

_categorical_condition_pool() built its 200-slot condition budget by
pairing every scalar projection (from _select_candidates()) and constant
with every other, in deterministic nested-loop order, and returning as
soon as 200 unique-signature conditions existed. On a RoleNormalizedTransition
-shaped input (action_type/acting_entity_role/candidate_affected_roles/a
nested visible_pre_state world), this let the entire budget be consumed by
self-comparisons and other conditions that are constant (all-True or
all-False) across every training example -- degenerate conditions that can
never partition any subgroup in _build_categorical_branch(), since a
condition constant on the whole example set is also constant on any
subset of it. A useful condition like
SELECT(action_type) == CONST("seal") never got proposed at all, even
though it was well within IFELSE/EQ/SELECT/CONST's existing 20-node
budget and fits all training evidence.

This is not a missing primitive -- the vocabulary, the input field, the
evidence, and the node budget were all already sufficient. The search
was starving itself on useless candidate geometry.

The repair, entirely domain-neutral (no special-casing of action_type,
seal, or RCEC):
  1. A proposed condition is evaluated against the examples before it is
     added to the pool; if it is all-True or all-False, it does not
     consume one of the 200 usable slots.
  2. Projections that produce identical values across every example are
     deduplicated to one representative (they are functionally the same
     condition ingredient).
  3. Discriminative-projection ==/!= observed-literal comparisons are
     proposed before projection-vs-projection and ordering comparisons.
  4. Discriminative (non-constant-across-examples) projections are tried
     before constant ones, since a constant projection alone carries no
     partition information.

The proof criterion: the same four untouched examples (2x seal->changes,
2x unseal->no_change) that previously produced unsynthesized_gap now
produce a candidate that fits all four and generalizes to unseen inputs
-- no new evidence, no hints, no RCEC-specific rule.
"""
from __future__ import annotations

import tempfile

from aurora_internal.aurora_operational_synthesis import (
    AuroraOperationalSynthesisChamber,
    SynthesisExample,
    _categorical_condition_pool,
    execute_program,
    synthesize_program,
)


def _visible_pre_state(world_id, sealed_vessel):
    return {
        "agent_id": "agent_a",
        "world_id": world_id,
        "entities": {
            "e_vessel": {"entity_type": "vessel", "sealed": sealed_vessel, "energy": 0},
            "e_conduit": {"entity_type": "conduit", "charge": "neutral", "sealed": False},
            "e_sensor": {"entity_type": "sensor", "reading": 0},
        },
    }


def _role_normalized_input(action_type, world_id, sealed_vessel):
    return {
        "action_type": action_type,
        "acting_entity_role": "vessel",
        "visible_pre_state": _visible_pre_state(world_id, sealed_vessel),
        "candidate_affected_roles": ["conduit", "sensor", "vessel"],
    }


_SEAL_CHANGES = {"affected_entity_role": "conduit", "affected_property": "charge", "direction": "change", "delay": 0}
_UNSEAL_NO_CHANGE = {"affected_entity_role": None, "affected_property": None, "direction": "no_change", "delay": 0}


# ---------------------------------------------------------------------------
# Pool-construction admissibility: degenerate conditions never consume a slot.
# ---------------------------------------------------------------------------

def _canary_examples():
    return [
        SynthesisExample("demo1", _role_normalized_input("seal", "w1", False), _SEAL_CHANGES),
        SynthesisExample("demo2", _role_normalized_input("seal", "w2", False), _SEAL_CHANGES),
        SynthesisExample("control1", _role_normalized_input("unseal", "w3", True), _UNSEAL_NO_CHANGE),
        SynthesisExample("control2", _role_normalized_input("unseal", "w4", True), _UNSEAL_NO_CHANGE),
    ]


def test_degenerate_self_comparisons_never_enter_the_pool():
    """acting_entity_role is 'vessel' in every example -- comparing it to
    itself, or to another always-'vessel' projection, is all-True or
    all-False and must be filtered before it reaches the pool."""
    pool = _categorical_condition_pool(_canary_examples())
    for cond in pool:
        left, right = cond["args"]
        if left == right:
            raise AssertionError(f"a condition compares a projection to itself: {cond}")


def test_action_type_equals_seal_is_proposed_and_reached_well_under_budget():
    """The user's own decisive check: SELECT(action_type) == CONST('seal')
    must actually appear in the pool, and the pool must not need anywhere
    near its full 200-slot budget to reach it now that degenerate
    candidates are filtered."""
    pool = _categorical_condition_pool(_canary_examples())
    target = {"op": "EQ", "args": [{"op": "SELECT", "path": ["action_type"]}, {"op": "CONST", "value": "seal"}]}
    assert target in pool
    assert pool.index(target) < 5, "the useful condition should be near the front, not buried"
    assert len(pool) < 200, "a starved pool that hits the raw budget ceiling signals padding with useless conditions"


def test_duplicate_projections_collapse_to_one_representative():
    """Two projection paths that yield identical values across every
    example (e.g. two different nested fields that happen to both read
    'w1'/'w2'/'w3'/'w4' in lockstep with world_id) are functionally the
    same condition ingredient and must not each get their own slot."""
    examples = [
        SynthesisExample("a", {"p": "x", "q": "x", "action_type": "seal"}, "changes"),
        SynthesisExample("b", {"p": "y", "q": "y", "action_type": "seal"}, "changes"),
        SynthesisExample("c", {"p": "z", "q": "z", "action_type": "unseal"}, "no_change"),
    ]
    pool = _categorical_condition_pool(examples)
    p_conditions = [c for c in pool if {"op": "SELECT", "path": ["p"]} in c["args"]]
    q_conditions = [c for c in pool if {"op": "SELECT", "path": ["q"]} in c["args"]]
    assert p_conditions and not q_conditions or q_conditions and not p_conditions, (
        "p and q produce identical values on every example -- only one should survive deduplication"
    )


def test_discriminative_projections_are_prioritized_over_constant_ones():
    """acting_entity_role is constant ('vessel') across the canary;
    action_type varies (seal/unseal). Conditions built from the varying
    projection must appear before conditions built purely from the
    constant one paired with another constant."""
    pool = _categorical_condition_pool(_canary_examples())
    action_type_positions = [
        i for i, c in enumerate(pool)
        if any(arg == {"op": "SELECT", "path": ["action_type"]} for arg in c["args"])
    ]
    vessel_constant_positions = [
        i for i, c in enumerate(pool)
        if all(
            arg.get("op") == "CONST" or arg == {"op": "SELECT", "path": ["acting_entity_role"]}
            for arg in c["args"]
        ) and any(arg == {"op": "SELECT", "path": ["acting_entity_role"]} for arg in c["args"])
    ]
    if action_type_positions and vessel_constant_positions:
        assert min(action_type_positions) < min(vessel_constant_positions)


# ---------------------------------------------------------------------------
# The proof criterion: the same untouched 4 examples now synthesize.
# ---------------------------------------------------------------------------

def test_four_example_canary_now_synthesizes_a_fitting_candidate():
    training = _canary_examples()
    tree = synthesize_program(training)
    assert tree is not None, "no_program_in_current_primitive_span should no longer occur for this evidence"
    for example in training:
        assert execute_program(tree, example.input_value) == example.expected_output


def test_four_example_canary_candidate_generalizes_to_unseen_worlds():
    """Not memorization of w1..w4 -- new world ids, still following the
    seal/unseal rule, must also resolve correctly."""
    tree = synthesize_program(_canary_examples())
    assert tree is not None
    seal_unseen = _role_normalized_input("seal", "w99", False)
    unseal_unseen = _role_normalized_input("unseal", "w100", True)
    assert execute_program(tree, seal_unseen) == _SEAL_CHANGES
    assert execute_program(tree, unseal_unseen) == _UNSEAL_NO_CHANGE


def test_four_example_canary_via_the_chamber_matches_the_reported_shape():
    """Exercises the same observe_example()/execute() path RCEC actually
    uses (consult_operational_synthesis_candidate()), not just the
    lower-level synthesize_program() helper."""
    tmp = tempfile.mkdtemp()
    chamber = AuroraOperationalSynthesisChamber(state_dir=tmp, persist=False)
    result = None
    for i, example in enumerate(_canary_examples()):
        kwargs = {"need_description": "effect"} if i == 0 else {}
        result = chamber.observe_example(
            "rcec_seal_unseal", example.input_value, example.expected_output, **kwargs,
        )
    assert result.get("candidate") is not None
    assert result.get("candidate", {}).get("training_score") == 1.0

    seal_result = chamber.execute("rcec_seal_unseal", _role_normalized_input("seal", "w9", False), allow_trial=True)
    assert seal_result.get("executed") is True
    assert seal_result.get("output") == _SEAL_CHANGES

    unseal_result = chamber.execute("rcec_seal_unseal", _role_normalized_input("unseal", "w10", True), allow_trial=True)
    assert unseal_result.get("executed") is True
    assert unseal_result.get("output") == _UNSEAL_NO_CHANGE


# ---------------------------------------------------------------------------
# Domain neutrality: the sign-classification and role-pair categorical
# tests in test_ifelse_synthesis_primitive.py already regression-cover this,
# but a direct check here keeps this file's own proof self-contained --
# ordering comparisons on a purely numeric, non-RCEC input still work.
# ---------------------------------------------------------------------------

def test_ordering_comparisons_still_generalize_for_an_unrelated_domain():
    """Same shape as test_ifelse_synthesis_primitive.py's own sign-
    classification regression (not duplicated here, just reconfirmed
    against this repair): EQ/NE-vs-literal is now tried before LT/LE/GT/GE
    per the directive, but the depth-bounded branch builder still
    backtracks past a memorizing EQ chain that can't fit its remaining
    depth budget onto a splitting LT/LE test that can, so ordering
    generalization is preserved."""
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
    for x, expected in ((42, "pos"), (-42, "neg"), (1000, "pos"), (7, "pos")):
        assert execute_program(tree, {"x": x}) == expected
