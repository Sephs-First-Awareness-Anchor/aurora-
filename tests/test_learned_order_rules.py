# Authors: Sunni (Sir) Morningstar & Cael Devo
"""FIX-A133 (phase 1, letters): a learned statement takes effect in what she can work out.

Everything here is taught the way she learns: as sentences through her own
statement parser.  The module under test reads only her learned relations.
"""
from __future__ import annotations

import pytest

from aurora_internal import aurora_confluence as C
from aurora_internal import aurora_learned_rules as R
from aurora_internal import aurora_propositional_understanding as P
from aurora_internal.aurora_ontological_scaffolding import OntologicalWeb

LESSON = ["The letter b comes after the letter a.", "The letter c comes after the letter b.",
          "The letter d follows the letter c."]


def _taught(lines=LESSON):
    web = OntologicalWeb()
    for line in lines:
        for st in P.statements_in(line):
            P.integrate_form(web, st, heard=line, speaker="sunni", listener="aurora", profile={})
    return web


def test_letters_and_order_phrases_are_read_as_statements():
    assert P.statements_in("B follows A.")[0]["relation"] == "follows"
    st = P.statements_in("The letter b comes after the letter a.")[0]
    assert (st["subject"], st["obj"], st["particle"]) == ("the letter b", "the letter a", "after")
    # the verb forms of her tagger can be the act of a statement
    assert P.statements_in("Rain causes growth.")[0]["relation"] == "causes"
    # "after" in front of its own clause is still a clause
    assert [s["subject"] for s in P.statements_in("I left after he cried.")] == ["i", "he"]


def test_the_letter_is_what_the_statement_is_about():
    web = _taught(LESSON[:1])
    rels = [(r.source_word, r.target_word) for r in web.relations.values() if getattr(r, "assertion", None)]
    assert rels == [("b", "a")]
    assert dict(next(iter(web.relations.values())).assertion["predicates"]).keys() == {"come after"}


def test_order_is_chained_from_what_she_was_told():
    web = _taught()
    reach = R.later_than(R.order_edges(web), "a")
    assert list(reach) == ["b", "c", "d"] and reach["d"] == ["a", "b", "c", "d"]


@pytest.mark.parametrize("question,agent,action,obj", [
    ("What comes after b?", "c", "comes after", "b"),
    ("What follows c?", "d", "comes after", "c"),
    ("What letter comes before d?", "c", "comes before", "d"),
    ("Is d after a?", "d", "is after", "a"),
    ("Does c follow b?", "c", "is after", "b"),
    ("Is a after d?", "a", "is not after", "d"),
])
def test_questions_are_answered_from_chained_order(question, agent, action, obj):
    got = R.derive(_taught(), question)
    assert [(i["lex"]["agent"], i["lex"]["action"], i["lex"]["object"]) for i in got] == [(agent, action, obj)]
    assert got[0]["derived"] and got[0]["learned_from"] == "inference"


def test_she_says_nothing_about_order_she_was_not_told():
    web = _taught()
    assert R.derive(web, "Is c after z?") == [] and R.derive(web, "What comes after d?") == []
    assert R.derive(OntologicalWeb(), "What comes after b?") == []
    assert R.derive(web, "What is a letter?") == []


def test_a_denied_order_is_not_held():
    web = OntologicalWeb()
    for line in ("The letter b comes after the letter a.", "The letter b does not come after the letter a."):
        for st in P.statements_in(line):
            P.integrate_form(web, st, heard=line, speaker="sunni", listener="aurora", profile={})
    assert R.order_edges(web) == {}


def test_the_confluence_composes_the_answer_in_her_own_composer(monkeypatch):
    web = _taught()
    systems = {"oets": type("O", (), {"web": web})(), "perception": None}
    known = C.knowledge(systems, ["aurora"], "What comes after b?", reach=2, session_id="x")
    assert known[0]["derived"] and known[0]["lex"]["agent"] == "c"


def test_a_new_letter_in_the_answer_is_not_an_echo():
    import aurora_voice_gate as G
    assert G.parrot_reason("C comes after b.", "What comes after b?") == ""
    assert G.parrot_reason("You feel calm when you are settled.", "You feel calm when you are settled.") == "echo"


# -- phase 2: kinds ----------------------------------------------------------------

KINDS = ["B is a letter.", "A letter is a symbol.", "The letter c is a letter.", "Glorp is a verb."]


def _told(lines):
    web = OntologicalWeb()
    for line in lines:
        for st in P.statements_in(line):
            P.integrate_form(web, st, heard=line, speaker="sunni", listener="aurora", profile={})
    return web


def test_a_kind_statement_is_one_predicate_with_the_article_as_its_particle():
    st = P.statements_in("B is a letter.")[0]
    assert (st["subject"], st["relation"], st["obj"], st["particle"]) == ("b", "be", "letter", "a")
    assert "particle" not in P.statements_in("My name is Sunni.")[0]          # an identity is not a kind


