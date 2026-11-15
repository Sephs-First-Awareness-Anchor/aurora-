# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Words that are used in the same places stand in for one another; the diffuse ones the distinctive-follower finder cannot class are found this way."""
import ast
import os
import random
import re

import pytest

from aurora_internal import crystal_grammar as G, crystal_promotion as P, crystal_substitutability as S
from aurora_internal.crystal_associations import AssociationStore, COUNTED_BASES, SYMMETRIC_TYPES

NOUNS = ["cat", "dog", "bird", "fish", "tree", "rock", "cloud", "river", "stone", "lamp", "door", "road"]
VERBS = ["runs", "sleeps", "falls", "waits", "grows", "shines"]
CONJ = ["and", "or", "but", "so"]
DETS = ["the", "a"]


def corpus(n=600, seed=7, conj=CONJ):
    rnd = random.Random(seed)
    out = []
    for _ in range(n):
        n2 = rnd.randrange(len(NOUNS))
        verb = VERBS[(n2 + rnd.randrange(3)) % len(VERBS)]                         # each noun goes with only some verbs: verbs are selective
        out.append([rnd.choice(DETS), rnd.choice(NOUNS), rnd.choice(conj), rnd.choice(DETS), NOUNS[n2], verb])
    return out


def profiles(n=600, **kw):
    p = S.ContextProfiles()
    for s in corpus(n, **kw):
        p.observe(s)
    return p


# -- alike by where they are used, not by what they are called --------------------------------------------------------------------------------------

def test_words_used_in_the_same_places_substitute_and_words_used_in_different_places_do_not():
    p = profiles()
    assert p.similarity("and", "or") > 0.6 and p.similarity("cat", "dog") > 0.3
    assert p.similarity("and", "cat") < 0.05 and p.similarity("and", "runs") < 0.05
    assert p.similarity("and", "or") == pytest.approx(p.similarity("or", "and")) and p.similarity("and", "and") == 0.0


def test_a_word_that_has_hardly_been_seen_cannot_match_anything_yet_and_each_sighting_raises_it():
    sims = []
    for n in (2, 6, 20, 80, 600):
        sims.append(profiles(n).similarity("and", "or"))
    assert sims[0] < 0.2 and all(b >= a - 1e-9 for a, b in zip(sims, sims[1:])) and sims[-1] > 0.6
    assert S.ContextProfiles().similarity("x", "y") == 0.0


def test_similarity_rises_smoothly_as_the_contexts_two_words_share_grow():
    out = []
    for shared in range(0, 9):
        p = S.ContextProfiles(max_contexts=10000)
        for i in range(120):
            p.observe(["a%d" % (i % 8), "w1", "z%d" % (i % 8 if i % 8 < shared else 100 + i)])
            p.observe(["a%d" % (i % 8), "w2", "z%d" % (i % 8 if i % 8 < shared else 200 + i)])
        out.append(p.similarity("w1", "w2"))
    assert all(b >= a - 1e-9 for a, b in zip(out, out[1:])) and out[-1] > 0.8 > out[0] and max(b - a for a, b in zip(out, out[1:])) < 0.3


def test_the_words_every_sentence_leans_on_are_the_broadest_and_nothing_is_cut_off():
    p = profiles()
    fl = {w: p.function_likeness(w) for w in p.vocabulary()}
    assert min(fl[c] for c in CONJ) > max(fl[v] for v in VERBS) and all(0.0 < v < 1.0 for v in fl.values())
    assert p.breadth("the") > p.breadth("cat")


# -- classes: found, as groups, by degree -----------------------------------------------------------------------------------------------------------

def test_the_conjunctions_are_found_as_one_class_and_it_ranks_above_a_group_of_unlike_words():
    p = profiles()
    rows = S.exemplar_classes(p, p.vocabulary())
    ranked = [h for h, _, _ in rows]
    best = {h: d for h, d, _ in rows}
    top_conj = max(CONJ, key=lambda c: best.get(c, 0.0))
    members = dict((h, m) for h, _, m in rows)[top_conj]
    assert {c for c in CONJ if c != top_conj} <= set(members) and all(members[c] > members.get("cat", 0.0) for c in CONJ if c != top_conj)
    assert best[top_conj] > 0.2 and [h for h, _, _ in S.exemplar_classes(p, p.vocabulary(), top=3)] == ranked[:3]
    assert S.class_degree(p, "x", {"and": 0.9, "cat": 0.9, "runs": 0.9}) < best[top_conj]            # mass without likeness is not a class


