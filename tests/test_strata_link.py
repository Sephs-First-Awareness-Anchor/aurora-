#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_strata_link.py -- FIX-A118: the carrier between a Surface device and the
Subsurface device.

Two temporary state directories stand in for the phone and the laptop.  Every
assertion about delivered content is made through the modules that own the
channel formats (surface_continuity_feed, PredictiveStager), i.e. through the
same calls aurora.py and aurora_daemon.py already make.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from aurora_internal.dual_strata import predictive_stager as ps
from aurora_internal.dual_strata import strata_link as sl
from aurora_internal.dual_strata.surface_continuity_feed import (
    read_and_clear_continuity_packets, write_continuity_packet)


class Wire:
    """An in-memory network between one server and any number of clients."""

    def __init__(self, server: sl.StrataLinkServer, monkeypatch, laptop: Path) -> None:
        self.server = server
        self.down = False            # request never arrives
        self.lose_response = False   # request applied, response lost
        self._mp = monkeypatch
        self._laptop = laptop

    def transport_for(self, device: Path):
        def transport(body, headers):
            if self.down:
                raise OSError("network unreachable")
            # PredictiveStager's queue path is a module global; point it at
            # whichever device is "running" at this moment.
            self._mp.setattr(ps, "_QUEUE_PATH", self._laptop / "predictive_frame_queue.json")
            status, out, extra = self.server.handle_http(body, headers)
            self._mp.setattr(ps, "_QUEUE_PATH", device / "predictive_frame_queue.json")
            if self.lose_response:
                raise OSError("connection reset")
            if status != 200:
                raise OSError(f"http {status}")
            return out, extra
        return transport


@pytest.fixture()
def rig(tmp_path, monkeypatch):
    laptop, phone = tmp_path / "laptop", tmp_path / "phone"
    laptop.mkdir()
    phone.mkdir()
    server = sl.StrataLinkServer(laptop, port=0)
    wire = Wire(server, monkeypatch, laptop)
    client = sl.StrataLinkClient(phone, endpoint="http://laptop", secret=server.secret,
                                 transport=wire.transport_for(phone))
    return {"laptop": laptop, "phone": phone, "server": server, "wire": wire,
            "client": client, "tmp": tmp_path, "mp": monkeypatch}


def _live_turn(state_dir: Path, n: int) -> str:
    return write_continuity_packet(state_dir, user_input=f"said {n}", aurora_response=f"answered {n}",
                                   concepts_activated=[f"c{n}"], dominant_axis="B", coherence=0.5)


# ---------------------------------------------------------------------------
# Durable outbox
# ---------------------------------------------------------------------------

def test_outbox_keeps_events_in_order_and_drops_only_what_is_acknowledged(tmp_path):
    box = sl.DurableOutbox(tmp_path / "o.json")
    seqs = [box.append("continuity", "event", {"n": n}) for n in range(5)]
    assert seqs == [1, 2, 3, 4, 5]
    assert box.ack(3) == 3
    assert [r["seq"] for r in box.pending()] == [4, 5]
    # survives a restart, and numbering never goes backwards
    again = sl.DurableOutbox(tmp_path / "o.json")
    assert [r["payload"]["n"] for r in again.pending()] == [3, 4]
    assert again.append("continuity", "event", {"n": 9}) == 6


def test_outbox_state_channel_keeps_only_the_latest(tmp_path):
    box = sl.DurableOutbox(tmp_path / "o.json")
    box.append("projection", "state", {"v": 1})
    box.append("continuity", "event", {"n": 1})
    box.append("projection", "state", {"v": 2})
    pending = box.pending()
    assert [(r["channel"], r["payload"]) for r in pending] == [
        ("continuity", {"n": 1}), ("projection", {"v": 2})]


def test_outbox_overflow_is_counted_not_silent(tmp_path):
    box = sl.DurableOutbox(tmp_path / "o.json", max_records=3)
    for n in range(5):
        box.append("continuity", "event", {"n": n})
    assert box.stats() == {"pending": 3, "next_seq": 6, "overflow_dropped": 2}


