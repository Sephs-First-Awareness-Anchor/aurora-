# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Inward growth: a complex crystal's aspects are held inside it as inner layers (quasi-recursive, finer each step in), not spawned as more crystals."""
import ast
import json
import os
import re

import pytest

from aurora_dimensional_systems import Crystal, CrystalLevel
from aurora_internal import crystal_interior as I, crystal_maturity as M
from aurora_internal.crystal_associations import AssociationStore


def add(s, a, b, st=0.8, t="related_to", source="co-occurrence"):
    s.add(a, b, t, ref=f"{a}|{b}|{t}|{source}", source=source, strength=st)


def bank():
    """`bank` has two sides: what is done with money, and the edge of a river.  Each member is tied to its own side's things; the money side itself falls into
    two closer groups (borrowing, saving) that share some of what they are tied to."""
    s = AssociationStore()
    for m in ("loan", "mortgage", "credit"):                 # borrowing
        add(s, "bank", m, 0.9)
        for x in ("interest", "finance", "money", "debt", "payments"):
            add(s, m, x, 0.8)
    for m in ("deposit", "savings", "cash"):                 # saving
        add(s, "bank", m, 0.8)
        for x in ("interest", "finance", "money", "balance", "account"):
            add(s, m, x, 0.8)
    for m in ("shore", "mud", "current"):                    # the river
        add(s, "bank", m, 0.7)
        for x in ("water", "flow", "reeds"):
            add(s, m, x, 0.8)
    return s


def complex_crystal(concept="bank", points=None):
    c = Crystal(crystal_id="c_" + concept, concept=concept)
    c.maturity = points if points is not None else {"associative": 60.0, "abstract": 0.95, "temporal": 0.95, "cognitive": 0.9, "recursive": 0.9, "emotional": None, "polarity": None}
    return c


# -- the aspects --------------------------------------------------------------------------------------------------------------------------------------

def test_the_things_it_is_tied_to_fall_into_the_sides_they_belong_to():
    a = I.aspects(bank(), "bank")
    sides = sorted(sorted(g["members"]) for g in a)
    assert any(set(side) == {"shore", "mud", "current"} for side in sides)
    money = [g for g in a if "loan" in g["members"]][0]
    assert {"loan", "mortgage", "credit", "deposit", "savings", "cash"} == set(money["members"])         # one side at the first resolution
    assert not any("shore" in g["members"] and "loan" in g["members"] for g in a)
    assert all(0.0 < g["unity"] <= 1.0 and g["mass"] > 0 for g in a)


def test_one_tie_alone_is_not_an_aspect_and_ties_with_nothing_in_common_do_not_join():
    s = AssociationStore()
    add(s, "x", "a")
    assert I.aspects(s, "x") == []
    add(s, "x", "b")
    add(s, "a", "p")
    add(s, "b", "q")
    assert I.aspects(s, "x") == []                                   # two ties, tied to different things: two lone members, no group


def test_the_resolution_gets_finer_with_each_step_in():
    assert [I.resolution(d) for d in range(4)] == [0.5, 0.75, 0.875, 0.9375]


# -- the layers: quasi-recursive ---------------------------------------------------------------------------------------------------------------------

def test_a_side_falls_into_closer_groups_inside_it_at_a_finer_resolution():
    ls = I.layers(bank(), "bank")
    money = [l for l in ls if "loan" in l["members"]][0]
    inner = sorted(sorted(x["members"]) for x in money["inner"])
    assert inner == [["cash", "deposit", "savings"], ["credit", "loan", "mortgage"]]
    assert all(x["depth"] == 1 and set(x["members"]) < set(money["members"]) for x in money["inner"])
    river = [l for l in ls if "shore" in l["members"]][0]
    assert river["inner"] == []                                      # nothing finer separates them: no layer that only repeats the whole


def test_the_depth_is_bounded_and_found_from_what_the_evidence_still_separates():
    assert I.depth_of(None) == 0 and I.depth_of({"layers": []}) == 0
    assert I.depth_of({"layers": I.layers(bank(), "bank")}) == 2
    assert I.depth_of({"layers": [{"inner": [{"inner": [{"inner": []}]}]}]}) == 3


