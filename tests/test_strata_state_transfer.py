#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_strata_state_transfer.py -- FIX-A125: seeding the Subsurface device,
state-preserving Surface migration, and the sensory channels.

Two temporary state directories stand in for the phone and the laptop (a third
for a replacement phone).  The client talks to the server through the same
signed request/response exchange the real transport carries; one test uses the
real HTTP server on loopback.  Nothing here is a physical two-device run.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from aurora_internal.dual_strata import predictive_stager as ps
from aurora_internal.dual_strata import strata_link as sl
from aurora_internal.dual_strata import strata_state_transfer as st
from aurora_internal.dual_strata.sensory_snapshot_channel import (
    append_surface_guidance, read_surface_guidance_queue, read_surface_snapshot,
    snapshot_path)


class Wire:
    def __init__(self, server, monkeypatch, laptop):
        self.server, self._mp, self._laptop = server, monkeypatch, laptop
        self.requests = 0
        self.die_after = None       # raise on the Nth request from now
        self.corrupt_chunks = False  # flip a byte in every chunk in flight

    def transport_for(self, device):
        def transport(body, headers):
            self.requests += 1
            if self.die_after is not None:
                self.die_after -= 1
                if self.die_after < 0:
                    raise OSError("network unreachable")
            if self.corrupt_chunks:
                req = json.loads(body)
                op = req.get("state_op") or {}
                if op.get("op") == "chunk" and op.get("data"):
                    raw = bytearray(base64.b64decode(op["data"]))
                    raw[0] ^= 0xFF
                    op["data"] = base64.b64encode(bytes(raw)).decode()
                    body = json.dumps(req).encode()
                    headers = {"X-Aurora-Ts": headers["X-Aurora-Ts"],
                               "X-Aurora-Sig": sl.sign(self.server.secret, headers["X-Aurora-Ts"], body)}
            self._mp.setattr(ps, "_QUEUE_PATH", self._laptop / "predictive_frame_queue.json")
            status, out, extra = self.server.handle_http(body, headers)
            self._mp.setattr(ps, "_QUEUE_PATH", device / "predictive_frame_queue.json")
            if status != 200:
                raise OSError(f"http {status}")
            return out, extra
        return transport


def _write(root: Path, rel: str, data: bytes) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


@pytest.fixture()
def rig(tmp_path, monkeypatch):
    laptop, phone, phone2 = tmp_path / "laptop", tmp_path / "phone", tmp_path / "phone2"
    for d in (laptop, phone, phone2):
        d.mkdir()
    server = sl.StrataLinkServer(laptop, port=0)
    wire = Wire(server, monkeypatch, laptop)

    def client_for(device):
        return sl.StrataLinkClient(device, endpoint="http://laptop", secret=server.secret,
                                   transport=wire.transport_for(device))

    # What the phone has lived (and what must not travel).
    _write(phone, "genealogy/abilities.json", b'{"a": 1}' * 400)
    _write(phone, "lexicon.json", b'{"words": ["fence"]}')
    _write(phone, "deep/er/crystals.json", bytes(range(256)) * 40)
    _write(phone, "empty_marker.json", b"")
    _write(phone, "surface_continuity_feed.json", b"[]")        # live channel
    _write(phone, "subsurface_heartbeat.json", b"{}")           # per-device
    _write(phone, "runtime_faults.jsonl", b"x\n")                # per-device
    _write(phone, "scratch.tmp", b"x")                           # temp
    # The laptop already holds one identical file and one different one.
    _write(laptop, "lexicon.json", b'{"words": ["fence"]}')
    _write(laptop, "genealogy/abilities.json", b"old laptop version")
    _write(laptop, "laptop_only.json", b"stays")
    return {"laptop": laptop, "phone": phone, "phone2": phone2, "server": server,
            "wire": wire, "client_for": client_for}


def _same(a: Path, b: Path, rel: str) -> bool:
    return (a / rel).read_bytes() == (b / rel).read_bytes()


# --------------------------------------------------------------------------- seed