def test_a_single_substitute_is_not_a_class_and_a_bigger_alike_group_is_more_of_one():
    p = profiles()
    assert S.class_degree(p, "and", {}) == 0.0
    one = S.class_degree(p, "and", {"or": p.similarity("and", "or")})
    three = S.class_degree(p, "and", {c: p.similarity("and", c) for c in ("or", "but", "so")})
    assert one == 0.0 < three                                                                       # one substitute is no class: nothing to be alike to each other


# -- links, ready for the crystals ---------------------------------------------------------------------------------------------------------------------

def test_substitutes_are_counted_symmetric_links_and_per_word_only_limits_how_many():
    p, s = profiles(), AssociationStore()
    n = S.place_substitutes(s, p, CONJ + NOUNS, per_word=2)
    assert n > 0 and "substitutes_for" in SYMMETRIC_TYPES
    assert s.strength("and", "or", "substitutes_for") == pytest.approx(s.strength("or", "and", "substitutes_for")) and s.strength("and", "or", "substitutes_for") > 0.0
    assert s.basis_counts().get("recurrence", 0) > 0 and "recurrence" in COUNTED_BASES
    assert len(s.connections_for("and")) <= 2 + 2 * len(CONJ + NOUNS)                              # limit applies to what it chose; others may have chosen it
    small, big = AssociationStore(), AssociationStore()
    S.place_substitutes(small, p, CONJ + NOUNS, per_word=1)
    S.place_substitutes(big, p, CONJ + NOUNS, per_word=8)
    assert len(small.records()) < len(big.records())


def test_state_round_trips():
    p = profiles(80)
    q = S.ContextProfiles()
    q.restore(p.state())
    assert q.similarity("and", "or") == pytest.approx(p.similarity("and", "or")) and q.vocabulary() == p.vocabulary()


# -- end to end: the class she finds is what the role groups join, and it promotes --------------------------------------------------------------------

def test_the_found_class_is_what_the_role_groups_join_and_it_promotes_with_nothing_declared_in_advance():
    p = profiles()
    rows = S.exemplar_classes(p, p.vocabulary())
    h, d, members = max((r for r in rows if r[0] in CONJ), key=lambda r: r[1])
    store = AssociationStore()
    roles = {"and": "addition", "or": "addition", "but": "contrast", "so": "consequence"}
    G.place_scaffold(store, roles)
    G.place_classes(store, {f"S:{h}": S.class_members(h, members)}, {f"S:{h}": 6})
    G.join_groups(store, roles, {f"S:{h}": S.class_members(h, members)}, {f"S:{h}": 6})
    for c in CONJ:                                                                              # and they are used with the same everyday things
        for x in ("sentence", "clause", "speech"):
            store.add(c, x, "related_to", ref=f"{c}|{x}", source="co-occurrence", strength=0.6)
    assert G.generalizations(store, "but")[0] == f"lexclass:S:{h}"
    assert {"pragmatic:addition", "pragmatic:contrast", "pragmatic:consequence"} <= set(G.members_of_generalization(store, f"lexclass:S:{h}"))
    assert P.promotion_degree(store, f"lexclass:S:{h}") > 0.0
    bare = AssociationStore()
    G.place_scaffold(bare, roles)
    assert P.promotion_degree(bare, "pragmatic:addition") == 0.0                                  # the lookup alone promotes nothing


# -- isolation -------------------------------------------------------------------------------------------------------------------------------------------

def test_it_imports_nothing_from_aurora_nothing_running_imports_it_and_no_degree_meets_a_cut_off():
    tree = ast.parse(open(S.__file__, encoding="utf-8").read())
    assert [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)) and "aurora" in ast.dump(n)] == []
    bad = [1 for n in ast.walk(tree) if isinstance(n, ast.Compare) for op, r in zip(n.ops, n.comparators)
           if isinstance(op, (ast.Gt, ast.GtE, ast.Lt, ast.LtE)) and isinstance(r, ast.Constant) and isinstance(r.value, float) and r.value != 0.0]
    assert bad == []
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hits = []
    for base, _, files in os.walk(root):
        if any(x in base for x in (".git", "tests", "scripts", "aurora_state", "node_modules")):
            continue
        for f in files:
            if f.endswith(".py") and f not in ("crystal_substitutability.py", "aurora_lexical_structure.py", "crystal_runtime.py", "aurora_word_use.py") and re.search(r"(from|import)\s+[\w.]*crystal_substitutability", open(os.path.join(base, f), encoding="utf-8", errors="ignore").read()):
                hits.append(f)
    assert hits == []


