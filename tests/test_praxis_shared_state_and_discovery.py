#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_praxis_shared_state_and_discovery.py -- Praxis reaches her shared state,
and Praxis is recognised without waiting for an idle field.

Three gaps the knowledge graph traced and the code confirmed:

1. `PraxisBridge.__init__` kept `dict(systems)`, a private copy, so the
   `_praxis_context` slot `_witness` writes never reached the systems dict her
   organs read.  These tests read the organism's own dict, never
   `bridge.systems`, which is how the old test hid the gap.
2. `_run` asked `_capacity()` before `_channel_open()`, so the /hello handshake
   (a network question that never touches the field) waited for an idle
   field, and a running Praxis read as "offline" while she was busy.
   Discovery now runs on its own; the pull still waits.
3. `start_praxis_bridge` returned the process singleton untouched on a second
   boot, still bound to the first organism.  It now follows the new one.
"""
from __future__ import annotations

import threading
import time
import types
from typing import Any, Dict, List

import aurora_praxis_bridge as pb
from aurora_praxis_bridge import PRAXIS_CONTRACT_VERSION, PraxisBridge


class _FakeResponse:
    response_id = "resp_1"
    confidence = 0.5


class _FakeGateway:
    def __init__(self) -> None:
        self.received: List[Dict[str, Any]] = []

    def receive(self, *, content, stream_type, source, metadata, mode):
        self.received.append({"content": content, "source": source})
        return _FakeResponse()


def _organism():
    gateway = _FakeGateway()
    systems: Dict[str, Any] = {
        "aurora": types.SimpleNamespace(gateway=gateway),
        "StreamType": types.SimpleNamespace(SENSOR_DATA="SENSOR_DATA"),
        "ExistenceMode": types.SimpleNamespace(BOUNDED="BOUNDED"),
    }
    return systems, gateway


def _situation(situation_id: str = "sit_1") -> Dict[str, Any]:
    return {
        "contract_version": PRAXIS_CONTRACT_VERSION,
        "episode_id": "ep_1",
        "situation_id": situation_id,
        "kind": "consequence",
        "actor": "aurora",
        "territory": "space",
        "operation": "move",
        "target_ids": ["e_1"],
        "affected_entities": ["e_1"],
        "parameters": {},
        "observable_delta": {"e_1": {"position": [0.3, 0.4]}},
        "permission_result": "permitted",
        "legal": True,
        "state_changed": True,
        "budget_remaining": 9,
        "timestamp": 1000.0,
        "provenance": "praxis_world",
        "epistemic_status": "observation_not_truth",
        "causal_status": "sequence_observed_causality_not_asserted",
    }


_HELLO = {"service": "praxis", "protocol": "praxis-experiential",
          "protocol_version": 1, "compatible_protocol_versions": [1],
          "contract_version": PRAXIS_CONTRACT_VERSION, "accepting": True}


def _server(calls: List[str], bridge: Any = None):
    """A fake Praxis.  Like the real `_request`, an answer marks the bridge
    online."""
    def _request(path, *, method="GET", payload=None):
        calls.append(path.split("?", 1)[0])
        if bridge is not None:
            bridge.online = True
        if path.startswith("/hello"):
            return dict(_HELLO)
        if path.startswith("/manifest"):
            return {"episode_id": "ep_1"}
        if path.startswith("/pull"):
            return {"situations": [_situation(f"sit_{len(calls)}")]}
        return {}
    return _request


def test_witnessed_context_lands_in_her_own_systems_dict(tmp_path):
    systems, gateway = _organism()
    bridge = PraxisBridge(systems, state_dir=str(tmp_path))
    bridge._request = lambda *a, **k: {"situations": [_situation()]}
    bridge.episode_id = "ep_1"

    assert bridge.pull_once() == 1
    assert gateway.received, "the situation never reached her gateway"
    # The organism's dict, not the bridge's attribute.
    context = systems["_praxis_context"]
    assert context["situation_id"] == "sit_1"
    assert context["epistemic_status"] == "observation_not_truth"
    assert bridge.systems is systems


def test_a_read_only_mapping_is_still_copied_so_the_bridge_can_write(tmp_path):
    from types import MappingProxyType
    systems, _gateway = _organism()
    view = MappingProxyType(systems)
    bridge = PraxisBridge(view, state_dir=str(tmp_path))
    assert isinstance(bridge.systems, dict)
    assert bridge.systems is not systems


def test_discovery_does_not_wait_for_an_idle_field_but_the_pull_does(tmp_path):
    systems, gateway = _organism()
    idle = {"v": False}
    bridge = PraxisBridge(systems, state_dir=str(tmp_path),
                          live_idle=lambda: idle["v"], poll_interval_s=0.02)
    calls: List[str] = []
    bridge._request = _server(calls, bridge)
    bridge.start()
    try:
        deadline = time.time() + 3.0
        while time.time() < deadline and bridge.discovery != "compatible":
            time.sleep(0.02)
        # She is busy: Praxis is recognised, nothing has crossed.
        assert bridge.discovery == "compatible"
        status = bridge.status()
        assert status["status"] == "running"
        assert bridge.pulls_attempted == 0
        assert "/pull" not in calls and "/manifest" not in calls
        assert gateway.received == []

        idle["v"] = True             # the field settles
        deadline = time.time() + 3.0
        while time.time() < deadline and not gateway.received:
            time.sleep(0.02)
    finally:
        bridge.stop()
    assert gateway.received, "the pull never ran once the field was idle"
    assert "_praxis_context" in systems


def test_pause_still_stops_discovery(tmp_path):
    systems, _gateway = _organism()
    bridge = PraxisBridge(systems, state_dir=str(tmp_path), poll_interval_s=0.02)
    calls: List[str] = []
    bridge._request = _server(calls, bridge)
    bridge.start()
    bridge.pause()
    time.sleep(0.1)                  # let any in-flight tick finish
    calls.clear()
    bridge.discovery = "unknown"     # force a handshake if the loop runs one
    try:
        time.sleep(0.2)
    finally:
        bridge.stop()
    assert calls == []
    assert bridge.discovery == "unknown"


def test_loop_still_pulls_with_the_real_field_lock_predicate(tmp_path):
    systems, gateway = _organism()
    field_lock = threading.Lock()
    bridge = PraxisBridge(systems, state_dir=str(tmp_path),
                          field_lock=field_lock,
                          live_idle=lambda: not field_lock.locked(),
                          poll_interval_s=0.02)
    bridge._request = _server([])
    bridge.start()
    try:
        deadline = time.time() + 3.0
        while time.time() < deadline and bridge.situations_witnessed < 2:
            time.sleep(0.02)
    finally:
        bridge.stop()
    assert bridge.situations_witnessed >= 2
    assert systems["_praxis_context"]["kind"] == "consequence"


def test_second_boot_rebinds_the_running_bridge_to_the_new_organism(tmp_path):
    pb.stop_praxis_bridge()
    first, _g1 = _organism()
    second, g2 = _organism()
    try:
        # Port 9 (discard) refuses at once; no Praxis is needed here.
        bridge = pb.start_praxis_bridge(first, state_dir=str(tmp_path),
                                        endpoint="http://127.0.0.1:9",
                                        poll_interval_s=5.0)
        assert bridge is not None and bridge.systems is first
        again = pb.start_praxis_bridge(second, state_dir=str(tmp_path),
                                       endpoint="http://127.0.0.1:9")
        assert again is bridge
        assert bridge.systems is second

        bridge._request = lambda *a, **k: {"situations": [_situation()]}
        bridge.episode_id = "ep_1"
        assert bridge.pull_once() == 1
        assert g2.received and "_praxis_context" in second
        assert "_praxis_context" not in first
    finally:
        pb.stop_praxis_bridge()


def test_rebind_with_the_same_dict_changes_nothing(tmp_path):
    systems, _gateway = _organism()
    bridge = PraxisBridge(systems, state_dir=str(tmp_path))
    assert bridge.rebind_systems(systems) is False
    assert bridge.rebind_systems(None) is False
    assert bridge.systems is systems
