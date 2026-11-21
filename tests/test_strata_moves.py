#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_strata_moves.py -- moving her: she asks, home carries it out (surface
restructure 3c).

These pin:
  * a move asked for by the holder ends with the target holding her at the
    next epoch and the old device frozen;
  * a device that does not hold her cannot ask;
  * a target that never shows up leaves her present where she is;
  * a target that goes quiet after the checkpoint is cancelled cleanly: the
    source holds her again and its freeze lifts;
  * a move to the desktop's own surface takes no network step;
  * a request made while away waits in the outbox and runs when home returns;
  * her tool asks home and never moves her itself; with no target it tells
    her where she can go, by the names home knows.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from aurora_internal.dual_strata import strata_link as sl
from aurora_internal import tool_registry

from tests.test_strata_fencing import Wire  # noqa: E402  (same in-memory wire)


@pytest.fixture()
def rig(tmp_path, monkeypatch):
    home, phone, tablet = tmp_path / "home", tmp_path / "phone", tmp_path / "tablet"
    for d in (home, phone, tablet):
        d.mkdir()
    server = sl.StrataLinkServer(home, port=0)
    wire = Wire(server, monkeypatch, home)

    def client_for(device: Path, name: str) -> sl.StrataLinkClient:
        sl.link_dir(device).joinpath("device_name.txt").write_text(name)
        return sl.StrataLinkClient(device, endpoint="http://home", secret=server.secret,
                                   transport=wire.transport_for(device))
    phone_client, tablet_client = client_for(phone, "phone"), client_for(tablet, "tablet")
    phone_client.sync_once()
    tablet_client.sync_once()
    assert phone_client.role == "active" and tablet_client.role == "standby"
    (phone / "surface_working_state.json").write_text('{"present": "on the phone"}')
    return {"home": home, "phone": phone, "tablet": tablet, "server": server, "wire": wire,
            "phone_client": phone_client, "tablet_client": tablet_client, "mp": monkeypatch}


def _frozen(device: Path) -> bool:
    return (sl.link_dir(device) / "surface_frozen").exists()


def _round(*clients):
    for client in clients:
        client.sync_once()
        client.follow_move_order()


def test_the_holder_asks_and_home_moves_her(rig):
    phone, tablet, server = rig["phone_client"], rig["tablet_client"], rig["server"]
    asked = server.request_move("tablet", from_surface=phone.surface_id)
    assert asked["ok"] and asked["to"] == tablet.surface_id
    for _ in range(4):
        _round(phone, tablet)
    assert tablet.role == "active" and tablet.surface_ready and tablet.epoch == 2
    assert phone.role == "standby" and _frozen(rig["phone"])
    assert json.loads((rig["tablet"] / "surface_working_state.json").read_text()) == {"present": "on the phone"}
    status = server.move_status()
    assert status["move"] is None and status["recent"][-1]["outcome"] == "completed"


def test_only_the_holder_may_ask(rig):
    server = rig["server"]
    out = server.request_move("phone", from_surface=rig["tablet_client"].surface_id)
    assert out == {"ok": False, "error": "only_the_holder_may_ask"}
    assert server.request_move("nowhere")["error"] == "unknown_device"


def test_a_target_that_never_shows_up_leaves_her_where_she_is(rig):
    phone, server = rig["phone_client"], rig["server"]
    mp = rig["mp"]
    server.request_move("tablet", from_surface=phone.surface_id)
    later = [sl.time.time() + sl.MOVE_TARGET_RECENT_S + 5]
    mp.setattr(sl.time, "time", lambda: later[0])
    _round(phone)                                   # the tablet has gone quiet
    assert phone.move_order is None and not _frozen(rig["phone"])
    assert server.move_status()["move"]["stage"] == "waiting_for_target"
    later[0] += sl.MOVE_WAIT_FOR_TARGET_S + 5
    _round(phone)
    assert server.move_status()["recent"][-1]["outcome"] == "target_never_showed"
    assert phone.role == "active" and phone.surface_ready


def test_a_target_that_goes_quiet_after_the_checkpoint_is_cancelled(rig):
    phone, tablet, server = rig["phone_client"], rig["tablet_client"], rig["server"]
    server.request_move("tablet", from_surface=phone.surface_id)
    _round(phone)                                   # checkpoint asked and taken
    assert _frozen(rig["phone"]) and server.move_status()["move"]["stage"] in ("checkpoint_asked",
                                                                                "claim_offered")
    _round(phone)
    assert server.move_status()["move"]["stage"] == "claim_offered"
    later = sl.time.time() + sl.MOVE_STEP_TIMEOUT_S + 5
    rig["mp"].setattr(sl.time, "time", lambda: later)
    _round(phone)
    _round(phone)
    assert server.move_status()["recent"][-1]["outcome"] == "target_went_quiet"
    assert phone.role == "active" and phone.surface_ready and not _frozen(rig["phone"])
    assert phone.epoch == 2                          # she holds herself again, fenced anew


def test_a_move_home_takes_no_network_step(rig, tmp_path):
    phone, server = rig["phone_client"], rig["server"]
    server.set_home_surface("desktop")
    server.request_move("home", from_surface=phone.surface_id)
    _round(phone)
    _round(phone)
    order = server.local_move_order("desktop")
    assert order["action"] == "claim" and order["token"]
    # The resident claims through its own local client, as its handoff_claim job does.
    desk = sl.StrataLinkClient(rig["home"], endpoint="http://home", secret=server.secret,
                               transport=rig["wire"].transport_for(rig["home"]))
    (sl.link_dir(rig["home"]) / "surface_id.txt").write_text("desktop")
    desk.surface_id = "desktop"
    assert desk.pull_handoff(order["token"])["ok"]
    assert server.status()["owner"] == "desktop"
    assert server.move_status()["recent"][-1]["outcome"] == "completed"


def test_a_request_made_away_waits_and_runs_when_home_returns(rig, monkeypatch):
    phone, tablet = rig["phone_client"], rig["tablet_client"]
    monkeypatch.setattr(sl, "_CLIENT", phone)
    rig["wire"].down = True
    phone.sync_once()
    assert phone.away()
    result = tool_registry.call("embodiment_move", to="tablet", systems={"state_dir": str(rig["phone"])})
    assert result.success and json.loads(result.data)["waiting_for_home"] is True
    assert rig["server"].move_status()["move"] is None
    rig["wire"].down = False
    phone.sync_once()                               # the request crosses
    requests, _ = sl.read_home_requests(rig["home"], 0)
    (req,) = [r for r in requests if r["kind"] == "embodiment_move"]
    # Home's resident files it exactly as _embodiment_move_requested does.
    filed = rig["server"].request_move(req["payload"]["to"], from_surface=req["from"])
    assert filed["ok"]
    for _ in range(4):
        _round(phone, tablet)
    assert tablet.role == "active"


def test_her_tool_only_asks_and_lists_where_she_can_go(rig, monkeypatch):
    phone = rig["phone_client"]
    monkeypatch.setattr(sl, "_CLIENT", phone)
    sl.link_dir(rig["home"]).joinpath("downlink_enabled").write_text("1")
    phone.sync_once()
    phone.sync_once()
    listed = tool_registry.call("embodiment_move", systems={"state_dir": str(rig["phone"])})
    names = {d["name"] for d in json.loads(listed.data)["devices"]}
    assert {"phone", "tablet"} <= names
    monkeypatch.setattr(sl, "_CLIENT", rig["tablet_client"])
    refused = tool_registry.call("embodiment_move", to="phone", systems={"state_dir": str(rig["tablet"])})
    assert refused.success is False and refused.note == "only_the_holder_may_ask"
