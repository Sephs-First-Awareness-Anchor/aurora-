# Authors: Sunni (Sir) Morningstar & Cael Devo
"""'B does not come after a.' reaches the composer as a negated verb, not as 'does' + object 'not come ...'."""
import pytest

from aurora_internal import aurora_proposition_frame as F


@pytest.mark.parametrize("rel,obj,expected", [
    ("does", "not come after a", ("come", "after a")),
    ("do", "not like rain", ("like", "rain")),
    ("did", "not come", ("come", "")),
    ("Does", "NOT follow b", ("follow", "b")),
])
def test_the_verb_after_do_not_is_the_relation(rel, obj, expected):
    assert F._split_negated_auxiliary(rel, obj) == expected


@pytest.mark.parametrize("rel,obj", [("does", "come after a"), ("comes", "not after a"), ("does", "not"), ("is", "not here"), ("", "")])
def test_other_shapes_are_left_alone(rel, obj):
    assert F._split_negated_auxiliary(rel, obj) is None


def test_the_frame_is_negated_with_the_real_verb():
    class Active:
        relational_form = {"subject": "B", "relation": "does", "obj": "not come after a", "negated": False}
    frame = F._frame_from_constraint_relation({"_active_turn_state": Active()})
    assert (frame.relation, frame.obj, frame.negated) == ("come", "after a", True)
