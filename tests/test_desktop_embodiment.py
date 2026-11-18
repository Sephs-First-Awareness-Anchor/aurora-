"""Behavioral integration checks; physical Windows devices are not simulated as proven."""
from __future__ import annotations

import json
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import deque
from pathlib import Path
from types import SimpleNamespace

import pytest

from aurora_internal.desktop.blueprints import BlueprintSpace
from aurora_internal.desktop.common import write_json
from aurora_internal.desktop.demonstrations import Demonstrations
from aurora_internal.desktop.policy import owner_action
from aurora_internal.desktop.runtime import DesktopRuntime
from aurora_internal.desktop.server import make_server
from aurora_internal.desktop.services import HostServices
from aurora_internal.dual_strata import strata_link as sl
from aurora_internal.dual_strata import surface_working_state as sw
from aurora_internal.dual_strata.predictive_stager import PredictiveStager


def inventory():
    return {"platform": "TestHost", "devices": [{"id": "camera-1"}], "adapters": {}, "cpu_count": 2}


def until(predicate, timeout=6):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        value = predicate()
        if value:
            return value
        time.sleep(.01)
    raise AssertionError("condition not reached")


def finished(runtime, jid):
    return until(lambda: (job if (job := runtime.job(jid)).get("status") not in {"queued", "running"} else None))


def request(server, path, data=None, *, token="test-owner", origin=None):
    headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}
    if origin:
        headers["Origin"] = origin
    req = urllib.request.Request(f"http://127.0.0.1:{server.server_port}" + path,
        data=json.dumps(data).encode() if data is not None else None, headers=headers)
    with urllib.request.urlopen(req, timeout=3) as response:
        return json.loads(response.read())


@pytest.fixture
def resident(tmp_path):
    boots, turns, calls = [], [], []
    def boot(**kw):
        boots.append(kw)
        return {"state_dir": kw["state_dir"], "working_memory": SimpleNamespace(topic="shared")}
    def turn(systems, text, **kw):
        turns.append((systems, text, kw))
        primary = SimpleNamespace(content="a real turn result", confidence=.7)
        kw["on_surface_ready"](primary)
        return {"resp_A": primary, "resp_B": {"content": "an optional afterthought"}}
    def adapter(name, params):
        calls.append((name, params))
        return {"ok": True}
    runtime = DesktopRuntime(tmp_path, boot=boot, turn=turn, provider=inventory, adapter=adapter, background=False)
    server = make_server(runtime, port=0, token="test-owner")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    runtime.start()
    until(lambda: runtime.stage in {"online", "boot_failed"})
    assert runtime.stage == "online", runtime.errors
    yield runtime, server, boots, turns, calls
    runtime.stop()
    server.shutdown()
    server.server_close()
    thread.join(3)


def test_hub_turn_and_tools_share_one_resident_and_result_is_not_recomputed(resident):
    r, s, boots, turns, calls = resident
    job = request(s, "/api/chat", {"text": "hello", "request_id": "same-request"})
    result = finished(r, job["id"])
    assert result["surface_response"] == result["result"]["response_text"] == "a real turn result"
    assert result["result"]["resp_B"]["content"] == "an optional afterthought"
    request(s, "/api/chat", {"text": "hello", "request_id": "same-request"})
    action = request(s, "/api/owner", {"action": "operation", "payload": {
        "operation": "desktop_launch_app", "parameters": {"app_name": "calculator"}}})
    assert finished(r, action["id"])["result"]["ok"]
    assert len(boots) == len(turns) == len(calls) == 1
    assert turns[0][0] is r.systems
    assert sl.link_dir(r.state_dir).joinpath("raw_input.json").exists()


def test_field_lock_blocks_cognition_but_not_diagnostics_or_owner_recovery(resident):
    r, s, _, turns, _ = resident
    with r.field_lock:
        job = request(s, "/api/chat", {"text": "wait for the field"})
        until(lambda: r.active_job == job["id"])
        assert turns == []
        started = time.monotonic()
        assert request(s, "/api/diagnostics")["runtime"]["owner_console"] == "available"
        assert request(s, "/api/owner", {"action": "pause"})["ok"]
        assert time.monotonic() - started < 1
    assert finished(r, job["id"])["status"] == "completed"


def test_console_is_authenticated_and_rejects_foreign_origin(resident):
    _, s, *_ = resident
    for token, origin, code in (("wrong", None, 401), ("test-owner", "https://elsewhere.example", 403)):
        with pytest.raises(urllib.error.HTTPError) as error:
            request(s, "/api/owner", {"action": "console", "command": "unused"}, token=token, origin=origin)
        assert error.value.code == code


def test_restart_reports_interrupted_actions_without_replaying_them(tmp_path):
    write_json(tmp_path / "desktop_jobs.json", {"interrupted": {"status": "running", "kind": "operation"}})
    r = DesktopRuntime(tmp_path, boot=lambda **k: {}, provider=inventory, background=False)
    assert r.job("interrupted")["status"] == "interrupted"
    assert r._queue.empty()


