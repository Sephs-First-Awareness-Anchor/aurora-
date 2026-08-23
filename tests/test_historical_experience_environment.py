import importlib.util
import json
import sys
import time
import zipfile
from pathlib import Path
from types import SimpleNamespace


MODULE_PATH = Path(__file__).resolve().parents[1] / "flutter_app/android/app/src/main/python/aurora_historical_experience_environment.py"
spec = importlib.util.spec_from_file_location("aurora_historical_experience_environment_test", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)
HistoricalExperienceEnvironment = mod.HistoricalExperienceEnvironment


class _StreamType:
    SENSOR_DATA = "sensor_data"


class _ExistenceMode:
    BOUNDED = "bounded"


class _Gateway:
    def __init__(self):
        self.calls = []

    def receive(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(response_id=f"r{len(self.calls)}", confidence=0.42)


class _Aurora:
    def __init__(self, gateway):
        self.gateway = gateway



class _Dimensional:
    def __init__(self):
        self.saves = 0

    def save_state(self, state_dir):
        self.saves += 1
        Path(state_dir, "dps_crystals.json").write_text(json.dumps({"save": self.saves}))
        return True


class _Registry:
    def __init__(self):
        self.saves = 0

    def save(self, state_dir):
        self.saves += 1
        Path(state_dir, "concept_crystals.test.json").write_text(json.dumps({"save": self.saves}))


def _write_archive(path: Path, events):
    episode_ids = []
    for e in events:
        if e["episode_id"] not in episode_ids:
            episode_ids.append(e["episode_id"])
    manifest = {
        "schema": "aurora_experiential_baseline_manifest_v1",
        "event_count": len(events),
        "episode_count": len(episode_ids),
        "first_event_utc": "2024-01-01T00:00:00+00:00",
        "last_event_utc": "2024-01-02T00:00:00+00:00",
    }
    episodes = []
    for i, eid in enumerate(episode_ids):
        episodes.append({
            "episode_id": eid,
            "previous_episode_gap_seconds": None if i == 0 else 3600.0,
        })
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(manifest))
        z.writestr("episodes.jsonl", "".join(json.dumps(x) + "\n" for x in episodes))
        z.writestr("events.jsonl", "".join(json.dumps(x) + "\n" for x in events))


def _event(i, actor="user", episode="ep1"):
    return {
        "event_id": f"evt{i}",
        "episode_id": episode,
        "actor": actor,
        "text": f"message {i}",
        "timestamp": 1704067200.0 + i,
        "delta_seconds_from_previous_turn": None if i == 0 else 1.0,
        "epistemic_status": "observation_not_truth",
        "causal_status": "sequence_observed_causality_not_asserted",
        "autobiographical_status": "not_aurora_memory",
        "provenance": "chatgpt_export_active_branch",
    }


def _env(tmp_path, events, *, idle=lambda: True):
    archive = tmp_path / "experiential_baseline_v1.zip"
    _write_archive(archive, events)
    gateway = _Gateway()
    systems = {
        "aurora": _Aurora(gateway),
        "StreamType": _StreamType,
        "ExistenceMode": _ExistenceMode,
        "dimensional": _Dimensional(),
        "_concept_crystal_registry": _Registry(),
    }
    env = HistoricalExperienceEnvironment(
        systems,
        state_dir=str(tmp_path),
        archive_path=str(archive),
        live_idle=idle,
        initial_delay_s=0.0,
    )
    return env, gateway, systems


def test_historical_turn_is_witnessed_as_sensor_data_not_user_or_truth(tmp_path):
    env, gateway, systems = _env(tmp_path, [_event(0, "assistant")])
    env._prepare()
    event = json.loads((env.extract_dir / "events.jsonl").read_text().splitlines()[0])
    result = env._witness(event)

    assert len(gateway.calls) == 1
    call = gateway.calls[0]
    assert call["stream_type"] == _StreamType.SENSOR_DATA
    assert call["mode"] == _ExistenceMode.BOUNDED
    assert call["source"] == "historical_experience:historical_other_assistant"
    assert call["content"] == "[historical_other_assistant] message 0"
    assert call["metadata"]["epistemic_status"] == "observation_not_truth"
    assert call["metadata"]["autobiographical_status"] == "not_aurora_memory"
    assert call["metadata"]["causal_status"] == "sequence_observed_causality_not_asserted"
    assert result["actor"] == "historical_other_assistant"
    assert systems["_historical_experience_context"]["actor"] == "historical_other_assistant"


def test_active_branch_history_resumes_after_last_committed_event(tmp_path):
    events = [_event(0), _event(1, "assistant"), _event(2, "user", "ep2")]
    env, gateway, _ = _env(tmp_path, events)
    assert env.start()
    deadline = time.time() + 4.0
    while time.time() < deadline and not env.status().get("completed"):
        time.sleep(0.02)
    env.stop()
    first_status = env.status()
    assert first_status["completed"] is True
    assert first_status["events_experienced"] == 3
    assert len(gateway.calls) == 3

    # A second runtime against the same state/archive must not replay anything.
    gateway2 = _Gateway()
    systems2 = {"aurora": _Aurora(gateway2), "StreamType": _StreamType, "ExistenceMode": _ExistenceMode,
                "dimensional": _Dimensional(), "_concept_crystal_registry": _Registry()}
    env2 = HistoricalExperienceEnvironment(
        systems2,
        state_dir=str(tmp_path),
        archive_path=str(tmp_path / "experiential_baseline_v1.zip"),
        initial_delay_s=0.0,
    )
    assert env2.start()
    time.sleep(0.15)
    env2.stop()
    assert env2.status()["completed"] is True
    assert env2.status()["events_experienced"] == 3
    assert gateway2.calls == []


