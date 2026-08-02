# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
WARP Universalization Directive, Phase 3d (2026-07-25, ratified priority
#4 of 4, last: mid-comprehension parse confidence).

_emit_honest_abstain_and_seek() (aurora.py:4635) was the ONLY confession
point in the whole reasoning/expression pipeline, and it only fires at
the terminal chokepoint when composition returns literally nothing.
The comprehension stages upstream -- starting with the very first one,
UtteranceParser building state.parsed at _chain_up1_information
(aurora.py:14125, called once per live turn) -- never confessed at all.

_confess_low_confidence_parse() adds a confession at the earliest point
Aurora can know she didn't understand: UtteranceParser found neither a
real communicative frame (frame == "unknown") NOR any topic_words. No
fabricated numeric "confidence" score is invented -- UtteranceIntent
carries none -- this uses the two real signals the parser already
produces.
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import aurora as A  # noqa: E402
import aurora_warp_protocol as awp  # noqa: E402
from aurora_warp_protocol import WarpTrigger  # noqa: E402


def _real_shaped_warp_guard_spy(calls):
    """Mirrors warp_guard's real signature exactly -- a call shaped
    differently would raise TypeError here the same way it would
    against the real function. _confess_low_confidence_parse imports
    warp_guard locally (same pattern as _emit_honest_abstain_and_seek),
    so the spy must replace it on the real aurora_warp_protocol module,
    not on the aurora module namespace."""
    def _spy(
        source: str, layer: str, trigger: str, *,
        unresolved_text: str = "", expected=None, actual=None,
        participants=None, profile=None, local_attempts=None,
        severity: float = 0.5, persistence_key: str = "",
    ):
        calls.append({
            "source": source, "layer": layer, "trigger": trigger,
            "unresolved_text": unresolved_text,
            "severity": severity, "persistence_key": persistence_key,
        })
        return None
    return _spy


def test_unclassifiable_parse_confesses(monkeypatch):
    calls = []
    monkeypatch.setattr(awp, "warp_guard", _real_shaped_warp_guard_spy(calls))

    A._confess_low_confidence_parse("asdkjqwe", {"frame": "unknown", "topic_words": []})

    assert len(calls) == 1
    call = calls[0]
    assert call["source"] == "comprehension"
    assert call["layer"] == "chain_up1_information"
    assert call["trigger"] == WarpTrigger.FAILED_COMPREHENSION
    assert call["unresolved_text"] == "asdkjqwe"
    assert call["persistence_key"] == "asdkjqwe"


def test_real_frame_does_not_confess(monkeypatch):
    """A trivial but genuinely classified utterance ("ok" -> acknowledging)
    is not a comprehension failure."""
    calls = []
    monkeypatch.setattr(awp, "warp_guard", _real_shaped_warp_guard_spy(calls))

    A._confess_low_confidence_parse("ok", {"frame": "acknowledging", "topic_words": []})

    assert calls == []


def test_topic_words_present_does_not_confess(monkeypatch):
    """Even with frame == unknown, having identified topic words means
    there's something real to work with -- not a comprehension miss."""
    calls = []
    monkeypatch.setattr(awp, "warp_guard", _real_shaped_warp_guard_spy(calls))

    A._confess_low_confidence_parse("tell me about dogs", {"frame": "unknown", "topic_words": ["dogs"]})

    assert calls == []


def test_empty_text_does_not_confess(monkeypatch):
    calls = []
    monkeypatch.setattr(awp, "warp_guard", _real_shaped_warp_guard_spy(calls))

    A._confess_low_confidence_parse("", {"frame": "unknown", "topic_words": []})
    A._confess_low_confidence_parse("   ", {"frame": "unknown", "topic_words": []})

    assert calls == []


def test_missing_parse_keys_treated_as_unclassified(monkeypatch):
    """A parse that raised and fell back to {} (state.parsed = {} in
    _chain_up1_information's except branch) should still be recognized
    as unclassifiable -- .get() defaults, not a KeyError."""
    calls = []
    monkeypatch.setattr(awp, "warp_guard", _real_shaped_warp_guard_spy(calls))

    A._confess_low_confidence_parse("asdkjqwe", {})

    assert len(calls) == 1
    assert calls[0]["trigger"] == WarpTrigger.FAILED_COMPREHENSION


def test_confession_exceptions_are_swallowed(monkeypatch):
    def _always_raises(*a, **kw):
        raise RuntimeError("warp field unavailable")
    monkeypatch.setattr(awp, "warp_guard", _always_raises)

    # Must not raise -- confession-path failures never break comprehension.
    A._confess_low_confidence_parse("asdkjqwe", {"frame": "unknown", "topic_words": []})


def test_chain_up1_information_wires_the_confession():
    """Structural confirmation of the wiring in aurora.py, matching this
    campaign's established pattern for verifying call sites inside the
    massive chain-stage functions (see test_m1_1a_relation_pairs.py's
    test_chain_down5_understanding_calls_tier2_logger)."""
    with open(os.path.join(REPO_ROOT, "aurora.py"), "r", encoding="utf-8") as f:
        source = f.read()
    idx = source.index("def _chain_up1_information(user_text: str, systems: dict, state: Any) -> None:")
    # Widened from 600 (zip integration phase D, 2026-07-29): exception
    # instrumentation added lines to the preceding handler in this
    # function, pushing the anchor further out without changing the
    # actual wiring relationship being checked.
    block = source[idx:idx + 900]
    assert "_confess_low_confidence_parse" in block
