# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Weaving the stores into the crystal architecture honours the evidence contract and makes links that change something."""
import ast
import os
import re

import pytest

from aurora_internal import crystal_facets as F
from aurora_internal import crystal_weave as W
from aurora_internal import evidence_qualification as Q
from aurora_internal.crystal_associations import AssociationStore


def ev(subject="mara|like|tea", basis=None, **kw):
    if kw.get("occurrence") == "derived":
        kw.setdefault("derived_from", ["input|t1|-"])
    return Q.make_event(subject, basis, t=kw.pop("t", 1), **kw)


# -- events -----------------------------------------------------------------------------------------------------------------------------------

def test_a_told_heard_event_counts_and_carries_its_occurrence_context_and_ancestry():
    b = F.FacetBook()
    e = ev(occurrence="heard", context={"world": "external"}, ancestry=["input|t1|-"], ancestry_status="traced")
    assert W.place_event(b, "tea", "evidence", "k", {"s": e["subject"]}, e)
    row = b._e["tea"]["evidence"]["k"]["evidence"][e["id"]]
    assert row["basis"] == "told" and row["occurrence_class"] == "heard" and row["ancestry"] == ["input|t1|-"] and row["context"]["world"] == "external"
    assert b.degree("tea", "evidence", "k") == pytest.approx(1.0)


@pytest.mark.parametrize("occ", ["dreamed", "imagined", "simulated", "overheard", "derived"])
def test_dreamed_imagined_simulated_overheard_and_derived_events_are_kept_and_never_counted(occ):
    b = F.FacetBook()
    e = ev(occurrence=occ)
    W.place_event(b, "tea", "evidence", "k", {}, e)
    assert b.degree("tea", "evidence", "k") == 0.0 and b.totals()["occasions"] == 1


def test_a_recollection_never_adds_what_the_original_gave():
    b = F.FacetBook()
    W.place_event(b, "tea", "evidence", "k", {}, ev(basis="told", occurrence="recalled", t=2))
    assert b.degree("tea", "evidence", "k") == 0.0 and b.totals()["occasions"] == 1       # kept, as a recollection, earning nothing
    W.place_event(b, "tea", "evidence", "k", {}, ev(occurrence="heard"))
    assert b.degree("tea", "evidence", "k") == pytest.approx(1.0)                          # the original is what earned it


def test_a_negated_event_is_evidence_against_and_an_unknown_one_is_not_upgraded():
    b = F.FacetBook()
    W.place_event(b, "tea", "evidence", "k", {}, ev(occurrence="heard"))
    W.place_event(b, "tea", "evidence", "k", {}, ev(occurrence="heard", negated=True, t=2))
    assert b.degree("tea", "evidence", "k") == 0.0
    b2 = F.FacetBook()
    W.place_event(b2, "tea", "evidence", "k", {}, ev())
    assert b2.degree("tea", "evidence", "k") == 0.0


def test_the_same_event_twice_is_one_occasion():
    b = F.FacetBook()
    e = ev(occurrence="heard")
    W.place_event(b, "tea", "evidence", "k", {}, e)
    W.place_event(b, "tea", "evidence", "k", {}, e)
    assert b.totals()["occasions"] == 1


# -- operations live in the crystals of what she was dealing with ------------------------------------------------------------------------------------

def exercise(book, occ, consequence=None, input_id="t1", concepts=("sunni", "aurora"), **kw):
    e = Q.make_event(f"input|{input_id}|-", occurrence=occ, t=1, nonce=input_id, **kw)
    return W.place_exercise(book, concepts, ability_id="X:ADMIT", input_event=e, consequence=consequence, ancestry=["NC:X>X"]), e


CONS = {"target": "pressure", "change": "relieved"}


def test_an_operation_lands_in_each_concepts_own_crystal_with_the_input_in_its_ancestry():
    b = F.FacetBook()
    n, e = exercise(b, "heard", CONS)
    assert n == 2 and set(b.concepts()) == {"sunni", "aurora"}
    ev = next(iter(b._e["sunni"]["operation"]["X:ADMIT"]["evidence"].values()))
    assert ev["ancestry"] == ["NC:X>X", e["id"]] and ev["basis"] == "observed" and ev["consequence"] == CONS


