"""
Her own NonComp read routes the turn; the phrase lists run in shadow.

Authors: Sunni (Sir) Morningstar and Cael Devo
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

import json
import types

import pytest

import aurora
import aurora_turn_read as tr
from aurora_internal.aurora_utterance_parser import UtteranceParser


@pytest.fixture(autouse=True)
def _clean_read():
    saved = tr.ROUTE_BY_TURN_READ
    tr.reset_shadow()
    tr.form_turn_read(None, "")
    yield
    tr.ROUTE_BY_TURN_READ = saved
    tr.reset_shadow()
    tr.form_turn_read(None, "")


def _read(text, systems=None):
    return tr.read_from(text, UtteranceParser().parse(text), None, systems=systems)


class _Core:
    self_name = "Aurora"

    def get_entity(self, name):
        return object() if name in {"sunni", "cael", "aurora"} else None


@pytest.mark.parametrize("text,question,about_her,inner", [
    ("How are you feeling?", True, True, True),
    ("Do you like music?", True, True, True),
    ("who built you?", True, True, False),
    ("What is photosynthesis?", True, False, False),
    ("Tell me about the moon", True, False, False),
    ("Can you explain gravity?", True, False, False),
    ("Do you know what photosynthesis is?", True, False, False),
    ("I had a rough day at work", False, False, False),
    ("The weather is nice", False, False, False),
])
def test_her_read_answers_the_routing_questions(text, question, about_her, inner):
    read = _read(text)
    assert read.is_question is question
    assert read.about_her is about_her
    assert read.inner_state is inner


def test_a_named_person_she_holds_is_about_her_only_when_asked():
    systems = {"core_identity": _Core()}
    assert _read("Who is Sunni?", systems).about_her is True
    # A statement that merely mentions Sunni is not a question about her;
    # the marker list says it is (it matches any text containing "sunni").
    assert _read("Sunni is tired today", systems).about_her is False
    assert aurora._lexical_is_aurora_self_question("Sunni is tired today") is True


def test_recall_is_the_speaker_asking_what_passed_between_them():
    assert _read("What did I just tell you?").recall is True
    assert _read("what is my name").recall is True
    assert _read("Could you tell me the time?").recall is False
    assert _read("What did I just tell you?").prefer_perspective is False


def test_route_uses_her_read_for_this_turn_and_records_the_list():
    tr.form_turn_read(None, "Sunni is tired today", parse=UtteranceParser().parse)
    assert aurora._is_aurora_self_question("Sunni is tired today") is False
    report = tr.shadow_report()
    assert report["totals"]["about_her"]["disagree"] == 1
    assert report["recent_disagreements"][-1]["lexical"] is True


def test_switch_off_restores_the_lists_and_keeps_the_comparison():
    tr.ROUTE_BY_TURN_READ = False
    tr.form_turn_read(None, "Sunni is tired today", parse=UtteranceParser().parse)
    assert aurora._is_aurora_self_question("Sunni is tired today") is True
    assert tr.shadow_report()["totals"]["about_her"]["disagree"] == 1


def test_text_she_has_not_read_falls_back_to_the_list():
    tr.form_turn_read(None, "How are you feeling?", parse=UtteranceParser().parse)
    assert aurora._looks_like_question("tell me something else") is True
    assert tr.shadow_report()["totals"]["is_question"]["no_read"] == 1


def test_the_turn_interprets_once_and_the_guidance_reuses_it():
    calls = []

    class _Interp:
        def interpret(self, text):
            calls.append(text)
            return types.SimpleNamespace(to_dict=lambda: {"frame": "exploratory", "semantic_override": None,
                                                         "noncomp_state": {"dominant_target": "X"}})

    systems = {"noncomp_reflexive_interpreter": _Interp()}
    read = tr.form_turn_read(systems, "How are you feeling?", parse=UtteranceParser().parse)
    assert read.source == "noncomp" and read.dominant_target == "X"
    assert calls == ["How are you feeling?"]
    assert tr.reuse_interpretation(systems, "how are you  feeling?")["frame"] == "exploratory"
    assert tr.reuse_interpretation(systems, "something else") is None


def test_comparison_is_journalled_once_per_question_per_turn(tmp_path):
    systems = {"state_dir": str(tmp_path)}
    tr.form_turn_read(systems, "Sunni is tired today", parse=UtteranceParser().parse)
    for _ in range(3):
        aurora._is_aurora_self_question("Sunni is tired today")
    aurora._looks_like_question("Sunni is tired today")
    tr.flush_turn(systems)
    lines = (tmp_path / tr.SHADOW_JOURNAL_NAME).read_text().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert [c["kind"] for c in record["calls"]] == ["about_her", "is_question"]
    assert record["disagreements"] == 1


def test_shadow_journal_is_a_journal_for_one_state():
    from aurora_internal.aurora_store_ownership import classify, JOURNAL
    assert classify(tr.SHADOW_JOURNAL_NAME) == JOURNAL