@pytest.mark.parametrize("question,expected", [
    ("What is b?", [("b", "is a", "letter"), ("b", "is a", "symbol")]),
    ("Is b a letter?", [("b", "is a", "letter")]),
    ("Is b a symbol?", [("b", "is a", "symbol")]),
    ("Is c a letter?", [("c", "is a", "letter")]),
    ("Is b a verb?", []),
    ("What is zzz?", []),
])
def test_kinds_are_answered_and_inherited(question, expected):
    got = R.derive(_told(KINDS), question)
    assert [(i["lex"]["agent"], i["lex"]["action"], i["lex"]["object"]) for i in got] == expected


def test_told_what_role_a_word_has_the_word_has_it():
    web = _told(["Glorp is a noun."])
    assert web.nodes["glorp"].role == "noun" and "glorp" in web._nodes_by_role["noun"]
    web = _told(["Glorp is a verb."])
    assert web.nodes["glorp"].role == "verb"
    assert "glorp" in web._nodes_by_role["verb"] and "glorp" not in web._nodes_by_role["noun"]
    # a kind that is not a role leaves the role alone
    before = _told(["B is a letter."]).nodes["b"].role
    assert before not in ("letter",)


def test_a_word_told_to_be_a_verb_is_no_longer_a_thing_she_talks_about():
    web = _told(["Glorp is a noun."])
    assert C._entity(web, "glorp")                      # a noun is something she can be about
    web = _told(["Glorp is a noun.", "Glorp is a verb."])
    assert not C._entity(web, "glorp")                  # a verb is something done, not a thing
    assert C._node_role(web, "glorp") == "verb"


def test_the_copula_with_a_particle_is_voiced_with_agreement():
    web = _told(["B is a letter."])
    rel = next(r for r in web.relations.values() if getattr(r, "assertion", None))
    lex = P.lexicalize_assertion(rel, speaker_now="sunni", self_now="aurora")
    assert (lex["agent"], lex["action"], lex["object"]) == ("b", "is a", "letter")


def test_a_worked_out_answer_is_the_whole_answer():
    web = _told(KINDS)
    systems = {"oets": type("O", (), {"web": web})(), "perception": None}
    known = C.knowledge(systems, ["b", "letter"], "Is c a letter?", reach=3, session_id="x")
    clause = C._knowledge_clause(known, set(), axis="X", prefer_axis=False)
    assert (clause["agent"], clause["object"]) == ("c", "letter")
    used = {("c", "letter"), (C._SAID, C._said_key(clause))}
    assert C._knowledge_clause(known, used, axis="X", prefer_axis=False) is None     # no unrelated extra fact


# -- phase 3: punctuation ----------------------------------------------------------

MARKS = ['The mark "?" ends a question.', 'The mark "." ends a statement.', 'The mark "!" ends an exclamation.']


def test_a_mark_mentioned_in_quotes_is_what_the_statement_is_about():
    st = P.statements_in(MARKS[0])[0]
    assert st["subject"] == 'the mark "?"' and st["relation"] == "ends"
    web = _told(MARKS[:1])
    assert [(r.source_word, r.target_word) for r in web.relations.values() if getattr(r, "assertion", None)] == [("?", "question")]


def test_a_mark_used_in_running_text_is_not_a_token():
    assert P._words("Is it? Yes. Hello, you!") == ["Is", "it", "Yes", "Hello", "you"]
    assert P._words('the mark "?" ends it') == ["the", "mark", "?", "ends", "it"]


@pytest.mark.parametrize("question,expected", [
    ('What does "?" end?', [("?", "ends", "question")]),
    ("What ends a question?", [("?", "ends", "question")]),
    ('What does "." end?', [(".", "ends", "statement")]),
    ("What ends an exclamation?", [("!", "ends", "exclamation")]),
    ("What ends a story?", []),
])
def test_what_a_mark_ends_is_answered_from_what_she_was_told(question, expected):
    got = R.derive(_told(MARKS), question)
    assert [(i["lex"]["agent"], i["lex"]["action"], i["lex"]["object"]) for i in got] == expected


def test_the_word_learner_makes_a_quoted_mark_a_word_but_not_running_punctuation(tmp_path):
    from aurora_expression_perception import ExpressionPerceptionEngine
    eng = ExpressionPerceptionEngine(state_dir=str(tmp_path))
    eng.ingest_interaction({"input": 'The mark "?" ends a question. Is it so?'}, mode="gateway")
    nodes = set(eng.oets.web.nodes)
    assert "?" in nodes and "." not in nodes and "," not in nodes


# -- phase 4: when-then rules ------------------------------------------------------

def test_a_condition_stays_attached_to_what_holds_under_it():
    after = P.statements_in("You feel calm when you are settled and safe.")
    assert after[0]["when"]["relation"] == "be" and after[0]["when"]["obj"] == "settled"
    assert "when" not in after[1]                                  # the condition is still a statement of its own
    before = P.statements_in("When you feel sad I listen.")        # no comma, no clause: nothing is invented
    assert not any("when" in st for st in before)
    lead = P.statements_in("When you greet me, I say hello.")
    assert lead[1]["when"]["relation"] == "greet"