def test_more_inputs_exercising_it_means_more_and_the_same_input_twice_is_one():
    b, ds = F.FacetBook(), []
    for i in range(12):
        exercise(b, "heard", CONS, input_id=f"t{i}", concepts=("sunni",))
        ds.append(b.degree("sunni", "operation", "X:ADMIT"))
    assert all(y > x for x, y in zip(ds, ds[1:])) and ds[0] == pytest.approx(0.1) and ds[-1] == pytest.approx(1 - 0.9 ** 12)
    exercise(b, "heard", CONS, input_id="t0", concepts=("sunni",))
    assert b.totals()["occasions"] == 12


@pytest.mark.parametrize("occ", ["acted", "tested", "perceived", "read"])
def test_a_rehearsal_that_is_lived_and_whose_effect_she_witnessed_counts(occ):
    b = F.FacetBook()
    exercise(b, occ, CONS, concepts=("sunni",))
    assert b.degree("sunni", "operation", "X:ADMIT") == pytest.approx(0.1)


def test_a_lived_exercise_with_no_witnessed_effect_is_kept_not_counted():
    b = F.FacetBook()
    exercise(b, "heard", None, concepts=("sunni",))
    assert b.degree("sunni", "operation", "X:ADMIT") == 0.0 and b.totals()["occasions"] == 1


@pytest.mark.parametrize("occ", ["dreamed", "imagined", "simulated", "overheard"])
def test_a_dreamed_imagined_simulated_or_overheard_rehearsal_is_kept_and_earns_nothing(occ):
    b = F.FacetBook()
    exercise(b, occ, CONS, concepts=("sunni",))
    assert b.degree("sunni", "operation", "X:ADMIT") == 0.0 and b.totals()["occasions"] == 1
    basis = next(iter(b._e["sunni"]["operation"]["X:ADMIT"]["evidence"].values()))["basis"]
    assert basis == ("overheard" if occ == "overheard" else "supposed")                 # kept for what it is, not as an unknown


# -- conversations are lived history, from either position ---------------------------------------------------------------------------------------

ENTRY = {"timestamp": 100.0, "session_id": "s1", "user_said": "My name is Sunni, nice to meet you!", "aurora_said": "I wonder about the bright mind.",
         "topic": "creator", "emotional_tone": "playful", "importance": 0.8}


def test_what_was_said_to_her_is_told_and_what_she_said_she_witnessed_and_both_count():
    b = F.FacetBook()
    assert W.place_conversation(b, [ENTRY], ["sunni", "mind", "tea"]) == 2
    s = b._e["sunni"]["episode_ref"]["s1:100"]["evidence"]["conv:s1:100:heard:sunni"]
    m = b._e["mind"]["episode_ref"]["s1:100"]["evidence"]["conv:s1:100:spoke:mind"]
    assert s["basis"] == "told" and m["basis"] == "observed" and s["context"] == {"session": "s1", "topic": "creator", "tone": "playful"}
    assert b.degree("sunni", "episode_ref", "s1:100") == pytest.approx(0.8) and b.degree("mind", "episode_ref", "s1:100") == pytest.approx(0.8)
    assert "tea" not in b.concepts()


def test_the_conversation_is_held_as_a_reference_not_a_copy_and_twice_is_once():
    b = F.FacetBook()
    long = dict(ENTRY, user_said="sunni " + "word " * 200)
    W.place_conversation(b, [long], ["sunni"])
    assert len(b.facets_for("sunni")["episode_ref"][0]["content"]["summary"]) <= 160
    t = b.totals()
    W.place_conversation(b, [long], ["sunni"])
    assert b.totals() == t


def test_how_much_a_conversation_weighs_follows_its_importance_and_an_unrecorded_one_is_full():
    ds = []
    for imp in (0.1, 0.5, 0.9, None):
        b = F.FacetBook()
        W.place_conversation(b, [dict(ENTRY, importance=imp)], ["sunni"])
        ds.append(b.degree("sunni", "episode_ref", "s1:100"))
    assert ds == [pytest.approx(0.1), pytest.approx(0.5), pytest.approx(0.9), pytest.approx(1.0)]
    assert W.place_conversation(F.FacetBook(), [{"user_said": "sunni"}], ["sunni"]) == 0         # no time: no identity, nothing placed


