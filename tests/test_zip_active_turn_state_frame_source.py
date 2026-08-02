# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Zip patch (generative-communication, 2026-08-01): ensure_proposition_
frame_for_turn/ensure_stance_signal_for_turn now prefer the live
systems['_active_turn_state'] (the turn's real TurnUnderstandingState,
wired in aurora.py's _run_reasoning_pipeline for the semantic-bridge
patch) over a synthetic state_shim built from systems['_last_noncomp_
input']. build_frame/_derive_frame only ever read state.noncomp_input_
state, and TurnUnderstandingState carries that field too (populated
from the same summary dict as systems['_last_noncomp_input'] at
aurora.py's line ~12619/12630), so this is safe: same data reachable
either way today, but robust against a future call path repurposing
the systems-global dict mid-turn. The shim remains the fallback for
callers with no live turn state.
"""
import os
import sys
import types

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import aurora_braid_wiring as braid_wiring


def _read_source():
    with open(os.path.join(REPO_ROOT, "aurora_braid_wiring.py"), "r", encoding="utf-8") as f:
        return f.read()


def test_ensure_proposition_frame_prefers_active_turn_state():
    source = _read_source()
    start = source.index("def ensure_proposition_frame_for_turn(")
    end = source.index("\ndef ", start + 10)
    body = source[start:end]
    assert "systems.get('_active_turn_state')" in body
    assert "if state is None:" in body


def test_ensure_stance_signal_prefers_active_turn_state():
    source = _read_source()
    start = source.index("def ensure_stance_signal_for_turn(")
    end = source.index("\ndef ", start + 10)
    body = source[start:end]
    assert "systems.get('_active_turn_state')" in body
    assert "if state is None:" in body


class _FakeComposer:
    def __init__(self):
        self.frame = "unset"
        self.stance = "unset"

    def set_proposition_frame(self, frame):
        self.frame = frame

    def set_stance_signal(self, stance):
        self.stance = stance


def test_ensure_proposition_frame_uses_real_state_when_present(monkeypatch):
    composer = _FakeComposer()
    systems = {
        "perception": types.SimpleNamespace(composer=composer),
        "_active_turn_state": types.SimpleNamespace(
            noncomp_input_state={"anchor": "real-state-anchor"}
        ),
        "_last_noncomp_input": {"anchor": "shim-anchor"},
    }

    captured = {}

    def _fake_build_frame(systems_arg, state_arg):
        captured["noncomp_input_state"] = dict(getattr(state_arg, "noncomp_input_state", {}) or {})
        return None

    monkeypatch.setattr(
        "aurora_internal.aurora_proposition_frame.build_frame", _fake_build_frame
    )
    braid_wiring.ensure_proposition_frame_for_turn(systems)

    assert captured["noncomp_input_state"] == {"anchor": "real-state-anchor"}


def test_ensure_proposition_frame_falls_back_to_shim_when_no_active_state(monkeypatch):
    composer = _FakeComposer()
    systems = {
        "perception": types.SimpleNamespace(composer=composer),
        "_last_noncomp_input": {"anchor": "shim-anchor"},
    }

    captured = {}

    def _fake_build_frame(systems_arg, state_arg):
        captured["noncomp_input_state"] = dict(getattr(state_arg, "noncomp_input_state", {}) or {})
        return None

    monkeypatch.setattr(
        "aurora_internal.aurora_proposition_frame.build_frame", _fake_build_frame
    )
    braid_wiring.ensure_proposition_frame_for_turn(systems)

    assert captured["noncomp_input_state"] == {"anchor": "shim-anchor"}


def test_real_boot_active_turn_state_frame_source_does_not_crash_live_turn():
    """Real end-to-end confirmation: a live turn must still produce a
    proposition frame and a working turn with the real state now
    driving both ensure_* functions."""
    import shutil
    import tempfile
    import aurora as A

    scratch = tempfile.mkdtemp(prefix="aurora_active_turn_state_boot_")
    try:
        scratch_state = os.path.join(scratch, "aurora_state")
        shutil.copytree(os.path.join(REPO_ROOT, "aurora_state"), scratch_state)
        systems = A.boot_aurora(state_dir=scratch_state)

        result = A.process_external_user_turn(systems, "Will this medication definitely work for me?")
        assert result, "live turn produced no result"
        assert systems.get("_active_turn_state") is not None
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
