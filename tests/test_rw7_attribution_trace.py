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
