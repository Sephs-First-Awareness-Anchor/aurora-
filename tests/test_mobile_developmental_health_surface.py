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
        "sedimemory": object(), "lattice": object(), "_geological_baseline": object(),
        "genealogy": object(), "recursive_causal_waveform": object(),
        "sensory_crystal": object(), "dimensional": object(),
        "autonomy": object(), "chamber": object(),
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
    del systems["autonomy"]
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


# ── record_boot_health(): durable boot record (Autonomous Development ─────
# ── Integrity pass, blocker 6) ─────────────────────────────────────────────

def test_record_boot_health_returns_the_same_payload_as_the_live_getter(monkeypatch, tmp_path):
    systems = _full_systems()
    systems["state_dir"] = str(tmp_path)
    bridge = _bridge()
    monkeypatch.setattr(bridge, "_systems", systems, raising=False)
    monkeypatch.setattr(bridge, "_dream_substrate_boot_ok", True, raising=False)

    returned = json.loads(bridge.record_boot_health())
    assert returned["overall"] == "healthy"


def test_record_boot_health_persists_a_durable_record(monkeypatch, tmp_path):
    """The exact gap this fixes: a headless BOOT_COMPLETED restart with no
    Flutter UI running previously left NO trace beyond an ephemeral
    Android Log.w. This must be readable later, independent of whether
    anyone was watching logcat at the moment it happened."""
    systems = _full_systems()
    systems["genealogy"] = None
    systems["state_dir"] = str(tmp_path)
    bridge = _bridge()
    monkeypatch.setattr(bridge, "_systems", systems, raising=False)
    monkeypatch.setattr(bridge, "_dream_substrate_boot_ok", True, raising=False)

    bridge.record_boot_health()

    record_path = tmp_path / "last_boot_health.json"
    assert record_path.exists()
    record = json.loads(record_path.read_text())
    assert record["overall"] == "degraded"
    assert "genealogy" in record["degraded_missing"]
    assert isinstance(record["timestamp"], (int, float))
    assert record["boot_count"] == 1


def test_record_boot_health_increments_boot_count_across_restarts(monkeypatch, tmp_path):
    systems = _full_systems()
    systems["state_dir"] = str(tmp_path)
    bridge = _bridge()
    monkeypatch.setattr(bridge, "_systems", systems, raising=False)
    monkeypatch.setattr(bridge, "_dream_substrate_boot_ok", True, raising=False)

    bridge.record_boot_health()
    bridge.record_boot_health()
    bridge.record_boot_health()

    record = json.loads((tmp_path / "last_boot_health.json").read_text())
    assert record["boot_count"] == 3, (
        "boot_count must accumulate across restarts so a later inspection "
        "can tell 'first boot ever' from 'she's restarted N times'"
    )


def test_record_boot_health_still_returns_payload_when_persistence_fails(monkeypatch, tmp_path):
    """A read-only or missing state directory must never prevent the LIVE
    health signal from reaching Flutter -- only the durable record is
    allowed to silently fail."""
    systems = _full_systems()
    # A path that cannot be created as a directory (its parent is a file).
    blocker_file = tmp_path / "not_a_directory"
    blocker_file.write_text("x")
    systems["state_dir"] = str(blocker_file / "nested")
    bridge = _bridge()
    monkeypatch.setattr(bridge, "_systems", systems, raising=False)
    monkeypatch.setattr(bridge, "_dream_substrate_boot_ok", True, raising=False)

    returned = json.loads(bridge.record_boot_health())
    assert returned["overall"] == "healthy", "the live payload must still be returned even if persistence fails"


def test_record_boot_health_never_raises_on_none_systems(monkeypatch, tmp_path):
    bridge = _bridge()
    monkeypatch.setattr(bridge, "_systems", None, raising=False)
    monkeypatch.setattr(bridge, "_dream_substrate_boot_ok", False, raising=False)

    payload = json.loads(bridge.record_boot_health())
    assert payload["overall"] == "fatal"


def test_record_boot_health_never_raises_when_cwd_is_gone(monkeypatch):
    # Caught via a real (order-dependent) test-suite failure: with no
    # _systems state_dir configured, record_boot_health() fell back to
    # os.getcwd() -- which itself raises FileNotFoundError when the
    # process's current working directory has been deleted out from
    # under it. That escaped every try/except in the function and broke
    # its one explicit contract: never raise, always return the live
    # health payload.
    bridge = _bridge()
    monkeypatch.setattr(bridge, "_systems", None, raising=False)

    def _raise_getcwd():
        raise FileNotFoundError("[Errno 2] No such file or directory")

    monkeypatch.setattr(bridge.os, "getcwd", _raise_getcwd)

    payload = json.loads(bridge.record_boot_health())
    assert payload["overall"] in ("healthy", "degraded", "fatal")
