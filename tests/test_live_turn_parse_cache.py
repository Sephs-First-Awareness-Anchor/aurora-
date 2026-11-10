"""The repeated live-turn parses must stay semantically identical."""
from __future__ import annotations

from aurora_internal.aurora_turn_parse_cache import TurnParseCache
from aurora_internal.aurora_utterance_parser import UtteranceParser


def test_same_message_is_parsed_once_across_three_readers():
    calls = []

    def parse(text):
        calls.append(text)
        return {"topic": "rain", "relational_form": {"role": ["observer"]}}

    cache = TurnParseCache(parse)
    attention = cache.parse("What makes rain fall?")
    attention["relational_form"]["role"].append("attention")
    raw = cache.parse("What makes rain fall?")
    raw["strata_context"] = {"heat": 0.5}
    synthesis = cache.parse("What makes rain fall?")

    assert calls == ["What makes rain fall?"]
    assert raw == synthesis
    assert attention != synthesis
    assert "strata_context" not in synthesis


def test_grounded_rewrite_triggers_new_parse():
    calls = []

    def parse(text):
        calls.append(text)
        return {"topic": text.lower()}

    cache = TurnParseCache(parse)
    cache.parse("unknown word")
    cache.parse("unknown word")
    grounded = cache.parse("grounded meaning")
    cache.parse("grounded meaning")
    assert grounded["topic"] == "grounded meaning"
    assert calls == ["unknown word", "grounded meaning"]


def test_same_parser_output_as_uncached_for_real_utterances():
    parser = UtteranceParser()
    cache = TurnParseCache(parser.parse)
    for sentence in (
        "What is your understanding of time?",
        "No, I meant the previous example.",
        "Show me how you reached this conclusion.",
        "Can rain cause changes in soil?",
    ):
        original = parser.parse(sentence)
        assert cache.parse(sentence) == original
        assert cache.parse(sentence) == original
