#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_surface_profile_bridge.py -- a paired phone runs as her surface, its
growth work asked of home (surface restructure 3, items 2 to 4).

These pin:
  * the phone is a surface only once paired AND its first pairing's receipt
    has been accepted; paired but still migrating, it stays the whole mind;
  * on a surface, organs left to home read "at home", never "degraded";
  * the hub's Curiosity Cycle and Evo Cycle become requests in the durable
    outbox, applied once at home and read back in order;
  * a request kind home does not know is refused at both ends.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ANDROID_PY_DIR = REPO_ROOT / "flutter_app" / "android" / "app" / "src" / "main" / "python"

from aurora_internal.dual_strata import strata_link as sl  # noqa: E402
from aurora_internal.dual_strata import strata_migration as sm  # noqa: E402


def _bridge():
    if str(ANDROID_PY_DIR) not in sys.path:
        sys.path.insert(0, str(ANDROID_PY_DIR))
    import aurora_bridge
    return aurora_bridge


def _pair(device: Path) -> None:
    sl.link_dir(device).joinpath("endpoint.txt").write_text("http://home:8791")
    sl.link_dir(device).joinpath("secret.txt").write_text("s" * 32)


def test_surface_only_needs_pairing_and_an_accepted_receipt(tmp_path):
    assert sm.surface_only_ready(tmp_path) is False
    _pair(tmp_path)
    assert sm.surface_only_ready(tmp_path) is False             # still the whole mind
    receipt = {"verified": True, "migration_id": "migrate-1", "source_digest": "d"}
    assert sm.accept_receipt(tmp_path, receipt, migration_id="migrate-1", source_digest="d")["ok"]
    assert sm.surface_only_ready(tmp_path) is True


def _surface_systems():
    return {
        "language_field": object(), "identity_field": object(), "consciousness": object(),
        "sedimemory": object(), "lattice": object(), "_geological_baseline": object(),
        "genealogy": None,                                      # deferred by the surface profile
        "recursive_causal_waveform": object(), "sensory_crystal": object(), "dimensional": object(),
        "autonomy": None, "chamber": None, "hardware": object(),
    }


def test_organs_left_to_home_read_at_home_not_degraded(monkeypatch):
    bridge = _bridge()
    monkeypatch.setattr(bridge, "_systems", _surface_systems(), raising=False)
    monkeypatch.setattr(bridge, "_dream_substrate_boot_ok", False, raising=False)
    monkeypatch.setattr(bridge, "_surface_only", True, raising=False)
    monkeypatch.setattr(bridge, "_deferred_to_home", ["curiosity", "scout"], raising=False)
    payload = json.loads(bridge.get_mobile_developmental_health())
    assert payload["profile"] == "surface"
    assert payload["overall"] == "healthy"
    assert payload["degraded_missing"] == []
    assert set(payload["at_home"]) == {"genealogy", "curiosity", "scout"}

    monkeypatch.setattr(bridge, "_surface_only", False, raising=False)
    whole = json.loads(bridge.get_mobile_developmental_health())
    assert whole["profile"] == "whole" and whole["overall"] == "degraded"
    assert "genealogy" in whole["degraded_missing"]


@pytest.fixture()
def paired_surface(tmp_path, monkeypatch):
    home, phone = tmp_path / "home", tmp_path / "phone"
    home.mkdir()
    phone.mkdir()
    server = sl.StrataLinkServer(home, port=0)

    def transport(body, headers):
        status, out, extra = server.handle_http(body, headers)
        if status != 200:
            raise OSError(f"http {status}")
        return out, extra
    client = sl.StrataLinkClient(phone, endpoint="http://home", secret=server.secret, transport=transport)
    monkeypatch.setattr(sl, "_CLIENT", client)
    client.sync_once()
    assert client.role == "active"
    return {"home": home, "phone": phone, "client": client}


def test_hub_buttons_on_a_surface_become_requests_home(paired_surface, monkeypatch):
    bridge = _bridge()
    monkeypatch.setattr(bridge, "_surface_only", True, raising=False)
    monkeypatch.setattr(bridge, "_strata_state_dir", str(paired_surface["phone"]), raising=False)
    asked = json.loads(bridge.trigger_curiosity_cycle(3))
    assert asked["status"] == "asked_home" and asked["ok"]
    evo = json.loads(bridge.trigger_evo_cycle(10))
    assert evo["status"] == "asked_home" and evo["ok"]
    burst = json.loads(bridge.run_evolutionary_burst(2))
    assert burst["at_home"] is True

    client = paired_surface["client"]
    client.sync_once()
    client.sync_once()                                          # a redelivery is not a second request
    requests, offset = sl.read_home_requests(paired_surface["home"], 0)
    assert [r["kind"] for r in requests] == ["curiosity_cycle", "evo_cycle", "evo_cycle"]
    assert requests[0]["payload"] == {"cycles": 3}
    again, _ = sl.read_home_requests(paired_surface["home"], offset)
    assert again == []
    assert client.outbox.stats()["pending"] == 0


def test_a_request_home_does_not_know_is_refused(paired_surface):
    assert sl.request_home(paired_surface["phone"], "rewrite_yourself")["ok"] is False
    record = {"channel": "home_request", "kind": "event",
              "payload": {"request_id": "x", "kind": "rewrite_yourself"}}
    assert sl.apply_uplink_record(paired_surface["home"], record) == "unknown_channel"


def test_a_request_delivered_twice_is_applied_once(paired_surface):
    record = {"channel": "home_request", "kind": "event",
              "payload": {"request_id": "abc", "kind": "curiosity_cycle", "payload": {}}}
    assert sl.apply_uplink_record(paired_surface["home"], record) == "applied"
    assert sl.apply_uplink_record(paired_surface["home"], record) == "duplicate"
    requests, _ = sl.read_home_requests(paired_surface["home"], 0)
    assert len(requests) == 1
