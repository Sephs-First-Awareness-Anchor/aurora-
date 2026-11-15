# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Placing what she records, takes in and puts out into the facets of the right concept: once, with every occasion attached, by degree."""
import ast
import os
import re

import pytest

from aurora_internal import crystal_facets as F
from aurora_internal.crystal_associations import AssociationStore, project_assertions


def add(b, concept="sunni", kind="definition", key="k", ref="r1", **kw):
    return b.add(concept, kind, key, kw.pop("content", {"t": 1}), ref=ref, **kw)


# -- held once, with every occasion attached ---------------------------------------------------------------------------------------------------

def test_the_same_thing_met_again_adds_an_occasion_not_a_copy():
    b = F.FacetBook()
    for i in range(50):
        add(b, ref=f"turn{i}", source="told")
    t = b.totals()
    assert t == {"concepts": 1, "entries": 1, "occasions": 50}
    assert b.facets_for("sunni")["definition"][0]["contexts"] == 50


def test_the_same_occasion_twice_is_one_occasion():
    b = F.FacetBook()
    add(b, ref="x", source="told")
    add(b, ref="x", source="told")
    assert b.totals()["occasions"] == 1


def test_unusable_placements_are_refused():
    b = F.FacetBook()
    assert add(b, kind="not_a_kind") is False and add(b, concept="") is False and add(b, ref="") is False
    assert b.totals()["entries"] == 0


def test_content_key_is_stable_and_ignores_case_and_spacing():
    assert F.content_key("My  Creator") == F.content_key("my creator") != F.content_key("my creators")


# -- degree is a gradient over counted evidence only ---------------------------------------------------------------------------------------------

def test_more_counted_occasions_always_mean_a_stronger_entry_and_never_reach_a_ceiling():
    b, ds = F.FacetBook(), []
    for i in range(30):
        add(b, ref=f"r{i}", source="told", strength=0.3)
        ds.append(b.degree("sunni", "definition", "k"))
    assert all(y > x for x, y in zip(ds, ds[1:])) and ds[-1] < 1.0 and max(y - x for x, y in zip([0.0] + ds, ds)) <= 0.3 + 1e-9


def test_uncounted_bases_are_kept_but_give_no_degree():
    b = F.FacetBook()
    for i, src in enumerate(["research", "backfill_role_heuristic", "seeded", "overheard", ""]):
        add(b, ref=f"r{i}", source=src)
    assert b.degree("sunni", "definition", "k") == 0.0
    assert b.facets_for("sunni") == {} and b.facets_for("sunni", include_uncounted=True)["definition"][0]["uncounted"] == 5


def test_a_dream_or_overheard_occasion_never_adds_to_what_a_told_one_earned():
    b = F.FacetBook()
    add(b, ref="t", source="told", strength=0.5)
    before = b.degree("sunni", "definition", "k")
    add(b, ref="d", source="dreamed", occurrence_class="dreamed", strength=1.0)
    add(b, ref="o", source="overheard", strength=1.0)
    assert b.degree("sunni", "definition", "k") == before


def test_evidence_against_lowers_it_in_proportion():
    ds = []
    for against in (0.0, 0.25, 0.5, 1.0):
        b = F.FacetBook()
        add(b, ref="a", source="told", strength=0.8)
        if against:
            add(b, ref="n", source="told", strength=against, polarity=-1)
        ds.append(b.degree("sunni", "definition", "k"))
    assert ds[0] == pytest.approx(0.8) and ds[0] > ds[1] > ds[2] > ds[3] == 0.0


def test_an_occasion_that_stood_for_many_exposures_weighs_that_many_times():
    b1, b2 = F.FacetBook(), F.FacetBook()
    add(b1, ref="a", source="told", strength=0.3, weight=1)
    add(b2, ref="a", source="told", strength=0.3, weight=4)
    assert b2.degree("sunni", "definition", "k") == pytest.approx(1 - 0.7 ** 4)
    assert b2.degree("sunni", "definition", "k") > b1.degree("sunni", "definition", "k") == pytest.approx(0.3)


