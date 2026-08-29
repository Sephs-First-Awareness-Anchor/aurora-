"""Build 774 (Android Surface/Subsurface Live-Turn Reconnection):
verification that handle_message() delivers Aurora's Surface response
the moment it is decided instead of waiting for the whole live turn --
including Subsurface consequence/genealogy/memory work -- to finish,
while that same call's Subsurface continuation keeps running to
completion afterward under the same causal identity, exactly once.

Drives the REAL aurora_bridge.handle_message() orchestration (turn_id
minting, the Surface box/event, the background continuation, the
diagnostics store). The only thing replaced is
aurora.process_external_user_turn() itself -- a fixture double standing
in for the real cognitive pipeline, since exercising deep cognition
here is Build 772/773's own concern, not this build's. This build's
concern is the transport around that call: does the response arrive
once, promptly, and does the deep work still happen exactly once,
afterward, under the same turn.
"""
from __future__ import annotations

import json
import os
import sys
import time

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANDROID_PY_DIR = os.path.join(REPO_ROOT, "flutter_app", "android", "app", "src", "main", "python")

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if ANDROID_PY_DIR not in sys.path:
    sys.path.insert(0, ANDROID_PY_DIR)

import aurora  # type: ignore
import aurora_bridge  # type: ignore


class _FakeResp:
    """Stands in for aurora.py's resp_A -- only .content is read by
    _extract_response(), matching the real object's shape exactly."""

    def __init__(self, content: str):
        self.content = content
        self.src = "constraint_communication_baseline"
        self.confidence = 0.7
        self.emotional_tone = "neutral"


def _states(turn_id: str) -> list:
    data = json.loads(aurora_bridge.get_live_turn_diagnostics(turn_id))
    return [s["state"] for s in data.get("states", [])]


@pytest.fixture(autouse=True)
def _reset_bridge_state():
    """Every test drives the real module-level orchestration state --
    reset it before each test so one test's turn can't leak into the
    next (correction-dialogue detection, entropy debt, diagnostics)."""
    aurora_bridge._systems = {}
    aurora_bridge._last_response = ""
    aurora_bridge._last_path_key = ""
    aurora_bridge._pending_correction_dialogue = False
    aurora_bridge._correction_context = {}
    aurora_bridge._pending_example_concept = ""
    aurora_bridge._pending_example_asked = ""
    aurora_bridge._capability_learning_mode = False
    aurora_bridge._capability_learning_context = {}
    aurora_bridge._pending_capability_gap = {}
    aurora_bridge._late_surface_response = ""
    aurora_bridge._live_turn_diagnostics = {}
    aurora_bridge._last_output_time = 0.0
    aurora_bridge._void_pending = False
    aurora_bridge._autonomous_cycles_since_exchange = 0
    aurora_bridge._reentry_context = {}
    aurora_bridge._vacuum_reconciliation_debt = 0.0
    aurora_bridge._entropy_debt_secs = 0.0
    aurora_bridge._SURFACE_WAIT_TIMEOUT_S = 20.0
    yield


def test_slow_subsurface_delivers_surface_response_promptly_and_exactly_once(monkeypatch):
    """The build's own named acceptance scenario: hold Subsurface work far
    beyond a reasonable wait and prove Surface still externalizes from
    what Aurora already decided, the deep work reaches completion exactly
    once afterward, and the two are genuinely decoupled -- not just
    reordered cosmetically."""
    calls = []
    deep_finished = {"flag": False}

    def fake_process(systems, text, *, on_surface_ready=None, **kw):
        calls.append(text)
        resp_a = _FakeResp(f"Surface reply to: {text}")
        on_surface_ready(resp_a)
        time.sleep(2.0)  # Subsurface: conversation memory, genealogy, etc.
        deep_finished["flag"] = True
        return {"resp_A": resp_a}

    monkeypatch.setattr(aurora, "process_external_user_turn", fake_process)

    t0 = time.time()
    reply = aurora_bridge.handle_message("slow subsurface turn")
    elapsed = time.time() - t0

    assert elapsed < 1.0, f"handle_message() should return well before the 2s Subsurface delay, took {elapsed:.2f}s"
    assert reply == "Surface reply to: slow subsurface turn"
    assert deep_finished["flag"] is False, "Subsurface work must not have finished when handle_message() returned"

    turn_id = aurora_bridge._systems["_current_turn_id"]
    time.sleep(2.2)

    assert deep_finished["flag"] is True
    assert calls == ["slow subsurface turn"], "process_external_user_turn must be called exactly once for this turn"
    assert aurora_bridge._last_response == reply, "deep continuation's bookkeeping must match what was actually externalized"
    assert _states(turn_id) == [
        "surface_received", "surface_processing", "surface_expressed",
        "subsurface_active", "subsurface_integrated",
    ]


