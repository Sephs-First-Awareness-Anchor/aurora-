# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Function words join generalizations through her own lexical signals, each at the standing it earned."""
import ast
import os
import re

import pytest

from aurora_internal import crystal_grammar as G, crystal_promotion as P
from aurora_internal.crystal_associations import AssociationStore, COUNTED_BASES, SOURCE_BASIS

ROLES = {"and": "addition", "also": "addition", "plus": "addition", "but": "contrast", "however": "contrast", "yet": "contrast",
         "so": "consequence", "therefore": "consequence", "thus": "consequence"}


# -- what each signal is worth ---------------------------------------------------------------------------------------------------------------------

def test_the_hand_authored_role_lookup_is_kept_and_never_counted():
    s = AssociationStore()
    assert G.place_scaffold(s, ROLES) == 9
    assert s.incoming("pragmatic:addition", "is_a") == {} and s.connections_for("and") == {}
    assert len(s.records()) == 9 and s.basis_counts().get("scaffold") == 9
    assert SOURCE_BASIS["lexical_scaffold"] not in COUNTED_BASES


def test_a_class_she_found_counts_and_counts_more_each_time_it_is_found_again():
    ds = []
    for n in (1, 2, 4, 20):
        s = AssociationStore()
        G.place_classes(s, {"L0@1": ["and", "or"]}, {"L0@1": n})
        ds.append(s.strength("and", "lexclass:L0@1", "is_a"))
    assert ds[0] == pytest.approx(0.5) and all(b > a for a, b in zip(ds, ds[1:])) and ds[-1] < 1.0


def test_a_family_counts_only_through_the_evidence_she_earned():
    cand = lambda ev: {"word": "because", "applicability_family": "F1", "candidate_id": "c", "evidence": ev}
    earned, inherited = {"provenance": "consequence_earned"}, {"provenance": "inherited_scaffold"}
    weights = []
    for ev in ([inherited], [earned], [earned, earned, inherited], [earned] * 6):
        s = AssociationStore()
        G.place_families(s, [cand(ev)])
        weights.append(s.strength("because", "lexfam:F1", "is_a"))
    assert weights[0] == 0.0 and 0.0 < weights[1] < weights[2] < weights[3] < 1.0
    s = AssociationStore()
    assert G.place_families(s, [cand([inherited])]) == 1 and len(s.records()) == 1 and s.basis_counts().get("scaffold") == 1   # kept, uncounted
    assert G.place_families(AssociationStore(), [{"word": "", "applicability_family": "F"}, {"word": "x"}]) == 0


# -- groups join the class that holds them -----------------------------------------------------------------------------------------------------------

def test_a_role_group_joins_a_class_by_the_share_of_it_the_class_covers():
    out = []
    for held in (["and"], ["and", "also"], ["and", "also", "plus"]):
        s = AssociationStore()
        G.join_groups(s, ROLES, {"L0@1": held + ["but"]}, {"L0@1": 3})
        out.append(s.strength("pragmatic:addition", "lexclass:L0@1", "is_a"))
    assert out[0] < out[1] < out[2] and out[2] == pytest.approx(0.75)                       # full cover x the class's own standing (3 -> 0.75)


def test_a_group_the_class_does_not_touch_does_not_join_it():
    s = AssociationStore()
    G.join_groups(s, ROLES, {"L0@1": ["and", "also"]}, {"L0@1": 1})
    assert s.strength("pragmatic:contrast", "lexclass:L0@1", "is_a") == 0.0 and s.strength("pragmatic:consequence", "lexclass:L0@1", "is_a") == 0.0
    assert s.strength("pragmatic:addition", "lexclass:L0@1", "is_a") > 0.0
    assert [r for r in s.records() if r[0].startswith("pragmatic:")] == [("pragmatic:addition", "lexclass:L0@1", "is_a")]     # nothing recorded for the rest


# -- the function words end up under one generalization, found, not declared ---------------------------------------------------------------

def world(with_class=True):
    s = AssociationStore()
    G.place_scaffold(s, ROLES)
    if with_class:
        G.place_classes(s, {"L0@1": list(ROLES)}, {"L0@1": 6})
        G.join_groups(s, ROLES, {"L0@1": list(ROLES)}, {"L0@1": 6})
    for w in ROLES:                                                                          # each used with the same everyday things: that is what they are
        for x in ("sentence", "clause", "speech"):
            s.add(w, x, "related_to", ref=f"{w}|{x}", source="co-occurrence", strength=0.6)
    return s


