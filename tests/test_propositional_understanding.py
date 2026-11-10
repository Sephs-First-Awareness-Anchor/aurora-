"""FIX-A115: understanding with more than two dimensions -- who asserted what
predicate of what, denied or not, when, meaning what; and where a concept sits
in her constraint space.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""

from types import SimpleNamespace

from aurora_internal import aurora_propositional_understanding as P
from aurora_internal import aurora_confluence as C
from aurora_internal.aurora_ontological_scaffolding import OntologicalWeb, RelationType


def _web():
    return OntologicalWeb()


AXIS_T = {"X": 0.1, "T": 0.6, "N": 0.1, "B": 0.1, "A": 0.1}


def test_participants_follow_the_session():
    assert P.participants("praxis_live") == ("sunni", "aurora")
    assert P.participants("rehearsal_gpt_hist:1") == ("sunni", "gpt")
    assert P.participants("rehearsal_hist:1") == ("gpt", "sunni")
    assert P.participants("demo_rehearsal_hist:1") == ("sunni", "gpt")
    assert P.participants("demo_rehearsal_gpt_hist:1") == ("gpt", "sunni")
    assert P.participants("praxis_dm_Echo") == ("dm_echo", "aurora")
    assert P.participants("x", {"_turn_participants": ("a", "b")}) == ("a", "b")


def test_a_statement_becomes_who_asserted_which_predicate_of_what():
    web = _web()
    form = {"subject": "I", "relation": "love", "obj": "old soul records"}
    props = P.integrate_form(web, form, heard="I love old soul records", speaker="sunni", listener="aurora",
                             profile=AXIS_T, time_ref="tonight")
    assert [(p["source"], p["predicate"], p["target"]) for p in props] == [
        ("sunni", "love", "soul"), ("sunni", "love", "records")]
    rel = web.relations[next(iter(web._relations_by_source["sunni"]))]
    assert rel.source_of_knowledge == "assertion"
    assert rel.assertion["by"] == {"sunni": 1}
    assert rel.assertion["predicates"]["love"]["n"] == 1
    assert rel.assertion["times"] == {"tonight": 1}
    # the type is the one nearest to what the statement MEANT (T-heavy -> precedes),
    # not the noun+noun type of the two words
    assert rel.relation_type is RelationType.PRECEDES


def test_denial_and_repetition_are_kept():
    web = _web()
    for neg in (True, True, False):
        P.integrate_form(web, {"subject": "the battery", "relation": "overheats", "obj": "the rig", "negated": neg},
                         heard="", speaker="sunni", listener="aurora", profile=AXIS_T)
    rel = web.relations[next(iter(web._relations_by_source["battery"]))]
    p = rel.assertion["predicates"]["overheat"]
    assert (p["n"], p["denied"], p["surface"]) == (3, 2, "overheats")
    lex = P.lexicalize_assertion(rel, speaker_now="sunni", self_now="aurora")
    assert lex["agent"] == "battery" and lex["action"] == "does not overheat" and lex["object"] == "rig"


def test_questions_are_not_facts():
    web = _web()
    props = P.integrate_form(web, {"subject": "you", "relation": "like", "obj": "music", "question": True},
                             heard="Do you like music?", speaker="sunni", listener="aurora", profile=AXIS_T)
    assert props == [] and not web.relations


def test_clauses_are_propositions_too():
    web = _web()
    form = {"subject": "we", "relation": "push", "obj": "the rig",
            "clauses": [{"subject": "I'm", "relation": "worried", "obj": "the battery"}]}
    props = P.integrate_form(web, form, heard="", speaker="sunni", listener="aurora", profile=AXIS_T)
    assert ("sunni", "worried", "battery") in [(p["source"], p["predicate"], p["target"]) for p in props]


def test_a_concept_gets_a_place_in_her_constraint_space():
    web = _web()
    P.integrate_form(web, {"subject": "I", "relation": "love", "obj": "records"}, heard="",
                     speaker="sunni", listener="aurora", profile=AXIS_T)
    P.integrate_form(web, {"subject": "I", "relation": "sell", "obj": "records"}, heard="",
                     speaker="sunni", listener="aurora", profile={"X": 1.0, "T": 0, "N": 0, "B": 0, "A": 0})
    node = web.nodes["records"]
    assert node.axis_samples == 2
    assert node.axis_profile["T"] == 0.3 and node.axis_profile["X"] == 0.55


def test_she_says_what_was_asserted_back_as_said(tmp_path):
    from tests.test_confluence import _engine, _ability, _abilities
    web = _web()
    P.integrate_form(web, {"subject": "I", "relation": "love", "obj": "old soul records"}, heard="",
                     speaker="sunni", listener="aurora", profile=AXIS_T)
    abil = _abilities(_ability("X:G", "X", "operator_action:operator_on_x", "operator_action:operator_on_n",
                               "complexity_axes:3", "complexity_slots:4", "generation_role:ADJACENT"))
    systems = {"grammar_engine": _engine(tmp_path), "genealogy": abil[0], "_last_active_ability_ids": abil[1],
               "oets": SimpleNamespace(web=web),
               "_last_pipeline_state": {"constraint_semantic_state": {"relational_form": {
                   "subject": "you", "relation": "think", "obj": "about records", "question": True}},
                   "salient_concepts": ["records"], "surface_reactive_emotion": {"tone_bias": "curious"}}}
    text, rec = C.compose(systems, "What do you think about records?", session_id="live")
    assert text == "I think about records, and you love records."
    assert rec["clauses"][1]["system"] == "knowledge"


def test_persistence_round_trip(tmp_path):
    from aurora_internal.aurora_identity_persistence import OETSPersistence
    from aurora_internal.aurora_ontological_scaffolding import OntologicalScaffoldingEngine
    eng = OntologicalScaffoldingEngine()
    P.integrate_form(eng.web, {"subject": "I", "relation": "love", "obj": "records"}, heard="",
                     speaker="sunni", listener="aurora", profile=AXIS_T)
    store = OETSPersistence(state_dir=str(tmp_path))
    assert store.save_web(eng)
    fresh = OntologicalScaffoldingEngine()
    assert store.load_web(fresh)
    rel = [r for r in fresh.web.relations.values() if r.source_word == "sunni"][0]
    assert rel.assertion["predicates"]["love"]["n"] == 1
    assert fresh.web.nodes["records"].axis_samples == 1


def test_the_same_statement_heard_twice_is_one_statement():
    web = _web()
    form = {"subject": "I", "relation": "love", "obj": "records"}
    systems = {"oets": SimpleNamespace(web=web),
               "_last_pipeline_state": {"constraint_semantic_state": {"relational_form": form},
                                        "native_meaning": {"domain_scores": AXIS_T}}}
    assert P.integrate_turn(systems, "I love records", session_id="rehearsal_gpt_hist:1")["status"] == "ok"
    assert P.integrate_turn(systems, "I love records", session_id="demo_rehearsal_hist:1")["status"] == "already_integrated"
    rel = [r for r in web.relations.values() if r.source_word == "sunni"][0]
    assert rel.assertion["n"] == 1


def test_statements_are_read_from_what_was_said():
    got = [(s["subject"], s["relation"], s["obj"], s["negated"], s["modality"]) for s in P.statements_in(
        "I love old soul records on a slow night. My battery overheats when I push the rig too hard. "
        "I don't trust that battery. We should test the rig first. The battery isn't the problem. "
        "Do you like music?")]
    assert got == [("i", "love", "old soul records", False, ""), ("my battery", "overheats", "", False, ""),
                   ("i", "push", "the rig", False, ""), ("i", "trust", "that battery", True, ""),
                   ("we", "test", "the rig", False, "should"), ("the battery", "be", "the problem", True, "")]


def test_possessives_are_not_the_speaker():
    assert P.heads("my battery", speaker="sunni", listener="aurora", acts=set()) == ["battery"]
    assert P.heads("honestly i", speaker="sunni", listener="aurora", acts=set()) == ["sunni"]


def test_the_copula_agrees_with_who_it_is_about():
    web = _web()
    P.integrate_form(web, {"subject": "the battery", "relation": "be", "obj": "the problem", "negated": True},
                     heard="", speaker="sunni", listener="aurora", profile=AXIS_T)
    rel = web.relations[next(iter(web._relations_by_source["battery"]))]
    assert P.lexicalize_assertion(rel, speaker_now="sunni", self_now="aurora")["action"] == "is not"


def test_real_history_is_read_as_written():
    got = [(s["subject"], s["relation"], s["obj"], s["negated"]) for s in P.statements_in(
        "I’m building a system to understand myself. You’re right, I told him to come back. "
        "I don’t know, you tell me.")]
    assert got == [("i", "building", "a system", False), ("you", "be", "right", False), ("i", "told", "him", False),
                   ("i", "know", "", True), ("you", "tell", "me", False)]
    assert P.heads("him", speaker="sunni", listener="aurora", acts=set()) == []


def test_a_progressive_is_said_with_its_copula():
    web = _web()
    P.integrate_form(web, {"subject": "I", "relation": "building", "obj": "a system"}, heard="",
                     speaker="sunni", listener="aurora", profile=AXIS_T)
    rel = [r for r in web.relations.values() if r.source_word == "sunni"][0]
    assert P.lexicalize_assertion(rel, speaker_now="sunni", self_now="aurora")["action"] == "are building"
