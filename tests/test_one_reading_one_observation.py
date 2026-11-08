#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""One reading, one observation (Sunni, 2026-11-08): within a turn the same
sentence is parsed -- and fed to lexical grounding -- once; a new turn, or a
promotion that changes how the text parses, derives it again."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import aurora_internal.aurora_constraint_semantic_continuity as C  # noqa: E402
import aurora_internal.aurora_lexical_grounding as L  # noqa: E402
import aurora_internal.aurora_turn_persistence as P  # noqa: E402


class CountingGrounding:
    def __init__(self):
        self.fed = []
        self._candidates = {}

    def observe_lexical_context(self, *, word, relational_form, provenance="", **_):
        self.fed.append(word)
        return {"action": "no_signal"}

    def has_promoted_relation_role(self, word):
        return any(c.word == word and c.status == "promoted"
                   and dict(c.structural_geometry or {}).get("slot") == "relation"
                   for c in self._candidates.values())


def _turn():
    P.begin_write_batch({})
    P.end_write_batch([])


def test_same_sentence_feeds_once_per_turn(monkeypatch):
    g = CountingGrounding()
    monkeypatch.setattr(L, "_global_lexical_grounding", g)
    _turn()
    P.begin_write_batch({})
    first = C.extract_relational_form("The moon reflects sunlight.")
    fed_once = list(g.fed)
    for _ in range(16):
        again = C.extract_relational_form("The moon reflects sunlight.")
        assert again == first and again is not first
    assert g.fed == fed_once and fed_once, "16 more parses, no more observations"
    P.end_write_batch([])
    _turn()
    P.begin_write_batch({})
    C.extract_relational_form("The moon reflects sunlight.")
    P.end_write_batch([])
    assert g.fed == fed_once * 2, "a new turn is a new reading"


def test_a_promotion_rederives_the_parse(monkeypatch):
    g = CountingGrounding()
    monkeypatch.setattr(L, "_global_lexical_grounding", g)
    _turn()
    P.begin_write_batch({})
    before = C.extract_relational_form("glorp wibble zonk")
    g._candidates["c"] = L.LexicalCandidate(
        candidate_id="LEX:w", word="wibble", component_id="warp:w", axis_profile={},
        applicability_family="F", parent_ids=[], structural_geometry={"slot": "relation"},
        dominant_constraints=[], status="promoted", evidence=[])
    after = C.extract_relational_form("glorp wibble zonk")
    P.end_write_batch([])
    assert after == C.extract_relational_form.__wrapped_uncached__("glorp wibble zonk")
    assert after != before
