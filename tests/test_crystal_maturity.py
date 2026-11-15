# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Build plan P3: level standing is a gradient of real occurrences, never a bar."""
import ast
import os
import re

import pytest

from aurora_internal import crystal_maturity as M


def P(**kw):
    base = dict(association_strengths=[], contexts=0, sessions=0, consequences_shown=0, consequences_total=0, members_promoted=0, members_total=0)
    base.update(kw)
    return M.points_from_evidence(**base)


FULL = dict(association_strengths=[1.0] * 40, contexts=40, sessions=30, consequences_shown=9, consequences_total=10, members_promoted=9, members_total=10)


# -- degrees -----------------------------------------------------------------------------------------------------------------------------------

def test_a_count_becomes_a_degree_that_is_half_at_the_reference_and_always_rising():
    assert M.degree(0, 5) == 0.0 and M.degree(5, 5) == pytest.approx(0.5)
    xs = [M.degree(i, 5) for i in range(0, 200)]
    assert all(b > a for a, b in zip(xs, xs[1:])) and xs[-1] < 1.0       # every further occurrence counts for a little more; never reaches a ceiling
    assert max(b - a for a, b in zip(xs, xs[1:])) < 0.2                   # no jump


def test_nothing_occurring_leaves_a_crystal_at_level_one_exactly():
    m = M.memberships(P())
    assert m == {1: 1.0, 2: 0.0, 3: 0.0, 4: 0.0} and M.expected_level(P()) == 1.0


# -- the points come from what occurred ------------------------------------------------------------------------------------------------------

def test_association_is_the_amount_carried_so_many_weak_ties_equal_a_few_strong_ones():
    assert P(association_strengths=[0.5] * 8)["associative"] == pytest.approx(P(association_strengths=[1.0] * 4)["associative"])
    assert P(association_strengths=[7.0])["associative"] == 1.0           # one tie cannot count for more than a whole one


def test_consequence_and_promotion_are_shares_and_zero_when_none_were_looked_for():
    p = P(consequences_shown=1, consequences_total=4, members_promoted=3, members_total=4)
    assert p["cognitive"] == 0.25 and p["recursive"] == 0.75
    assert P()["cognitive"] == 0.0 and P()["recursive"] == 0.0


def test_emotional_stays_unknown_until_it_is_wired():
    assert P()["emotional"] is None and P(emotional=0.4)["emotional"] == 0.4


def test_polarity_keeps_its_sign():
    assert P(axis_displacement=[-0.6, -0.2])["polarity"] == pytest.approx(-0.4)
    assert P(axis_displacement=[0.6, 0.2])["polarity"] == pytest.approx(0.4)
    assert P(axis_displacement=[-5, -5])["polarity"] == -1.0 and P()["polarity"] is None


# -- levels are memberships --------------------------------------------------------------------------------------------------------------------

def test_memberships_are_nested_and_inside_zero_to_one_for_any_evidence():
    import random
    rnd = random.Random(1)
    for _ in range(300):
        p = P(association_strengths=[rnd.random() for _ in range(rnd.randint(0, 40))], contexts=rnd.randint(0, 50), sessions=rnd.randint(0, 40),
              consequences_shown=rnd.randint(0, 5), consequences_total=rnd.randint(0, 5), members_promoted=rnd.randint(0, 5), members_total=rnd.randint(0, 5))
        m = M.memberships(p)
        assert m[1] == 1.0 and 1.0 >= m[2] >= m[3] >= m[4] >= 0.0 and 1.0 <= M.expected_level(p) <= 4.0


@pytest.mark.parametrize("field,values", [
    ("association_strengths", [[1.0] * n for n in range(0, 41)]),
    ("contexts", list(range(0, 41))),
    ("sessions", list(range(0, 41))),
    ("consequences_shown", list(range(0, 11))),
    ("members_promoted", list(range(0, 11))),
])
def test_standing_rises_smoothly_with_each_kind_of_evidence_and_never_falls(field, values):
    xs, ms = [], []
    for v in values:
        kw = dict(FULL)
        kw[field] = v
        if field in ("consequences_shown", "members_promoted"):
            kw["consequences_total"], kw["members_total"] = 10, 10
        xs.append(M.expected_level(P(**kw)))
        ms.append(M.memberships(P(**kw)))
    assert all(b >= a - 1e-12 for a, b in zip(xs, xs[1:]))
    for lv in (2, 3, 4):
        assert max(b[lv] - a[lv] for a, b in zip(ms, ms[1:])) < 0.3        # no level's standing jumps on one more occurrence
    assert xs[-1] > xs[0]