def test_the_condition_is_recorded_on_the_predicate_it_governs():
    web = _told(["You feel calm when you are settled and safe."])
    rel = next(r for r in web.relations.values() if r.target_word == "calm")
    assert dict(rel.assertion["predicates"]["feel"])["when"][0]["obj"] == "settled"
    assert len(R.rules(web)) == 1


CALM = "You feel calm when you are settled and safe."


def _fired(web, heard):
    return [(i["lex"]["agent"], i["lex"]["action"], i["lex"]["object"])
            for i in R.derive(web, heard, speaker_now="sunni", self_now="aurora")]


def test_what_she_holds_under_a_condition_is_said_when_it_is_confirmed():
    web = _told([CALM])
    got = R.derive(web, "You are settled and safe.", speaker_now="sunni", self_now="aurora")
    assert [(i["lex"]["agent"], i["lex"]["action"], i["lex"]["object"]) for i in got] == [("I", "feel", "calm")]
    assert got[0]["basis"] == "told" and got[0]["learned_from"] == "rule"      # testimony, not observation


@pytest.mark.parametrize("heard", [
    "Are you settled and safe?",                    # asked about
    "Are you settled and safe right now?",
    "What if you are settled and safe?",            # supposed
    "If you are settled and safe, tell me.",
    "You might be settled and safe.",               # a maybe
    "You are not settled and safe.",                # denied
    "I am settled and safe.",                       # true of someone else
    "It rained.",
    "You feel calm when you are settled and safe.",  # the lesson said again
])
def test_a_condition_that_is_mentioned_asked_supposed_denied_or_about_someone_else_does_not_hold(heard):
    assert _fired(_told([CALM]), heard) == []


def test_a_condition_is_about_the_person_it_was_said_of():
    web = _told(["When I greet you, you say hello."])
    assert _fired(web, "I greet you.") == [("I", "say", "hello")]            # sunni greeting
    assert _fired(web, "You greet me.") == []                                 # aurora greeting is another matter
    assert _fired(web, "Do I greet you?") == []


def test_nothing_fires_without_a_rule():
    assert R.derive(_told(["You feel calm."]), "I am settled.", speaker_now="sunni", self_now="aurora") == []


# -- numbers and basic communication (FIX-A134) ------------------------------------

NUMBERS = ["Two comes after one.", "Three comes after two.", "Four comes after three.",
           "Five comes after four.", "Six comes after five.", "Seven comes after six.",
           "One is a number.", "Seven is a number.", "A number is a symbol."]


def test_number_words_are_ordered_even_when_a_pronoun_or_misread_as_an_act():
    web = _told(NUMBERS)                               # "one" is a pronoun; the tagger calls "seven" an act
    got = lambda q: [(i["lex"]["agent"], i["lex"]["action"], i["lex"]["object"]) for i in R.derive(web, q, speaker_now="sunni", self_now="aurora")]
    assert got("What comes after one?") == [("two", "comes after", "one")]
    assert got("Is seven after two?") == [("seven", "is after", "two")]
    assert got("Is two after seven?") == [("two", "is not after", "seven")]
    assert ("seven", "is a", "symbol") in got("What is seven?")           # kinds chain across lessons


def test_words_that_are_closed_class_can_still_be_named_and_classed():
    web = _told(["Hello is a greeting.", "Yes is an answer.", "Thanks is a courtesy."])
    got = lambda q: [(i["lex"]["agent"], i["lex"]["action"], i["lex"]["object"]) for i in R.derive(web, q, speaker_now="sunni", self_now="aurora")]
    assert got("What is hello?") == [("hello", "is a", "greeting")]
    assert got("Is yes an answer?") == [("yes", "is a", "answer")]
    assert [st["relation"] for st in P.statements_in("Hello is a greeting.")] == ["be"]     # "greeting" is a thing here, not the act


def test_what_she_says_when_greeted_comes_from_the_rule_she_was_told():
    web = _told(["When I greet you, you say hello.", "When I thank you, you say welcome."])
    got = lambda h: [(i["lex"]["agent"], i["lex"]["action"], i["lex"]["object"]) for i in R.derive(web, h, speaker_now="sunni", self_now="aurora")]
    assert got("I greet you.") == [("I", "say", "hello")]
    assert got("I thank you today.") == [("I", "say", "welcome")]
    assert got("I like rain.") == []


def test_a_turn_that_opens_with_when_is_integrated_even_if_the_pipeline_calls_it_a_question():
    web = OntologicalWeb()
    systems = {"oets": type("O", (), {"web": web})(), "perception": None,
               "_last_pipeline_state": {"constraint_semantic_state": {"relational_form": {"question": True}}}}
    P.integrate_turn(systems, "When I greet you, you say hello.", session_id="x")
    assert [r["predicate"] for r in R.rules(web)] == ["say"]
    P.integrate_turn(systems, "When did you greet me?", session_id="x")          # a real question still is not
    assert len(R.rules(web)) == 1
