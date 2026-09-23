#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_app_bridge_praxis.py -- Stage 6: the app surface.

Destination: Aurora's repository `tests/` directory.

Covers the Praxis trio added to flutter_app/android/app/src/main/python/
aurora_bridge.py (get_praxis_status / pause_praxis / resume_praxis), which
mirror the historical-experience trio beside them, plus endpoint resolution
and idle delegation.

The app bridge is located by walking up from this file to the repository's
flutter_app tree, or taken from AURORA_APP_PYTHON when set.  If neither is
found the suite skips rather than failing, since it cannot test code it
cannot see.

Deliberately imports nothing from Praxis: the app surface is Aurora's side
of the wire.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import pytest

_APP_REL = Path("flutter_app/android/app/src/main/python")


def _locate_app_python() -> Path | None:
    override = os.environ.get("AURORA_APP_PYTHON", "").strip()
    if override and (Path(override) / "aurora_bridge.py").exists():
        return Path(override)
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / _APP_REL
        if (candidate / "aurora_bridge.py").exists():
            return candidate
    return None


_APP_PY = _locate_app_python()
if _APP_PY is None:
    pytest.skip("app aurora_bridge.py not found", allow_module_level=True)
sys.path.insert(0, str(_APP_PY))

ab = pytest.importorskip("aurora_bridge")
if not hasattr(ab, "get_praxis_status"):
    pytest.skip("this aurora_bridge.py predates the Praxis trio",
                allow_module_level=True)


class _FakeBridge:
    """Stands in for aurora_praxis_bridge.PraxisBridge with the same three
    methods the trio calls."""

    def __init__(self) -> None:
        self.paused = False

    def status(self):
        return {"status": "paused" if self.paused else "running",
                "paused": self.paused, "situations_witnessed": 7}

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False


@pytest.fixture()
def installed(monkeypatch):
    fake = _FakeBridge()
    monkeypatch.setattr(ab, "_praxis", fake)
    return fake


# ---------------------------------------------------------------------------
# The trio
# ---------------------------------------------------------------------------

def test_trio_before_boot_reports_not_initialized(monkeypatch):
    monkeypatch.setattr(ab, "_praxis", None)
    for call in (ab.get_praxis_status, ab.pause_praxis, ab.resume_praxis):
        payload = json.loads(call())
        assert payload["status"] == "not_initialized"
        assert payload["thread_alive"] is False


def test_trio_returns_json_strings_like_the_historical_trio(installed):
    for call in (ab.get_praxis_status, ab.pause_praxis, ab.resume_praxis):
        raw = call()
        assert isinstance(raw, str)
        assert "status" in json.loads(raw)


def test_pause_and_resume_switch_the_bridge_and_report_the_new_state(installed):
    assert json.loads(ab.pause_praxis())["status"] == "paused"
    assert installed.paused is True
    assert json.loads(ab.resume_praxis())["status"] == "running"
    assert installed.paused is False


def test_a_status_error_is_reported_not_raised(monkeypatch):
    class _Broken:
        def status(self):
            raise RuntimeError("boom")

    monkeypatch.setattr(ab, "_praxis", _Broken())
    payload = json.loads(ab.get_praxis_status())
    assert payload["status"] == "error"
    assert "RuntimeError" in payload["error"]


def test_trio_exposes_no_path_to_send_her_anything():
    """Status and switching only.  Nothing on the app surface can push a
    situation to her or read what she concluded."""
    names = {name for name in dir(ab) if "praxis" in name.lower()}
    for forbidden in ("send", "inject", "teach", "act", "submit", "push",
                      "outcome", "progress", "score"):
        assert not any(forbidden in name.lower() for name in names), names


# ---------------------------------------------------------------------------
# Endpoint resolution
# ---------------------------------------------------------------------------

def test_endpoint_defaults_when_nothing_is_configured(tmp_path, monkeypatch):
    monkeypatch.delenv("AURORA_PRAXIS_ENDPOINT", raising=False)
    assert ab._praxis_endpoint(str(tmp_path)) == "http://127.0.0.1:8787"


def test_endpoint_file_points_the_phone_at_the_lan(tmp_path, monkeypatch):
    monkeypatch.delenv("AURORA_PRAXIS_ENDPOINT", raising=False)
    (tmp_path / "praxis").mkdir()
    (tmp_path / "praxis" / "endpoint.txt").write_text("http://192.168.1.40:8787\n")
    assert ab._praxis_endpoint(str(tmp_path)) == "http://192.168.1.40:8787"


def test_environment_variable_outranks_the_file(tmp_path, monkeypatch):
    (tmp_path / "praxis").mkdir()
    (tmp_path / "praxis" / "endpoint.txt").write_text("http://from-file:1\n")
    monkeypatch.setenv("AURORA_PRAXIS_ENDPOINT", "http://from-env:2")
    assert ab._praxis_endpoint(str(tmp_path)) == "http://from-env:2"


def test_an_empty_endpoint_file_falls_back_to_default(tmp_path, monkeypatch):
    monkeypatch.delenv("AURORA_PRAXIS_ENDPOINT", raising=False)
    (tmp_path / "praxis").mkdir()
    (tmp_path / "praxis" / "endpoint.txt").write_text("   \n")
    assert ab._praxis_endpoint(str(tmp_path)) == "http://127.0.0.1:8787"


# ---------------------------------------------------------------------------
# Deference
# ---------------------------------------------------------------------------

def test_praxis_yields_on_exactly_the_historical_terms(monkeypatch):
    """One definition of "the live path is not claiming the field" for every
    background source -- Praxis delegates rather than keeping its own copy."""
    monkeypatch.setattr(ab, "_historical_experience_live_idle", lambda: True)
    assert ab._praxis_live_idle() is True
    monkeypatch.setattr(ab, "_historical_experience_live_idle", lambda: False)
    assert ab._praxis_live_idle() is False


def test_praxis_is_not_idle_while_sunni_was_just_answered(monkeypatch):
    """The real predicate, not a stand-in: a reply in the last few seconds
    means the present is active and Praxis waits."""
    if getattr(ab, "_systems", None) is None:
        monkeypatch.setattr(ab, "_systems", {})
    monkeypatch.setattr(ab, "_last_output_time", time.time())
    assert ab._praxis_live_idle() is False