def test_genuine_silence_is_distinguishable_from_timeout_and_empty_expression(monkeypatch):
    """A legitimate Aurora decision not to speak must remain possible and
    must be diagnostically distinct from infrastructure failing to
    deliver a response."""
    def fake_process(systems, text, *, on_surface_ready=None, **kw):
        resp_a = _FakeResp("")  # Aurora chose not to speak
        on_surface_ready(resp_a)
        return {"resp_A": resp_a}

    monkeypatch.setattr(aurora, "process_external_user_turn", fake_process)

    reply = aurora_bridge.handle_message("say nothing turn")
    turn_id = aurora_bridge._systems["_current_turn_id"]
    time.sleep(0.2)

    assert reply == ""
    states = _states(turn_id)
    assert "suppressed_by_aurora" in states
    assert "timeout" not in states
    assert "empty_expression" not in states


def test_surface_timeout_returns_empty_and_late_callback_delivers_exactly_once(monkeypatch):
    """A Surface-wait timeout followed by a delayed callback firing after
    handle_message() already returned "" must land in
    get_late_surface_response() exactly once, tagged late_completion --
    never delivered twice for the same turn."""
    aurora_bridge._SURFACE_WAIT_TIMEOUT_S = 0.5

    def fake_process(systems, text, *, on_surface_ready=None, **kw):
        time.sleep(1.2)  # Surface generation itself stalls past the wait
        resp_a = _FakeResp("late surface answer")
        on_surface_ready(resp_a)
        return {"resp_A": resp_a}

    monkeypatch.setattr(aurora, "process_external_user_turn", fake_process)

    t0 = time.time()
    reply = aurora_bridge.handle_message("slow surface turn")
    elapsed = time.time() - t0
    turn_id = aurora_bridge._systems["_current_turn_id"]

    assert reply == ""
    assert elapsed < 1.0, "must return at the Surface timeout bound, not wait for the slow callback"
    assert "timeout" in _states(turn_id)
    assert aurora_bridge.get_late_surface_response() == "", "nothing delivered yet -- the callback hasn't fired"

    time.sleep(1.3)  # let the slow callback actually fire

    assert "late_completion" in _states(turn_id)
    assert aurora_bridge.get_late_surface_response() == "late surface answer"
    # Exactly once: a second read must come back empty, never re-deliver.
    assert aurora_bridge.get_late_surface_response() == ""


def test_transport_failure_before_any_callback_still_returns_promptly(monkeypatch):
    """An exception escaping process_external_user_turn before resp_A is
    ever decided must not hang handle_message() for the full Surface
    timeout -- it must surface the same error text today's synchronous
    path always returned, quickly, and record transport_failure."""
    aurora_bridge._SURFACE_WAIT_TIMEOUT_S = 5.0

    def fake_process(systems, text, *, on_surface_ready=None, **kw):
        raise RuntimeError("simulated cognitive pipeline failure")

    monkeypatch.setattr(aurora, "process_external_user_turn", fake_process)

    t0 = time.time()
    reply = aurora_bridge.handle_message("crashing turn")
    elapsed = time.time() - t0
    turn_id = aurora_bridge._systems["_current_turn_id"]

    assert reply == "I encountered an error processing your request."
    assert elapsed < 2.0, "an early failure must not force waiting out the full Surface timeout"
    time.sleep(0.2)
    assert "transport_failure" in _states(turn_id)


