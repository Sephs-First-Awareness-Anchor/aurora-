# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Hub panels: the resolution ledger, the strata link and the crystal pass, read-only and without secrets."""
import ast
import json
import os
import threading
import urllib.request

from aurora_internal import crystal_runtime as R
from aurora_internal import crystal_web_server as S
from aurora_internal import hub_panels as H


def hyp(role, rec, n=0):
    return {f"h{n}": {"facet_id": f"h{n}", "role": role, "content": json.dumps(rec), "confidence": 0.2}}


def test_the_ledger_panel_reads_its_research_off_the_crystals_most_evidence_first():
    facets = {}
    facets.update(hyp("hyp:cal:ledger", {"n_obs": {"history": 4210, "turns": 380}, "emitted": 5, "unsubmitted": 2, "last_emission": {"subject": "history"}, "streams": {"history": {"next_index": 9}}}, 0))
    facets.update(hyp("hyp:res:history:X>T", {"subject": "history", "path": "X>T", "st": {"n": 50, "gain": 5.0, "null": 2.5, "nb": 3}}, 1))
    facets.update(hyp("hyp:res:history:N>A", {"subject": "history", "path": "N>A", "st": {"n": 200, "gain": 8.0, "null": 4.0, "nb": 9}}, 2))
    d = H.ledger_panel({"c1": {"concept": "x", "facets": facets}, "c2": {"concept": "y", "facets": {"a": {"role": "oets:semantic", "content": "y"}}}})
    assert d["present"] and d["demands_submitted"] == 5 and d["demands_unsubmitted"] == 2 and list(d["subjects"]) == ["history", "turns"]
    assert [h["path"] for h in d["under_test"]] == ["N>A", "X>T"] and d["under_test"][0]["gain_per_obs"] == 0.04 and d["streams"] == {"history": 9}


def test_with_nothing_kept_the_ledger_panel_says_so():
    assert H.ledger_panel({"c": {"concept": "x", "facets": {}}})["present"] is False


def link_files(tmp):
    d = tmp / "strata_link"
    d.mkdir()
    (d / "server_state.json").write_text(json.dumps({"epoch": 3, "owner": "phone", "applied": {"phone": 12}, "last_seen": {"phone": 1000.0}, "migrations": [{"at": 1}], "handoff": {"x": 1}}))
    (d / "client_state.json").write_text(json.dumps({"down_applied": 7, "link_key": "KEY-DO-NOT-SHOW"}))
    (d / "secret.txt").write_text("SECRET-DO-NOT-SHOW")
    (d / "seeded.json").write_text(json.dumps({"at": 5, "surface": "phone", "secret": "ALSO-HIDDEN"}))
    (d / "down_outbox.json").write_text(json.dumps({"records": [{"seq": 1}, {"seq": 2}], "next_seq": 3, "overflow_dropped": 1}))
    (d / "downlink_enabled").write_text("")


def test_the_strata_panel_shows_the_link_but_never_a_secret(tmp_path):
    link_files(tmp_path)
    d = H.strata_panel(str(tmp_path), now=1042.0)
    assert d["server"]["epoch"] == 3 and d["server"]["last_seen_seconds_ago"] == {"phone": 42.0} and d["server"]["handoff_pending"] is True
    assert d["down_outbox"] == {"pending": 2, "next_seq": 3, "overflow_dropped": 1} and d["downlink_enabled"] and d["paired"] and d["seeded"]
    assert d["client"] == {"down_applied": 7, "has_link_key": True}
    blob = json.dumps(d)
    assert not any(s in blob for s in ("KEY-DO-NOT-SHOW", "SECRET-DO-NOT-SHOW", "ALSO-HIDDEN"))


def test_looking_creates_nothing_and_a_missing_link_is_just_not_configured(tmp_path):
    d = H.strata_panel(str(tmp_path))
    assert d["configured"] is False and d["server"] is None and not os.listdir(tmp_path)


def test_a_process_is_running_when_its_pid_lives(tmp_path):
    pids = tmp_path / "strata_stack" / "pids"
    pids.mkdir(parents=True)
    (pids / "surface.pid").write_text(str(os.getpid()))
    (pids / "hub.pid").write_text("999999")
    p = H.strata_panel(str(tmp_path))["processes"]
    assert p["surface"] is True and p["hub"] is False and p["room"] is None


def test_the_pass_leaves_its_report_and_a_bounded_history(tmp_path):
    for i in range(R.REPORT_HISTORY + 5):
        R._write_report(str(tmp_path), {"ok": True, "seconds": 1.0 + i, "links": {"links": 10 + i}, "facets": {"facets": 3}, "held": {"facets": 7}, "generalizations": 2}, float(i))
    d = H.pass_panel(str(tmp_path))
    assert d["present"] and len(d["history"]) == R.REPORT_HISTORY and d["history"][-1]["links"] == 10 + R.REPORT_HISTORY + 4 and d["history"][-1]["held"] == 7
    assert H.pass_panel(str(tmp_path / "none")) == {"present": False}


def test_run_pass_writes_the_report_the_hub_reads(tmp_path):
    from aurora_dimensional_systems import CrystalProcessingSystem

    class T:
        def record(self, *a, **k):
            pass
    r = R.run_pass(CrystalProcessingSystem(tracker=T()), str(tmp_path), force=True)
    d = H.pass_panel(str(tmp_path))
    assert r["ok"] and d["present"] and d["report"]["ok"] is True and len(d["history"]) == 1


def test_the_hub_serves_the_panels_and_a_page_with_tabs(tmp_path):
    (tmp_path / "dps_crystals.json").write_text(json.dumps({"crystals": {}}))
    link_files(tmp_path)
    srv = S.serve(str(tmp_path), "127.0.0.1", 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        g = lambda p: urllib.request.urlopen(f"http://127.0.0.1:{srv.server_address[1]}{p}").read()
        assert json.loads(g("/api/strata"))["server"]["epoch"] == 3 and json.loads(g("/api/ledger"))["present"] is False and json.loads(g("/api/pass"))["present"] is False
        assert b"Strata link" in g("/") and b"KEY-DO-NOT-SHOW" not in g("/api/strata")
    finally:
        srv.shutdown()


def test_the_panels_read_only_and_import_nothing_of_the_stack():
    src = open(H.__file__).read()
    tree = ast.parse(src)
    mods = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module} | {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert not {m for m in mods if m.startswith("aurora")}
    opens = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "open"]
    assert all(len(c.args) > 1 and getattr(c.args[1], "value", None) == "r" for c in opens)
    assert not any(w in src for w in ("write_text", "os.replace", "makedirs", "mkdir", "os.remove", "secret.txt\").read", "read_text"))
