#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_strata_fencing.py -- one holder at a time, and every lived moment
integrated exactly once (surface restructure 3e, Sir's tightenings 2 and 3).

Two temporary state directories stand in for the phone and home, joined by an
in-memory wire, as in test_strata_link.py.  These pin:
  * the source freezes on disk BEFORE its checkpoint is committed, and home
    refuses a handoff commit from a source that has not frozen;
  * a lost commit reply leaves the source frozen until home says whether the
    checkpoint landed; a commit that never arrived thaws it;
  * role, readiness and epoch survive a restart: the last holder stays present
    away from home, a device that never held her cannot start living;
  * every lived moment carries (surface_id, epoch, seq);
  * home recognises a redelivered moment long after it left the feed;
  * a superseded device's moments from its own epochs, up to its seal, are
    integrated late and once; anything after the seal waits on the device;
  * the target of a completed move drops a freeze left from an earlier time;
  * an outbox that cannot be written keeps the moments in the feed.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from aurora_internal.dual_strata import predictive_stager as ps
from aurora_internal.dual_strata import strata_link as sl
from aurora_internal.dual_strata import surface_continuity_feed as feed
from aurora_internal.dual_strata.surface_continuity_feed import (
    deposit_continuity_packet, peek_continuity_packets,
    read_and_clear_continuity_packets, write_continuity_packet)


class Wire:
    def __init__(self, server, monkeypatch, home: Path) -> None:
        self.server = server
        self.down = False
        self.lose_response = False
        self.fail_op = ""           # request with this state op never arrives
        self.lose_op = ""           # request with this state op applied, reply lost
        self.rewrite = None         # optional body rewrite before home reads it
        self._mp = monkeypatch
        self._home = home

    def transport_for(self, device: Path):
        def transport(body, headers):
            op = (json.loads(body.decode("utf-8")).get("state_op") or {}).get("op", "")
            if self.down or (self.fail_op and op == self.fail_op):
                raise OSError("network unreachable")
            if self.rewrite is not None:
                body = self.rewrite(body)
                ts = headers["X-Aurora-Ts"]
                headers = {"X-Aurora-Ts": ts, "X-Aurora-Sig": sl.sign(self.server.secret, ts, body)}
            self._mp.setattr(ps, "_QUEUE_PATH", self._home / "predictive_frame_queue.json")
            status, out, extra = self.server.handle_http(body, headers)
            self._mp.setattr(ps, "_QUEUE_PATH", device / "predictive_frame_queue.json")
            if self.lose_response or (self.lose_op and op == self.lose_op):
                raise OSError("connection reset")
            if status != 200:
                raise OSError(f"http {status}")
            return out, extra
        return transport


@pytest.fixture()
def rig(tmp_path, monkeypatch):
    home, phone, tablet = tmp_path / "home", tmp_path / "phone", tmp_path / "tablet"
    for d in (home, phone, tablet):
        d.mkdir()
    server = sl.StrataLinkServer(home, port=0)
    wire = Wire(server, monkeypatch, home)

    def client_for(device: Path) -> sl.StrataLinkClient:
        return sl.StrataLinkClient(device, endpoint="http://home", secret=server.secret,
                                   transport=wire.transport_for(device))
    return {"home": home, "phone": phone, "tablet": tablet, "server": server, "wire": wire,
            "client_for": client_for, "phone_client": client_for(phone)}


def _live(state_dir: Path, n: int) -> str:
    return write_continuity_packet(state_dir, user_input=f"said {n}", aurora_response=f"answered {n}",
                                   concepts_activated=[f"c{n}"], dominant_axis="B", coherence=0.5,
                                   visual_description="the kitchen")


def _ready_for_handoff(rig) -> sl.StrataLinkClient:
    client = rig["phone_client"]
    client.sync_once()
    assert (client.role, client.epoch) == ("active", 1)
    (rig["phone"] / "surface_working_state.json").write_text('{"present": "state"}')
    return client


def _frozen(device: Path) -> bool:
    return (sl.link_dir(device) / "surface_frozen").exists()


# ---------------------------------------------------------------------------
# Freeze before release
# ---------------------------------------------------------------------------

def test_source_is_frozen_on_disk_before_home_commits(rig, monkeypatch):
    client = _ready_for_handoff(rig)
    seen = {}
    real_state_op = rig["server"]._state_op

    def watch(state, surface_id, active, op, now):
        if op.get("op") == "commit":
            seen["frozen_at_commit"] = _frozen(rig["phone"])
            seen["flag"] = op.get("source_frozen")
        return real_state_op(state, surface_id, active, op, now)
    monkeypatch.setattr(rig["server"], "_state_op", watch)
    result = client.push_state("handoff")
    assert result["ok"] and seen == {"frozen_at_commit": True, "flag": True}
    assert _frozen(rig["phone"]) and client.surface_ready is False


def test_home_refuses_a_handoff_from_a_source_that_has_not_frozen(rig):
    client = _ready_for_handoff(rig)

    def strip_flag(body: bytes) -> bytes:
        data = json.loads(body.decode("utf-8"))
        if (data.get("state_op") or {}).get("op") == "commit":
            data["state_op"].pop("source_frozen", None)
        return json.dumps(data).encode("utf-8")
    rig["wire"].rewrite = strip_flag
    result = client.push_state("handoff")
    assert result == {"ok": False, "error": "source_not_frozen"}
    # Home answered and refused: no checkpoint exists, so the source thaws.
    assert not _frozen(rig["phone"]) and client.surface_ready
    assert sl.StrataLinkServer(rig["home"], port=0)._load_state()["handoff"] is None


def test_a_lost_commit_reply_keeps_the_source_frozen_until_home_answers(rig):
    client = _ready_for_handoff(rig)
    rig["wire"].lose_op = "commit"
    result = client.push_state("handoff")
    assert result["ok"] is False and _frozen(rig["phone"])
    assert client._load_client_state()["handoff_in_flight"]
    rig["wire"].lose_op = ""
    client.sync_once()
    # The checkpoint did land: the freeze stays, the doubt is resolved.
    assert _frozen(rig["phone"]) and client.surface_ready is False
    assert client._load_client_state()["handoff_in_flight"] is None


def test_a_commit_that_never_arrived_thaws_the_source(rig):
    client = _ready_for_handoff(rig)
    rig["wire"].fail_op = "commit"
    result = client.push_state("handoff")
    assert result["ok"] is False and _frozen(rig["phone"])
    rig["wire"].fail_op = ""
    client.sync_once()
    assert not _frozen(rig["phone"]) and client.surface_ready and client.role == "active"


def test_a_failed_move_never_makes_two_holders(rig):
    client = _ready_for_handoff(rig)
    token = client.push_state("handoff")["token"]
    tablet = rig["client_for"](rig["tablet"])
    claimed = tablet._call({"claim": True, "handoff_token": token})
    assert claimed["role"] == "active" and claimed["surface_ready"] is False
    # The tablet stops before handoff_complete; the phone takes her back.
    assert client.cancel_handoff(token)["ok"]
    tablet.sync_once()
    assert (client.role, client.surface_ready) == ("active", True)
    assert (tablet.role, tablet.surface_ready) == ("standby", False)
    with pytest.raises(RuntimeError):
        sl.require_surface_admission({"strata_link": tablet, "state_dir": str(rig["tablet"])})
    sl.require_surface_admission({"strata_link": client, "state_dir": str(rig["phone"])})


def test_the_target_of_a_completed_move_drops_an_old_freeze(rig):
    client = _ready_for_handoff(rig)
    (sl.link_dir(rig["tablet"]) / "surface_frozen").write_text("from an earlier move")
    token = client.push_state("handoff")["token"]
    tablet = rig["client_for"](rig["tablet"])
    assert tablet.pull_handoff(token)["ok"]
    assert not _frozen(rig["tablet"]) and tablet.surface_ready
    sl.require_surface_admission({"strata_link": tablet, "state_dir": str(rig["tablet"])})


# ---------------------------------------------------------------------------
# Away from home: the holder stays present; nobody else starts living
# ---------------------------------------------------------------------------

def test_the_holder_stays_present_after_a_restart_away_from_home(rig):
    rig["phone_client"].sync_once()
    rig["wire"].down = True
    restarted = rig["client_for"](rig["phone"])
    assert restarted.sync_once() is False
    assert (restarted.role, restarted.surface_ready, restarted.epoch) == ("active", True, 1)
    assert restarted.away() and restarted.status()["status"] == "away"
    sl.require_surface_admission({"strata_link": restarted, "state_dir": str(rig["phone"])})


def test_a_device_that_never_held_her_cannot_start_living_offline(rig):
    rig["phone_client"].sync_once()
    rig["wire"].down = True
    tablet = rig["client_for"](rig["tablet"])
    tablet.sync_once()
    assert not tablet.away() and tablet.status()["status"] == "offline"
    with pytest.raises(RuntimeError):
        sl.require_surface_admission({"strata_link": tablet, "state_dir": str(rig["tablet"])})


# ---------------------------------------------------------------------------
# Lived moments: numbered, integrated once, late ones kept
# ---------------------------------------------------------------------------

def test_every_lived_moment_is_numbered_by_device_epoch_and_seq(rig):
    client = rig["phone_client"]
    client.sync_once()
    _live(rig["phone"], 1)
    _live(rig["phone"], 2)
    stamps = [(p["surface_id"], p["epoch"], p["seq"]) for p in peek_continuity_packets(rig["phone"])]
    assert stamps == [(client.surface_id, 1, 1), (client.surface_id, 1, 2)]
    assert sl.lived_high_water(rig["phone"]) == 2


def test_home_recognises_a_redelivery_long_after_it_left_the_feed(rig):
    client = rig["phone_client"]
    client.sync_once()
    _live(rig["phone"], 1)
    first = dict(peek_continuity_packets(rig["phone"])[0])
    client.sync_once()
    assert len(read_and_clear_continuity_packets(rig["home"])) == 1
    # Push the original far out of the feed's own 20-packet window.
    for n in range(2, 40):
        _live(rig["phone"], n)
    client.flush_outbox()
    read_and_clear_continuity_packets(rig["home"])
    assert deposit_continuity_packet(rig["home"], first) is False
    replay = dict(first, packet_id="a-new-id-for-the-same-moment")
    assert deposit_continuity_packet(rig["home"], replay) is False
    status = feed.integrated_ledger_status(rig["home"])
    assert status["duplicates_refused"] == 2
    assert status["devices"][f"{client.surface_id}:1"] == {"high_water": 39, "missing": 0}


def test_a_superseded_device_delivers_what_it_lived_up_to_its_seal(rig):
    server = rig["server"]
    state = server._load_state()
    state["owner"], state["epoch"] = "surface-new", 4
    state["owner_epochs"] = {"3": "surface-old", "4": "surface-new"}
    state["sealed"] = {"3": 2}
    sl._atomic_write_json(server._state_path, state)

    def record(seq, lived_seq):
        return {"seq": seq, "channel": "continuity", "kind": "event",
                "payload": {"packet_id": f"p{lived_seq}", "surface_id": "surface-old",
                            "epoch": 3, "seq": lived_seq, "user_input": f"late {lived_seq}"}}
    reply = server.handle_sync({"surface_id": "surface-old", "up": [record(1, 1), record(2, 2), record(3, 3)]})
    assert reply["role"] == "standby" and reply["up_ack"] == 2
    arrived = read_and_clear_continuity_packets(rig["home"])
    assert [(p["user_input"], p["arrived_late"]) for p in arrived] == [("late 1", True), ("late 2", True)]
    assert server.counters["late_applied"] == 2
    # Redelivered: acknowledged again, lived once.
    again = server.handle_sync({"surface_id": "surface-old", "up": [record(1, 1), record(2, 2)]})
    assert again["up_ack"] == 2 and read_and_clear_continuity_packets(rig["home"]) == []
    # A device that never held her is not integrated; its records wait.
    stranger = server.handle_sync({"surface_id": "surface-x", "up": [
        {"seq": 1, "channel": "continuity", "kind": "event",
         "payload": {"packet_id": "x1", "surface_id": "surface-x", "epoch": 3, "seq": 1}}]})
    assert stranger["up_ack"] == 0 and read_and_clear_continuity_packets(rig["home"]) == []


def test_a_handoff_seals_the_sources_epoch_at_its_last_lived_moment(rig):
    client = _ready_for_handoff(rig)
    _live(rig["phone"], 1)
    _live(rig["phone"], 2)
    assert client.push_state("handoff")["ok"]
    assert rig["server"]._load_state()["sealed"] == {"1": 2}


# ---------------------------------------------------------------------------
# Finite storage
# ---------------------------------------------------------------------------

def test_an_outbox_that_cannot_be_written_keeps_moments_in_the_feed(rig, monkeypatch):
    client = rig["phone_client"]
    _live(rig["phone"], 1)
    real_write = sl._atomic_write_json

    def full_disk(path, payload):
        if Path(path).name == "up_outbox.json":
            raise OSError(28, "No space left on device")
        return real_write(path, payload)
    monkeypatch.setattr(sl, "_atomic_write_json", full_disk)
    client.sync_once()
    assert len(peek_continuity_packets(rig["phone"])) == 1
    assert client.outbox.stats()["condition"] == "storage_exhausted"
    monkeypatch.setattr(sl, "_atomic_write_json", real_write)
    client.sync_once()
    assert peek_continuity_packets(rig["phone"]) == []
    assert [p["user_input"] for p in read_and_clear_continuity_packets(rig["home"])] == ["said 1"]


def test_low_free_space_keeps_new_turns_compact(tmp_path):
    box = sl.DurableOutbox(tmp_path / "o.json", free_space=lambda _p: 1024)
    box.append("continuity", "event", {"packet_id": "a", "user_input": "hi",
                                       "visual_description": "the kitchen", "recent_speech": "hi"})
    payload = box.pending()[0]["payload"]
    assert payload == {"packet_id": "a", "user_input": "hi", "compact": True}
    assert box.stats()["condition"] == "storage_low"
