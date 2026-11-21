#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_hub_route.py -- the desktop hub speaks to her where she is, Sir's Move
button, and home's setup (surface restructure 2, 3c, easy setup).

These pin:
  * a message typed at the hub while a phone holds her reaches the phone, is
    lived there as a turn, and her answer comes back to the hub;
  * while she is on the desktop, nothing is sent down;
  * a phone cannot file the hub's own requests through its uplink;
  * Sir's Move button files a move for the holder that home carries out;
  * home listens where the setup chose, and the desktop is known by name;
  * a phone whose first pairing is waiting asks home by itself.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from aurora_internal.dual_strata import hub_route as hr
from aurora_internal.dual_strata import strata_link as sl

from tests.test_strata_fencing import Wire  # noqa: E402  (same in-memory wire)


@pytest.fixture()
def rig(tmp_path, monkeypatch):
    home, phone = tmp_path / "home", tmp_path / "phone"
    for d in (home, phone):
        d.mkdir()
    server = sl.StrataLinkServer(home, port=0)
    server.set_home_surface("desk-1")
    wire = Wire(server, monkeypatch, home)
    sl.link_dir(phone).joinpath("device_name.txt").write_text("phone")
    client = sl.StrataLinkClient(phone, endpoint="http://home", secret=server.secret,
                                 transport=wire.transport_for(phone))
    client.sync_once()
    assert client.role == "active"
    return {"home": home, "phone": phone, "server": server, "client": client, "wire": wire}


def _hold(home: Path) -> None:
    (sl.link_dir(home) / "downlink_enabled").write_text("migrated test")


def test_a_message_from_the_hub_reaches_her_on_the_phone_and_her_answer_comes_back(rig):
    home, phone, server, client = rig["home"], rig["phone"], rig["server"], rig["client"]
    _hold(home)
    where = hr.holder(home)
    assert where["elsewhere"] and where["name"] == "phone"
    sent = hr.send_hub_message(home, "are you warm enough?")
    requests, _ = sl.read_home_requests(home, 0)
    (req,) = [r for r in requests if r["kind"] == "hub_message"]
    assert req["from"] == "hub"
    assert hr.send_to_holder(server, req["payload"])["status"] == "sent"
    client.sync_once()                                     # the message comes down
    assert [m["text"] for m in hr.pending_messages(phone)] == ["are you warm enough?"]
    heard = []
    answered = hr.answer_pending(phone, lambda text: heard.append(text) or "a little cold", client.outbox)
    assert answered == 1 and heard == ["are you warm enough?"]
    assert hr.pending_messages(phone) == []                # lived once
    client.sync_once()                                     # her answer goes home
    reply = hr.read_reply(home, sent["message_id"])
    assert reply["status"] == "answered" and reply["text"] == "a little cold"


def test_nothing_is_sent_down_while_she_is_on_the_desktop(rig, tmp_path):
    home, server = rig["home"], rig["server"]
    _hold(home)
    state = server._load_state()
    state["owner"] = "desk-1"
    sl._atomic_write_json(server._state_path, state)
    assert hr.holder(home)["elsewhere"] is False
    out = hr.send_to_holder(server, {"message_id": "m1", "text": "hello"})
    assert out["status"] == "not_sent" and out["error"] == "she_is_here"
    assert not [r for r in server.outbox.pending() if r["channel"] == "hub_message"]


def test_a_phone_cannot_file_the_hubs_own_requests(rig):
    home = rig["home"]
    record = {"channel": "home_request", "payload": {"request_id": "x1", "kind": "hub_move",
                                                     "payload": {"to": "phone"}, "from": "hub"}}
    assert sl.apply_uplink_record(home, record) == "unknown_channel"
    requests, _ = sl.read_home_requests(home, 0)
    assert not requests


def test_sirs_move_button_files_a_move_home_carries_out(rig):
    home, server, client = rig["home"], rig["server"], rig["client"]
    filed = hr.file_hub_request(home, "hub_move", {"to": "home"})
    assert filed["ok"]
    requests, _ = sl.read_home_requests(home, 0)
    (req,) = requests
    # The resident files it exactly as runtime._hub_request does.
    out = server.request_move(req["payload"]["to"], requested_by="hub")
    assert out["ok"] and out["to"] == "desk-1" and out["requested_by"] == "hub"


def test_home_listens_where_the_setup_chose(tmp_path, monkeypatch):
    monkeypatch.delenv("AURORA_STRATA_LINK_HOST", raising=False)
    assert sl.listen_host(tmp_path) == "127.0.0.1"
    sl.link_dir(tmp_path).joinpath("listen_host.txt").write_text("192.168.1.20")
    assert sl.listen_host(tmp_path) == "192.168.1.20"
    monkeypatch.setenv("AURORA_STRATA_LINK_HOST", "10.0.0.5")
    assert sl.listen_host(tmp_path) == "10.0.0.5"


def test_the_desktop_is_known_by_name(rig):
    home, server = rig["home"], rig["server"]
    sl.link_dir(home).joinpath("device_name.txt").write_text("desktop")
    server.handle_sync({"surface_id": "desk-1", "name": sl.device_name(home)})
    assert server._load_state()["names"]["desk-1"] == "desktop"
    names = {d["name"] for d in server.known_devices()}
    assert {"home", "phone"} <= names                       # her tool calls the desktop home


def test_a_phone_with_a_first_pairing_waiting_asks_home_by_itself(rig, monkeypatch):
    client = rig["client"]
    client.online = True
    assert client._migration_check_due() is False          # nothing sent yet
    client._save_client_state(migration={"id": "migrate-abc", "digest": "d", "lived_seq": 0})
    assert client._migration_check_due() is True
    client._next_migration_check_at = sl.time.time() + 30
    assert client._migration_check_due() is False          # asks on its own schedule