def test_a_word_is_matched_as_a_whole_word_not_inside_another():
    b = F.FacetBook()
    W.place_conversation(b, [dict(ENTRY, user_said="a mindful teacup", aurora_said="")], ["mind", "tea", "cup"])
    assert b.concepts() == []                                                    # mindful, teacup: not mind, tea, cup


def test_a_relation_learned_in_conversation_is_told():
    s = AssociationStore()
    s.add("a", "b", "is_a", ref="1", source="conversation", strength=0.9)
    assert s.strength("a", "b", "is_a") == pytest.approx(0.9)


# -- where and when a representation developed, and what was associated -------------------------------------------------------------------------

LINK = {"parents": ["NC:N>N", "NC:N>T"], "created_at_tick": 65, "depth": 1, "dominant_relief_axis": "X",
        "semantic_identity": {"operation_lineage": "OP:1", "origin_signature": "T^1*N^3"}}


def test_a_development_carries_where_when_what_and_what_it_was_made_from():
    b = F.FacetBook()
    e = Q.make_event("input|turn9|-", occurrence="heard", t=500, nonce="x")
    assert W.place_development(b, ["sunni", "tea"], rep_id="L:1", record=LINK, input_event=e, associated=["NC:T>N", "cup"], consequence=CONS) == 2
    row = b.facets_for("tea")["operation"][0]
    assert row["content"] == {"id": "L:1", "parents": ["NC:N>N", "NC:N>T"], "operation_lineage": "OP:1", "signature": "T^1*N^3", "dominant_relief_axis": "X"}
    ev = next(iter(b._e["tea"]["operation"]["L:1"]["evidence"].values()))
    assert ev["context"] == {"developed_at_tick": 65, "input_time": 500, "depth": 1, "associated": ["NC:T>N", "cup"]}
    assert ev["ancestry"] == ["NC:N>N", "NC:N>T", e["id"]] and ev["basis"] == "observed"


def test_the_inputs_of_a_ledger_row_join_to_the_concepts_of_their_turns_and_nothing_is_guessed():
    row = {"by": {"lived": {"inputs": ["i1", "i2"]}, "hypothetical": {"inputs": ["i3"]}}}
    events = {"i1": {"subject": "input|turnA|-"}, "i2": {"subject": "input|turnB|-"}, "i3": {"subject": "input|turnA|-"}}
    got = W.concepts_of_inputs(row, events, {"turnA": ["sunni", "tea"]})
    assert got == {"i1": ["sunni", "tea"], "i3": ["sunni", "tea"]}                  # turnB is unknown to the join: left out
    assert W.concepts_of_inputs(row, {"i1": {"subject": "weird"}}, {"turnA": ["x"]}) == {}


# -- a waveform cycle's operations ------------------------------------------------------------------------------------------------------------------

def wcycle(admitted=False, **kw):
    c = {"cycle_id": "RCRW:c1", "effective_interpretation": {"subject": "sunni", "relation": "make", "obj": "aurora"},
         "genealogy_trace": {"parent_operation_ids": ["A:CHOOSE", "REFAB:N:OPERATOR:A"]},
         "representation_experiment_result": {"evidence_admitted": admitted, "status": "measured"}, "representation_experiment_control": {"marginal_l1": 0.4}}
    c.update(kw)
    return c


def test_the_operations_that_parented_a_cycle_land_in_the_crystals_of_what_it_was_about():
    b = F.FacetBook()
    assert W.place_cycle_operations(b, wcycle(admitted=True), occurrence_class="heard") == 4
    assert set(b.concepts()) == {"sunni", "aurora"} and set(b.facets_for("sunni")["operation"][0]["content"]) == {"id"}
    assert {r["content"]["id"] for r in b.facets_for("sunni")["operation"]} == {"A:CHOOSE", "REFAB:N:OPERATOR:A"}


def test_a_cycle_whose_experiment_was_not_admitted_keeps_its_operations_uncounted():
    b = F.FacetBook()
    W.place_cycle_operations(b, wcycle(admitted=False), occurrence_class="heard")
    assert b.facets_for("sunni") == {} and b.totals()["occasions"] == 4
    b2 = F.FacetBook()
    W.place_cycle_operations(b2, wcycle(admitted=True), occurrence_class="dreamed")
    assert b2.facets_for("sunni") == {}


