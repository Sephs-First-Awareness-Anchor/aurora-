# Authors: Sunni (Sir) Morningstar & Cael Devo
"""FIX-A132: brackets are punctuation, and transport labels are not language.

The live web held "[afterthought]", "[internal", "understanding.]", "[user]",
"[rec" ... as words: the tokenizer stripped ordinary punctuation but not brackets,
a leading internal-caller label was heard, and a recall marker cut off by a length
limit was not recognised.
"""
from __future__ import annotations

import re

from aurora_expression_perception import (
    ExpressionPerceptionEngine, strip_recall_markers, strip_transport_labels)
from scripts.prune_recall_marker_nodes import is_recall_marker, prune_web_dict


def test_leading_transport_label_is_dropped_but_what_follows_is_kept():
    assert strip_transport_labels("[AFTERTHOUGHT] what do you feel?") == "what do you feel?"
    assert strip_transport_labels("[PRESSURE ROUTING] gap at 0.2") == "gap at 0.2"
    assert strip_transport_labels("[CODE] [PRESSURE] x") == "x"


def test_lower_case_and_mid_text_brackets_are_left_for_the_tokenizer():
    assert strip_transport_labels("[user] hi") == "[user] hi"
    assert strip_transport_labels("she wrote [NOTE] there") == "she wrote [NOTE] there"


def test_a_cut_off_recall_marker_is_dropped():
    assert strip_recall_markers("keep this [rec") == "keep this"
    assert strip_recall_markers("keep this [recalled:cur") == "keep this"
    assert strip_recall_markers("a [recalled:x] b") == "a b"
    assert strip_recall_markers("a [record] b") == "a [record] b"


def test_no_bracket_ever_becomes_a_word(tmp_path):
    eng = ExpressionPerceptionEngine(state_dir=str(tmp_path))
    for text in ("[AFTERTHOUGHT] What do you feel about learning?",
                 "[user] hello there [assistant] hello to you friend",
                 "She wrote [Internal: x? y.] on the card and left.",
                 "tail cut off here [rec"):
        eng.ingest_interaction({"input": text}, mode="gateway")
    nodes = eng.oets.web.nodes
    assert not [n for n in nodes if re.search(r"[\[\]]", n)]
    assert "afterthought" not in nodes and "learning" in nodes


def test_prune_takes_any_bracket_token_and_nothing_else():
    assert all(is_recall_marker(w) for w in ("[afterthought]", "[internal", "point?]", "[rec", "[recalled:x]"))
    assert not any(is_recall_marker(w) for w in ("afterthought", "internal", "point", "record"))
    data = {"nodes": {"[user]": {}, "user": {}}, "categories": {"growth": ["[user]", "user"]},
            "relations": {"1": {"source_word": "[user]", "target_word": "user"},
                          "2": {"source_word": "user", "target_word": "user"}}}
    assert prune_web_dict(data) == {"nodes": 1, "relations": 1, "category_entries": 1}
    assert list(data["nodes"]) == ["user"] and data["categories"]["growth"] == ["user"]