def test_outbox_dedupe_id_queues_once(tmp_path):
    box = sl.DurableOutbox(tmp_path / "o.json")
    assert box.append("continuity", "event", {}, dedupe_id="p1") == 1
    assert box.append("continuity", "event", {}, dedupe_id="p1") == 0
    assert box.stats()["pending"] == 1


# ---------------------------------------------------------------------------
# Uplink: lived turns reach the Subsurface, once
# ---------------------------------------------------------------------------

def test_a_lived_turn_reaches_the_subsurface_feed_unchanged(rig):
    packet_id = _live_turn(rig["phone"], 1)
    assert rig["client"].sync_once() is True
    received = read_and_clear_continuity_packets(rig["laptop"])
    assert len(received) == 1
    packet = received[0]
    assert packet["packet_id"] == packet_id
    assert packet["user_input"] == "said 1" and packet["aurora_response"] == "answered 1"
    assert packet["concepts_activated"] == ["c1"] and packet["dominant_axis"] == "B"
    # acknowledged, so nothing is left to send and nothing repeats
    assert rig["client"].outbox.stats()["pending"] == 0
    assert rig["client"].sync_once() is False
    assert read_and_clear_continuity_packets(rig["laptop"]) == []


def test_a_long_disconnect_loses_nothing_and_keeps_order(rig):
    """The feed file itself keeps only 20 packets.  With the link draining it
    into the durable outbox, 60 turns lived offline all arrive, in order."""
    rig["wire"].down = True
    ids = []
    for n in range(60):
        ids.append(_live_turn(rig["phone"], n))
        assert rig["client"].sync_once() is False
    assert rig["client"].status()["status"] == "offline"
    assert rig["client"].outbox.stats() == {"pending": 60, "next_seq": 61, "overflow_dropped": 0}
    assert read_and_clear_continuity_packets(rig["laptop"]) == []

    rig["wire"].down = False
    while rig["client"].outbox.stats()["pending"]:
        assert rig["client"].sync_once() is True
    received = read_and_clear_continuity_packets(rig["laptop"])
    assert [p["packet_id"] for p in received] == ids
    assert rig["client"].status()["status"] == "online"


def test_a_lost_response_is_resent_but_never_applied_twice(rig):
    for n in range(3):
        _live_turn(rig["phone"], n)
    rig["wire"].lose_response = True
    assert rig["client"].sync_once() is False          # applied over there, ack never came back
    assert rig["client"].outbox.stats()["pending"] == 3
    rig["wire"].lose_response = False
    rig["client"].sync_once()                           # resend
    assert rig["client"].outbox.stats()["pending"] == 0
    assert len(read_and_clear_continuity_packets(rig["laptop"])) == 3
    assert rig["server"].counters["applied"] == 3
    assert rig["server"].counters["duplicates"] == 3


def test_a_crash_between_copy_and_consume_repeats_nothing(rig):
    """collect copies to the outbox before consuming the feed.  Simulate the
    crash by collecting twice without the feed having been consumed."""
    _live_turn(rig["phone"], 1)
    feed = rig["phone"] / "surface_continuity_feed.json"
    before = feed.read_text(encoding="utf-8")
    sl.collect_surface_uplink(rig["phone"], rig["client"].outbox)
    feed.write_text(before, encoding="utf-8")           # as if consume never happened
    sl.collect_surface_uplink(rig["phone"], rig["client"].outbox)
    assert rig["client"].outbox.stats()["pending"] == 1


# ---------------------------------------------------------------------------
# Ownership: one active Surface
# ---------------------------------------------------------------------------

def test_only_the_owner_is_applied_and_a_claim_raises_the_epoch(rig):
    tablet = rig["tmp"] / "tablet"
    tablet.mkdir()
    second = sl.StrataLinkClient(tablet, endpoint="http://laptop", secret=rig["server"].secret,
                                 transport=rig["wire"].transport_for(tablet))
    _live_turn(rig["phone"], 1)
    rig["client"].sync_once()
    assert (rig["client"].role, rig["client"].epoch) == ("active", 1)

    # A second device is told to stand by; what it lived waits in its outbox.
    _live_turn(tablet, 2)
    second.sync_once()
    assert second.status()["status"] == "standby"
    assert second.outbox.stats()["pending"] == 1
    assert len(read_and_clear_continuity_packets(rig["laptop"])) == 1   # the phone's only

    # An explicit claim moves ownership and raises the epoch.
    second.request_claim()
    second.sync_once()
    assert (second.role, second.epoch) == ("active", 2)
    assert second.outbox.stats()["pending"] == 0
    assert [p["user_input"] for p in read_and_clear_continuity_packets(rig["laptop"])] == ["said 2"]

    # The previous owner now stands by and is no longer applied.
    _live_turn(rig["phone"], 3)
    rig["client"].sync_once()
    assert rig["client"].status()["status"] == "standby"
    assert rig["client"].outbox.stats()["pending"] == 1
    assert read_and_clear_continuity_packets(rig["laptop"]) == []