def test_a_cycle_with_no_developed_relation_places_no_operations():
    b = F.FacetBook()
    assert W.place_cycle_operations(b, wcycle(effective_interpretation={"subject": "sunni", "relation": "", "obj": ""}), occurrence_class="heard") == 0 and b.totals()["entries"] == 0
    assert W.place_cycle_operations(b, wcycle(effective_interpretation={"subject": "", "relation": "", "obj": ""}), occurrence_class="heard") == 0
    assert W.place_cycle_operations(b, wcycle(effective_interpretation={"subject": "", "relation": "make", "obj": ""}), occurrence_class="heard") == 0
    assert W.place_cycle_operations(b, wcycle(cycle_id=""), occurrence_class="heard") == 0


# -- the genealogy as associations --------------------------------------------------------------------------------------------------------------

PAIRS = {"A|B": {"left_id": "A", "right_id": "B", "count": 22}, "A|C": {"left_id": "A", "right_id": "C", "count": 1}, "X|Y": {"left_id": "X", "right_id": "Y", "count": 0}}
LINKS = {"L:1": {"parents": ["A", "B"], "stats": {"count": 7}},
         "L:2": {"parents": ["A", "C"], "stats": {"count": 3}, "evidence_qualification": {"ledger": "recorded", "by_kind": {
             "lived": {"n_inputs": 2, "n_external": 1}, "hypothetical": {"n_inputs": 5, "n_external": 0}, "overheard": {"n_inputs": 4}}}}}


def test_used_together_more_often_means_a_stronger_association_by_degree():
    s = W.genealogy_associations(PAIRS, {})
    assert s.strength("A", "B", "used_with") == pytest.approx(1 - 0.9 ** 22)
    assert s.strength("A", "C", "used_with") == pytest.approx(0.1)
    assert s.strength("A", "C", "used_with") < s.strength("A", "B", "used_with")
    assert s.strength("X", "Y", "used_with") == 0.0 and len(s) == 2


def test_a_link_is_composed_of_its_parents_by_how_often_they_recurred():
    s = W.genealogy_associations({}, LINKS)
    assert s.strength("L:1", "A", "composed_of") == pytest.approx(1 - 0.9 ** 7)


def test_what_the_genealogy_qualified_by_occurrence_arrives_qualified():
    s = W.genealogy_associations({}, LINKS)
    ev = s.evidence("L:2", "A", "composed_of")
    by = {k.split(":")[-1]: v["basis"] for k, v in ev.items()}
    assert by["lived"] == "observed" and "external" not in by and by["hypothetical"] == "supposed" and by["overheard"] == "overheard"
    s2 = W.genealogy_associations({}, {"L:2": {"parents": ["A"], "stats": {"count": 0}, "evidence_qualification": LINKS["L:2"]["evidence_qualification"]}})
    assert s2.strength("L:2", "A", "composed_of") == pytest.approx(1 - 0.9 ** 2)    # two lived inputs; the external one is among them, not extra
    s3 = W.genealogy_associations({}, {"L:3": {"parents": ["A"], "stats": {"count": 0}, "evidence_qualification": {"by_kind": {"hypothetical": {"n_inputs": 9}, "overheard": {"n_inputs": 9}}}}})
    assert s3.strength("L:3", "A", "composed_of") == 0.0               # dreamed or overheard alone earns nothing, however much


def test_running_it_twice_changes_nothing():
    s = W.genealogy_associations(PAIRS, LINKS)
    once = s.to_dict()
    assert W.genealogy_associations(PAIRS, LINKS, s).to_dict() == once


# -- weaving a state directory ------------------------------------------------------------------------------------------------------------------------

def state(tmp_path):
    import json
    (tmp_path / "genealogy").mkdir()
    web = {"nodes": {"tea": {"word": "tea", "role": "noun", "definitions": [{"text": "a drink", "source": "initial", "confidence": 0.3}]}},
           "relations": {"r1": {"relation_id": "r1", "source_word": "tea", "target_word": "cup", "relation_type": "related_to", "strength": 0.8, "confidence": 0.9,
                                "source_of_knowledge": "co-occurrence"},
                         "r2": {"relation_id": "r2", "source_word": "tea", "target_word": "drink", "relation_type": "is_a", "strength": 0.9, "confidence": 0.9,
                                "source_of_knowledge": "co-occurrence"}}}
    (tmp_path / "aurora_oets_web.json").write_text(json.dumps(web))
    (tmp_path / "genealogy" / "pair_stats.json").write_text(json.dumps(PAIRS))
    (tmp_path / "genealogy" / "links.json").write_text(json.dumps(LINKS))
    return str(tmp_path)


