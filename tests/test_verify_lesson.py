# Authors: Sunni (Sir) Morningstar & Cael Devo
"""The probe runner's reading and judging (the live run is checked by hand, not in CI)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import verify_lesson as V


def test_lesson_lines_skip_comments_and_blanks():
    assert V.parse_lesson("# note\n\nThe letter b comes after a.\n  # x\nThe letter c comes after b.\n") == [
        "The letter b comes after a.", "The letter c comes after b."]


def test_probes_parse_sections_alternatives_and_forbidden_terms():
    ps = V.parse_probes("[before]\nWhat comes after b? => !c\n[after]\nIs a after b? => not after | not sure ;; !is after a\n")
    assert [(p["section"], p["ask"]) for p in ps] == [("before", "What comes after b?"), ("after", "Is a after b?")]
    assert ps[0]["terms"] == [(["c"], True)]
    assert ps[1]["terms"] == [(["not after", "not sure"], False), (["is after a"], True)]


@pytest.mark.parametrize("bad", ["The letter b comes after a. => b", "Is b after a?", "[later]\nIs b after a? => yes", "Is b after a? =>"])
def test_a_probe_must_be_a_question_with_an_expectation(bad):
    with pytest.raises(ValueError):
        V.parse_probes(bad)


def test_judge_uses_her_reply_only_case_insensitive():
    terms = [(["is after"], False), (["not sure"], True)]
    assert V.judge("B is after a.", terms) == (True, [])
    ok, why = V.judge("I am not sure if b is after a.", terms)
    assert not ok and why == ["contains 'not sure'"]
    ok, why = V.judge("", terms)
    assert not ok and why == ["lacks 'is after'"]


def test_every_shipped_probe_file_parses_and_has_a_lesson():
    lessons = Path(__file__).resolve().parent.parent / "lessons"
    for pf in lessons.glob("*.probes"):
        assert V.parse_probes(pf.read_text(encoding="utf-8")), pf.name
        assert pf.with_suffix(".txt").exists(), pf.name


def test_terms_match_whole_words_so_a_letter_is_not_found_inside_comes():
    assert V.judge("after. comes.", [(["c"], True)]) == (True, [])
    assert V.judge("C comes after b.", [(["c"], False)]) == (True, [])


def test_a_correction_block_is_said_after_the_lesson_proper():
    text = "# n\nB comes after a.\n#@correction\nB does not come after a.\n"
    assert V.parse_lesson_blocks(text) == {"teach": ["B comes after a."], "correction": ["B does not come after a."]}
    assert V.parse_lesson(text) == ["B comes after a."]


def test_after_correction_is_a_probe_section():
    ps = V.parse_probes("[after-correction]\nIs b after a? => not after\n")
    assert ps[0]["section"] == "after-correction"


@pytest.mark.parametrize("line", [
    "When I greet you, you say hello.", "If I ask you, you answer me.", "You comfort me if I feel sad.",
    "You should always answer.", "I want you to be kind.", "You feel curious when you learn something new.",
    "You like rain.", "My name is Sunni.", "Devlin is my brother.", "Aurora is not a person.", "I am Sunni.",
])
def test_lint_rejects_prescribed_behaviour_assigned_states_and_identity_stated_as_fact(line):
    assert V.lint_lesson([line])


@pytest.mark.parametrize("line", [
    "Hello is a greeting.", "A greeting is a word people say to begin talking.",
    "Suppose that my name is Rowan.", "Imagine that Mara is the sister of Teo.",
    "Pretend that Teo does not like tea.", "People feel sad when they lose something.",
    "The letter b comes after a.", "Actually, b does not come after a.",
])
def test_lint_lets_through_meaning_general_statements_and_explicit_examples(line):
    assert V.lint_lesson([line]) == []


def test_a_supposed_example_is_exempt_from_identity_rules_only():
    assert V.lint_lesson(["Suppose that you like rain."])          # still assigns her a want


def test_paraphrases_all_must_be_questions_and_are_kept():
    ps = V.parse_probes("[after]\nIs b after a? || Does b come after a? => is after\n")
    assert ps[0]["asks"] == ["Is b after a?", "Does b come after a?"]
    with pytest.raises(ValueError):
        V.parse_probes("[after]\nIs b after a? || B comes after a. => is after\n")


def test_twin_maps_names_and_keeps_capitals_and_whole_words():
    twin = V.parse_twin("[after]\n@twin mara=nia teo=omar tea=coffee\n")
    assert twin == {"mara": "nia", "teo": "omar", "tea": "coffee"}
    assert V.substitute("Mara likes tea. Teo steams.", twin) == "Nia likes coffee. Omar steams."
    assert V.substitute_terms([(["mara likes tea"], False)], twin) == [(["nia likes coffee"], False)]


def test_a_gap_section_exists_and_a_gap_fails_readiness():
    ps = V.parse_probes("[gap]\nWho am I? => you are\n")
    assert ps[0]["section"] == "gap"
    base = {"lint": [], "failed": 0, "open_gaps": 1, "twin": {}}
    assert V.status(base)[0] == 2
    assert V.status(dict(base, open_gaps=0))[0] == 0
    assert V.status(dict(base, open_gaps=0, failed=1))[0] == 1
    assert V.status(dict(base, lint=[{"line": "x", "why": "y"}]))[0] == 3