def test_pairing_carries_the_claim(tmp_path):
    result = sl.configure_surface(tmp_path, "http://laptop:8791#s3cret")
    assert result == {"ok": True, "endpoint": "http://laptop:8791"}
    assert sl.load_surface_config(tmp_path) == ("http://laptop:8791", "s3cret")
    assert (sl.link_dir(tmp_path) / "claim_pending").exists()
    assert sl.configure_surface(tmp_path, "laptop:8791")["ok"] is False


# ---------------------------------------------------------------------------
# Signing
# ---------------------------------------------------------------------------

def test_a_wrong_secret_applies_nothing(rig):
    intruder = sl.StrataLinkClient(rig["tmp"] / "x", endpoint="http://laptop", secret="not-the-secret",
                                   transport=rig["wire"].transport_for(rig["tmp"] / "x"))
    _live_turn(rig["tmp"] / "x", 1)
    assert intruder.sync_once() is False
    assert rig["server"].counters["rejected_signature"] == 1
    assert rig["server"].status()["owner"] == ""
    assert read_and_clear_continuity_packets(rig["laptop"]) == []


def test_a_forged_response_is_rejected(rig):
    def forged(body, headers):
        return json.dumps({"v": 1, "role": "active", "epoch": 9, "up_ack": 10 ** 9, "down": []}).encode(), {}

    client = sl.StrataLinkClient(rig["phone"], endpoint="http://laptop", secret=rig["server"].secret,
                                 transport=forged)
    _live_turn(rig["phone"], 1)
    assert client.sync_once() is False
    assert client.counters["bad_signature"] == 1
    assert client.outbox.stats()["pending"] == 1        # the forged ack dropped nothing


def test_stale_timestamps_are_refused():
    body = b"{}"
    assert sl.verify("k", "1000.0", body, sl.sign("k", "1000.0", body), now=1000.0 + 10)
    assert not sl.verify("k", "1000.0", body, sl.sign("k", "1000.0", body), now=1000.0 + 301)


# ---------------------------------------------------------------------------
# Downlink
# ---------------------------------------------------------------------------

def _enable_downlink(laptop: Path) -> None:
    (sl.link_dir(laptop) / "downlink_enabled").write_text("1", encoding="utf-8")


def test_downlink_is_off_until_enabled(rig):
    (rig["laptop"] / "subsurface_projection.json").write_text(json.dumps({"dominant_axis": "T"}))
    rig["client"].sync_once()
    assert not (rig["phone"] / "subsurface_projection.json").exists()
    assert rig["server"].status()["down_outbox"]["pending"] == 0


def test_projection_is_delivered_once_and_only_when_it_changes(rig):
    _enable_downlink(rig["laptop"])
    projection = rig["laptop"] / "subsurface_projection.json"
    projection.write_text(json.dumps({"dominant_axis": "T", "pressure": 0.4}))
    assert rig["client"].sync_once() is True
    assert json.loads((rig["phone"] / "subsurface_projection.json").read_text()) == {
        "dominant_axis": "T", "pressure": 0.4}
    rig["client"].sync_once()                           # carries the ack
    assert rig["server"].status()["down_outbox"]["pending"] == 0
    assert rig["client"].sync_once() is False           # unchanged: nothing to send
    assert rig["client"].counters["received"] == 1

    projection.write_text(json.dumps({"dominant_axis": "N", "pressure": 0.7}))
    assert rig["client"].sync_once() is True
    assert json.loads((rig["phone"] / "subsurface_projection.json").read_text())["dominant_axis"] == "N"


