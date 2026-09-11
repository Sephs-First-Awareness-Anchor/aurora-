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


# ── Directive 3.21: beyond bool(systems.get(key)) ──────────────────────────

class _FakeOrgan:
    """A truthy stand-in object that can carry the same identity/wiring
    attributes real organs expose (.genealogy, .warp_field, .state_dir,
    .attach_systems/.systems), so tests can prove the health check
    actually inspects them rather than just truthiness."""
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


def test_detached_genealogy_singleton_is_not_reported_healthy(monkeypatch):
    """A truthy organ whose .genealogy is a DIFFERENT real object than
    systems['genealogy'] is exactly the detached-singleton case bool()
    alone cannot see."""
    bridge = _bridge()
    canonical_genealogy = object()
    detached_genealogy = object()
    systems = _full_systems()
    systems["genealogy"] = canonical_genealogy
    systems["recursive_causal_waveform"] = _FakeOrgan(genealogy=detached_genealogy)
    monkeypatch.setattr(bridge, "_systems", systems, raising=False)
    monkeypatch.setattr(bridge, "_dream_substrate_boot_ok", True, raising=False)

    payload = json.loads(bridge.get_mobile_developmental_health())
    assert "recursive_causal_waveform" in payload["degraded_missing"]
    assert payload["overall"] == "degraded"


def test_organ_sharing_canonical_genealogy_is_healthy(monkeypatch):
    """The same organ shape, but genuinely sharing the canonical
    genealogy object, must NOT be flagged -- proving this isn't just
    rejecting any organ with a .genealogy attribute."""
    bridge = _bridge()
    canonical_genealogy = object()
    systems = _full_systems()
    systems["genealogy"] = canonical_genealogy
    systems["recursive_causal_waveform"] = _FakeOrgan(genealogy=canonical_genealogy)
    monkeypatch.setattr(bridge, "_systems", systems, raising=False)
    monkeypatch.setattr(bridge, "_dream_substrate_boot_ok", True, raising=False)

    payload = json.loads(bridge.get_mobile_developmental_health())
    assert "recursive_causal_waveform" not in payload["degraded_missing"]
    assert payload["overall"] == "healthy"


def test_organ_pointed_at_stale_state_dir_is_not_reported_healthy(monkeypatch, tmp_path):
    bridge = _bridge()
    active_dir = tmp_path / "active"
    stale_dir = tmp_path / "stale"
    active_dir.mkdir()
    stale_dir.mkdir()
    systems = _full_systems()
    systems["state_dir"] = str(active_dir)
    systems["sensory_crystal"] = _FakeOrgan(state_dir=str(stale_dir))
    monkeypatch.setattr(bridge, "_systems", systems, raising=False)
    monkeypatch.setattr(bridge, "_dream_substrate_boot_ok", True, raising=False)

    payload = json.loads(bridge.get_mobile_developmental_health())
    assert "sensory_crystal" in payload["degraded_missing"]


def test_organ_using_the_active_state_dir_is_healthy(monkeypatch, tmp_path):
    bridge = _bridge()
    systems = _full_systems()
    systems["state_dir"] = str(tmp_path)
    systems["sensory_crystal"] = _FakeOrgan(state_dir=str(tmp_path))
    monkeypatch.setattr(bridge, "_systems", systems, raising=False)
    monkeypatch.setattr(bridge, "_dream_substrate_boot_ok", True, raising=False)

    payload = json.loads(bridge.get_mobile_developmental_health())
    assert "sensory_crystal" not in payload["degraded_missing"]


def test_organ_with_attach_systems_never_called_is_not_reported_healthy(monkeypatch):
    """An organ that declares an attach_systems() dependency contract but
    whose .systems is still empty never actually joined the live boot
    graph, even though the bare instance is truthy."""
    bridge = _bridge()

    class _UnattachedOrgan:
        def __init__(self):
            self.systems = {}
        def attach_systems(self, systems):
            self.systems = dict(systems)

    systems = _full_systems()
    systems["dimensional"] = _UnattachedOrgan()  # attach_systems() never called
    monkeypatch.setattr(bridge, "_systems", systems, raising=False)
    monkeypatch.setattr(bridge, "_dream_substrate_boot_ok", True, raising=False)

    payload = json.loads(bridge.get_mobile_developmental_health())
    assert "dimensional" in payload["degraded_missing"]


def test_organ_with_attach_systems_actually_called_is_healthy(monkeypatch):
    bridge = _bridge()

    class _AttachedOrgan:
        def __init__(self):
            self.systems = {}
        def attach_systems(self, systems):
            self.systems = dict(systems)

    organ = _AttachedOrgan()
    organ.attach_systems({"genealogy": object()})
    systems = _full_systems()
    systems["dimensional"] = organ
    monkeypatch.setattr(bridge, "_systems", systems, raising=False)
    monkeypatch.setattr(bridge, "_dream_substrate_boot_ok", True, raising=False)

    payload = json.loads(bridge.get_mobile_developmental_health())
    assert "dimensional" not in payload["degraded_missing"]


def test_plain_sentinel_organs_without_checkable_attributes_stay_healthy(monkeypatch):
    """A bare object() (no .genealogy/.state_dir/.attach_systems) must be
    treated exactly as before -- present and truthy is sufficient when
    there's nothing further to check. Regression guard against the new
    checks becoming falsely strict."""
    bridge = _bridge()
    monkeypatch.setattr(bridge, "_systems", _full_systems(), raising=False)
    monkeypatch.setattr(bridge, "_dream_substrate_boot_ok", True, raising=False)

    payload = json.loads(bridge.get_mobile_developmental_health())
    assert payload["overall"] == "healthy"
    assert payload["fatal_missing"] == []
    assert payload["degraded_missing"] == []


def test_validate_boot_also_catches_detached_genealogy_singleton(monkeypatch):
    """_validate_boot() (which gates whether background threads start)
    uses the same _classify_missing() helper -- must not regress to
    bool()-only checking either."""
    bridge = _bridge()
    canonical_genealogy = object()
    detached_genealogy = object()
    systems = _full_systems()
    systems["genealogy"] = detached_genealogy
    # _BOOT_DEGRADED_SYSTEMS includes "genealogy"; give it a distinct
    # canonical reference to compare against via a second organ that
    # legitimately shares the canonical one.
    systems["lattice"] = _FakeOrgan(genealogy=canonical_genealogy)
    fatal, degraded = bridge._validate_boot(systems)
    assert "lattice" in degraded