def test_each_level_asks_for_more_than_the_one_below():
    p = P(association_strengths=[1.0] * 8, contexts=10, sessions=8, consequences_shown=8, consequences_total=10, members_promoted=8, members_total=10)
    m = M.memberships(p)
    assert m[2] > m[3] > m[4] > 0.0


def test_without_any_consequence_shown_the_third_and_fourth_levels_stay_at_nothing_but_the_second_grows():
    m = M.memberships(P(**{**FULL, "consequences_shown": 0}))
    assert m[2] > 0.8 and m[3] == 0.0 and m[4] == 0.0


def test_without_promoted_members_only_the_fourth_level_is_held_back():
    with_ = M.memberships(P(**FULL))
    without = M.memberships(P(**{**FULL, "members_promoted": 0}))
    assert without[3] == pytest.approx(with_[3]) and without[2] == pytest.approx(with_[2])
    assert without[4] == 0.0 < with_[4]


def test_what_is_unknown_leaves_the_blend_and_what_was_found_empty_holds_it_down():
    p = {"associative": 40.0, "abstract": None, "temporal": None, "cognitive": None, "recursive": None}
    assert M.memberships(p)[3] > 0.7                                     # only association known: judged on that alone
    p["cognitive"] = 0.0
    assert M.memberships(p)[3] == 0.0                                    # looked for and absent: holds it at nothing


def test_the_balance_between_the_requirements_matters_not_just_their_total():
    even = M.memberships({"associative": 20.0, "abstract": 0.5, "temporal": 0.5, "cognitive": 0.5, "recursive": 0.5})[3]
    lopsided = M.memberships({"associative": 20.0, "abstract": 1.0, "temporal": 1.0, "cognitive": 0.1, "recursive": 0.5})[3]
    assert lopsided < even                                               # the weakest holds it down even when the others are full
    better_rest = M.memberships({"associative": 20.0, "abstract": 0.9, "temporal": 0.9, "cognitive": 0.5, "recursive": 0.5})[3]
    assert better_rest > even                                            # same weakest part, the rest better met: stands higher


# -- no bars, isolated ----------------------------------------------------------------------------------------------------------------------------

def test_the_module_never_compares_a_degree_with_a_cut_off():
    tree = ast.parse(open(M.__file__, encoding="utf-8").read())
    bad = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Compare):
            for op, right in zip(n.ops, n.comparators):
                if isinstance(op, (ast.Gt, ast.GtE, ast.Lt, ast.LtE)) and isinstance(right, ast.Constant) and isinstance(right.value, (int, float)) \
                        and right.value not in (0, 0.0):
                    bad.append(ast.dump(n)[:80])
    assert bad == []


def test_it_imports_nothing_from_aurora_and_nothing_running_imports_it():
    tree = ast.parse(open(M.__file__, encoding="utf-8").read())
    assert [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)) and "aurora" in ast.dump(n)] == []
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hits = []
    for base, _, files in os.walk(root):
        if any(x in base for x in (".git", "tests", "scripts", "aurora_state", "node_modules")):
            continue
        for f in files:
            if f.endswith(".py") and f not in ("crystal_maturity.py", "crystal_weave.py", "aurora_dimensional_systems.py", "crystal_interior.py") and re.search(r"(from|import)\s+[\w.]*crystal_maturity", open(os.path.join(base, f), encoding="utf-8", errors="ignore").read()):
                hits.append(f)
    assert hits == []


def test_a_higher_level_is_never_better_met_than_the_one_below_even_when_an_extra_requirement_is_fully_met():
    # the fourth level adds "members promoted"; with that fully met and the same weakest part, it would otherwise out-score the third
    p = {"associative": 60.0, "abstract": 0.3, "temporal": 0.3, "cognitive": 0.3, "recursive": 1.0}
    m = M.memberships(p)
    assert m[4] <= m[3] <= m[2]
    # and the third, when association is nearly the same as at the second, with the rest strongly met
    q = {"associative": 8.0, "abstract": 0.3, "temporal": 1.0, "cognitive": 1.0, "recursive": 1.0}
    n = M.memberships(q)
    assert n[3] <= n[2] and n[4] <= n[3]