# -- the rules, one at a time --------------------------------------------------------------------------------------------------------------------------

def feed(rows, reps=1):
    p = S.ContextProfiles()
    for _ in range(reps):
        for r in rows:
            p.observe(r)
    return p


def test_two_words_seen_once_in_identical_places_have_not_earned_a_match_and_do_with_every_sighting():
    once = feed([["a", "w1", "b"], ["a", "w2", "b"]])
    many = feed([["a", "w1", "b"], ["a", "w2", "b"]], reps=100)
    assert once.similarity("w1", "w2") < 0.05 and many.similarity("w1", "w2") > 0.8


def test_alike_on_one_side_only_is_not_standing_in():
    p = feed([["a", "w1", "x"], ["a", "w2", "y"]], reps=100)                         # the same before, different after
    assert p.similarity("w1", "w2") == pytest.approx(0.0, abs=1e-9)


def test_breadth_counts_distinct_places_on_either_side_not_how_often_and_likeness_adds_how_often():
    rows = [["a%d" % i, "w", "b%d" % i] for i in range(10)]
    few, lots = feed(rows, reps=1), feed(rows, reps=50)
    assert few.distinct_contexts("w") == lots.distinct_contexts("w") == 20 and few.breadth("w") == pytest.approx(lots.breadth("w"))
    assert lots.function_likeness("w") > few.function_likeness("w")
    right_only = feed([["fixed", "w1", "r%d" % i] for i in range(30)] + [["fixed", "w2", "r0"]] * 30)
    assert right_only.breadth("w1") > right_only.breadth("w2")


def test_a_class_is_more_of_one_the_more_substitutes_it_has_all_else_alike():
    rows = [["a", "w%d" % i, "b"] for i in range(10)]
    p = feed(rows, reps=60)
    two = S.class_degree(p, "w0", {"w1": p.similarity("w0", "w1"), "w2": p.similarity("w0", "w2")})
    ten = S.class_degree(p, "w0", {"w%d" % i: p.similarity("w0", "w%d" % i) for i in range(1, 10)})
    assert 0.0 < two < ten < 1.0


def test_a_member_that_belongs_only_slightly_barely_disturbs_how_alike_the_class_is():
    p = feed([["a", "w1", "b"], ["a", "w2", "b"], ["a", "w3", "b"], ["q", "odd", "r"]], reps=80)
    full = S.class_degree(p, "w1", {"w2": 0.9, "w3": 0.9, "odd": 0.9})
    faint = S.class_degree(p, "w1", {"w2": 0.9, "w3": 0.9, "odd": 0.02})
    assert faint > full > 0.0


def test_the_class_as_the_crystals_take_it_holds_the_exemplar_fully_and_each_substitute_at_its_similarity():
    assert S.class_members("and", {"or": 0.62, "but": 0.4}) == {"and": 1.0, "or": 0.62, "but": 0.4}


def test_the_same_members_belonging_more_make_more_of_a_class_because_the_mass_is_more():
    p = feed([["a", "w1", "b"], ["a", "w2", "b"]], reps=80)
    weak = S.class_degree(p, "w0", {"w1": 0.1, "w2": 0.1})
    strong = S.class_degree(p, "w0", {"w1": 0.9, "w2": 0.9})
    assert 0.0 < weak < strong < 1.0


def test_memory_is_bounded_by_dropping_the_least_seen_and_the_most_seen_survive():
    p = S.ContextProfiles(max_words=40, max_contexts=8)
    for i in range(400):
        p.observe(["common", "w%d" % i, "common"])
        p.observe(["a%d" % i, "hub", "b%d" % i])
    assert len(p.vocabulary()) <= 50 and p.count("common") == 800 and p.count("hub") == 400
    assert p.distinct_contexts("hub") <= 2 * 10                                         # each side held to its limit (plus the quarter allowed before a trim)