def test_empty_expression_distinguishable_from_suppressed_by_aurora(monkeypatch):
    """Empty content because building the surface text itself raised
    (empty_expression) must never be confused with Aurora's own genuine
    choice to say nothing (suppressed_by_aurora)."""
    def _raising_sanitize(*a, **kw):
        raise RuntimeError("sanitize boom")

    monkeypatch.setattr(aurora_bridge, "_sanitize_response", _raising_sanitize)

    def fake_process(systems, text, *, on_surface_ready=None, **kw):
        resp_a = _FakeResp("some content that never gets sanitized")
        on_surface_ready(resp_a)
        return {"resp_A": resp_a}

    monkeypatch.setattr(aurora, "process_external_user_turn", fake_process)

    reply = aurora_bridge.handle_message("boom turn")
    turn_id = aurora_bridge._systems["_current_turn_id"]
    time.sleep(0.2)

    assert reply == ""
    states = _states(turn_id)
    assert "empty_expression" in states
    assert "suppressed_by_aurora" not in states


def test_two_independent_turns_each_get_their_own_surface_content(monkeypatch):
    """A second, independent utterance must be unaffected in its own
    Surface content -- each turn gets its own turn_id and its own
    correctly-matched response, run sequentially since _lock still
    serializes entry into a turn exactly as before this build."""
    def fake_process(systems, text, *, on_surface_ready=None, **kw):
        resp_a = _FakeResp(f"reply for: {text}")
        on_surface_ready(resp_a)
        return {"resp_A": resp_a}

    monkeypatch.setattr(aurora, "process_external_user_turn", fake_process)

    reply_1 = aurora_bridge.handle_message("first turn")
    turn_id_1 = aurora_bridge._systems["_current_turn_id"]
    reply_2 = aurora_bridge.handle_message("second turn")
    turn_id_2 = aurora_bridge._systems["_current_turn_id"]

    assert reply_1 == "reply for: first turn"
    assert reply_2 == "reply for: second turn"
    assert turn_id_1 != turn_id_2


def test_pending_autonomous_report_and_correction_ack_still_compose_into_surface_text(monkeypatch):
    """The bridge-level composition that used to run after
    process_external_user_turn() returned (correction acknowledgment,
    pending autonomous report prefix) now runs inside the Surface
    callback -- confirm it still produces the same composed text, once,
    with nothing left for the deep continuation to redundantly reapply."""
    aurora_bridge._systems = {"_pending_autonomous_report": "I finished my curiosity session."}

    def fake_process(systems, text, *, on_surface_ready=None, **kw):
        resp_a = _FakeResp("here is my answer")
        on_surface_ready(resp_a)
        return {"resp_A": resp_a}

    monkeypatch.setattr(aurora, "process_external_user_turn", fake_process)

    reply = aurora_bridge.handle_message("what did you find")

    assert reply == "I finished my curiosity session.\n\nhere is my answer"
    # Popped exactly once -- must not still be sitting in _systems for a
    # later turn to redundantly re-prepend.
    assert "_pending_autonomous_report" not in aurora_bridge._systems


def test_on_surface_ready_defaults_to_none_for_every_existing_caller():
    """PR1's own invariant: every existing caller of
    process_external_user_turn()/_run_live_response_turn() that omits the
    new kwarg must see byte-for-byte identical behavior -- confirmed here
    by construction (default value), not merely assumed."""
    import inspect
    sig_outer = inspect.signature(aurora.process_external_user_turn)
    assert sig_outer.parameters["on_surface_ready"].default is None
    sig_inner = inspect.signature(aurora._run_live_response_turn)
    assert sig_inner.parameters["on_surface_ready"].default is None
