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
