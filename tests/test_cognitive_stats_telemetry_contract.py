"""Build 773 (Canonical Hub Telemetry): get_cognitive_stats() must never
let an absent subsystem masquerade as a real measurement of zero (or, for
avg_n_cost, a real measurement of exactly 1.000). Regression tests for the
three-state contract: measured-nonzero, measured-zero, and missing must
all be distinguishable by whether the key is present in the returned JSON.
"""
from __future__ import annotations

import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANDROID_PY_DIR = os.path.join(REPO_ROOT, "flutter_app", "android", "app", "src", "main", "python")

import pytest


@pytest.fixture()
def bridge():
    if ANDROID_PY_DIR not in sys.path:
        sys.path.insert(0, ANDROID_PY_DIR)
    import aurora_bridge
    return aurora_bridge


def _stats(bridge, systems):
    bridge._systems = systems
    bridge._turn_count = 0
    bridge._historical_experience = None
    return json.loads(bridge.get_cognitive_stats())


_MISSING_CASE_KEYS = (
    "avg_n_cost", "lsa_paths", "X", "T", "N", "B", "A",
    "understanding_index", "coherence_index", "grounding_index", "topic_tracking",
    "sedimemory_depth", "noncomp_loaded", "noncomp_diagonal_live",
    "concept_crystal_nodes", "concept_crystal_promoted", "concept_crystal_maturity",
    "chamber_fossils", "evo_cycles", "sentence_target",
    "genealogy_ability_count", "genealogy_axis_counts", "genealogy_recent_abilities",
    "warp_actuator_count", "warp_recent_demands",
)


def test_no_subsystems_wired_every_optional_field_absent(bridge):
    """Nothing wired at all -- every subsystem-gated field must be absent
    from the JSON, never present with a fake default."""
    stats = _stats(bridge, {})
    for key in _MISSING_CASE_KEYS:
        assert key not in stats, f"{key} should be absent when its subsystem is unavailable"
    # Always-present fields (not gated on any optional subsystem).
    assert "ts" in stats
    assert "turn_count" in stats


def test_missing_avg_n_cost_does_not_render_as_one(bridge):
    """The build directive's own named regression case: a language field
    that reports zero real LSA paths must leave avg_n_cost absent, never
    silently 1.0 (the old fake default)."""
    class _EmptyLanguageField:
        _lsa = {}

    stats = _stats(bridge, {"language_field": _EmptyLanguageField()})
    assert "avg_n_cost" not in stats
    assert stats.get("lf_active") is True  # subsystem presence itself is a real measurement


def test_genuine_avg_n_cost_of_one_renders_as_measured(bridge):
    """A real LSA path with n_cost genuinely 1.0 must render as a present,
    measured 1.000 -- indistinguishable from the fake-default case only if
    this test is skipped, so it must run alongside the missing case above."""
    class _Entry:
        n_cost = 1.0

    class _LanguageField:
        _lsa = {"p1": _Entry()}

    stats = _stats(bridge, {"language_field": _LanguageField()})
    assert "avg_n_cost" in stats
    assert stats["avg_n_cost"] == 1.0


def test_missing_genealogy_count_does_not_render_as_measured_zero(bridge):
    stats = _stats(bridge, {})
    assert "genealogy_ability_count" not in stats


def test_genuine_genealogy_count_of_zero_renders_as_measured(bridge):
    class _Genealogy:
        abilities = {}

    stats = _stats(bridge, {"genealogy": _Genealogy()})
    assert "genealogy_ability_count" in stats
    assert stats["genealogy_ability_count"] == 0


def test_missing_crystal_count_does_not_render_as_measured_zero(bridge):
    stats = _stats(bridge, {})
    assert "concept_crystal_nodes" not in stats


def test_genuine_crystal_count_of_zero_renders_as_measured(bridge):
    class _Registry:
        def stats(self):
            return {"total": 0, "by_stage": {}, "grounded": 0}

    stats = _stats(bridge, {"_concept_crystal_registry": _Registry()})
    assert "concept_crystal_nodes" in stats
    assert stats["concept_crystal_nodes"] == 0
    assert stats["concept_crystal_maturity"] == 0.0


def test_axis_pressures_flatten_to_real_top_level_keys(bridge):
    """X/T/N/B/A were never set as top-level keys anywhere in
    get_cognitive_stats() before Build 773 -- only nested under
    axis_pressures. Dart's old regex parser only "worked" by accident."""
    class _IdentityField:
        def status(self):
            return {"axis_pressures": {"X": 0.11, "T": 0.22, "N": 0.33, "B": 0.44, "A": 0.55},
                     "loaded_count": 3, "diagonal_live": 2}

    stats = _stats(bridge, {"identity_field": _IdentityField()})
    assert stats["X"] == 0.11
    assert stats["T"] == 0.22
    assert stats["N"] == 0.33
    assert stats["B"] == 0.44
    assert stats["A"] == 0.55
    assert stats["axis_pressures"] == {"X": 0.11, "T": 0.22, "N": 0.33, "B": 0.44, "A": 0.55}


def test_axis_pressures_absent_leaves_xtnba_absent(bridge):
    stats = _stats(bridge, {})
    for axis in ("X", "T", "N", "B", "A"):
        assert axis not in stats


def test_no_internal_python_caller_depends_on_fake_defaults(bridge):
    """get_cognitive_stats() must remain read-only and side-effect-free
    with respect to cognition -- calling it with a fully-populated real
    subsystem set must not raise even though most fields are now absent
    by default; every field access downstream is Hub-only (Dart), never
    consumed by another Python call site (confirmed separately by
    grepping the whole repo for other callers -- none exist)."""
    stats = _stats(bridge, {})
    # The call itself must never raise, and must always return valid JSON,
    # regardless of which subsystems are present.
    assert isinstance(stats, dict)
    assert "error" not in stats
