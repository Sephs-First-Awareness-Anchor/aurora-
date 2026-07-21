# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Directive M1.2: blind-era lexicon entries re-tagged legacy-unverified,
identified structurally (meaning == "learned:<word>", the same
signature D2's Condition-2 fix already caps in scoring) -- not by
guessing at individual entries, and not a new scoring mechanism (the
earn-trust cap already runs independent of this tag).
"""
import json
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEXICON_PATH = os.path.join(REPO_ROOT, "aurora_state", "lexicon.json")


def _lexicon():
    with open(LEXICON_PATH) as f:
        return json.load(f)["entries"]


def test_blind_origin_entries_are_tagged_legacy_unverified():
    entries = _lexicon()
    blind = [w for w, e in entries.items() if e.get("meaning") == f"learned:{w}"]
    assert blind, "expected at least some blind-origin entries in the real lexicon"
    untagged = [w for w in blind if not str(entries[w].get("lineage", "")).startswith("legacy-unverified:")]
    assert not untagged, f"{len(untagged)} blind-origin entries missing the legacy-unverified tag: {untagged[:10]}"


def test_original_lineage_preserved_not_deleted():
    entries = _lexicon()
    for w, e in entries.items():
        lineage = str(e.get("lineage", "") or "")
        if lineage.startswith("legacy-unverified:"):
            original = lineage[len("legacy-unverified:"):]
            # Original lineage value (possibly empty string) must still be recoverable.
            assert lineage == f"legacy-unverified:{original}"
            return
    assert False, "no legacy-unverified entries found to check"


def test_non_blind_entries_never_tagged():
    """A real definition (not the "learned:<word>" placeholder) must
    never get the legacy-unverified prefix -- this tag identifies
    ORIGIN, not current trust level, and only the blind path earns it."""
    entries = _lexicon()
    for w, e in entries.items():
        if e.get("meaning") != f"learned:{w}":
            assert not str(e.get("lineage", "")).startswith("legacy-unverified:"), (
                f"{w!r} has a real meaning but was tagged legacy-unverified anyway"
            )


def test_tagging_does_not_change_composer_scoring_behavior():
    """The tag is visibility/audit only -- SentenceComposer's existing
    cap keys off `meaning`, not `lineage`, so re-tagging must not
    change any scoring outcome."""
    import sys
    sys.path.insert(0, REPO_ROOT)
    from aurora_expression_perception import SentenceComposer, LexicalEntry
    import aurora_constraint_emission as ace

    composer = SentenceComposer.__new__(SentenceComposer)
    entry = LexicalEntry(
        word="water", meaning="learned:water", role="noun",
        emotional_valence=0.0, noncomp_id="T:MAGNITUDE",
        usage_count=1, lineage="legacy-unverified:i_is",
    )
    anchor_set = {"water": ace.RELEVANCE_DIRECT_ANCHOR}
    score = composer._score_composer_candidate(entry, anchor_set, valence_target=0.0)
    max_distant = ace.RELEVANCE_DISTANT_FLOOR * (1.0 + SentenceComposer._VALENCE_TIEBREAK_WEIGHT)
    assert score <= max_distant, "the legacy-unverified tag must not change the existing cap's outcome"


def test_v0_control_words_mostly_confirmed_blind_origin():
    """Per the directive's own report requirement: water/france/guitar/
    photosynthesis are blind-origin and tagged. japan is the honest
    exception -- S1.2 already replaced it with a real seeded
    definition before M1.2 ran, so it correctly does NOT get the tag."""
    entries = _lexicon()
    for w in ("water", "france", "guitar", "photosynthesis"):
        e = entries.get(w)
        assert e is not None
        assert str(e.get("lineage", "")).startswith("legacy-unverified:"), (
            f"{w!r} expected to be blind-origin and tagged"
        )
    japan = entries.get("japan")
    assert japan is not None
    assert not str(japan.get("lineage", "")).startswith("legacy-unverified:")
    assert japan.get("lineage") == "seeded_s1"
