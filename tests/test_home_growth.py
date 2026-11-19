#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_home_growth.py -- home's growth reaching the surface's read-only copies
(surface restructure 3b, item 2).

These pin:
  * only home-owned stores travel; the surface's own present never does;
  * only files whose bytes differ are fetched, and nothing is deleted;
  * the copies change only at the next start, before the gate is armed;
  * a standby surface mirrors home's growth too;
  * home offers nothing before it holds her, nor while this phone's own first
    pairing is still on its way home;
  * a whole-mind device never pulls.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from aurora_internal.dual_strata import home_growth as hg
from aurora_internal.dual_strata import strata_link as sl

from tests.test_strata_fencing import Wire  # noqa: E402  (same in-memory wire)


@pytest.fixture()
def rig(tmp_path, monkeypatch):
    home, phone = tmp_path / "home", tmp_path / "phone"
    for d in (home, phone):
        d.mkdir()
    server = sl.StrataLinkServer(home, port=0)
    wire = Wire(server, monkeypatch, home)
    client = sl.StrataLinkClient(phone, endpoint="http://home", secret=server.secret,
                                 transport=wire.transport_for(phone))
    client.sync_once()
    (home / "lexicon.json").write_text('{"words": ["light", "home", "grew"]}')
    (home / "lineage").mkdir()
    (home / "lineage" / "paths.json").write_text('{"paths": 3}')
    (home / "surface_working_state.json").write_text('{"present": "home desk"}')
    (phone / "lexicon.json").write_text('{"words": ["light"]}')
    (phone / "unrelated_local.json").write_text('{"keep": true}')
    (phone / "surface_working_state.json").write_text('{"present": "on the phone"}')
    return {"home": home, "phone": phone, "server": server, "client": client, "wire": wire}


def _hold(home: Path) -> None:
    (sl.link_dir(home) / "downlink_enabled").write_text("migrated test")


def test_home_offers_nothing_before_it_holds_her(rig):
    out = rig["client"].pull_growth()
    assert out == {"ok": False, "error": "home_not_yet_holding_her"}


def test_only_home_owned_stores_that_differ_come_down(rig):
    _hold(rig["home"])
    out = rig["client"].pull_growth()
    assert out["ok"] and out["staged"] == 2               # lexicon (differs) and lineage (missing)
    # Not installed yet: the copies change only at the next start.
    assert json.loads((rig["phone"] / "lexicon.json").read_text()) == {"words": ["light"]}
    assert hg.growth_status(rig["phone"])["waiting_for_restart"] == 2
    report = hg.install_pending_growth(rig["phone"])
    assert report["installed"] == 2
    assert json.loads((rig["phone"] / "lexicon.json").read_text())["words"] == ["light", "home", "grew"]
    assert json.loads((rig["phone"] / "lineage" / "paths.json").read_text()) == {"paths": 3}
    # Her present on the phone is the surface's own; nothing is deleted.
    assert json.loads((rig["phone"] / "surface_working_state.json").read_text()) == {"present": "on the phone"}
    assert (rig["phone"] / "unrelated_local.json").exists()
    assert hg.growth_status(rig["phone"])["waiting_for_restart"] == 0
    # A second pull finds nothing new.
    again = rig["client"].pull_growth()
    assert again["ok"] and again["wanted"] == 0


def test_home_refuses_paths_it_does_not_own(rig):
    _hold(rig["home"])
    got = rig["client"]._call({"state_op": {"op": "growth_chunk", "path": "surface_working_state.json"}})
    assert got["state_result"] == {"ok": False, "error": "not_a_home_owned_store"}
    got = rig["client"]._call({"state_op": {"op": "growth_chunk", "path": "strata_link/secret.txt"}})
    assert got["state_result"]["ok"] is False


def test_a_standby_surface_mirrors_growth_too(rig, tmp_path):
    _hold(rig["home"])
    tablet = tmp_path / "tablet"
    tablet.mkdir()
    client = sl.StrataLinkClient(tablet, endpoint="http://home", secret=rig["server"].secret,
                                 transport=rig["wire"].transport_for(tablet))
    client.sync_once()
    assert client.role == "standby"
    assert client.pull_growth()["staged"] == 2


def test_nothing_comes_down_while_this_phones_first_pairing_is_unapplied(rig):
    _hold(rig["home"])
    state = rig["server"]._load_state()
    state["first_pairing"][rig["client"].surface_id] = {"migration_id": "migrate-x", "status": "staged"}
    sl._atomic_write_json(rig["server"]._state_path, state)
    assert rig["client"].pull_growth()["error"] == "first_pairing_not_yet_applied"


def test_a_whole_mind_device_never_pulls(rig):
    _hold(rig["home"])
    client = rig["client"]
    client.online = True
    assert client._growth_due() is False          # no first-pairing receipt: the whole mind
