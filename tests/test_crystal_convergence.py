# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Build plan P2: wholes converge by degree, never by threshold; letters are found from what is associated, not listed."""
import ast
import os
import string

import pytest

from aurora_internal import crystal_convergence as C
from aurora_internal.crystal_associations import AssociationStore


def add(s, a, b, st=0.8, rtype="related_to", source="co-occurrence", ref=None):
    s.add(a, b, rtype, ref=ref or f"{a}|{b}|{rtype}|{source}", source=source, strength=st)


def letters_world(symbol_strength_for_digits=0.7):
    s = AssociationStore()
    for ch in string.ascii_lowercase:
        add(s, ch, "letter", 0.9, "is_a")
        for n in ("spelling", "word", "alphabet_order", "symbol"):
            add(s, ch, n, 0.6)
    for d in "0123456789":
        add(s, d, "number", 0.9, "is_a")
        for n in ("counting", "quantity"):
            add(s, d, n, 0.6)
        if symbol_strength_for_digits:
            add(s, d, "symbol", symbol_strength_for_digits)
    for f in ("apple", "pear", "plum"):
        add(s, f, "fruit", 0.9, "is_a")
        for n in ("eat", "sweet"):
            add(s, f, n, 0.6)
    return s


# -- the letters are found, not listed ---------------------------------------------------------------------------------------------------------

def test_the_letters_are_found_as_what_the_letter_whole_holds_not_listed():
    s = letters_world()
    held = C.members_of(s, "letter")
    assert set(held) == set(string.ascii_lowercase) and all(v == pytest.approx(0.9) for v in held.values())
    assert C.members_of(s, "number") != held and set(C.members_of(s, "fruit")) == {"apple", "pear", "plum"}
    f = C.field_of(s, "letter")
    assert all(f[c] >= held[c] for c in string.ascii_lowercase)             # held letters belong at least to the degree they are held
    assert f["symbol"] > 0.0                                                # and what the letters are associated with belongs by degree too


def test_nothing_unrelated_belongs_at_all():
    s = letters_world()
    f = C.field_of(s, "letter")
    assert all(k not in f for k in ("apple", "pear", "plum", "fruit", "eat", "sweet"))


def test_wholes_that_share_something_converge_more_than_wholes_that_share_nothing():
    s = letters_world()
    fl, fn, ff = C.field_of(s, "letter"), C.field_of(s, "number"), C.field_of(s, "fruit")
    assert C.whole_convergence(fl, fn) > C.whole_convergence(fl, ff) == 0.0
    mat = C.convergence_matrix({"letter": fl, "number": fn, "fruit": ff})
    assert mat[("letter", "number")] > mat[("fruit", "letter")] and mat[("fruit", "number")] == 0.0


# -- it is a gradient: no cliff -------------------------------------------------------------------------------------------------------------

def test_convergence_rises_smoothly_with_the_strength_of_what_is_shared():
    vals = []
    for i in range(0, 11):
        s = letters_world(symbol_strength_for_digits=i / 10)
        vals.append(C.whole_convergence(C.field_of(s, "letter"), C.field_of(s, "number")))
    assert all(b >= a - 1e-12 for a, b in zip(vals, vals[1:]))          # never goes down as the shared thing gets stronger
    assert max(b - a for a, b in zip(vals, vals[1:])) < 0.25            # and no step is a jump
    assert vals[0] == 0.0 and vals[-1] > vals[5] > vals[1] > 0.0


def test_a_very_weak_association_still_belongs_a_very_little():
    s = AssociationStore()
    add(s, "hub", "strong", 0.9)
    add(s, "hub", "faint", 0.001)
    f = C.field_of(s, "hub")
    assert 0.0 < f["faint"] < 0.01 < f["strong"]                         # present, in proportion; nothing was cut off


def test_the_top_limit_only_limits_what_is_returned_not_what_belongs():
    s = letters_world()
    full = C.field_of(s, "letter")
    cut = C.field_of(s, "letter", top=5)
    assert len(cut) == 5 and all(cut[k] == full[k] for k in cut)
    assert set(cut) == set(sorted(full, key=lambda k: -full[k])[:5])


# -- only what is counted can converge ------------------------------------------------------------------------------------------------------

def test_associations_that_are_only_labels_make_nothing_converge():
    s = letters_world(symbol_strength_for_digits=0.0)
    before = C.whole_convergence(C.field_of(s, "letter"), C.field_of(s, "number"))
    for d in "0123456789":
        for n in ("spelling", "word", "alphabet_order", "symbol"):
            add(s, d, n, 1.0, source="backfill_role_heuristic")           # digits are LABELLED like letters, nothing more
    after = C.whole_convergence(C.field_of(s, "letter"), C.field_of(s, "number"))
    assert before == after == 0.0