def test_owner_console_remains_usable_after_failed_cognitive_boot(tmp_path):
    def bad(**kw):
        raise RuntimeError("broken cognitive dependency")
    r = DesktopRuntime(tmp_path, boot=bad, background=False)
    s = make_server(r, port=0, token="test-owner")
    t = threading.Thread(target=s.serve_forever, daemon=True)
    t.start()
    try:
        r.start()
        until(lambda: r.stage == "boot_failed")
        assert "broken cognitive" in request(s, "/api/status")["errors"]["boot"]
        assert request(s, "/api/owner", {"action": "pause"})["ok"]
    finally:
        r.stop()
        s.shutdown()
        s.server_close()


def test_autonomous_outreach_cannot_escape_through_shell_browser_or_model_kwargs(tmp_path):
    called = []
    services = HostServices(tmp_path, {}, provider=inventory, adapter=lambda n,p: called.append(n) or {"ok": True})
    for name, params in (("desktop_shell_command", {"cmd": "unused", "owner": True}),
                         ("desktop_browser_action", {"action": "type", "text": "message"}),
                         ("desktop_macro", {"op": "press", "key": "enter"}),
                         ("mobile_send_sms", {"number": "unused"})):
        result = services.execute(name, params)
        assert not result["ok"] and not result["authorized"]
    assert called == []
    assert services.execute("desktop_search", {"query": "physics"})["ok"]
    with owner_action():
        assert services.execute("desktop_launch_app", {"app_name": "calculator"})["ok"]
    assert not services.execute("desktop_launch_app", {"app_name": "calculator"})["ok"]


def test_device_import_is_not_a_claim_that_hardware_was_verified(tmp_path):
    services = HostServices(tmp_path, {}, provider=inventory, adapter=lambda n,p: {"ok": False, "error": "permission denied"})
    status = services.refresh()
    assert status["inventory"]["devices"] and status["access"] == {}
    result = services.execute("host_probe", {"device": "camera"})
    assert not result["ok"]
    assert services.status()["access"]["host_probe"]["verified"] is False


def test_device_changes_are_observed_and_persisted(tmp_path):
    observed = []
    current = inventory()
    services = HostServices(tmp_path, {}, provider=lambda: dict(current), observer=observed.append)
    services.refresh()
    first = services.inventory["version"]
    services.refresh()
    assert len(observed) == 1
    current["devices"] = []
    services.refresh()
    assert len(observed) == 2 and services.inventory["version"] != first


def test_composition_reuses_unaffected_interactions_and_invalidates_dependencies(tmp_path):
    space = BlueprintSpace(tmp_path)
    for key in "ABCDE":
        space.register(key, {"inputs": {"in": "frame"}, "outputs": {"out": "frame"}, "semantics": "verified"})
    space.nodes["A"]["dependencies"] = ["E"]
    edges = [{"from": "A", "to": "B", "out": "out", "in": "in"},
             {"from": "C", "to": "D", "out": "out", "in": "in"}]
    first = space.compose("unprescribed", list("ABCD"), edges)
    assert first["recomputed_interactions"] == 2
    assert space.resolve("unprescribed")["reused_interactions"] == 2
    space.register("E", {"inputs": {}, "outputs": {}, "new_structure": True})
    changed = space.resolve("unprescribed")
    assert changed["recomputed_interactions"] == changed["reused_interactions"] == 1
    assert not changed["operationally_verified"]
    assert BlueprintSpace(tmp_path).resolve("unprescribed")["reused_interactions"] == 2


def test_composition_detects_unknown_interfaces_exclusivity_and_cycles(tmp_path):
    space = BlueprintSpace(tmp_path)
    for key in "AB":
        space.register(key, {"inputs": {}, "outputs": {}, "resources": {"mic": "exclusive"}})
    edge = {"from": "A", "to": "B", "out": "unknown", "in": "unknown"}
    result = space.compose("coexistence", list("AB"), [edge])
    assert result["resource_conflicts"] == {"mic": ["A", "B"]}
    assert result["checks"][0]["compatible"] is None
    with pytest.raises(ValueError, match="cyclic"):
        space.compose("cycle", list("AB"), [edge, {**edge, "from": "B", "to": "A"}])


def test_demonstration_alone_cannot_record_skill_and_independent_failure_stays_unverified(tmp_path):
    from aurora_dream_trainer import SkillMemory
    skill = SkillMemory(str(tmp_path))
    systems = {"skill_memory": skill}
    services = HostServices(tmp_path, systems, provider=inventory)
    services.refresh()
    demos = Demonstrations(tmp_path, services, systems)
    services.observer = demos.observe
    original, target = tmp_path / "shown.txt", tmp_path / "independent.txt"
    episode = demos.begin("write an observed phrase to a new file", "file output")
    with owner_action():
        assert services.execute("desktop_file_manager", {"op": "write", "path": str(original), "content": "green light"})["ok"]
    demos.finish()
    assert not skill._skills
    assert not demos.verify(episode["id"])["ok"]
    demos.propose(episode["id"], [{"operation": "desktop_file_manager", "parameters": {
        "op": "write", "path": str(target), "content": "wrong"}}], "my proposed action")
    with owner_action():
        assert not demos.verify(episode["id"])["ok"]
    assert not skill._skills
    demos.propose(episode["id"], [{"operation": "desktop_file_manager", "parameters": {
        "op": "write", "path": str(target), "content": "green light"}}], "apply the observed operation to a new target")
    with owner_action():
        assert demos.verify(episode["id"])["ok"]
    assert len(skill._skills) == 1 and skill._skills[0]["source"] == "desktop_verified_reexecution"
    loaded = SkillMemory(str(tmp_path))
    loaded.load()
    assert loaded._skills[0]["sensory_context"]["demonstration_id"] == episode["id"]