def test_a_layers_weight_rises_with_how_single_it_is_how_much_it_holds_and_the_crystals_standing():
    base = I.layers(bank(), "bank", 1.0)
    half = I.layers(bank(), "bank", 0.5)
    for a, b in zip(base, half):
        assert b["weight"] == pytest.approx(a["weight"] / 2, abs=1e-5)
        assert a["weight"] == pytest.approx(a["unity"] * a["mass"] / (a["mass"] + I.REF_LAYER_MASS), abs=1e-5)
    s = bank()
    for m in ("a1", "a2", "a3", "a4"):                              # more tied to the same things: more mass in the river side
        add(s, "bank", m, 0.9)
        for x in ("water", "flow", "reeds"):
            add(s, m, x, 0.8)
    heavier = [l for l in I.layers(s, "bank") if "shore" in l["members"]][0]
    assert heavier["mass"] > [l for l in base if "shore" in l["members"]][0]["mass"]
    assert heavier["weight"] > [l for l in base if "shore" in l["members"]][0]["weight"]


# -- standing at the top level is what lets a crystal grow inward ------------------------------------------------------------------------------------

def test_how_far_a_crystal_grows_inward_follows_how_fully_it_stands_at_the_top_level():
    assert I.standing(Crystal(crystal_id="n", concept="n")) == 0.0                                  # never looked at
    low = complex_crystal(points={"associative": 2.0, "abstract": 0.1, "temporal": 0.0, "cognitive": 0.0, "recursive": 0.0})
    hi = complex_crystal()
    assert 0.0 <= I.standing(low) < I.standing(hi) <= 1.0
    assert I.standing(hi) == pytest.approx(M.memberships(hi.maturity)[4])


def test_a_crystal_with_no_standing_grows_nothing_and_a_complex_one_grows_the_interior_it_earned():
    s = bank()
    crystals = {"b": complex_crystal(), "z": Crystal(crystal_id="z", concept="z")}
    crystals["z"].maturity = {"associative": 0.0, "abstract": 0.0, "temporal": 0.0, "cognitive": 0.0, "recursive": 0.0}
    idx = {"bank": "b", "z": "z"}
    r = I.apply_to_crystals(s, idx, crystals, dry_run=True)
    assert r["crystals_with_interior"] == 1 and r["dry_run"] is True and crystals["b"].interior == {}          # dry run changes nothing
    r = I.apply_to_crystals(s, idx, crystals, dry_run=False)
    assert r["crystals_with_interior"] == 1 and r["deepest"] == 2 and r["layers"] == 2
    assert crystals["z"].interior == {}
    inner = crystals["b"].interior
    assert inner["depth"] == 2 and inner["standing"] == pytest.approx(I.standing(crystals["b"]), abs=1e-5) and len(inner["layers"]) == 2


def test_growing_inward_spawns_no_crystal_and_touches_nothing_but_the_interior():
    s = bank()
    before = json.dumps(s.to_dict(), sort_keys=True)
    crystals = {"b": complex_crystal()}
    snapshot = {k: v for k, v in crystals["b"].to_dict().items() if k != "interior"}
    I.apply_to_crystals(s, {"bank": "b"}, crystals, dry_run=False)
    assert list(crystals) == ["b"] and json.dumps(s.to_dict(), sort_keys=True) == before
    assert {k: v for k, v in crystals["b"].to_dict().items() if k != "interior"} == snapshot
    assert crystals["b"].level == CrystalLevel.BASE


def test_it_is_additive_and_running_again_changes_nothing_more():
    s = bank()
    crystals = {"b": complex_crystal()}
    I.apply_to_crystals(s, {"bank": "b"}, crystals, dry_run=False)
    once = json.dumps(crystals["b"].interior, sort_keys=True)
    I.apply_to_crystals(s, {"bank": "b"}, crystals, dry_run=False)
    assert json.dumps(crystals["b"].interior, sort_keys=True) == once
    crystals["b"].interior["layers"].append({"anchor": "old", "members": {"old1": 0.4, "old2": 0.4}, "unity": 0.9, "mass": 0.8, "weight": 0.3, "depth": 0, "inner": []})
    crystals["b"].interior["layers"][0]["members"]["extra"] = 0.5
    I.apply_to_crystals(s, {"bank": "b"}, crystals, dry_run=False)
    anchors = {l["anchor"] for l in crystals["b"].interior["layers"]}
    assert "old" in anchors and "extra" in crystals["b"].interior["layers"][0]["members"]               # what was there stays


