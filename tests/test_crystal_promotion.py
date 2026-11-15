# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Promotion follows associative group classification: a group that one generalization classifies promotes to a higher-level crystal under it."""
import ast
import os
import re
import string

import pytest

from aurora_internal import crystal_promotion as P
from aurora_internal.crystal_associations import AssociationStore


def add(s, a, b, st=0.8, t="related_to", source="co-occurrence", ref=None):
    s.add(a, b, t, ref=ref or f"{a}|{b}|{t}|{source}", source=source, strength=st)


def world(n_letters=26, shared=("spelling", "word", "symbol")):
    s = AssociationStore()
    for ch in string.ascii_lowercase[:n_letters]:
        add(s, ch, "letter", 0.9, "is_a")
        for x in shared:
            add(s, ch, x, 0.6)
    for d in "0123456789":
        add(s, d, "number", 0.9, "is_a")
        add(s, d, "counting", 0.6)
        add(s, d, "symbol", 0.5)
    for f in ("apple", "pear", "plum"):
        add(s, f, "fruit", 0.9, "is_a")
        for x in ("eat", "sweet"):
            add(s, f, x, 0.6)
    return s


# -- a group classified by one generalization promotes it --------------------------------------------------------------------------------------------

def test_the_letters_classify_under_letter_and_it_promotes_high():
    s = world()
    c = P.classification(s, "letter")
    assert set(string.ascii_lowercase) <= set(c) and all(c[l] >= 0.9 - 1e-9 for l in string.ascii_lowercase) and "letter" not in c
    assert P.promotion_degree(s, "letter") > 0.6


def test_a_bigger_group_promotes_more_and_a_tiny_one_a_little():
    ds = [P.promotion_degree(world(n), "letter") for n in (1, 2, 3, 6, 12, 26)]
    assert all(b > a for a, b in zip(ds, ds[1:])) and ds[0] < 0.5 * ds[-1]        # one lone member is hardly a group
    assert P.promotion_degree(world(), "fruit") < P.promotion_degree(world(), "letter")


def test_a_group_that_shares_nothing_is_not_one_kind_of_thing():
    s = AssociationStore()
    for i in range(20):
        add(s, f"x{i}", "box", 0.9, "is_a")
        add(s, f"x{i}", f"own{i}", 0.6)                                          # each tied only to its own private thing
    assert P.unity(s, P.classification(s, "box"), ["box"]) == 0.0 and P.promotion_degree(s, "box") == 0.0


def test_unity_rises_smoothly_with_what_the_members_share():
    ds = []
    for k in range(0, 6):
        s = AssociationStore()
        for i in range(8):
            add(s, f"m{i}", "kind", 0.9, "is_a")
            for j in range(5):
                add(s, f"m{i}", f"common{j}" if j < k else f"own{i}_{j}", 0.6)
        ds.append(P.promotion_degree(s, "kind"))
    assert all(b >= a for a, b in zip(ds, ds[1:])) and ds[0] == 0.0 and ds[-1] > ds[3] > ds[1] > 0.0
    assert max(b - a for a, b in zip(ds, ds[1:])) < 0.35


def test_a_generalization_classifies_by_converging_too_not_only_by_being_said_so():
    s = world()
    for x in ("spelling", "word", "symbol"):
        add(s, "glyph", x, 0.6)                                                 # looks like a letter, never said to be one
    c = P.classification(s, "letter")
    assert 0.0 < c["glyph"] <= min(c[l] for l in string.ascii_lowercase) and "spelling" not in c
    add(s, "mark", "spelling", 0.6)
    add(s, "mark", "own", 0.6)
    assert 0.0 < P.classification(s, "letter")["mark"] < c["glyph"]              # one that matches less closely is classified less


def test_only_counted_evidence_classifies_anything():
    s = AssociationStore()
    for i in range(30):
        add(s, f"m{i}", "kind", 1.0, "is_a", source="seeded")
        add(s, f"m{i}", "shared", 1.0, source="backfill_role_heuristic")
    assert P.classification(s, "kind") == {} and P.promotion_degree(s, "kind") == 0.0


def test_candidates_are_ranked_by_degree_and_top_only_limits_what_is_returned():
    s = world()
    allc = P.promotion_candidates(s, list(s.connections_for("letter")) + ["letter", "number", "fruit"])
    names = [g for g, _ in allc]
    assert names.index("letter") < names.index("number") < names.index("fruit")
    assert [g for g, _ in P.promotion_candidates(s, ["letter", "number", "fruit"], top=1)] == ["letter"]
    assert all(d > 0.0 for _, d in allc)


# -- the level it stands at --------------------------------------------------------------------------------------------------------------------------

def test_a_generalization_stands_above_what_it_classifies_by_its_degree():
    s = world()
    every = list(P.classification(s, "letter"))
    low = P.level_under(s, "letter", {c: 1.0 for c in every})
    high = P.level_under(s, "letter", {c: 2.0 for c in every})
    assert 1.0 < low < 2.0 < high < 3.0 and high - 1.0 == pytest.approx(2 * (low - 1.0))
    assert P.level_under(s, "nothing", {}) == 1.0


def test_the_level_never_passes_the_top_and_rises_with_the_members_level():
    s = world()
    every = list(P.classification(s, "letter"))
    ls = [P.level_under(s, "letter", {c: float(v) for c in every}) for v in (1, 1.5, 2, 3, 4, 9)]
    assert all(b > a for a, b in zip(ls, ls[1:])) or ls[-1] == 4.0
    assert max(ls) == 4.0 and ls[4] <= 4.0


def test_a_member_with_no_stated_level_counts_as_level_one():
    s = world()
    assert P.level_under(s, "letter", {}) == pytest.approx(P.level_under(s, "letter", {c: 1.0 for c in P.classification(s, "letter")}))


# -- reads only, no bars, isolated ----------------------------------------------------------------------------------------------------------------------

def test_nothing_is_changed_by_asking():
    s = world()
    before = s.to_dict()
    P.promotion_candidates(s, ["letter", "number"])
    P.level_under(s, "letter", {})
    assert s.to_dict() == before


def test_no_degree_is_compared_with_a_cut_off_and_nothing_running_imports_it():
    tree = ast.parse(open(P.__file__, encoding="utf-8").read())
    bad = [ast.dump(n)[:80] for n in ast.walk(tree) if isinstance(n, ast.Compare) for op, r in zip(n.ops, n.comparators)
           if isinstance(op, (ast.Gt, ast.GtE, ast.Lt, ast.LtE)) and isinstance(r, ast.Constant) and isinstance(r.value, float) and r.value != 0.0]
    assert bad == []
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hits = []
    for base, _, files in os.walk(root):
        if any(x in base for x in (".git", "tests", "scripts", "aurora_state", "node_modules")):
            continue
        for f in files:
            if f.endswith(".py") and f not in ("crystal_promotion.py", "crystal_runtime.py") and re.search(r"(from|import)\s+[\w.]*crystal_promotion", open(os.path.join(base, f), encoding="utf-8", errors="ignore").read()):
                hits.append(f)
    assert hits == []
