# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
RW7 (Architecture Wiring Audit, 2026-07-20): the attribution capture
module is a read-only observer -- disabled by default, zero cost/effect
on any normal boot. These tests cover its own mechanics only (the real
attribution measurement is scripts/rw7_attribution_run.py, a live,
multi-minute battery run, not something to re-run in the unit suite).
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_internal.aurora_attribution_trace import (  # noqa: E402
    enable_capture, disable_capture, is_capture_enabled,
    record_composer_raw, pop_composer_raw,
    record_word_sources_and_motifs, pop_word_sources_and_motifs,
)


def test_disabled_by_default():
    disable_capture()
    assert is_capture_enabled() is False


def test_record_is_a_noop_when_disabled():
    disable_capture()
    record_composer_raw("should not be captured")
    assert pop_composer_raw() is None


def test_enable_then_record_then_pop():
    try:
        enable_capture()
        assert is_capture_enabled() is True
        record_composer_raw("hello world")
        assert pop_composer_raw() == "hello world"
    finally:
        disable_capture()


def test_pop_clears_the_scratch_slot():
    try:
        enable_capture()
        record_composer_raw("first")
        assert pop_composer_raw() == "first"
        assert pop_composer_raw() is None
    finally:
        disable_capture()


def test_record_accepts_dict_shape_matching_compose_return():
    """SentenceComposer.compose() returns a dict with an 'expression' key
    (confirmed live: aurora_governance_persistence_gateway.py:1147 reads
    expr_result.get('expression', '')) -- the capture must unwrap it the
    same way, not just handle a bare string."""
    try:
        enable_capture()
        record_composer_raw({"expression": "the actual text", "other_field": 123})
        assert pop_composer_raw() == "the actual text"
    finally:
        disable_capture()


def test_record_degrades_gracefully_on_garbage_input():
    try:
        enable_capture()
        record_composer_raw(None)
        assert pop_composer_raw() == ""
        record_composer_raw(12345)
        assert pop_composer_raw() == "12345"
    finally:
        disable_capture()


class _FakeRole:
    def __init__(self, value):
        self.value = value


class _FakeMotif:
    def __init__(self, pattern_id, roles):
        self.pattern_id = pattern_id
        self.role_sequence = [_FakeRole(r) for r in roles]


class _FakeComposer:
    def __init__(self, word_sources, motifs):
        self._last_word_sources = word_sources
        self._last_motifs_used = motifs


def test_word_sources_and_motifs_disabled_by_default_is_noop():
    disable_capture()
    record_word_sources_and_motifs(_FakeComposer({"hi": {"tag": "X"}}, []))
    ws, ms = pop_word_sources_and_motifs()
    assert ws is None
    assert ms is None


def test_word_sources_and_motifs_capture_and_pop():
    try:
        enable_capture()
        composer = _FakeComposer(
            word_sources={"leaves": {"tag": "X:MAGNITUDE", "candidate_source": "dps_crystal",
                                      "usage_count_at_selection": 0}},
            motifs=[_FakeMotif("motif_42", ["agent", "action", "object"])],
        )
        record_word_sources_and_motifs(composer)
        ws, ms = pop_word_sources_and_motifs()
        assert ws == {"leaves": {"tag": "X:MAGNITUDE", "candidate_source": "dps_crystal",
                                  "usage_count_at_selection": 0}}
        assert ms == [{"motif_id": "motif_42", "role_sequence": ["agent", "action", "object"]}]
    finally:
        disable_capture()


def test_word_sources_and_motifs_pop_clears_scratch():
    try:
        enable_capture()
        record_word_sources_and_motifs(_FakeComposer({"a": {}}, []))
        pop_word_sources_and_motifs()
        ws, ms = pop_word_sources_and_motifs()
        assert ws is None
        assert ms is None
    finally:
        disable_capture()


def test_word_sources_and_motifs_degrades_gracefully_on_garbage():
    try:
        enable_capture()
        record_word_sources_and_motifs(object())  # no _last_word_sources/_last_motifs_used
        ws, ms = pop_word_sources_and_motifs()
        assert ws == {}
        assert ms == []
    finally:
        disable_capture()