def test_the_strongest_come_first_and_top_only_limits_what_is_returned():
    b = F.FacetBook()
    for i in range(10):
        add(b, key=f"k{i}", ref=f"r{i}", source="told", strength=(i + 1) / 10)
    rows = b.facets_for("sunni", top=3)["definition"]
    assert [r["key"] for r in rows] == ["k9", "k8", "k7"] and len(b.facets_for("sunni")["definition"]) == 10


# -- associations land by what their type means ----------------------------------------------------------------------------------------------

def store():
    s = AssociationStore()
    for t, a, b in (("is_a", "a", "letter"), ("causes", "rain", "wet"), ("enables", "key", "door"), ("context_of", "kitchen", "cooking"),
                    ("opposite_of", "hot", "cold"), ("related_to", "tea", "cup"), ("like", "mara", "tea")):
        s.add(a, b, t, ref=f"{a}{b}", source="co-occurrence", strength=0.8)
    return s


def test_each_type_puts_the_right_kind_at_each_end():
    b = F.FacetBook()
    F.place_associations(b, store())
    kinds = lambda c: {k: [r["content"]["other"] for r in v] for k, v in b.facets_for(c).items()}
    assert kinds("a") == {"generalization": ["letter"]} and kinds("letter") == {"particular": ["a"]}
    assert kinds("rain") == {"effect": ["wet"]} and kinds("wet") == {"cause": ["rain"]}
    assert kinds("key") == {"effect": ["door"]} and kinds("door") == {"condition": ["key"]}
    assert kinds("cooking") == {"context": ["kitchen"]} and kinds("kitchen") == {"relation": ["cooking"]}
    assert kinds("hot") == {"comparison": ["cold"]} and kinds("cold") == {"comparison": ["hot"]}
    assert kinds("mara") == {"relation": ["tea"]} and {"relation"} == set(kinds("tea")) and set(kinds("tea")["relation"]) == {"cup", "mara"}


def test_the_direction_of_what_was_said_is_kept():
    b = F.FacetBook()
    F.place_associations(b, store())
    assert b.facets_for("mara")["relation"][0]["content"]["direction"] == "out"
    assert [r["content"]["direction"] for r in b.facets_for("tea")["relation"] if r["content"]["type"] == "like"] == ["in"]


def test_placing_associations_twice_changes_nothing():
    b = F.FacetBook()
    F.place_associations(b, store())
    once = b.to_dict()
    F.place_associations(b, store())
    assert b.to_dict() == once


def test_an_association_that_is_argued_over_also_places_an_open_entry_as_strong_as_it_is_contested():
    s = project_assertions({"r": {"relation_id": "r", "source_word": "mara", "target_word": "tea", "assertion": {"predicates": {"like": {"n": 4, "denied": 2, "basis": {"told": 4}}}}}})
    b = F.FacetBook()
    F.place_associations(b, s)
    o = b.facets_for("mara")["open"][0]
    assert o["content"]["what"] == "contested" and o["degree"] == pytest.approx(1.0)
    s2 = project_assertions({"r": {"relation_id": "r", "source_word": "mara", "target_word": "tea", "assertion": {"predicates": {"like": {"n": 4, "denied": 0, "basis": {"told": 4}}}}}})
    b2 = F.FacetBook()
    F.place_associations(b2, s2)
    assert "open" not in b2.facets_for("mara")


def test_heuristic_associations_are_held_but_earn_nothing():
    s = AssociationStore()
    s.add("a", "b", "related_to", ref="1", source="backfill_role_heuristic", strength=1.0)
    b = F.FacetBook()
    F.place_associations(b, s)
    assert b.facets_for("a") == {} and b.totals()["entries"] == 2


# -- concept nodes ---------------------------------------------------------------------------------------------------------------------------------

NODE = {"word": "sunni", "role": "noun", "emotional_valence": 1.0,
        "definitions": [{"text": "My creator.", "source": "initial", "confidence": 0.3}, {"text": "A person who told me things.", "source": "told", "confidence": 0.6}],
        "usage_examples": [{"text": "Used in expression", "context": "expression", "timestamp": 1.0, "fitness": 0.8}]}