def test_predictive_frames_cross_through_the_stagers_own_queue(rig):
    _enable_downlink(rig["laptop"])
    rig["mp"].setattr(ps, "_QUEUE_PATH", rig["laptop"] / "predictive_frame_queue.json")
    ps.PredictiveStager.push_staged_frame({"context_hash": "h1", "lens": "X"})
    ps.PredictiveStager.push_staged_frame({"context_hash": "h2", "lens": "XT"})
    assert rig["client"].sync_once() is True
    # the wire leaves the stager pointed at the phone, as a phone process would be
    frames = ps.PredictiveStager.pop_all_recent_frames()
    assert sorted(f["context_hash"] for f in frames) == ["h1", "h2"]
    # and they are gone from the laptop's queue: one Surface consumes a frame
    rig["mp"].setattr(ps, "_QUEUE_PATH", rig["laptop"] / "predictive_frame_queue.json")
    assert ps.PredictiveStager.pop_all_recent_frames() == []


def test_a_rebuilt_subsurface_restarts_downlink_numbering(rig):
    _enable_downlink(rig["laptop"])
    projection = rig["laptop"] / "subsurface_projection.json"
    for n in range(3):
        projection.write_text(json.dumps({"n": n}))
        rig["client"].sync_once()
    # The laptop's link state is lost (reinstall); a fresh server numbers from 1.
    for name in ("server_state.json", "down_outbox.json"):
        (sl.link_dir(rig["laptop"]) / name).unlink()
    projection.write_text(json.dumps({"n": "after rebuild"}))
    rig["client"].sync_once()
    assert json.loads((rig["phone"] / "subsurface_projection.json").read_text()) == {"n": "after rebuild"}


# ---------------------------------------------------------------------------
# Over a real socket
# ---------------------------------------------------------------------------

def test_one_turn_over_real_http(tmp_path):
    laptop, phone = tmp_path / "laptop", tmp_path / "phone"
    laptop.mkdir()
    phone.mkdir()
    server = sl.StrataLinkServer(laptop, host="127.0.0.1", port=0)
    server.start()
    try:
        sl.configure_surface(phone, f"http://127.0.0.1:{server.port}#{server.secret}")
        endpoint, secret = sl.load_surface_config(phone)
        client = sl.StrataLinkClient(phone, endpoint=endpoint, secret=secret)
        packet_id = _live_turn(phone, 1)
        assert client.sync_once() is True
        assert client.status()["status"] == "online"
        assert not (sl.link_dir(phone) / "claim_pending").exists()
        assert [p["packet_id"] for p in read_and_clear_continuity_packets(laptop)] == [packet_id]
    finally:
        server.stop()


def test_unconfigured_devices_start_nothing(tmp_path):
    assert sl.start_strata_link_client_if_configured(tmp_path / "a") is None
    assert sl.start_strata_link_server_if_configured(tmp_path / "b") is None
    assert sl.strata_link_client_status()["status"] == "not_configured"


# ---------------------------------------------------------------------------
# End to end: the Subsurface's own consumer receives the remote turn
# ---------------------------------------------------------------------------

def test_the_daemons_own_consumer_integrates_a_turn_lived_on_another_device(rig, monkeypatch):
    """aurora_daemon._consume_surface_continuity_feed is the existing
    Subsurface receiver.  Nothing about it changes; it is simply handed a
    packet that was lived on the phone."""
    D = pytest.importorskip("aurora_daemon")
    monkeypatch.setattr(D, "_STATE_DIR", rig["laptop"])

    class _Sedi:
        def __init__(self):
            self.events = []

        def ingest_event(self, *args, **kwargs):
            self.events.append((args, kwargs))

    sedi = _Sedi()
    _live_turn(rig["phone"], 7)
    rig["client"].sync_once()
    D._consume_surface_continuity_feed({"sedimemory": sedi})
    assert len(sedi.events) == 1
    assert "said 7" in json.dumps(sedi.events[0], default=str)
    # consumed there: a second cycle integrates nothing more
    D._consume_surface_continuity_feed({"sedimemory": sedi})
    assert len(sedi.events) == 1