def test_seed_installs_verified_files_and_nothing_excluded(rig):
    phone, laptop = rig["phone"], rig["laptop"]
    result = rig["client_for"](phone).push_state("seed", chunk_bytes=300)
    assert result["ok"], result
    for rel in ("genealogy/abilities.json", "lexicon.json", "deep/er/crystals.json", "empty_marker.json"):
        assert _same(phone, laptop, rel), rel
    for rel in ("surface_continuity_feed.json", "subsurface_heartbeat.json",
                "runtime_faults.jsonl", "scratch.tmp"):
        assert not (laptop / rel).exists(), rel
    assert (laptop / "laptop_only.json").read_bytes() == b"stays"
    assert result["skipped_already_there"] == 1                      # lexicon.json already identical
    assert result["backed_up"] == 1                                  # the differing abilities.json
    backup = next((laptop / "strata_link" / "backup").rglob("abilities.json"))
    assert backup.read_bytes() == b"old laptop version"
    seeded = json.loads((laptop / "strata_link" / "seeded.json").read_text())
    assert seeded["restart_required"] is True and seeded["files"] == 4
    assert rig["server"].downlink_enabled()                          # the stated condition is met


def test_seed_resumes_after_the_link_drops(rig):
    phone, laptop = rig["phone"], rig["laptop"]
    client, wire = rig["client_for"](phone), rig["wire"]
    wire.die_after = 8
    first = client.push_state("seed", chunk_bytes=200)
    assert not first["ok"] and "link down" in first["error"]
    assert not (laptop / "strata_link" / "seeded.json").exists()     # nothing half-installed
    wire.die_after = None
    wire.requests = 0
    second = client.push_state("seed", chunk_bytes=200)
    assert second["ok"], second
    assert _same(phone, laptop, "deep/er/crystals.json")
    # The first attempt's completed files were not sent again.
    full_chunks = sum(-(-s // 200) for s in (3200, 10240))
    assert wire.requests < full_chunks + 10


def test_a_corrupted_chunk_is_caught_and_installs_nothing(rig):
    phone, laptop = rig["phone"], rig["laptop"]
    rig["wire"].corrupt_chunks = True
    result = rig["client_for"](phone).push_state("seed", chunk_bytes=100000)
    assert not result["ok"] and "sha256" in result["error"]
    assert (laptop / "genealogy/abilities.json").read_bytes() == b"old laptop version"
    assert not (laptop / "strata_link" / "seeded.json").exists()
    assert not rig["server"].downlink_enabled()


def test_a_manifest_that_escapes_the_state_dir_is_refused(rig):
    client = rig["client_for"](rig["phone"])
    client.flush_outbox()
    for bad in ("../evil.json", "/etc/passwd", "a/../../x.json"):
        with pytest.raises(st.TransferError):
            client._state_call({"op": "offer", "transfer_id": "t", "purpose": "seed",
                                "manifest": [{"path": bad, "size": 1, "sha256": "0" * 64}]})
    assert not (rig["laptop"].parent / "evil.json").exists()


def test_only_the_active_surface_may_seed(rig):
    rig["client_for"](rig["phone"]).sync_once()                      # phone becomes owner
    _write(rig["phone2"], "x.json", b"{}")
    result = rig["client_for"](rig["phone2"]).push_state("seed")
    assert not result["ok"] and "not the active Surface" in result["error"]


def test_verify_sync_reports_what_matches_and_what_drifted(rig):
    phone = rig["phone"]
    client = rig["client_for"](phone)
    assert client.push_state("seed")["ok"]
    report = client.verify_sync()
    assert report["ok"] and report["differ"] == [] and report["missing"] == []
    assert report["match"] == 4
    _write(phone, "lexicon.json", b'{"words": ["fence", "posts"]}')
    _write(phone, "new_since.json", b"{}")
    drift = client.verify_sync()
    assert drift["differ"] == ["lexicon.json"] and drift["missing"] == ["new_since.json"]


# ------------------------------------------------------------------------ handoff

def test_state_preserving_migration_to_a_second_device(rig):
    phone, phone2, laptop = rig["phone"], rig["phone2"], rig["laptop"]
    old, new = rig["client_for"](phone), rig["client_for"](phone2)
    old.sync_once()
    epoch_before = rig["server"].status()["epoch"]
    checkpoint = old.push_state("handoff", chunk_bytes=500)
    assert checkpoint["ok"] and checkpoint["token"]
    # The laptop's own state dir is untouched by a handoff checkpoint.
    assert (laptop / "genealogy/abilities.json").read_bytes() == b"old laptop version"

    # A claim without the token must not take the role from the waiting checkpoint.
    new.request_claim()
    new.sync_once()
    assert new.role == "standby" and rig["server"].status()["epoch"] == epoch_before
    assert new.last_error == "handoff_pending"
    wrong = new.pull_handoff("not-the-token")
    assert not wrong["ok"]

    _write(phone2, "lexicon.json", b'{"words": ["fence"]}')       # already identical: not re-pulled
    moved = new.pull_handoff(checkpoint["token"], chunk_bytes=500)
    assert moved["ok"], moved
    for rel in ("genealogy/abilities.json", "lexicon.json", "deep/er/crystals.json", "empty_marker.json"):
        assert _same(phone, phone2, rel), rel
    assert moved["reused_local"] == 1
    assert not (phone2 / "surface_continuity_feed.json").exists()
    status = rig["server"].status()
    assert status["epoch"] == epoch_before + 1 and status["handoff_pending"] is False
    assert status["migrations"][-1]["to"] == new.surface_id
    assert not (laptop / "strata_link" / "handoff").exists()

    old.sync_once()
    assert old.role == "standby"                                  # the old Surface stands down
    new.sync_once()
    assert new.role == "active"


def test_an_expired_checkpoint_no_longer_blocks_a_claim(rig, monkeypatch):
    old, new = rig["client_for"](rig["phone"]), rig["client_for"](rig["phone2"])
    old.sync_once()
    assert old.push_state("handoff")["ok"]
    state = rig["server"]._load_state()
    state["handoff"]["at"] -= sl.HANDOFF_TTL_S + 5
    sl._atomic_write_json(rig["server"]._state_path, state)
    new.request_claim()
    new.sync_once()
    assert new.role == "active"
    assert rig["server"].status()["handoff_pending"] is False


# ------------------------------------------------------------------ sensory channels

def test_sensory_snapshot_goes_up_and_guidance_comes_down(rig):
    phone, laptop = rig["phone"], rig["laptop"]
    client = rig["client_for"](phone)
    snapshot_path(phone).write_text(json.dumps({"mic_live": True, "camera_live": False,
                                                "visual_description": "a fence"}))
    client.sync_once()
    assert read_surface_snapshot(laptop)["visual_description"] == "a fence"
    client.sync_once()                                            # unchanged: not sent twice
    assert rig["server"].counters["applied"] == 1

    (laptop / "strata_link").mkdir(exist_ok=True)
    (laptop / "strata_link" / "downlink_enabled").write_text("on")
    append_surface_guidance(laptop, {"event_id": "g1", "kind": "look_closer"})
    client.sync_once()
    client.sync_once()
    queue = read_surface_guidance_queue(phone)
    assert [e["event_id"] for e in queue] == ["g1"]               # arrived once, id preserved


# ----------------------------------------------------------------- real HTTP loopback

def test_seed_over_the_real_http_server(tmp_path):
    laptop, phone = tmp_path / "laptop", tmp_path / "phone"
    laptop.mkdir()
    phone.mkdir()
    _write(phone, "a/state.json", b'{"k": "v"}' * 5000)
    server = sl.StrataLinkServer(laptop, host="127.0.0.1", port=0)
    assert server.start()
    try:
        client = sl.StrataLinkClient(phone, endpoint=f"http://127.0.0.1:{server.port}",
                                     secret=server.secret)
        result = client.push_state("seed", chunk_bytes=8192)
        assert result["ok"], result
        assert (laptop / "a/state.json").read_bytes() == (phone / "a/state.json").read_bytes()
        assert client.verify_sync()["differ"] == []
    finally:
        server.stop()
