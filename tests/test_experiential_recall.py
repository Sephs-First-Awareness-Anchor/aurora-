"""Directive V2 -- contextual relational understanding, developmental reinterpretation and experiential recall.

Each test runs through the consumers she actually uses (her statement intake, her fact answers, her confluence, her
crystal projection, the strata evidence of a turn), not storage alone.  The numbers follow the directive's §8.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
import copy
import json
import os
import shutil
import tempfile
import time
from types import SimpleNamespace

import pytest

from aurora_internal import aurora_propositional_understanding as P
from aurora_internal import aurora_learned_rules as R
from aurora_internal import aurora_confluence as C
from aurora_internal import aurora_experiential_recall as ER
from aurora_internal import crystal_facets as F
from aurora_internal import crystal_weave as W
from aurora_internal import evidence_qualification as Q
from aurora_internal.aurora_ontological_scaffolding import OntologicalWeb


def _say(web, line, basis="told", speaker="sunni"):
    for st in P.statements_in(line):
        P.integrate_form(web, st, heard=line, speaker=speaker, listener="aurora", profile={}, basis=basis)


def _told(lines):
    web = OntologicalWeb()
    for line in lines:
        _say(web, line)
    return web


def _ask(web, q):
    return [(i["lex"]["agent"], i["lex"]["action"], i["lex"]["object"]) for i in R.derive(web, q, speaker_now="sunni", self_now="aurora")]


def _pred(web, s, o, pred):
    for rel in web.relations.values():
        if rel.source_word == s and rel.target_word == o and getattr(rel, "assertion", None):
            return rel, dict(rel.assertion["predicates"][pred])
    raise AssertionError(f"no {s} {pred} {o}")


WARM_COLD = ["Devlin likes rain when it is warm.", "Devlin does not like rain when it is cold."]


# -- 1. conditional learning ---------------------------------------------------------------------------------------------------------------

def test_1_one_entity_two_situations_is_two_conditions_not_a_contradiction():
    web = _told(WARM_COLD)
    rel, p = _pred(web, "devlin", "rain", "like")
    assert P.verdict(p) == "conditional"
    by = {c["key"]: c["verdict"] for c in P.conditional_standing(p)}
    assert by == {"it be warm": "held", "it be cold": "denied"}
    assert R.contradictions(web) == []                       # nothing to resolve: each condition is decided


def test_1_asked_under_a_condition_she_answers_under_that_condition_only():
    web = _told(WARM_COLD)
    assert _ask(web, "Does Devlin like rain when it is cold?") == [("devlin", "does not like", "rain when it is cold")]
    assert _ask(web, "Does Devlin like rain when it is warm?") == [("devlin", "likes", "rain when it is warm")]


def test_1_neither_behaviour_is_declared_universal_in_her_confluence():
    web = _told(WARM_COLD)
    systems = {"oets": SimpleNamespace(web=web), "_last_pipeline_state": {}}
    said = [(k["lex"]["agent"], k["lex"]["action"], k["lex"]["object"]) for k in C.knowledge(systems, ["devlin"], "tell me about devlin", reach=2)]
    assert ("devlin", "likes", "rain when it is warm") in said and ("devlin", "does not like", "rain when it is cold") in said
    assert not any(obj == "rain" for _, _, obj in said)     # never "devlin likes rain" as if it held everywhere


def test_1_baseline_the_same_statements_without_conditions_are_still_contested():
    web = _told(["Devlin likes rain.", "Devlin does not like rain."])
    _, p = _pred(web, "devlin", "rain", "like")
    assert P.verdict(p) == "contested"
    assert _ask(web, "Does Devlin like rain?") == [("I", "am not sure", "if devlin likes rain")]


# -- 2. same outward result, different histories -------------------------------------------------------------------------------------------

def test_2_the_same_outcome_under_different_antecedents_stays_two_retrievable_histories():
    web = _told(["Devlin drinks tea when it is late.", "Devlin drinks tea when it is cold."])
    rel, p = _pred(web, "devlin", "tea", "drink")
    conds = {c["key"]: c for c in P.conditional_standing(p)}
    assert set(conds) == {"it be late", "it be cold"} and all(c["verdict"] == "held" for c in conds.values())
    rec = ER.recollect_predicate(rel, "drink")
    assert [o["condition"] for o in rec["then"]] == ["it be late", "it be cold"]
    assert rec["then"][0]["episode"]["ref"] != rec["then"][1]["episode"]["ref"]   # each points at its own utterance


def test_2_facet_situations_are_kept_apart_in_the_crystal_projection():
    b = F.FacetBook()
    b.add("mara", "effect", "tired", {"t": 1}, ref="a", source="told", context={"topic": "running"})
    b.add("mara", "effect", "tired", {"t": 1}, ref="b", source="told", context={"topic": "working", "session": "s2"})
    groups = b.conditions_of("mara", "effect", "tired")
    assert sorted(g["when"]["topic"] for g in groups) == ["running", "working"]
    assert {g["first"] for g in groups} == {"a", "b"}


# -- 3. historical viewpoint -----------------------------------------------------------------------------------------------------------------

def test_3_she_recalls_what_she_held_then_and_separately_what_she_holds_now():
    web = _told(["Devlin likes snow."])
    _say(web, "Devlin does not like snow.", basis="corrected")
    rel, p = _pred(web, "devlin", "snow", "like")
    rec = ER.recollect_predicate(rel, "like")
    then = rec["then"]
    assert [o["held_after"] for o in then] == ["held", "denied"]
    assert [o["basis"] for o in then] == ["told", "corrected"] and [o["seq"] for o in then] == [1, 2]
    assert then[0]["t"] <= then[1]["t"]
    assert rec["now"]["verdict"] == "denied" and rec["revised"]
    assert rec["before_revision"]["verdict"] == "held" and rec["before_revision"]["changed_by"]["basis"] == "corrected"


def test_3_asked_how_it_was_she_answers_now_and_offers_what_she_thought_then():
    web = _told(["Devlin likes snow."])
    _say(web, "Devlin does not like snow.", basis="corrected")
    items = R.derive(web, "Did Devlin like snow?", speaker_now="sunni", self_now="aurora")
    said = [(i["lex"]["agent"], i["lex"]["action"], i["lex"]["object"]) for i in items]
    assert said[0] == ("devlin", "does not like", "snow")              # what she holds now answers first
    assert said[1] == ("I", "thought", "that devlin likes snow")         # what she held then, as then
    assert items[1]["axis"] == "T" and items[1]["asked"] is False and items[1]["basis"] == "recalled"
    # asked in the present, the answer carries the recollection as ground but voices only the present
    now = R.derive(web, "Does Devlin like snow?", speaker_now="sunni", self_now="aurora")
    assert len(now) == 1 and now[0]["recollection"]["revised"] is True


def test_3_her_confluence_voices_the_then_clause_only_when_her_clause_budget_allows():
    web = _told(["Devlin likes snow."])
    _say(web, "Devlin does not like snow.", basis="corrected")
    known = R.derive(web, "Did Devlin like snow?", speaker_now="sunni", self_now="aurora")
    one = C.plan({"knowledge": known}, {"clauses": 1, "axis_order": ["X", "T"]})
    two = C.plan({"knowledge": known}, {"clauses": 2, "axis_order": ["X", "T"]})
    assert [c["action"] for c in one] == ["does not like"]
    assert [c["action"] for c in two] == ["does not like", "thought"]


# -- 4. revision without historical rewriting ----------------------------------------------------------------------------------------------

def test_4_a_correction_lowers_the_old_explanation_and_leaves_the_old_belief_and_the_correction_visible():
    web = _told(["Devlin likes snow."])
    _, before = _pred(web, "devlin", "snow", "like")
    first = dict(before["history"][0])
    _say(web, "Devlin does not like snow.", basis="corrected")
    _, after = _pred(web, "devlin", "snow", "like")
    assert after["history"][0] == first                    # the first occasion is exactly as it was recorded
    assert after["history"][-1]["b"] == "corrected" and P.verdict(after) == "denied"


def test_4_a_correction_under_one_condition_does_not_erase_the_other_condition():
    web = _told(WARM_COLD)
    _say(web, "Devlin likes rain when it is cold.", basis="corrected")
    _, p = _pred(web, "devlin", "rain", "like")
    by = {c["key"]: c["verdict"] for c in P.conditional_standing(p)}
    assert by == {"it be warm": "held", "it be cold": "held"}
    assert not p.get("settled")                             # the correction settled its own condition only


# -- 5. no fabricated original state -------------------------------------------------------------------------------------------------------

def test_5_what_was_not_captured_is_unknown_never_reconstructed():
    web = _told(["Devlin likes snow."])
    rel, p = _pred(web, "devlin", "snow", "like")
    for e in rel.assertion["predicates"]["like"]["history"]:       # an occasion recorded before held-after was kept
        e.pop("v", None)
        e.pop("h", None)
    rec = ER.recollect_predicate(rel, "like")
    assert rec["then"][0]["held_after"] == "unknown" and rec["then"][0]["held_after_source"] == "not captured"
    assert rec["then"][0]["episode"] == {"ref": None, "status": "unknown"}
    assert not rec["revised"] and rec["before_revision"] is None   # nothing she held then is invented
    assert any("not captured" in g for g in rec["unknown"])


def test_5_an_episode_resolves_by_its_utterance_and_missing_tone_stays_unknown():
    web = _told(["Devlin likes snow."])
    rel, _ = _pred(web, "devlin", "snow", "like")
    rec = ER.recollect_predicate(rel, "like")
    entries = [{"user_said": "Something else.", "timestamp": 1.0, "emotional_tone": "warm"},
               {"user_said": "Devlin  likes snow.", "aurora_said": "noted", "timestamp": 2.0, "turn_id": "t2"}]
    out = ER.resolve_episodes(rec, entries)
    ep = out["then"][0]["episode"]
    assert ep["turn_id"] == "t2" and ep["tone"] == "unknown" and ep["topic"] == "unknown"
    assert rec["then"][0]["episode"] == {"ref": rec["then"][0]["episode"]["ref"]}     # the record itself is not changed


def test_5_a_history_thinned_past_its_bound_is_said_to_be_incomplete():
    web = _told([f"Devlin likes snow." for _ in range(1)])
    rel, _ = _pred(web, "devlin", "snow", "like")
    for i in range(P.MAX_HISTORY + 2):
        P._record_assertion(rel, predicate="like", surface="like", negated=False, modality="", speaker="sunni",
                            time_ref="", profile={}, context=f"Devlin likes snow {i}", basis="told")
    rec = ER.recollect_predicate(rel, "like")
    assert rec["history_complete"] is False and rec["occasions_recorded"] == P.MAX_HISTORY + 3
    assert any("thinned" in g for g in rec["unknown"])


# -- 6. recall is not re-experience ---------------------------------------------------------------------------------------------------------

def test_6_remembering_changes_nothing_and_a_new_statement_is_recorded_once():
    web = _told(WARM_COLD)
    _say(web, "Devlin likes rain when it is cold.", basis="corrected")
    rel, _ = _pred(web, "devlin", "rain", "like")
    frozen = copy.deepcopy(rel.assertion)
    for _ in range(5):
        ER.recollect(web, ["devlin"])
        ER.recollect_predicate(rel, "like")
        R.derive(web, "Did Devlin like rain when it is cold?", speaker_now="sunni", self_now="aurora")
        C.knowledge({"oets": SimpleNamespace(web=web), "_last_pipeline_state": {}}, ["devlin"], "devlin and rain", reach=2)
    assert rel.assertion == frozen
    _say(web, "Devlin likes rain when it is warm.")
    _, p = _pred(web, "devlin", "rain", "like")
    assert p["seq"] == frozen["predicates"]["like"]["seq"] + 1 and p["n"] == frozen["predicates"]["like"]["n"] + 1


def test_6_a_recollection_event_never_counts_in_the_crystal_book():
    b = F.FacetBook()
    ev = Q.make_event("devlin|like|rain", occurrence="heard", t=1)
    W.place_event(b, "devlin", "relation", "like|rain", {"t": 1}, ev)
    before = b.degree("devlin", "relation", "like|rain")
    for i in range(3):
        rec = Q.make_event("devlin|like|rain", "told", occurrence="recalled", t=10 + i)
        W.place_event(b, "devlin", "relation", "like|rain", {"t": 1}, rec)
    assert b.degree("devlin", "relation", "like|rain") == before
    assert [g["for"] for g in b.conditions_of("devlin", "relation", "like|rain")] == [1]


# -- 7. dream / simulation boundary --------------------------------------------------------------------------------------------------------

def test_7_a_supposed_alternative_stays_hypothetical_and_never_upgrades_the_episode():
    web = _told(["Devlin likes snow."])
    line = "Suppose that Devlin does not like snow."
    m = P._SUPPOSE.match(line)
    for st in P.statements_in(line[m.end():]):
        P.integrate_form(web, st, heard=line[m.end():], speaker="sunni", listener="aurora", profile={}, basis="supposed")
    rel, p = _pred(web, "devlin", "snow", "like")
    assert P.verdict(p) == "held" and p["n"] == 1
    assert sum(c["n"] for c in P.conditional_standing(p)) == 1          # the supposition is in no condition tally
    rec = ER.recollect_predicate(rel, "like")
    assert [o["basis"] for o in rec["then"]] == ["told", "supposed"] and not rec["revised"]


def test_7_a_dreamed_alternative_is_kept_uncounted_in_the_crystal_book():
    b = F.FacetBook()
    W.place_event(b, "devlin", "relation", "like|snow", {}, Q.make_event("devlin|like|snow", occurrence="heard", t=1))
    dream = Q.make_event("devlin|like|snow", occurrence="dreamed", negated=True, t=2, context={"world": "dreamed"})
    W.place_event(b, "devlin", "relation", "like|snow", {}, dream)
    assert not b.contradicted("devlin", "relation", "like|snow")
    assert [g["against"] for g in b.conditions_of("devlin", "relation", "like|snow")] == [0]


# -- 8. contextless question ----------------------------------------------------------------------------------------------------------------

def test_8_asked_with_no_condition_she_gives_the_conditions_she_knows_instead_of_inventing_one():
    web = _told(WARM_COLD)
    said = _ask(web, "Does Devlin like rain?")
    assert sorted(said) == [("devlin", "does not like", "rain when it is cold"), ("devlin", "likes", "rain when it is warm")]


def test_8_asked_under_a_condition_she_was_never_told_about_she_gives_what_she_knows():
    web = _told(WARM_COLD)
    said = _ask(web, "Does Devlin like rain when it is windy?")
    assert sorted(said) == [("devlin", "does not like", "rain when it is cold"), ("devlin", "likes", "rain when it is warm")]


# -- 9. identity protection -------------------------------------------------------------------------------------------------------------------

def test_9_two_people_sharing_words_are_never_merged():
    web = _told(["Devlin likes tea when it is hot.", "Mara does not like tea when it is hot."])
    assert P.verdict(_pred(web, "devlin", "tea", "like")[1]) == "held"
    assert P.verdict(_pred(web, "mara", "tea", "like")[1]) == "denied"
    assert _ask(web, "Does Devlin like tea when it is hot?") == [("devlin", "likes", "tea when it is hot")]
    recs = ER.recollect(web, ["devlin"], only_developed=False)
    assert {r["source"] for r in recs} == {"devlin"}


# -- 10. live cognitive consequence: the strata evidence of a turn carries the view ---------------------------------------------------------

def test_10_the_turn_evidence_packet_carries_the_bounded_then_now_view():
    import aurora
    web = _told(["Devlin likes snow."])
    _say(web, "Devlin does not like snow.", basis="corrected")
    systems = {"oets": SimpleNamespace(web=web)}
    state = SimpleNamespace(pipeline_state={}, parsed={"topic_words": ["devlin", "snow"]})
    ev = aurora._build_established_strata_evidence(systems, state, "did devlin like snow")
    view = ev["experiential_recall"]
    assert view[0]["about"] == ["devlin", "like", "snow"] and view[0]["revised"] is True
    assert view[0]["before_revision"]["verdict"] == "held" and view[0]["now"]["verdict"] == "denied"
    assert [o["held_after"] for o in view[0]["then"]] == ["held", "denied"]


def test_10_nothing_moved_means_no_view_is_carried():
    import aurora
    web = _told(["Devlin likes snow."])
    state = SimpleNamespace(pipeline_state={}, parsed={"topic_words": ["devlin"]})
    ev = aurora._build_established_strata_evidence({"oets": SimpleNamespace(web=web)}, state, "devlin")
    assert "experiential_recall" not in ev


# -- 11. across save, restart and hand-off ---------------------------------------------------------------------------------------------------

def test_11_then_and_now_survive_a_save_and_a_restart_unchanged():
    from aurora_internal.aurora_identity_persistence import OETSPersistence
    from aurora_internal.aurora_ontological_scaffolding import OntologicalScaffoldingEngine
    scratch = tempfile.mkdtemp(prefix="er_persist_")
    try:
        persist = OETSPersistence(state_dir=os.path.join(scratch, "state"))
        persist.primary_web_file = type(persist.primary_web_file)(os.path.join(scratch, "primary.json"))
        persist.web_file = persist.primary_web_file
        persist._isolated = False
        eng = OntologicalScaffoldingEngine()
        for line in WARM_COLD:
            _say(eng.web, line)
        _say(eng.web, "Devlin likes rain when it is cold.", basis="corrected")
        rel, _ = _pred(eng.web, "devlin", "rain", "like")
        before = ER.recollect_predicate(rel, "like")
        assert persist.save_web(eng)
        eng2 = OntologicalScaffoldingEngine()
        assert persist.load_web(eng2)
        rel2, _ = _pred(eng2.web, "devlin", "rain", "like")
        assert ER.recollect_predicate(rel2, "like") == before
        assert persist.save_web(eng2) and persist.load_web(OntologicalScaffoldingEngine())   # a second hand-off adds nothing
        rel3, p3 = _pred(eng2.web, "devlin", "rain", "like")
        assert p3["seq"] == before["occasions_recorded"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


# -- 12. stale projection --------------------------------------------------------------------------------------------------------------------

def _Crystal():
    from aurora_dimensional_systems import Crystal
    return Crystal(crystal_id="id", concept="devlin")


def _facet(cr, kind="relation"):
    return next(f for f in cr.facets.values() if f.role == f"fk:{kind}")


def _fk(cr, kind="relation"):
    return {e["key"]: e for e in _facet(cr, kind).content["entries"]}


def test_12_a_contradiction_lowers_old_strong_projected_support_and_unrelated_contexts_stay():
    b = F.FacetBook()
    b.add("devlin", "relation", "like|rain", {}, ref="w1", source="told", strength=0.9, context={"topic": "warm"})
    b.add("devlin", "relation", "like|rain", {}, ref="c1", source="told", strength=0.9, context={"topic": "cold"})
    b.add("devlin", "relation", "like|tea", {}, ref="t1", source="told", strength=0.8)
    cr = {"id": _Crystal()}
    F.apply_to_crystals(b, {"devlin": "id"}, cr, dry_run=False)
    high = _fk(cr["id"])["like|rain"]["degree"]
    b.add("devlin", "relation", "like|rain", {}, ref="c2", source="corrected", strength=0.95, polarity=-1, context={"topic": "cold"})
    r = F.apply_to_crystals(b, {"devlin": "id"}, cr, dry_run=False)
    ents = _fk(cr["id"])
    assert ents["like|rain"]["degree"] < high and r["lowered"] == 1
    conds = {c["when"]["topic"]: c for c in ents["like|rain"]["conditions"]}
    assert conds["warm"]["degree"] == pytest.approx(0.9) and conds["cold"]["degree"] < 0.1
    assert ents["like|tea"]["degree"] == pytest.approx(0.8)                       # unrelated entry untouched


def test_12_replaying_and_rebuilding_give_the_same_view():
    def book():
        b = F.FacetBook()
        b.add("devlin", "relation", "like|rain", {}, ref="w1", source="told", strength=0.9, context={"topic": "warm"})
        b.add("devlin", "relation", "like|rain", {}, ref="c2", source="corrected", strength=0.95, polarity=-1, context={"topic": "cold"})
        return b
    replayed = {"id": _Crystal()}
    for _ in range(3):
        F.apply_to_crystals(book(), {"devlin": "id"}, replayed, dry_run=False)
    rebuilt = {"id": _Crystal()}
    F.apply_to_crystals(book(), {"devlin": "id"}, rebuilt, dry_run=False)
    assert _facet(replayed["id"]).content == _facet(rebuilt["id"]).content
    assert _facet(replayed["id"]).confidence == pytest.approx(_facet(rebuilt["id"]).confidence)


def test_12_an_entry_whose_store_was_trimmed_is_kept_and_said_to_have_no_source_now():
    b = F.FacetBook()
    b.add("devlin", "relation", "like|tea", {}, ref="t1", source="told", strength=0.5)
    cr = {"id": _Crystal()}
    cr["id"].add_facet("fk:relation", {"entries": [{"key": "old", "content": {}, "degree": 0.99, "contexts": 3}]}, confidence=0.99)
    F.apply_to_crystals(b, {"devlin": "id"}, cr, dry_run=False)
    ents = _fk(cr["id"])
    assert ents["old"]["source_present"] is False and ents["old"]["degree"] == 0.99
    assert _facet(cr["id"]).confidence == pytest.approx(0.5)


# -- 13. performance: bounded, index-driven, no loop of its own ------------------------------------------------------------------------------

def test_13_recall_reads_only_the_relations_of_the_words_asked_about():
    web = OntologicalWeb()
    for i in range(400):
        _say(web, f"Person{i} likes item{i}.")
    _say(web, "Devlin likes snow.")
    _say(web, "Devlin does not like snow.", basis="corrected")
    t0 = time.perf_counter()
    for _ in range(50):
        recs = ER.recollect(web, ["devlin"])
    per_call = (time.perf_counter() - t0) / 50
    assert len(recs) == 1 and per_call < 0.01          # milliseconds, whatever else she holds


# -- 14. regression: what was established stays ----------------------------------------------------------------------------------------------

def test_14_plain_statements_corrections_and_examples_keep_their_verdicts():
    web = _told(["Devlin likes snow.", "Mara likes tea."])
    _say(web, "Mara does not like tea.", basis="corrected")
    assert _ask(web, "Does Devlin like snow?") == [("devlin", "likes", "snow")]
    assert _ask(web, "Does Mara like tea?") == [("mara", "does not like", "tea")]
    assert R.contradictions(web) == []