def test_recurrence_earns_the_convergence_a_label_could_not():
    s = letters_world(symbol_strength_for_digits=0.0)
    for d in "0123456789":
        add(s, d, "symbol", 0.9, source="backfill_role_heuristic")
    assert C.whole_convergence(C.field_of(s, "letter"), C.field_of(s, "number")) == 0.0
    for d in "0123456789":
        add(s, d, "symbol", 0.9, source="co-occurrence")
    assert C.whole_convergence(C.field_of(s, "letter"), C.field_of(s, "number")) > 0.0


# -- the quantities themselves ----------------------------------------------------------------------------------------------------------------

def test_concept_convergence_is_symmetric_in_range_and_extremes():
    s = AssociationStore()
    for n in ("x", "y", "z"):
        add(s, "a", n, 0.7)
        add(s, "b", n, 0.7)
        add(s, "c", "other", 0.7)
    assert C.convergence(s, "a", "b") == pytest.approx(1.0)               # associated with the same things in the same proportion
    assert C.convergence(s, "a", "c") == 0.0
    s.add("a", "x", "related_to", ref="weaker", source="co-occurrence", strength=0.1)   # a is now a little less strongly tied to x than b is
    v = C.convergence(s, "a", "b")
    assert v == C.convergence(s, "b", "a") and 0.0 < v < 1.0


def test_two_concepts_are_not_made_to_converge_by_being_associated_with_each_other():
    s = AssociationStore()
    add(s, "a", "b", 1.0)
    assert C.convergence(s, "a", "b") == 0.0                              # each other is left out of the comparison


def test_a_more_general_whole_is_the_weighted_blend_of_the_wholes():
    f = {"x": 1.0, "y": 0.5}
    g = {"y": 1.0, "z": 0.5}
    gen = C.general_field({"f": f, "g": g})
    assert gen == {"x": 0.5, "y": 0.75, "z": 0.25}                        # y, in both, belongs more than x or z, in one each
    heavy = C.general_field({"f": f, "g": g}, {"f": 3.0, "g": 1.0})
    assert heavy["x"] == pytest.approx(0.75) and heavy["z"] == pytest.approx(0.125)
    assert C.general_field({}) == {} and C.general_field({"f": f}, {"f": 0.0}) == {}


def test_the_general_whole_of_letters_and_numbers_contains_what_they_share_most():
    s = letters_world()
    fields = {"letter": C.field_of(s, "letter"), "number": C.field_of(s, "number")}
    gen = C.general_field(fields)
    assert gen["symbol"] > gen["spelling"] and gen["symbol"] > gen["counting"]    # shared by both, so it belongs most


# -- reads only, and isolated ---------------------------------------------------------------------------------------------------------------

def test_nothing_is_changed_by_reading():
    s = letters_world()
    before = s.to_dict()
    C.field_of(s, "letter")
    C.convergence(s, "a", "b")
    C.convergence_matrix({"l": C.field_of(s, "letter"), "n": C.field_of(s, "number")})
    assert s.to_dict() == before


def test_the_module_has_no_numeric_cutoff_to_compare_against():
    tree = ast.parse(open(C.__file__, encoding="utf-8").read())
    comps = [n for n in ast.walk(tree) if isinstance(n, ast.Compare)]
    bad = []
    for n in comps:
        for op, right in zip(n.ops, n.comparators):
            if isinstance(op, (ast.Gt, ast.GtE, ast.Lt, ast.LtE)) and isinstance(right, ast.Constant) and isinstance(right.value, float) \
                    and right.value not in (0.0,):
                bad.append(ast.dump(n)[:80])
    assert bad == []                                                        # only comparisons with zero (empty or absent), never a bar to clear


def test_only_the_association_store_is_imported_and_nothing_running_imports_it():
    tree = ast.parse(open(C.__file__, encoding="utf-8").read())
    mods = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module and n.module.startswith("aurora")}
    assert mods == {"aurora_internal.crystal_associations"}
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hits = []
    for base, _, files in os.walk(root):
        if any(x in base for x in (".git", "tests", "scripts", "aurora_state", "node_modules")):
            continue
        for f in files:
            if f.endswith(".py") and f not in ("crystal_convergence.py", "crystal_weave.py"):
                if "crystal_convergence" in open(os.path.join(base, f), encoding="utf-8", errors="ignore").read():
                    hits.append(f)
    assert hits == []


def test_being_tied_to_the_hub_and_converging_with_it_pull_together():
    s = AssociationStore()
    add(s, "h", "m", 0.5)
    for n in ("n", "p"):
        add(s, "h", n, 0.6)
    for n in ("n", "q"):
        add(s, "m", n, 0.6)
    assert C.convergence(s, "h", "m") == pytest.approx(0.5)
    assert C.field_of(s, "h")["m"] == pytest.approx(0.75)                  # 1 - (1 - 0.5)(1 - 0.5): more than either alone


def test_concepts_tied_to_each_other_and_to_the_same_things_converge_fully():
    s = AssociationStore()
    add(s, "a", "b", 1.0)
    add(s, "a", "x", 0.7)
    add(s, "b", "x", 0.7)
    assert C.convergence(s, "a", "b") == pytest.approx(1.0)               # the tie between them is not part of what they are compared on