def test_nine_function_words_of_three_roles_are_one_class_she_found_and_the_class_promotes():
    s = world()
    assert G.generalizations(s, "and") == ["lexclass:L0@1"]                                  # the scaffold role group is not counted into it
    held = G.members_of_generalization(s, "lexclass:L0@1")
    assert set(held) >= set(ROLES) and {"pragmatic:addition", "pragmatic:contrast", "pragmatic:consequence"} <= set(held)
    small = AssociationStore()
    G.place_classes(small, {"L0@1": ["and", "also", "plus"]}, {"L0@1": 6})
    for w in ("and", "also", "plus"):
        for x in ("sentence", "clause", "speech"):
            small.add(w, x, "related_to", ref=f"{w}|{x}", source="co-occurrence", strength=0.6)
    assert P.promotion_degree(s, "lexclass:L0@1") > P.promotion_degree(small, "lexclass:L0@1") > 0.0     # more words, more roles joined: promoted further


def test_with_only_the_scaffold_nothing_is_promoted_because_nothing_has_been_lived():
    s = world(with_class=False)
    assert G.generalizations(s, "and") == [] and P.promotion_degree(s, "pragmatic:addition") == 0.0 and P.promotion_degree(s, "lexclass:L0@1") == 0.0


def test_a_class_of_words_that_share_nothing_promotes_less_than_one_that_behaves_alike():
    alike = world()
    odd = AssociationStore()
    G.place_classes(odd, {"L1@1": list(ROLES)}, {"L1@1": 6})
    for i, w in enumerate(ROLES):
        odd.add(w, f"own{i}", "related_to", ref=f"o{i}", source="co-occurrence", strength=0.6)
    assert P.promotion_degree(odd, "lexclass:L1@1") < P.promotion_degree(alike, "lexclass:L0@1")


# -- isolation and sources ---------------------------------------------------------------------------------------------------------------------------

def test_it_imports_only_the_association_store_and_nothing_running_imports_it_and_no_degree_meets_a_cut_off():
    tree = ast.parse(open(G.__file__, encoding="utf-8").read())
    assert {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module and n.module.startswith("aurora")} == {"aurora_internal.crystal_associations"}
    bad = [1 for n in ast.walk(tree) if isinstance(n, ast.Compare) for op, r in zip(n.ops, n.comparators)
           if isinstance(op, (ast.Gt, ast.GtE, ast.Lt, ast.LtE)) and isinstance(r, ast.Constant) and isinstance(r.value, float) and r.value != 0.0]
    assert bad == []
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hits = []
    for base, _, files in os.walk(root):
        if any(x in base for x in (".git", "tests", "scripts", "aurora_state", "node_modules")):
            continue
        for f in files:
            if f.endswith(".py") and f != "crystal_grammar.py" and re.search(r"(from|import)\s+[\w.]*crystal_grammar", open(os.path.join(base, f), encoding="utf-8", errors="ignore").read()):
                hits.append(f)
    assert hits == []


def test_the_lexical_sources_have_the_standing_they_have_earned():
    assert SOURCE_BASIS["lexical_class"] in COUNTED_BASES and SOURCE_BASIS["lexical_grounding"] in COUNTED_BASES
    assert SOURCE_BASIS["lexical_scaffold"] not in COUNTED_BASES


def test_a_class_member_is_held_at_the_degree_it_belongs_times_the_standing_of_the_class():
    s = AssociationStore()
    G.place_classes(s, {"S:and": {"and": 1.0, "or": 0.4, "x": 7.0, "y": -3.0}}, {"S:and": 3})                   # standing 0.75; out-of-range degrees are clamped
    assert s.strength("and", "lexclass:S:and", "is_a") == pytest.approx(0.75) and s.strength("or", "lexclass:S:and", "is_a") == pytest.approx(0.3)
    assert s.strength("x", "lexclass:S:and", "is_a") == pytest.approx(0.75) and s.strength("y", "lexclass:S:and", "is_a") == 0.0