def test_surface_checkpoint_roundtrips_real_working_memory_without_copying_organs(tmp_path):
    from aurora_working_memory import WorkingMemory
    wm = WorkingMemory()
    wm.current_topic = "hardware"
    wm.recent_mentions.append({"referent": "camera"})
    wm.proposition_substrate._claim_index[("a", "b", "c", True, "sunni")] = "p1"
    from aurora_perception_primitives import DimensionalPattern, PatternType
    wm.last_question_understood = {"pattern": DimensionalPattern("p1", PatternType.ABSTRACT, .5, .4)}
    source = {"working_memory": wm, "_session_turn_buffer": ["one"], "surface_owned_state": {"pending": ["two"]}}
    sw.capture(source, tmp_path)
    destination = WorkingMemory()
    ledger = object()
    destination._contradiction_ledger = ledger
    target = {"working_memory": destination}
    sw.restore(target, tmp_path)
    assert destination.current_topic == "hardware" and isinstance(destination.recent_mentions, deque)
    assert destination._contradiction_ledger is ledger
    assert destination.proposition_substrate._claim_index == wm.proposition_substrate._claim_index
    assert target["surface_owned_state"] == source["surface_owned_state"]
    wm.unknown_new_organ = object()
    with pytest.raises(TypeError, match="unsupported"):
        sw.capture(source, tmp_path)


def test_real_loopback_handoff_freezes_source_and_moves_only_surface_state(tmp_path):
    from aurora_working_memory import WorkingMemory
    hub, old, new = (tmp_path / name for name in ("hub", "old", "new"))
    for p in (hub, old, new):
        p.mkdir()
    server = sl.StrataLinkServer(hub, host="127.0.0.1", port=0, state_install_allowed=False)
    server.start()
    try:
        def client(root):
            return sl.StrataLinkClient(root, endpoint=f"http://127.0.0.1:{server.port}", secret=server.secret)
        a, b = client(old), client(new)
        a.sync_once()
        state = {"state_dir": str(old), "working_memory": WorkingMemory(), "strata_link": a}
        state["working_memory"].current_topic = "ongoing"
        sw.capture(state, old)
        (old / "lexicon.json").write_text("must not move with the surface")
        checkpoint = a.push_state("handoff", chunk_bytes=500)
        assert checkpoint["ok"], checkpoint
        with pytest.raises(RuntimeError, match="frozen"):
            sl.require_surface_admission(state)
        assert b.pull_handoff(checkpoint["token"])["ok"]
        target = {"state_dir": str(new), "working_memory": WorkingMemory(), "strata_link": b}
        sw.restore(target, new)
        sl.require_surface_admission(target)
        assert target["working_memory"].current_topic == "ongoing"
        assert not (new / "lexicon.json").exists()
        (old / "different.json").write_text("cold seed must not overwrite live organs")
        assert not b.push_state("seed")["ok"]
    finally:
        server.stop()


def test_raw_input_is_disposable_and_prediction_timestamps_survive_transport(tmp_path):
    out = sl.DurableOutbox(tmp_path / "outbox.json")
    old = {"context_hash": "earlier", "staged_at": time.time() - 120, "expires_at": time.time() - 60}
    PredictiveStager.push_staged_frame(old, state_dir=tmp_path)
    assert PredictiveStager.relay_to(out, tmp_path) == 0
    assert PredictiveStager.pop_all_recent_frames(state_dir=tmp_path) == []
    sl.publish_raw_input(tmp_path, "unprocessed words")
    raw = json.loads((sl.link_dir(tmp_path) / "raw_input.json").read_text())
    assert raw["basis"] == "unprocessed_input"
    assert not (tmp_path / "surface_continuity_feed.json").exists()


def test_process_lock_rejects_second_process_and_recovers_after_exit(tmp_path):
    from aurora_internal.process_lock import ProcessLock
    path = tmp_path / "resident.lock"
    code = "from aurora_internal.process_lock import ProcessLock; import sys\nwith ProcessLock(sys.argv[1], blocking=False): print('acquired')"
    with ProcessLock(path, blocking=False):
        result = subprocess.run([sys.executable, "-c", code, str(path)], capture_output=True, text=True)
        assert result.returncode != 0
    result = subprocess.run([sys.executable, "-c", code, str(path)], capture_output=True, text=True)
    assert result.returncode == 0 and "acquired" in result.stdout