def test_a_node_places_each_definition_once_with_its_own_provenance():
    b = F.FacetBook()
    assert F.place_oets_node(b, NODE) == F.place_oets_node(b, NODE) and b.totals()["entries"] == 5
    d = b.facets_for("sunni", include_uncounted=True)["definition"]
    by = {r["content"]["text"]: r for r in d}
    assert by["My creator."]["degree"] == 0.0 and by["A person who told me things."]["degree"] == pytest.approx(0.6)   # seeded is placed, told is earned


def test_the_category_a_label_gave_is_not_counted():
    b = F.FacetBook()
    F.place_oets_node(b, NODE)
    assert "generalization" not in b.facets_for("sunni") and b.facets_for("sunni", include_uncounted=True)["generalization"][0]["content"] == {"category": "noun"}


# -- episodes, expressions, open items, abilities ----------------------------------------------------------------------------------------------

def test_an_episode_is_a_reference_not_a_quoted_copy_at_each_concept_it_involved():
    b = F.FacetBook()
    long = "word " * 200
    assert F.place_episode(b, ["sunni", "aurora"], episode_id="t42", time=1.0, summary=long, source="told") == 2
    row = b.facets_for("sunni")["episode_ref"][0]["content"]
    assert row["id"] == "t42" and len(row["summary"]) <= 160 and "text" not in row


def test_what_she_said_carries_what_it_led_to():
    b = F.FacetBook()
    F.place_expression(b, "sunni", expression_id="e1", summary="I am here", context="t42", outcome=0.7, source="observed", strength=0.7)
    ev = b._e["sunni"]["expression"]["e1"]["evidence"]["expression:e1:sunni"]
    assert ev["consequence"] == 0.7 and b.degree("sunni", "expression", "e1") == pytest.approx(0.7)


def test_open_items_and_abilities_land_in_their_own_kinds():
    b = F.FacetBook()
    F.place_open_item(b, "sunni", item_id="q1", status="open", settles="a correction", source="told")
    F.place_ability(b, "sunni", ability_id="X:ADMIT", ancestry=["X", "B"], source="observed")
    k = b.facets_for("sunni")
    assert k["open"][0]["content"]["settles"] == "a correction" and "operation" in k
    assert b._e["sunni"]["operation"]["X:ADMIT"]["evidence"]["ability:X:ADMIT:sunni"]["ancestry"] == ["X", "B"]


def test_stores_that_are_not_knowledge_are_routed_outside():
    for n, cls in (("daemon_status", "substrate"), ("runtime_faults.json", "substrate"), ("system_introspection_index", "substrate"),
                   ("evo_625_pressure_map", "frame"), ("pressure_ontology", "frame"), ("probe_battery", "instrument"), ("live_growth_assessment", "instrument")):
        assert F.classify_store(n) == cls
    assert F.classify_store("lexicon") is None and F.classify_store("aurora_oets_web") is None and F.classify_store("") is None


# -- waveform cycles ---------------------------------------------------------------------------------------------------------------------------------

def cycle(**kw):
    c = {"cycle_id": "RCRW:c1", "created_at": 5.0,
         "effective_interpretation": {"subject": "sunni", "relation": "make", "obj": "aurora"},
         "global_understanding": {"completeness": 0.8, "coherence": 0.7, "retrospective_confidence": 0.6},
         "interference": {"axis_delta": {"X": -0.1, "T": 0.2}},
         "response_wave": {"text": "I am yours", "text_hash": "h1", "relation_alignment": {"score": 0.9}},
         "wavelets": [{"primitive": "existence_admission"}]}
    c.update(kw)
    return c


def test_a_cycle_places_what_the_understanding_became_and_what_was_said_but_never_the_machinery():
    b = F.FacetBook()
    info = F.place_cycle(b, cycle(), occurrence_class="observed")
    assert info["placed"] == 5 and info["axis_delta"] == {"X": -0.1, "T": 0.2} and info["completeness"] == 0.8
    assert b.facets_for("sunni")["relation"][0]["content"] == {"type": "make", "other": "aurora", "direction": "out"}
    assert b.facets_for("aurora")["relation"][0]["content"]["direction"] == "in"
    assert b.facets_for("sunni")["relation"][0]["degree"] == pytest.approx(0.6)
    assert "existence_admission" not in str(b.to_dict())
    assert b.facets_for("sunni")["expression"][0]["degree"] == pytest.approx(0.6)
    assert b._e["sunni"]["expression"]["h1"]["evidence"]["expression:h1:sunni"]["consequence"] == 0.9