def test_a_stronger_value_wins_and_a_weaker_one_does_not_lower_it():
    s = bank()
    crystals = {"b": complex_crystal()}
    I.apply_to_crystals(s, {"bank": "b"}, crystals, dry_run=False)
    crystals["b"].interior["layers"][0]["weight"] = 9.0
    crystals["b"].interior["standing"] = 9.0
    I.apply_to_crystals(s, {"bank": "b"}, crystals, dry_run=False)
    assert crystals["b"].interior["layers"][0]["weight"] == 9.0 and crystals["b"].interior["standing"] == 9.0


def test_the_interior_is_kept_when_the_crystal_is_saved_and_loaded():
    s = bank()
    crystals = {"b": complex_crystal()}
    I.apply_to_crystals(s, {"bank": "b"}, crystals, dry_run=False)
    back = Crystal.from_dict(json.loads(json.dumps(crystals["b"].to_dict())))
    assert back.interior == crystals["b"].interior and I.depth_of(back.interior) == 2
    old = crystals["b"].to_dict()
    old.pop("interior")
    assert Crystal.from_dict(old).interior == {}                      # a crystal saved before this still loads


def test_the_layers_are_the_same_whatever_order_the_ties_arrived_in():
    a, b = bank(), AssociationStore()
    for (x, y, t), ev in reversed(list(bank()._links.items())):
        for ref, e in ev.items():
            b.add(x, y, t, ref=ref, source=e["source"], strength=e["strength"])
    assert json.dumps(I.layers(a, "bank"), sort_keys=True) == json.dumps(I.layers(b, "bank"), sort_keys=True)


# -- boundaries --------------------------------------------------------------------------------------------------------------------------------------

def test_it_has_no_cut_off_of_its_own_and_only_the_runtime_uses_it():
    src = open(os.path.join(os.path.dirname(__file__), "..", "aurora_internal", "crystal_interior.py"), encoding="utf-8").read()
    floats = [n.value for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Constant) and isinstance(n.value, float)]
    assert sorted(set(floats)) == [0.0, 0.5, 1.0, 3.0]               # the half in the resolution, the references, the zero/one that bound a degree
    base = os.path.join(os.path.dirname(__file__), "..", "aurora_internal")
    users = [f for f in os.listdir(base) if f.endswith(".py") and f != "crystal_interior.py"
             and re.search(r"(from|import)\s+[\w.]*crystal_interior", open(os.path.join(base, f), encoding="utf-8", errors="ignore").read())]
    assert users == ["crystal_runtime.py"]


def test_two_ties_that_are_tied_to_each_other_are_compared_by_what_else_they_share():
    s = AssociationStore()
    add(s, "x", "a")
    add(s, "x", "b")
    add(s, "a", "b", 0.9)
    add(s, "a", "c", 0.5)
    add(s, "b", "c", 0.5)
    g = I.aspects(s, "x", depth=1)
    assert len(g) == 1 and set(g[0]["members"]) == {"a", "b"}          # their link to each other is not counted as a difference between them


def test_a_crystal_with_ties_but_no_standing_is_left_without_an_interior():
    s = bank()
    z = complex_crystal(points={"associative": 0.0, "abstract": 0.0, "temporal": 0.0, "cognitive": 0.0, "recursive": 0.0})
    assert I.standing(z) == 0.0
    r = I.apply_to_crystals(s, {"bank": "z"}, {"z": z}, dry_run=False)
    assert r["crystals_with_interior"] == 0 and z.interior == {}


def test_a_member_held_more_strongly_than_now_keeps_its_strength():
    s = bank()
    crystals = {"b": complex_crystal()}
    I.apply_to_crystals(s, {"bank": "b"}, crystals, dry_run=False)
    layer = [l for l in crystals["b"].interior["layers"] if "loan" in l["members"]][0]
    layer["members"]["loan"] = 5.0
    I.apply_to_crystals(s, {"bank": "b"}, crystals, dry_run=False)
    assert [l for l in crystals["b"].interior["layers"] if "loan" in l["members"]][0]["members"]["loan"] == 5.0
