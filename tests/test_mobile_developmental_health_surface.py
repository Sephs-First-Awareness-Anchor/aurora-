#!/usr/bin/env python3
"""Regression coverage for Build 650 Multimodal Representational Autonomy
Directive, Section XXIII/XXIV (Sunni & Cael): get_mobile_developmental_health()
must classify systems as fatal/degraded/optional and never report "healthy"
when a major developmental organ is silently missing.
"""
from __future__ import annotations

import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANDROID_PY_DIR = os.path.join(REPO_ROOT, "flutter_app", "android", "app", "src", "main", "python")


def _bridge():
    if ANDROID_PY_DIR not in sys.path:
        sys.path.insert(0, ANDROID_PY_DIR)
    import aurora_bridge
    return aurora_bridge


def _full_systems():
    """A systems dict with every checked key present and truthy."""
    return {
        "language_field": object(), "identity_field": object(), "consciousness": object(),
        "sedimemory": object(), "lattice": object(), "geological_baseline": object(),
        "genealogy": object(), "recursive_causal_waveform": object(),
        "sensory_crystal": object(), "dimensional": object(),
        "_curiosity_engine": object(), "chamber": object(),
        "hardware": object(),
    }


def test_fully_healthy_boot_reports_healthy(monkeypatch):
    bridge = _bridge()
    monkeypatch.setattr(bridge, "_systems", _full_systems(), raising=False)
    monkeypatch.setattr(bridge, "_dream_substrate_boot_ok", True, raising=False)

    payload = json.loads(bridge.get_mobile_developmental_health())
    assert payload["overall"] == "healthy"
    assert payload["fatal_missing"] == []
    assert payload["degraded_missing"] == []
    assert all(payload["optional_status"].values())


def test_missing_language_field_is_fatal_not_silently_healthy(monkeypatch):
    """This is the exact regression Section XXIII names: a fatal system
    missing must never be swallowed into a blanket 'ready' report."""
    systems = _full_systems()
    systems["language_field"] = None
    bridge = _bridge()
    monkeypatch.setattr(bridge, "_systems", systems, raising=False)
    monkeypatch.setattr(bridge, "_dream_substrate_boot_ok", True, raising=False)

    payload = json.loads(bridge.get_mobile_developmental_health())
    assert payload["overall"] == "fatal"
    assert "language_field" in payload["fatal_missing"]


def test_missing_genealogy_is_reported_degraded_not_silently_healthy(monkeypatch):
    """The core confirmed gap: genealogy/RCRW/Sensory Crystal/DPS were
    previously not checked by ANYTHING -- a boot with all four silently
    None reported plain 'ready' with no warning at all."""
    systems = _full_systems()
    systems["genealogy"] = None
    systems["recursive_causal_waveform"] = None
    systems["sensory_crystal"] = None
    systems["dimensional"] = None
    bridge = _bridge()
    monkeypatch.setattr(bridge, "_systems", systems, raising=False)
    monkeypatch.setattr(bridge, "_dream_substrate_boot_ok", True, raising=False)

    payload = json.loads(bridge.get_mobile_developmental_health())
    assert payload["overall"] == "degraded"
    assert set(payload["degraded_missing"]) == {
        "genealogy", "recursive_causal_waveform", "sensory_crystal", "dimensional",
    }


def test_missing_curiosity_and_dream_substrate_downgrade_overall_status(monkeypatch):
    systems = _full_systems()
    del systems["_curiosity_engine"]
    bridge = _bridge()
    monkeypatch.setattr(bridge, "_systems", systems, raising=False)
    monkeypatch.setattr(bridge, "_dream_substrate_boot_ok", False, raising=False)

    payload = json.loads(bridge.get_mobile_developmental_health())
    assert payload["overall"] == "degraded"
    assert payload["optional_status"]["curiosity"] is False
    assert payload["optional_status"]["dream_substrate_boot_attempted"] is False


def test_no_systems_at_all_reports_fatal(monkeypatch):
    bridge = _bridge()
    monkeypatch.setattr(bridge, "_systems", {}, raising=False)
    monkeypatch.setattr(bridge, "_dream_substrate_boot_ok", False, raising=False)

    payload = json.loads(bridge.get_mobile_developmental_health())
    assert payload["overall"] == "fatal"
    assert set(payload["fatal_missing"]) == {"language_field", "identity_field", "consciousness"}


def test_health_check_never_raises_on_none_systems(monkeypatch):
    """Boot health reporting must be safe to call even before boot
    completes (_systems is None at module import time)."""
    bridge = _bridge()
    monkeypatch.setattr(bridge, "_systems", None, raising=False)
    monkeypatch.setattr(bridge, "_dream_substrate_boot_ok", False, raising=False)

    payload = json.loads(bridge.get_mobile_developmental_health())
    assert payload["overall"] == "fatal"