def test_a_cycle_without_a_developed_relation_places_nothing_but_still_reports_its_points():
    b = F.FacetBook()
    info = F.place_cycle(b, cycle(effective_interpretation={"subject": "", "relation": "", "obj": ""}), occurrence_class="observed")
    assert info["placed"] == 0 and b.totals()["entries"] == 0 and info["axis_delta"]


def test_a_cycle_whose_class_was_not_stated_is_kept_and_not_counted_and_the_same_cycle_twice_is_one():
    b = F.FacetBook()
    F.place_cycle(b, cycle())
    assert b.facets_for("sunni") == {}
    F.place_cycle(b, cycle())
    before = b.to_dict()
    F.place_cycle(b, cycle())
    assert b.to_dict() == before


# -- persistence ---------------------------------------------------------------------------------------------------------------------------------------

def test_it_survives_save_and_load_and_a_failed_save_leaves_the_old_file(tmp_path):
    b = F.FacetBook()
    F.place_oets_node(b, NODE)
    p = str(tmp_path / "fb.json")
    b.save(p)
    assert F.FacetBook.load(p).to_dict() == b.to_dict()
    b2 = F.FacetBook()
    b2.add("x", "definition", "k", object(), ref="r")                      # not serialisable
    with pytest.raises(TypeError):
        b2.save(p)
    assert F.FacetBook.load(p).to_dict() == b.to_dict() and [f for f in os.listdir(tmp_path) if f.endswith(".tmp")] == []
    assert F.FacetBook.load(str(tmp_path / "missing.json")).totals()["entries"] == 0


# -- the one writer ----------------------------------------------------------------------------------------------------------------------------------------

def crystals():
    from aurora_dimensional_systems import Crystal
    return {"id_s": Crystal(crystal_id="id_s", concept="sunni"), "id_l": Crystal(crystal_id="id_l", concept="letter")}


def test_apply_dry_run_changes_nothing_and_reports():
    b = F.FacetBook()
    add(b, source="told", strength=0.6)
    cr = crystals()
    r = F.apply_to_crystals(b, {"sunni": "id_s", "letter": "id_l"}, cr)
    assert r == {"crystals_touched": 1, "facets": 1, "entries": 1, "dry_run": True} and len(cr["id_s"].facets) == 0


def test_apply_writes_one_facet_per_kind_with_counted_entries_only_and_is_additive_and_idempotent():
    b = F.FacetBook()
    add(b, key="a", ref="1", source="told", strength=0.6)
    add(b, key="u", ref="2", source="research")                              # uncounted: never reaches a crystal
    add(b, kind="example", key="e", ref="3", source="told", strength=0.5)
    cr = crystals()
    idx = {"sunni": "id_s", "letter": "id_l", "ghost": "id_gone"}
    add(b, concept="ghost", ref="4", source="told")
    r = F.apply_to_crystals(b, idx, cr, dry_run=False)
    assert r["crystals_touched"] == 1 and r["facets"] == 2 and r["entries"] == 2
    roles = {f.role: f for f in cr["id_s"].facets.values()}
    assert set(roles) == {"fk:definition", "fk:example"} and [e["key"] for e in roles["fk:definition"].content["entries"]] == ["a"]
    assert roles["fk:definition"].confidence == pytest.approx(0.6) and len(cr["id_l"].facets) == 0
    snap = {f.role: (f.content, f.confidence) for f in cr["id_s"].facets.values()}
    F.apply_to_crystals(b, idx, cr, dry_run=False)
    assert {f.role: (f.content, f.confidence) for f in cr["id_s"].facets.values()} == snap and len(cr["id_s"].facets) == 2


