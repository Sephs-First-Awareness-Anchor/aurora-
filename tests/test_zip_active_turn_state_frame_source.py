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
    driving both ensure_* functions.

    Bug Report 2 investigation (2026-08-03) found this test's original
    example input, "Will this medication definitely work for me?",
    always -- even before that session's changes -- routes through
    dual_question_pipeline's private-context-clarification early return
    (_user_context_anchor_needed() flags "this medication" as an
    ungrounded private referent, added by a LATER directive, commit
    91f9f7704, "public-fact vs. private-context gap research router").
    That path legitimately bypasses _run_reasoning_pipeline entirely by
    design -- Aurora correctly asks for clarification instead of
    fabricating an answer -- so _active_turn_state was never going to be
    set for that specific input, regardless of anything this test is
    actually meant to verify. Confirmed via git diff that no code this
    campaign has touched altered that routing decision; the test's own
    fixture had simply gone stale after a later, unrelated feature
    changed what its example input does. Swapped to an ordinary
    definition-question input that reaches the real pipeline, which is
    what this test needs to exercise the ensure_* wiring it's named for.
    """
    import shutil
    import tempfile
    import aurora as A

    scratch = tempfile.mkdtemp(prefix="aurora_active_turn_state_boot_")
    try:
        scratch_state = os.path.join(scratch, "aurora_state")
        shutil.copytree(os.path.join(REPO_ROOT, "aurora_state"), scratch_state)
        systems = A.boot_aurora(state_dir=scratch_state)

        result = A.process_external_user_turn(systems, "What is a guitar chord?")
        assert result, "live turn produced no result"
        assert systems.get("_active_turn_state") is not None
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
