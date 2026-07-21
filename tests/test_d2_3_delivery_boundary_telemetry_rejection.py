# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Directive D2.3 (Rider 2, 2026-07-17): _sanitize_response() upgraded from
pattern-matching to a structural rule -- any candidate response matching
internal-telemetry shape (key=value runs, axis dumps, trace formats) is
REJECTED at the delivery boundary and routed to honest-abstain with a
logged reason, fail-closed, never delivering internals.

The pinned live regression: a device turn ("What's your name?") once
delivered the raw string "Active axes: existence=0.30, time/belief=0.28,
cost/purpose=0.15. Field state: heat=0.004, dominant-emotion=calm.
Energy/cost moved down since the last exchange." verbatim (D1's live
trace) -- no existing check in _sanitize_response was shape-based, only
specific-phrasing-based, so this slipped through every one of them.
"""
import json
import os
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANDROID_PY_DIR = os.path.join(REPO_ROOT, "flutter_app", "android", "app", "src", "main", "python")
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, ANDROID_PY_DIR)

import aurora_bridge  # type: ignore


def test_looks_like_internal_telemetry_detects_pinned_live_leak():
    leaked = (
        "Active axes: existence=0.30, time/belief=0.28, cost/purpose=0.15. "
        "Field state: heat=0.004, dominant-emotion=calm. Energy/cost moved "
        "down since the last exchange."
    )
    reason = aurora_bridge._looks_like_internal_telemetry(leaked)
    assert reason, "the pinned live leak was not detected as internal telemetry"


def test_looks_like_internal_telemetry_detects_key_value_runs_generically():
    """Structural, not string-specific: a DIFFERENT key=value dump the
    checker has never seen before must still be caught."""
    novel_leak = "heat=0.812, novelty=0.44, stagnation=0.03, coherence=0.91"
    reason = aurora_bridge._looks_like_internal_telemetry(novel_leak)
    assert reason
    assert "key_value_run" in reason


def test_looks_like_internal_telemetry_allows_ordinary_speech():
    ordinary = [
        "I think music helps people feel connected to each other.",
        "A guitar chord is a group of notes played together.",
        "I'm not sure, but I'd like to understand more about that.",
        "Good morning! I've been thinking about our last conversation.",
        "Photosynthesis is how plants turn light into energy.",
    ]
    for text in ordinary:
        reason = aurora_bridge._looks_like_internal_telemetry(text)
        assert reason == "", f"false positive on ordinary speech: {text!r} -> {reason!r}"


def test_looks_like_internal_telemetry_single_kv_pair_is_not_enough():
    """One incidental key=value-looking fragment (e.g. a casual aside)
    should not alone trigger rejection -- the rule requires the SHAPE of
    a dump (2+ pairs) or an explicit section label, not any equals sign."""
    single = "My confidence=0.8 today, but otherwise I feel like myself."
    reason = aurora_bridge._looks_like_internal_telemetry(single)
    assert reason == ""


def test_sanitize_response_rejects_pinned_leak_and_returns_honest_abstain(tmp_path):
    # Isolate the module-global _systems' state_dir for this call so the
    # rejection log this exercises writes into a scratch dir, not
    # whatever cwd happens to be during a real pytest run (the repo root).
    orig_systems = aurora_bridge._systems
    try:
        aurora_bridge._systems = {"state_dir": str(tmp_path)}
        leaked = (
            "Active axes: existence=0.30, time/belief=0.28, cost/purpose=0.15. "
            "Field state: heat=0.004, dominant-emotion=calm. Energy/cost moved "
            "down since the last exchange."
        )
        result = aurora_bridge._sanitize_response(leaked, "What's your name?")
        assert result == aurora_bridge._TELEMETRY_REJECTION_ABSTAIN_TEXT
        assert "active axes" not in result.lower()
        assert "=" not in result
    finally:
        aurora_bridge._systems = orig_systems


def test_sanitize_response_rejection_is_logged_not_silent(tmp_path):
    """Silent-fallback rule (this campaign's governing doctrine): a
    fail-closed catch must never be silent. Confirm the rejection is
    logged to disk with a reason, mirroring aurora.py's
    _log_constraint_fallback / constraint_fallback_log.jsonl pattern."""
    orig_systems = aurora_bridge._systems
    try:
        aurora_bridge._systems = {"state_dir": str(tmp_path)}
        leaked = "heat=0.44, novelty=0.91, stagnation=0.02"
        result = aurora_bridge._sanitize_response(leaked, "hello")
        assert result == aurora_bridge._TELEMETRY_REJECTION_ABSTAIN_TEXT

        log_path = os.path.join(str(tmp_path), "delivery_boundary_rejection_log.jsonl")
        assert os.path.exists(log_path), "rejection was not logged (silent-fallback rule)"
        with open(log_path, "r", encoding="utf-8") as f:
            lines = [json.loads(l) for l in f if l.strip()]
        assert len(lines) == 1
        entry = lines[0]
        assert entry["reason"]
        assert "heat=0.44" in entry["raw_text"]
        assert entry["timestamp"]
    finally:
        aurora_bridge._systems = orig_systems


def test_sanitize_response_still_passes_ordinary_grounded_reply():
    """Regression guard: the new check-0 must not suppress normal
    conversational content that happens to contain no telemetry shape."""
    ordinary = "I've been thinking about what you said earlier -- it stuck with me."
    result = aurora_bridge._sanitize_response(ordinary, "How are you feeling?")
    assert result == ordinary