def test_apply_merges_into_an_existing_facet_keeping_the_stronger_and_never_lowers_confidence():
    b = F.FacetBook()
    add(b, key="a", ref="1", source="told", strength=0.3)
    cr = crystals()
    cr["id_s"].add_facet("fk:definition", {"entries": [{"key": "a", "content": {"t": 1}, "degree": 0.9, "contexts": 9}, {"key": "z", "content": {}, "degree": 0.2, "contexts": 1}]}, confidence=0.9)
    F.apply_to_crystals(b, {"sunni": "id_s"}, cr, dry_run=False)
    f = next(x for x in cr["id_s"].facets.values() if x.role == "fk:definition")
    ents = {e["key"]: e for e in f.content["entries"]}
    assert ents["a"]["degree"] == 0.9 and "z" in ents and f.confidence == 0.9


def test_it_works_on_the_real_crystal_and_its_serialisation():
    from aurora_dimensional_systems import Crystal
    b = F.FacetBook()
    add(b, source="told", strength=0.6)
    cr = crystals()
    F.apply_to_crystals(b, {"sunni": "id_s"}, cr, dry_run=False)
    back = Crystal.from_dict(cr["id_s"].to_dict())
    assert [f.role for f in back.facets.values()] == ["fk:definition"]


# -- isolation ---------------------------------------------------------------------------------------------------------------------------------------------

def test_only_the_association_module_is_imported_and_nothing_running_imports_this():
    tree = ast.parse(open(F.__file__, encoding="utf-8").read())
    mods = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module and n.module.startswith("aurora")}
    assert mods == {"aurora_internal.crystal_associations"}
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hits = []
    for base, _, files in os.walk(root):
        if any(x in base for x in (".git", "tests", "scripts", "aurora_state", "node_modules")):
            continue
        for f in files:
            if f.endswith(".py") and f != "crystal_facets.py" and re.search(r"(from|import)\s+[\w.]*crystal_facets", open(os.path.join(base, f), encoding="utf-8", errors="ignore").read()):
                hits.append(f)
    assert hits == []


def test_no_degree_is_compared_with_a_cut_off():
    tree = ast.parse(open(F.__file__, encoding="utf-8").read())
    bad = [ast.dump(n)[:80] for n in ast.walk(tree) if isinstance(n, ast.Compare)
           for op, r in zip(n.ops, n.comparators)
           if isinstance(op, (ast.Gt, ast.GtE, ast.Lt, ast.LtE)) and isinstance(r, ast.Constant) and isinstance(r.value, (int, float)) and r.value not in (0, 0.0)]
    assert bad == []


def test_a_cycle_that_only_found_a_subject_or_only_a_relation_places_nothing():
    for eff in ({"subject": "sunni", "relation": "", "obj": ""}, {"subject": "", "relation": "make", "obj": "aurora"}):
        b = F.FacetBook()
        assert F.place_cycle(b, cycle(effective_interpretation=eff), occurrence_class="observed")["placed"] == 0 and b.totals()["entries"] == 0


def test_recorded_uses_go_where_they_belong_and_repeats_attach_to_one_entry():
    node = {"word": "honesty", "usage_examples": [
        {"text": "What do you think about honesty?", "context": "interaction", "timestamp": 1.0, "fitness": 0.6},
        {"text": "What do you think about honesty?", "context": "interaction", "timestamp": 2.0, "fitness": 0.6},
        {"text": "What do you think about honesty?", "context": "conversation", "timestamp": 3.0, "fitness": 0.6},
        {"text": "Used in expression (fitness=0.86)", "context": "expression", "timestamp": 4.0, "fitness": 0.86},
        {"text": "honesty is telling the truth", "context": "clarification_context", "timestamp": 5.0}]}
    b = F.FacetBook()
    F.place_oets_node(b, node)
    k = b.facets_for("honesty", include_uncounted=True)
    assert [r["contexts"] for r in k["episode_ref"]] == [3] and len(k["episode_ref"]) == 1       # one entry, three times met
    assert k["expression"][0]["contexts"] == 1 and "example" in k and set(k) == {"episode_ref", "expression", "example"}
    ev = next(iter(b._e["honesty"]["expression"].values()))["evidence"]
    assert next(iter(ev.values()))["consequence"] == 0.86
    t0 = b.totals()
    F.place_oets_node(b, node)
    assert b.totals() == t0
