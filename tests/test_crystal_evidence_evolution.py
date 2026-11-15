# Authors: Sunni (Sir) Morningstar & Cael Devo
"""A crystal grows by what it has been through (counted evidence, as degrees), not by how many facets or uses it has accumulated (Sir, 2026-11-15)."""
import pytest

from aurora_dimensional_systems import Crystal, CrystalFacet, CrystalLevel
from aurora_internal import crystal_facets as F, crystal_maturity as M, crystal_weave as W
from aurora_internal.crystal_associations import AssociationStore


def crystal(level=CrystalLevel.BASE, facets=0, usage=0, fk=0, maturity=None):
    c = Crystal(crystal_id="c1", concept="x", level=level)
    for i in range(facets):
        c.add_facet(f"role{i}", {"v": i}, confidence=0.5)
    for i in range(fk):
        c.add_facet(f"fk:kind{i}", {"entries": []}, confidence=0.9)
    c.usage_count = usage
    c.maturity = maturity
    return c


RICH = {"associative": 40.0, "abstract": 0.9, "temporal": 0.9, "cognitive": 0.9, "recursive": 0.9}


# -- with evidence recorded, evidence decides and counts do not ----------------------------------------------------------------------------------

def test_a_crystal_with_evidence_grows_on_it_and_one_with_none_does_not():
    assert crystal(maturity={"associative": 40.0}).can_evolve() is True
    assert crystal(maturity={"associative": 0.0}).can_evolve() is False


def test_facet_and_usage_counts_are_not_consulted_once_evidence_is_recorded():
    busy = crystal(facets=30, usage=5000, maturity={"associative": 0.0, "abstract": 0.0})
    assert busy.can_evolve() is False                                             # the old rule would have said yes
    quiet = crystal(facets=0, usage=0, maturity={"associative": 40.0})
    assert quiet.can_evolve() is True                                             # the old rule would have said no


def test_the_top_level_never_grows_and_each_step_needs_more_than_the_last():
    assert crystal(level=CrystalLevel.QUASI, maturity=RICH).can_evolve() is False
    mid = {"associative": 12.0, "abstract": 0.5, "temporal": 0.5, "cognitive": 0.5}
    assert crystal(level=CrystalLevel.BASE, maturity=mid).can_evolve() is True
    assert crystal(level=CrystalLevel.COMPOSITE, maturity=mid).can_evolve() is False   # level 3 needs abstraction, recurrence and consequence met too
    assert crystal(level=CrystalLevel.COMPOSITE, maturity=RICH).can_evolve() is True


def test_evolve_follows_the_evidence_one_level_at_a_time():
    c = crystal(maturity=RICH)
    assert c.evolve() is True and c.level == CrystalLevel.COMPOSITE
    assert c.evolve() is True and c.level == CrystalLevel.FULL_CONCEPT
    c.maturity = {"associative": 0.0}
    assert c.evolve() is False and c.level == CrystalLevel.FULL_CONCEPT


def test_the_standing_rises_smoothly_and_is_read_as_a_class_exactly_once():
    xs = [M.standing_next({"associative": a}, 1) for a in (0.0, 1.0, 3.0, 5.0, 10.0, 40.0, 400.0)]
    assert all(b > a for a, b in zip(xs, xs[1:])) and xs[0] == 0.0 and xs[-1] < 1.0 + 1e-9
    assert max(b - a for a, b in zip(xs, xs[1:])) < 0.4                            # no cliff in the standing itself
    flips = [M.ready_to_grow({"associative": a / 4.0}, 1) for a in range(0, 200)]
    assert flips == sorted(flips) and flips[0] is False and flips[-1] is True      # one change, upward, as evidence accumulates


# -- not yet looked at: the earlier rule, minus the derived facets -------------------------------------------------------------------------------

def test_a_crystal_nobody_has_looked_at_keeps_the_earlier_rule():
    assert crystal(facets=3, usage=10).can_evolve() is True
    assert crystal(facets=2, usage=10).can_evolve() is False and crystal(facets=3, usage=9).can_evolve() is False


def test_facets_placed_from_the_weave_never_count_toward_the_earlier_rule():
    assert crystal(facets=0, usage=500, fk=12).can_evolve() is False
    assert crystal(facets=3, usage=10, fk=12).can_evolve() is True                 # its own facets still count as before


# -- the points persist, and old files still load --------------------------------------------------------------------------------------------------

def test_maturity_survives_save_and_load_and_an_old_file_has_none():
    c = crystal(maturity={"associative": 7.5, "abstract": 0.4, "emotional": None})
    back = Crystal.from_dict(c.to_dict())
    assert back.maturity == {"associative": 7.5, "abstract": 0.4, "emotional": None}
    d = c.to_dict()
    d.pop("maturity")
    assert Crystal.from_dict(d).maturity is None


