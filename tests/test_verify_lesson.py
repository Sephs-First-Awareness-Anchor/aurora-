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