def test_weaving_a_state_directory_reads_every_store_and_changes_none(tmp_path):
    d = state(tmp_path)
    before = {p.name: p.read_bytes() for p in tmp_path.rglob("*.json")}
    r = W.weave(d)
    assert {p.name: p.read_bytes() for p in tmp_path.rglob("*.json")} == before
    s = r["summary"]
    assert s["oets"] == {"nodes": 1, "relations": 2} and s["genealogy"] == {"pairs": 3, "links": 2, "links_with_qualification": 1}
    assert r["book"].facets_for("tea")["particular" if False else "generalization"][0]["content"]["other"] == "drink"
    assert r["book"].facets_for("A")["relation"] and r["store"].strength("A", "B", "used_with") > 0


def test_weaving_includes_the_conversations_from_either_position(tmp_path):
    import json
    d = state(tmp_path)
    (tmp_path / "aurora_conversation_memory.json").write_text(json.dumps({"entries": [dict(ENTRY, user_said="a nice tea", aurora_said="the cup is warm")]}))
    r = W.weave(d)
    assert r["summary"]["conversations"] == {"records": 1, "placements": 1}                      # only `tea` is a known concept here; `cup` is not
    assert r["book"].degree("tea", "episode_ref", "s1:100") == pytest.approx(0.8) and "episode_ref" not in r["book"].facets_for("cup", include_uncounted=True)


def test_a_missing_state_directory_weaves_nothing_rather_than_failing(tmp_path):
    r = W.weave(str(tmp_path / "nope"))
    assert r["book"].totals()["entries"] == 0 and r["summary"]["waveform_cycle"] is None


# -- what linking changes ----------------------------------------------------------------------------------------------------------------------------------

def test_consequence_counts_only_what_has_a_crystal_and_finds_the_hubs_is_a_forms():
    s = AssociationStore()
    for c in ("a", "b", "c"):
        s.add(c, "letter", "is_a", ref=c, source="co-occurrence", strength=0.9)
    s.add("a", "x", "related_to", ref="ax", source="co-occurrence", strength=0.5)
    s.add("x", "ghost", "related_to", ref="xg", source="co-occurrence", strength=0.5)
    idx = {c: f"id_{c}" for c in ("a", "b", "c", "x", "letter")}
    r = W.consequence(s, idx, hub="a")
    assert r["crystals"] == 5 and r["crystals_with_connections"] == 5 and r["links"] == 4          # ghost has no crystal: not counted
    assert r["reach"]["one_step"] == 2 and r["reach"]["two_steps"] == 4                            # a: letter, x; then b, c
    assert r["wholes_formed_by_is_a"] == {"hubs": 1, "largest": [("letter", 3)]}


def test_links_that_are_only_labels_form_no_wholes():
    s = AssociationStore()
    s.add("a", "letter", "is_a", ref="1", source="seeded", strength=1.0)
    assert W.consequence(s, {"a": "1", "letter": "2"})["wholes_formed_by_is_a"]["hubs"] == 0


# -- isolation -----------------------------------------------------------------------------------------------------------------------------------------------

def test_nothing_running_imports_the_weave_and_it_never_writes():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = open(W.__file__, encoding="utf-8").read()
    assert not re.search(r"open\([^)]*[\"'][wa]b?[\"']", src) and "write_text" not in src and "os.replace" not in src
    hits = []
    for base, _, files in os.walk(root):
        if any(x in base for x in (".git", "tests", "scripts", "aurora_state", "node_modules")):
            continue
        for f in files:
            if f.endswith(".py") and f != "crystal_weave.py" and re.search(r"(from|import)\s+[\w.]*crystal_weave", open(os.path.join(base, f), encoding="utf-8", errors="ignore").read()):
                hits.append(f)
    assert hits == []
