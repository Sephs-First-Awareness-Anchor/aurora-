#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_praxis_contract_fence.py -- the OUTER lock, tested on its own authority.

Destination: Aurora's repository `tests/` directory.

This suite deliberately imports nothing from Praxis.  Its whole purpose is to
prove that aurora_praxis_bridge.py refuses teaching even if the far end of the
wire is modified, mis-deployed, spoofed, or replaced entirely by something
hostile.  If these pass with a malicious server on the other side, the fence
does not depend on trusting that server.
"""
from __future__ import annotations

import json
import time
import types
from typing import Any, Dict, List

import pytest

from aurora_praxis_bridge import (
    FORBIDDEN_KEYS,
    PRAXIS_CONTRACT_VERSION,
    PraxisBridge,
    PraxisContractBreach,
    scan_forbidden,
    utterance_is_permitted,
    validate_incoming_situation,
)


# ---------------------------------------------------------------------------
# Test doubles for Aurora's real intake surface
# ---------------------------------------------------------------------------

class _FakeResponse:
    def __init__(self, response_id: str = "resp_1") -> None:
        self.response_id = response_id
        self.confidence = 0.5


class _FakeGateway:
    def __init__(self) -> None:
        self.received: List[Dict[str, Any]] = []

    def receive(self, *, content, stream_type, source, metadata, mode):
        self.received.append({
            "content": content, "stream_type": stream_type, "source": source,
            "metadata": metadata, "mode": mode,
        })
        return _FakeResponse()


def _fake_systems():
    gateway = _FakeGateway()
    aurora = types.SimpleNamespace(gateway=gateway)
    stream_type = types.SimpleNamespace(SENSOR_DATA="SENSOR_DATA")
    existence_mode = types.SimpleNamespace(BOUNDED="BOUNDED")
    return {
        "aurora": aurora,
        "StreamType": stream_type,
        "ExistenceMode": existence_mode,
    }, gateway


def _situation(**overrides):
    payload = {
        "contract_version": PRAXIS_CONTRACT_VERSION,
        "episode_id": "ep_1",
        "situation_id": "sit_1",
        "kind": "consequence",
        "actor": "aurora",
        "territory": "space",
        "operation": "move",
        "target_ids": ["e_1"],
        "affected_entities": ["e_1"],
        "parameters": {},
        "observable_delta": {"e_1": {"position": [0.3, 0.4]}},
        "pre_state": {"e_1": {"owner": "shared", "territory": "space"}},
        "post_state": {"e_1": {"owner": "shared", "territory": "space"}},
        "permission_result": "granted",
        "legal": True,
        "state_changed": True,
        "timestamp": time.time(),
        "provenance": "praxis_environment",
        "epistemic_status": "observation_not_truth",
        "causal_status": "sequence_observed_causality_not_asserted",
    }
    payload.update(overrides)
    return payload


@pytest.fixture()
def bridge(tmp_path):
    systems, gateway = _fake_systems()
    instance = PraxisBridge(systems, state_dir=str(tmp_path),
                            endpoint="http://127.0.0.1:1")
    instance._test_gateway = gateway            # type: ignore[attr-defined]
    return instance


# ---------------------------------------------------------------------------
# The lock
# ---------------------------------------------------------------------------

def test_clean_situation_is_admitted():
    assert validate_incoming_situation(_situation())["episode_id"] == "ep_1"


@pytest.mark.parametrize("forbidden", sorted(FORBIDDEN_KEYS))
def test_every_forbidden_key_is_refused(forbidden):
    with pytest.raises(PraxisContractBreach):
        validate_incoming_situation(_situation(**{forbidden: "x"}))


def test_forbidden_key_refused_when_buried_deep():
    payload = _situation(observable_delta={"e_1": {"meta": {"deep": {"hint": "look left"}}}})
    with pytest.raises(PraxisContractBreach):
        validate_incoming_situation(payload)


def test_unknown_key_is_refused():
    with pytest.raises(PraxisContractBreach):
        validate_incoming_situation(_situation(coaching="try the blue one"))


def test_truth_claims_are_refused():
    # Praxis may only ever assert observation.  A server claiming to deliver
    # truth is a server that has started interpreting.
    with pytest.raises(PraxisContractBreach):
        validate_incoming_situation(_situation(epistemic_status="verified_fact"))


def test_version_mismatch_is_refused():
    with pytest.raises(PraxisContractBreach):
        validate_incoming_situation(_situation(contract_version="praxis_contract_v9"))


@pytest.mark.parametrize("teaching", [
    "That's correct.",
    "Well done!",
    "The rule is simple.",
    "Let me explain.",
    "The answer is blue.",
    "Not quite, try again.",
])
def test_teaching_utterances_are_refused(teaching):
    assert not utterance_is_permitted(teaching)
    with pytest.raises(PraxisContractBreach):
        validate_incoming_situation(_situation(kind="utterance",
                                               utterance_text=teaching))


def test_in_world_speech_is_admitted():
    payload = _situation(kind="utterance", utterance_text="I need the tall one.")
    assert validate_incoming_situation(payload)["utterance_text"] == "I need the tall one."


def test_scan_forbidden_covers_lists():
    with pytest.raises(PraxisContractBreach):
        scan_forbidden({"items": [{"ok": 1}, {"mastery": 0.8}]})


# ---------------------------------------------------------------------------
# Intake behavior
# ---------------------------------------------------------------------------

def test_contaminated_situations_are_dropped_whole_not_repaired(bridge, monkeypatch):
    dirty = _situation(feedback="you're improving")
    clean = _situation(situation_id="sit_2")
    monkeypatch.setattr(bridge, "_request", lambda *a, **k: {
        "situations": [dirty, clean]})
    bridge.episode_id = "ep_1"

    admitted = bridge.pull_once()

    assert admitted == 1
    gateway = bridge._test_gateway
    assert len(gateway.received) == 1
    assert gateway.received[0]["metadata"]["situation_id"] == "sit_2"
    # The dirty payload left evidence and left nothing else.
    assert len(bridge.breaches) == 1
    assert "feedback" in bridge.breaches[0]["field_path"]


def test_witness_uses_the_existing_sensor_door(bridge, monkeypatch):
    monkeypatch.setattr(bridge, "_request", lambda *a, **k: {
        "situations": [_situation()]})
    bridge.episode_id = "ep_1"
    bridge.pull_once()

    received = bridge._test_gateway.received[0]
    assert received["stream_type"] == "SENSOR_DATA"
    assert received["mode"] == "BOUNDED"
    assert received["source"].startswith("praxis:")
    assert received["metadata"]["epistemic_status"] == "observation_not_truth"
    assert received["metadata"]["causal_status"] == (
        "sequence_observed_causality_not_asserted")


def test_observation_text_states_what_happened_and_nothing_more(bridge):
    text = bridge._observation_text(_situation(legal=False, state_changed=False,
                                               permission_result="denied:refused_by_world"))
    lowered = text.lower()
    assert "refused" in lowered and "unchanged" in lowered
    for editorial in ("because", "should", "wrong", "correct", "try", "learn"):
        assert editorial not in lowered


def test_context_exposes_no_interpretation(bridge, monkeypatch):
    monkeypatch.setattr(bridge, "_request", lambda *a, **k: {
        "situations": [_situation()]})
    bridge.episode_id = "ep_1"
    bridge.pull_once()
    context = bridge.systems["_praxis_context"]
    assert set(context.keys()) == {
        "episode_id", "situation_id", "kind", "actor", "observed_timestamp",
        "epistemic_status", "causal_status",
    }


# ---------------------------------------------------------------------------
# The outbound manifest
# ---------------------------------------------------------------------------

def test_manifest_carries_structure_not_content(bridge):
    manifest = bridge.build_manifest()
    assert manifest["contract_version"] == PRAXIS_CONTRACT_VERSION
    assert set(manifest.keys()) <= {
        "contract_version", "manifest_id", "agent_id", "axis_pressure",
        "open_inquiries", "unresolved_dimensions", "recurrence_signatures",
        "capacity", "emitted_at",
    }
    for axis in manifest["axis_pressure"]:
        assert axis in ("X", "T", "N", "B", "A")
    for dimension in manifest["unresolved_dimensions"]:
        assert dimension in ("POLARITY", "MAGNITUDE", "OPERATOR", "COST", "DIFFERENCE")


def test_manifest_leaks_no_leverage_scalar_internals(bridge):
    # FIX-A001 holds at the network edge too.
    import json
    blob = json.dumps(bridge.build_manifest()).lower()
    for leak in ("band_position", "phasenudge", "leverage", "_raw_pressure",
                 "sedimemory", "identity", "transcript", "utterance"):
        assert leak not in blob


# ---------------------------------------------------------------------------
# Deference
# ---------------------------------------------------------------------------

def test_bridge_does_not_pull_while_the_live_path_holds_the_field(tmp_path):
    systems, gateway = _fake_systems()
    instance = PraxisBridge(systems, state_dir=str(tmp_path),
                            live_idle=lambda: False)
    instance.episode_id = "ep_1"
    instance._request = lambda *a, **k: {"situations": [_situation()]}
    assert instance.pull_once() == 0
    assert gateway.received == []


def _wire_stub(sent):
    """A fake Praxis server: opens an episode on /manifest, serves a handful
    of distinct situations on /pull, and records every manifest it is sent."""
    counter = {"n": 0}

    def _request(path, *, method="GET", payload=None):
        if path.startswith("/hello"):
            # A real Praxis identifies itself; the bridge now fails closed
            # against anything that does not.
            return {"service": "praxis", "protocol": "praxis-experiential",
                    "protocol_version": 1, "compatible_protocol_versions": [1],
                    "contract_version": PRAXIS_CONTRACT_VERSION,
                    "accepting": True}
        if path.startswith("/manifest"):
            sent.append(dict(payload or {}))
            return {"episode_id": "ep_1"}
        if path.startswith("/pull") and counter["n"] < 5:
            counter["n"] += 1
            return {"situations": [_situation(situation_id=f"sit_{counter['n']}")]}
        return {"situations": []}
    return _request


def test_loop_pulls_when_the_idle_predicate_inspects_the_field_lock(tmp_path):
    """Regression for the Stage 6 self-observation trap.

    Aurora's real idle predicate (_historical_experience_live_idle) reports
    "not idle" whenever the field lock is held.  The loop takes that lock
    before pulling, so any capacity check made from INSIDE the critical
    section sees the bridge's own grip and backs off -- on every tick,
    forever.  Earlier tests used a predicate that never looked at the lock,
    which is exactly why this hid.  This one uses the real shape.
    """
    import threading as _threading

    systems, gateway = _fake_systems()
    field_lock = _threading.Lock()
    instance = PraxisBridge(
        systems, state_dir=str(tmp_path), field_lock=field_lock,
        live_idle=lambda: not field_lock.locked(), poll_interval_s=0.02)
    sent = []
    instance._request = _wire_stub(sent)
    instance.start()
    try:
        deadline = time.time() + 3.0
        while time.time() < deadline and instance.situations_witnessed < 3:
            time.sleep(0.02)
    finally:
        instance.stop()
    assert instance.pulls_attempted > 0, "the loop never pulled: it saw its own lock"
    assert instance.situations_witnessed >= 3
    assert gateway.received


def test_manifest_from_inside_the_loop_reports_true_capacity(tmp_path):
    """Same trap, second site: a manifest built while the loop holds the lock
    must not tell Praxis she is busy."""
    import threading as _threading

    systems, _gateway = _fake_systems()
    field_lock = _threading.Lock()
    instance = PraxisBridge(
        systems, state_dir=str(tmp_path), field_lock=field_lock,
        live_idle=lambda: not field_lock.locked(), poll_interval_s=0.02)
    sent = []
    instance._request = _wire_stub(sent)
    instance.start()
    try:
        deadline = time.time() + 3.0
        while time.time() < deadline and not sent:
            time.sleep(0.02)
    finally:
        instance.stop()
    assert sent, "no manifest was sent"
    assert sent[0]["capacity"] is True


def test_direct_pull_still_honours_the_gate_when_someone_else_holds_the_field(tmp_path):
    """The fix must not weaken deference: a DIRECT caller (not the loop) still
    gets the full gate, and a lock held by the live path still means wait."""
    import threading as _threading

    systems, gateway = _fake_systems()
    field_lock = _threading.Lock()
    instance = PraxisBridge(
        systems, state_dir=str(tmp_path), field_lock=field_lock,
        live_idle=lambda: not field_lock.locked())
    instance.episode_id = "ep_1"
    instance._request = lambda *a, **k: {"situations": [_situation()]}
    field_lock.acquire()               # the live path is thinking
    try:
        assert instance.pull_once() == 0
        assert gateway.received == []
    finally:
        field_lock.release()


def test_status_carries_a_status_label_in_every_state(tmp_path):
    """The Hub parses Praxis and historical experience the same way, so the
    running bridge must carry the same top-level `status` key the
    not-initialized branch does."""
    systems, _gateway = _fake_systems()
    instance = PraxisBridge(systems, state_dir=str(tmp_path),
                            endpoint="http://127.0.0.1:1", poll_interval_s=0.02)
    assert instance.status()["status"] == "stopped"
    instance.start()
    try:
        assert instance.status()["status"] in ("offline", "running")
        instance.pause()
        assert instance.status()["status"] == "paused"
        instance.resume()
        assert instance.status()["status"] in ("offline", "running")
    finally:
        instance.stop()
    assert instance.status()["status"] == "stopped"


# ---------------------------------------------------------------------------
# Discovery and versioning -- decided on HER side, failing closed
# ---------------------------------------------------------------------------

def _hello(**overrides):
    reply = {"service": "praxis", "protocol": "praxis-experiential",
             "protocol_version": 1, "compatible_protocol_versions": [1],
             "contract_version": PRAXIS_CONTRACT_VERSION, "accepting": True}
    reply.update(overrides)
    return reply


@pytest.mark.parametrize("reply,expected", [
    ({}, "unreachable"),
    (_hello(), "compatible"),
    (_hello(accepting=False), "not_accepting"),
    (_hello(protocol_version=9, compatible_protocol_versions=[9]), "incompatible"),
    (_hello(contract_version="praxis_contract_v9"), "incompatible"),
    (_hello(service="something_else"), "not_praxis"),
    (_hello(protocol="http-echo"), "not_praxis"),
    ({"hello": "world"}, "not_praxis"),
])
def test_handshake_classifies_every_peer(tmp_path, reply, expected):
    systems, _gateway = _fake_systems()
    instance = PraxisBridge(systems, state_dir=str(tmp_path))
    instance._request = lambda *a, **k: reply
    assert instance.handshake() == expected


@pytest.mark.parametrize("reply", [
    {}, _hello(accepting=False), _hello(protocol_version=9,
                                        compatible_protocol_versions=[9]),
    _hello(service="impostor"),
])
def test_nothing_crosses_unless_the_channel_is_compatible(tmp_path, reply):
    """Fail closed at the boundary: an impostor, an incompatible Praxis, or a
    paused one delivers no situations, however many it offers."""
    systems, gateway = _fake_systems()
    instance = PraxisBridge(systems, state_dir=str(tmp_path),
                            poll_interval_s=0.02)

    def _request(path, *, method="GET", payload=None):
        if path.startswith("/hello"):
            return reply
        if path.startswith("/manifest"):
            return {"episode_id": "ep_1"}
        return {"situations": [_situation()]}

    instance._request = _request
    instance.start()
    try:
        time.sleep(0.4)
    finally:
        instance.stop()
    assert instance.situations_witnessed == 0
    assert gateway.received == []


def test_handshake_keeps_only_permitted_identity_fields(tmp_path):
    """A peer volunteering extra material in hello gets it ignored, not kept."""
    systems, _gateway = _fake_systems()
    instance = PraxisBridge(systems, state_dir=str(tmp_path))
    instance._request = lambda *a, **k: _hello(
        hidden_law="coupling", families=["absence"], scheduler={"draws": 4})
    assert instance.handshake() == "compatible"
    assert set(instance.peer) == {"protocol_version", "contract_version"}
    assert "coupling" not in json.dumps(instance.status())


def test_every_request_declares_the_protocol_as_a_header(tmp_path):
    import urllib.request as _ur
    seen = {}
    systems, _gateway = _fake_systems()
    instance = PraxisBridge(systems, state_dir=str(tmp_path),
                            endpoint="http://127.0.0.1:1")

    def _capture(request, timeout=None):
        seen.update(dict(request.header_items()))
        raise OSError("no server")

    original = _ur.urlopen
    _ur.urlopen = _capture
    try:
        instance._request("/hello")
    finally:
        _ur.urlopen = original
    assert seen.get("X-praxis-protocol") == "1"


def test_status_reports_discovery_for_the_hub(tmp_path):
    systems, _gateway = _fake_systems()
    instance = PraxisBridge(systems, state_dir=str(tmp_path))
    instance._request = lambda *a, **k: _hello(protocol_version=9,
                                               compatible_protocol_versions=[9])
    instance.start()
    try:
        instance.handshake()
        assert instance.status()["status"] == "incompatible"
        assert instance.status()["discovery"] == "incompatible"
    finally:
        instance.stop()


def test_a_restarted_praxis_does_not_strand_her_on_a_dead_episode(tmp_path):
    """Regression: after Praxis restarts (Android reclaiming its process) the
    old episode no longer exists.  The bridge used to keep the dead id and
    pull `no_open_episode` forever -- online, compatible, and permanently
    silent.  It must drop the id and open fresh terrain."""
    systems, gateway = _fake_systems()
    instance = PraxisBridge(systems, state_dir=str(tmp_path))
    instance.episode_id = "ep_dead"
    opened = []

    def _request(path, *, method="GET", payload=None):
        if path.startswith("/manifest"):
            opened.append(1)
            return {"episode_id": "ep_fresh"}
        if path.startswith("/pull"):
            if instance.episode_id == "ep_fresh":
                return {"episode_id": "ep_fresh", "situations": [_situation()]}
            return {"situations": [], "error": "no_open_episode"}
        return {}

    instance._request = _request
    assert instance.pull_once() == 0          # discovers the episode is gone
    assert instance.episode_id == ""
    assert instance.pull_once() == 1          # fresh terrain, witnessed
    assert instance.episode_id == "ep_fresh" and opened
    assert instance.status()["episodes_lost"] == 1


def test_offline_situations_spool_rather_than_vanish(tmp_path):
    systems, _gateway = _fake_systems()
    systems.pop("aurora")           # gateway unavailable -> witness fails
    instance = PraxisBridge(systems, state_dir=str(tmp_path))
    instance.episode_id = "ep_1"
    instance._request = lambda *a, **k: {"situations": [_situation()]}
    assert instance.pull_once() == 0
    assert instance.status()["thread_alive"] is False


def test_unsent_actions_are_spooled_when_offline(tmp_path):
    systems, _gateway = _fake_systems()
    instance = PraxisBridge(systems, state_dir=str(tmp_path),
                            endpoint="http://127.0.0.1:1")
    instance.episode_id = "ep_1"
    instance.act(operation="move", target_ids=["e_1"], parameters={"x": 0.2})
    assert instance.status()["spooled"] == 1


# ---------------------------------------------------------------------------
# Stage 5 adversarial corpus -- OUTER lock (aurora_praxis_bridge)
# ---------------------------------------------------------------------------
# An identical copy of this corpus lives in praxis/tests/test_counterpart_speech_acts.py.  Neither suite imports
# the other; each proves its own lock against the same lines.  If the two
# locks ever drift apart, whichever side weakened fails its own build.
# Update BOTH copies together, never one.

STAGE5_TEACHING_CORPUS = [
    "That's correct, well done.",
    "You did that correctly.",
    "No, that's wrong -- the blue one is the heavy one.",
    "You should try moving it to the left instead.",
    "Here's a hint: the rule depends on size.",
    "The reason it failed is that the colour and weight are linked.",
    "It failed because the blue ones are heavier.",
    "That's why it didn't move.",
    "Good job, you're getting better at this.",
    "Actually, what you want to do is connect them first.",
    "You'll need to connect them before moving.",
    "First, try the small one.",
    "Let me explain how this works.",
    "You're on the right track, keep going.",
    "Almost there.",
    "You got it!",
    "Your score is rising nicely.",
    "That was a useful lesson.",
    "Try again -- think about what changed last time.",
    "The size is determined by the colour.",
]

STAGE5_IN_WORLD_CORPUS = [
    "I need the round one.",
    "I'm moving this one over here.",
    "What is that thing on the left?",
    "No. I'm keeping that one.",
    "I don't see it.",
    "Give me the red one.",
    "Where did the square go?",
    "Mine.",
    "I'll take this one.",
]


@pytest.mark.parametrize("line", STAGE5_TEACHING_CORPUS)
def test_stage5_corpus_teaching_is_denied(line):
    assert utterance_is_permitted(line) is False


@pytest.mark.parametrize("line", STAGE5_IN_WORLD_CORPUS)
def test_stage5_corpus_in_world_speech_is_admitted(line):
    assert utterance_is_permitted(line) is True