def test_live_activity_gate_prevents_historical_witness_until_idle(tmp_path):
    gate = {"idle": False}
    env, gateway, _ = _env(tmp_path, [_event(0)], idle=lambda: gate["idle"])
    assert env.start()
    time.sleep(0.2)
    assert gateway.calls == []
    gate["idle"] = True
    deadline = time.time() + 2.0
    while time.time() < deadline and not gateway.calls:
        time.sleep(0.02)
    env.stop()
    assert len(gateway.calls) == 1


def test_episode_gap_is_preserved_as_metadata_not_semantic_title(tmp_path):
    events = [_event(0, "user", "ep1"), _event(1, "user", "ep2")]
    env, gateway, _ = _env(tmp_path, events)
    env._prepare()
    lines = [json.loads(x) for x in (env.extract_dir / "events.jsonl").read_text().splitlines()]
    env._witness(lines[0])
    env._state["current_episode_id"] = "ep1"
    env._witness(lines[1])
    call = gateway.calls[-1]
    assert call["metadata"]["episode_boundary"] is True
    assert call["metadata"]["previous_episode_gap_seconds"] == 3600.0
    assert "title" not in call["metadata"]
    assert call["content"] == "[historical_user] message 1"


def test_gateway_preserves_observation_metadata_as_namespaced_evidence():
    import aurora_governance_persistence_gateway as g
    gateway = g.NSpaceGateway()
    packet = g.InboundPacket(
        packet_id="p1",
        stream_type=g.StreamType.SENSOR_DATA,
        content="observed",
        metadata={"historical_experience": True, "actor": "historical_user", "epistemic_status": "observation_not_truth"},
        source="historical_experience:historical_user",
    )
    evidence = gateway._build_evidence(packet, g.ExistenceMode.BOUNDED)
    assert evidence["source_metadata"] == packet.metadata
    assert "X" not in evidence["source_metadata"]
    assert "T" not in evidence["source_metadata"]


def test_ledger_recovers_successful_witness_if_cursor_write_was_interrupted(tmp_path):
    env, gateway, _ = _env(tmp_path, [_event(0), _event(1, "assistant")])
    env._prepare()
    with (env.extract_dir / "events.jsonl").open("r", encoding="utf-8") as fh:
        first_line = fh.readline()
        next_offset = fh.tell()
    event = json.loads(first_line)
    ledger = env._witness(event)
    ledger.update({
        "next_byte_offset": next_offset,
        "event_index_after": 1,
        "events_experienced_after": 1,
        "episodes_entered_after": 1,
    })
    env._append_ledger(ledger)
    # Deliberately do NOT advance runtime_state.json: simulate process death
    # after the observation completed but before the compact cursor write.

    gateway2 = _Gateway()
    systems2 = {"aurora": _Aurora(gateway2), "StreamType": _StreamType, "ExistenceMode": _ExistenceMode,
                "dimensional": _Dimensional(), "_concept_crystal_registry": _Registry()}
    env2 = HistoricalExperienceEnvironment(
        systems2,
        state_dir=str(tmp_path),
        archive_path=str(tmp_path / "experiential_baseline_v1.zip"),
        initial_delay_s=0.0,
    )
    env2._prepare()
    # Witness ledger alone is not enough anymore.  Without a matching crystal
    # checkpoint, the event is replayed so retained development and cursor agree.
    assert env2.status()["event_index"] == 0
    assert env2.status()["events_experienced"] == 0
    assert env2.status()["last_event_id"] == ""


def test_crystal_checkpoint_makes_cursor_durable_and_uncheckpointed_tail_rewinds(tmp_path):
    events = [_event(i) for i in range(5)]
    env, gateway, systems = _env(tmp_path, events)
    env.crystal_checkpoint_interval = 2
    assert env.start()
    deadline = time.time() + 4.0
    while time.time() < deadline and not env.status().get("completed"):
        time.sleep(0.02)
    env.stop()
    status = env.status()
    assert status["events_experienced"] == 5
    assert status["crystal_checkpoint_event_index"] == 5
    assert systems["dimensional"].saves >= 3

    # Simulate a later witnessed cursor tail without a crystal checkpoint.
    state_path = tmp_path / "historical_experience" / "runtime_state.json"
    state = json.loads(state_path.read_text())
    state["completed"] = False
    state["event_index"] = 6
    state["events_experienced"] = 6
    state_path.write_text(json.dumps(state))

    gateway2 = _Gateway()
    systems2 = {"aurora": _Aurora(gateway2), "StreamType": _StreamType, "ExistenceMode": _ExistenceMode,
                "dimensional": _Dimensional(), "_concept_crystal_registry": _Registry()}
    env2 = HistoricalExperienceEnvironment(
        systems2, state_dir=str(tmp_path), archive_path=str(tmp_path / "experiential_baseline_v1.zip"),
        initial_delay_s=0.0, crystal_checkpoint_interval=2,
    )
    env2._prepare()
    assert env2.status()["event_index"] == 5
    assert env2.status()["events_experienced"] == 5
