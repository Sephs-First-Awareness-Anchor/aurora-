#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_strata_migration.py -- the first pairing of a phone that lived as a whole
mind (surface restructure 3d, Sir's tightening 1).

Home holds her (as the desktop resident does); the phone pairs as standby and
sends its whole state to be staged.  These pin:
  * a standby phone may stage a migration, and home's live state is untouched;
  * the report classes each differing store: histories union, developmental
    stores need Sir's choice (with a suggestion), the present frame is the
    phone's, a device's own traces are left behind;
  * nothing is applied until every choice is made;
  * apply unions histories without losing a record from either side, installs
    the chosen side, archives the other, keeps a backup, writes a receipt;
  * the phone keeps only a receipt matching its own snapshot, and only then is
    it surface-only;
  * what the phone lived before its snapshot is not lived twice at home; what
    it lived after, while it waited, is integrated once;
  * another device cannot read or drive this phone's migration.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from aurora_internal.dual_strata import strata_link as sl
from aurora_internal.dual_strata import strata_migration as sm
from aurora_internal.dual_strata.surface_continuity_feed import (
    integrated_ledger_status, peek_continuity_packets, write_continuity_packet)

from tests.test_strata_fencing import Wire  # noqa: E402  (same in-memory wire)


def _lines(path: Path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


@pytest.fixture()
def rig(tmp_path, monkeypatch):
    home, phone, other = tmp_path / "home", tmp_path / "phone", tmp_path / "other"
    for d in (home, phone, other):
        d.mkdir()
    server = sl.StrataLinkServer(home, port=0)
    server.handle_sync({"surface_id": "desktop"})           # home holds her
    wire = Wire(server, monkeypatch, home)

    def client_for(device: Path) -> sl.StrataLinkClient:
        return sl.StrataLinkClient(device, endpoint="http://home", secret=server.secret,
                                   transport=wire.transport_for(device))

    # Home's own life.
    (home / "lexicon.json").write_text(json.dumps({"entries": {"rain": 1}}))
    (home / "grammar_state.json").write_text(json.dumps({"motifs": {"a": 1, "b": 2, "c": 3}}))
    (home / "developmental_timeline.jsonl").write_text(
        json.dumps({"id": "h1", "at": 1.0}) + "\n" + json.dumps({"id": "both", "at": 2.0}) + "\n")
    # The phone's own life as a whole mind.
    (phone / "lexicon.json").write_text(json.dumps({"entries": {"rain": 1, "sun": 2, "wind": 3}}))
    (phone / "grammar_state.json").write_text(json.dumps({"motifs": {"a": 1}}))
    (phone / "developmental_timeline.jsonl").write_text(
        json.dumps({"id": "both", "at": 2.0}) + "\n" + json.dumps({"id": "p1", "at": 3.0}) + "\n")
    (phone / "phone_only_store.json").write_text(json.dumps({"entries": {"x": 1}}))
    (phone / "surface_working_state.json").write_text(json.dumps({"present": "phone"}))
    (phone / "last_turn_trace.json").write_text("{}")
    return {"home": home, "phone": phone, "other": other, "server": server, "wire": wire,
            "client_for": client_for}


def _staged(rig):
    client = rig["client_for"](rig["phone"])
    client.sync_once()
    assert client.role == "standby"
    result = client.migrate()
    assert result["ok"], result
    return client, result


def test_standby_phone_stages_and_home_is_untouched(rig):
    before = {p.name: p.read_bytes() for p in rig["home"].iterdir() if p.is_file()}
    client, result = _staged(rig)
    assert result["purpose"] == "migrate" and result["status"] == "awaiting_choice"
    after = {p.name: p.read_bytes() for p in rig["home"].iterdir() if p.is_file()}
    assert after == before
    pending = sm.load_pending(rig["home"])
    stores = pending["report"]["stores"]
    assert stores["developmental_timeline.jsonl"]["class"] == sm.HISTORY
    assert stores["lexicon.json"]["class"] == sm.DEVELOPMENTAL
    assert stores["lexicon.json"]["suggested"] == sm.PHONE          # phone lived more words
    assert stores["grammar_state.json"]["suggested"] == sm.HOME     # home lived more motifs
    assert stores["phone_only_store.json"]["needs_choice"] is False
    assert stores["surface_working_state.json"]["class"] == sm.PRESENT
    assert "last_turn_trace.json" not in stores
    assert sorted(pending["report"]["choices_needed"]) == ["grammar_state.json", "lexicon.json"]


def test_nothing_applies_until_every_choice_is_made(rig):
    _staged(rig)
    assert sm.apply_pending_migration(rig["home"]) is None
    assert sm.choose(rig["home"], {"lexicon.json": "phone"})["missing"] == ["grammar_state.json"]
    assert sm.apply_pending_migration(rig["home"]) is None
    assert sm.choose(rig["home"], {"lexicon.json": "sideways"})["ok"] is False


def test_apply_unions_installs_archives_and_receipts(rig):
    _staged(rig)
    home = rig["home"]
    sm.choose(home, {"lexicon.json": "phone", "grammar_state.json": "home"})
    receipt = sm.apply_pending_migration(home)
    assert receipt["ok"] and receipt["verified"]
    assert [r["id"] for r in _lines(home / "developmental_timeline.jsonl")] == ["h1", "both", "p1"]
    assert json.loads((home / "lexicon.json").read_text())["entries"] == {"rain": 1, "sun": 2, "wind": 3}
    assert json.loads((home / "grammar_state.json").read_text())["motifs"] == {"a": 1, "b": 2, "c": 3}
    assert json.loads((home / "phone_only_store.json").read_text()) == {"entries": {"x": 1}}
    assert json.loads((home / "surface_working_state.json").read_text()) == {"present": "phone"}
    assert not (home / "last_turn_trace.json").exists()
    archive = home / receipt["archive"]
    assert json.loads((archive / "home" / "lexicon.json").read_text())["entries"] == {"rain": 1}
    assert json.loads((archive / "phone" / "grammar_state.json").read_text())["motifs"] == {"a": 1}
    assert receipt["chosen"] == {"lexicon.json": "phone", "grammar_state.json": "home"}
    assert sl.link_dir(home).joinpath(sm.RECEIPT_FILENAME).exists()


def test_phone_is_surface_only_only_after_a_matching_receipt(rig):
    client, _ = _staged(rig)
    phone = rig["phone"]
    sl.link_dir(phone).joinpath("endpoint.txt").write_text("http://home")
    sl.link_dir(phone).joinpath("secret.txt").write_text(rig["server"].secret)
    assert sm.surface_only_ready(phone) is False
    assert client.check_migration()["status"] == "awaiting_choice"
    assert sm.surface_only_ready(phone) is False

    sm.choose(rig["home"], {}, accept_suggested=True)
    sm.apply_pending_migration(rig["home"])
    checked = client.check_migration()
    assert checked["ok"] and checked["surface_only_at_next_start"]
    assert sm.surface_only_ready(phone) is True


def test_a_receipt_for_another_snapshot_is_refused(rig):
    receipt = {"verified": True, "migration_id": "migrate-aaa", "source_digest": "x"}
    out = sm.accept_receipt(rig["phone"], receipt, migration_id="migrate-bbb", source_digest="x")
    assert out == {"ok": False, "error": "receipt_does_not_match_this_snapshot"}
    assert sm.load_receipt(rig["phone"]) is None


def _live(device: Path, n: int) -> None:
    write_continuity_packet(device, user_input=f"said {n}", aurora_response=f"answered {n}",
                            concepts_activated=[f"c{n}"], dominant_axis="B", coherence=0.5)


def test_lived_before_snapshot_is_not_lived_twice_and_after_is_integrated_once(rig):
    phone, home = rig["phone"], rig["home"]
    client = rig["client_for"](phone)
    client.sync_once()
    _live(phone, 1)
    client.sync_once()                       # standby: waits in the outbox
    result = client.migrate()                # snapshot holds moment 1
    assert result["ok"]
    _live(phone, 2)                          # lived while the migration waits
    client.sync_once()
    assert integrated_ledger_status(home)["devices"] == {}

    sm.choose(home, {}, accept_suggested=True)
    sm.apply_pending_migration(home)
    assert client.check_migration()["status"] == "applied"
    for _ in range(3):
        client.sync_once()
    ledger = integrated_ledger_status(home)["devices"]
    (key,) = list(ledger)                    # (surface_id, epoch) it lived in
    assert key.startswith(client.surface_id + ":")
    assert ledger[key]["high_water"] == 2
    said = [p.get("user_input") for p in peek_continuity_packets(home)]
    assert said.count("said 2") == 1 and "said 1" not in said
    assert client.outbox.stats()["pending"] == 0


def test_another_device_cannot_see_or_drive_this_migration(rig):
    client, result = _staged(rig)
    other = rig["client_for"](rig["other"])
    other.sync_once()
    assert other._state_call({"op": "migration_status"})["status"] == "none"
    with pytest.raises(Exception):
        other._state_call({"op": "commit", "transfer_id": result["transfer_id"]})