# -- the points come only from counted evidence -------------------------------------------------------------------------------------------------------

def ev(book, concept, key, *, basis="observed", ctx=None, cons=None, occ="tested", ref=None):
    book.add(concept, "relation", key, {"k": key}, ref=ref or f"r:{concept}:{key}:{basis}:{occ}", source="conversation", basis=basis, strength=0.6,
             occurrence_class=occ, context=ctx, consequence=cons)


def test_association_comes_from_the_counted_ties_and_abstraction_and_recurrence_from_distinct_contexts_and_sessions():
    s, b = AssociationStore(), F.FacetBook()
    for i in range(4):
        s.add("tea", f"o{i}", "related_to", ref=f"t{i}", source="conversation", strength=0.5)
    s.add("tea", "ghost", "related_to", ref="g", source="backfill_role_heuristic", strength=1.0)      # not counted
    for i, sess in enumerate(("s1", "s1", "s2")):
        ev(b, "tea", f"k{i}", ctx={"session": sess, "n": i})
    p = W.maturity_points("tea", s, b)
    assert p["associative"] == pytest.approx(2.0)
    assert p["abstract"] == pytest.approx(M.degree(3, M.REF_ABSTRACT)) and p["temporal"] == pytest.approx(M.degree(2, M.REF_TEMPORAL))
    assert W.maturity_points("nothing", s, b)["associative"] == 0.0


def test_only_a_consequence_shown_outside_her_own_simulation_raises_the_cognitive_point():
    s, b = AssociationStore(), F.FacetBook()
    ext = {"world": "external", "n": 1}
    ev(b, "a", "k1", ctx=ext, cons={"target": "t"}, occ="tested")
    ev(b, "a", "k2", ctx={"world": "internal"}, cons={"target": "t"}, occ="tested")
    ev(b, "a", "k3", ctx=ext, cons={"target": "t"}, occ="imagined", basis="supposed")           # not counted at all
    ev(b, "a", "k4", ctx=ext, cons=None, occ="tested")                                          # no consequence witnessed: not in the share
    assert W.maturity_points("a", s, b)["cognitive"] == pytest.approx(0.5)
    ev(b, "a", "k5", ctx=ext, cons={"target": "t"}, occ="tested", basis="told")                 # she was told it was tested: counted, but not witnessed by her
    assert W.maturity_points("a", s, b)["cognitive"] == pytest.approx(1 / 3)
    ev(b, "z", "k", ctx=ext, cons={"target": "t"}, occ="heard")                                  # heard, not lived externally
    assert W.maturity_points("z", s, b)["cognitive"] == 0.0


def test_the_recursive_point_follows_how_far_the_members_have_themselves_grown():
    s, b = AssociationStore(), F.FacetBook()
    for m in ("apple", "pear"):
        s.add(m, "fruit", "is_a", ref=f"{m}-fruit", source="conversation", strength=0.9)
    low = W.maturity_points("fruit", s, b)["recursive"]
    for i in range(12):
        s.add("apple", f"x{i}", "related_to", ref=f"a{i}", source="conversation", strength=0.9)
    assert W.maturity_points("fruit", s, b)["recursive"] > low > 0.0
    assert W.maturity_points("apple", s, b)["recursive"] == 0.0                                  # holds no members


def test_the_writer_sets_the_points_and_a_dry_run_changes_nothing():
    s, b = AssociationStore(), F.FacetBook()
    for i in range(30):
        s.add("tea", f"o{i}", "related_to", ref=f"t{i}", source="conversation", strength=0.9)
    c1, c2 = Crystal(crystal_id="c1", concept="tea"), crystal(facets=9, usage=900)          # c1 has the evidence; c2 has only counts
    c2.crystal_id, c2.concept = "c2", "idle"
    cs = {"c1": c1, "c2": c2}
    r = W.apply_maturity(s, b, {"tea": "c1", "idle": "c2", "nocrystal": "zz"}, cs)
    assert r == {"crystals": 2, "ready_to_grow": 1, "ready_by_counts_but_not_by_evidence": 1, "dry_run": True} and c1.maturity is None and c2.maturity is None
    assert c2.can_evolve() is True                                                                # by counts, today
    W.apply_maturity(s, b, {"tea": "c1", "idle": "c2"}, cs, dry_run=False)
    assert c1.maturity["associative"] > 20.0 and c2.maturity["associative"] == 0.0
    assert c1.can_evolve() is True and c2.can_evolve() is False                                    # evidence now decides: counts no longer carry c2
