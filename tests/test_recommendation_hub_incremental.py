#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""The recommendation hub reads only appended lines (phone load, 2026-11-07)
and gives exactly the answers the old full-file scans gave."""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import aurora_internal.aurora_recommendation_hub as H  # noqa: E402


def _old_pending(output_dir, limit=10):
    p = H._paths(output_dir)
    acted = H._action_index(output_dir)
    pending = [r for r in H._read_jsonl(p["inbox"]) if str(r.get("id") or "") and str(r.get("id") or "") not in acted]
    pending.sort(key=lambda r: (-(float(r.get("priority", 0.0) or 0.0)), str(r.get("created_at", ""))))
    return pending[: max(1, int(limit))]


def _old_block(output_dir, cooldown):
    p = H._paths(output_dir)
    now = time.time()
    for row in reversed(H._read_jsonl(p["actions"])):
        if str(row.get("action") or "") != "discuss_with_user":
            continue
        decided_at = H._parse_iso_epoch(row.get("decided_at"))
        if decided_at <= 0.0:
            continue
        return (now - decided_at) < cooldown
    return False


def _append(path, row):
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")


def test_matches_full_scan_through_appends_actions_and_rewrites(tmp_path):
    H._HUB_INDEXES.clear()
    out = str(tmp_path)
    p = H._paths(out)
    for i in range(30):
        _append(p["inbox"], {"id": f"r{i}", "priority": (i % 10) / 10, "created_at": f"2026-11-0{1 + i % 8}"})
    _append(p["inbox"], {"id": "r3", "priority": 0.95, "created_at": "2026-11-08"})   # duplicate id
    for limit in (3, 10, 50):
        assert H.pending_recommendations(out, limit) == _old_pending(out, limit)
    for rec in H.pending_recommendations(out, 4):
        H.act_recommendation(out, rec, action=H.choose_action(rec), rationale="t")
    assert H.pending_recommendations(out, 50) == _old_pending(out, 50)
    assert H._recent_discuss_block(out, 3600) == _old_block(out, 3600)
    with open(p["inbox"], "a", encoding="utf-8") as fh:
        fh.write('{"id": "half"')                      # write in progress
    assert H.pending_recommendations(out, 50) == [r for r in _old_pending(out, 50) if r.get("id") != "half"]
    with open(p["inbox"], "a", encoding="utf-8") as fh:
        fh.write(', "priority": 0.99}\n')
    assert H.pending_recommendations(out, 50) == _old_pending(out, 50)
    # log rotated / rewritten smaller
    Path(p["inbox"]).write_text(json.dumps({"id": "only", "priority": 0.5}) + "\n")
    assert H.pending_recommendations(out, 50) == _old_pending(out, 50)


def test_real_logs_match(tmp_path):
    src = ROOT / "aurora_state"
    if not (src / "aurora_recommendation_inbox.jsonl").exists():
        return
    for name in ("aurora_recommendation_inbox.jsonl", "aurora_recommendation_actions.jsonl"):
        shutil.copy(src / name, tmp_path / name)
    H._HUB_INDEXES.clear()
    out = str(tmp_path)
    assert H.pending_recommendations(out, 10) == _old_pending(out, 10)
    assert H._recent_discuss_block(out, 1e9) == _old_block(out, 1e9)
    t = time.time()
    for _ in range(20):
        H.pending_recommendations(out, 3)
    assert time.time() - t < 1.0, "repeat reads must not re-parse the logs"


def test_settle_ages_out_and_releases_without_changing_answers(tmp_path):
    from datetime import datetime, timezone
    H._HUB_INDEXES.clear(); H._LAST_SETTLE.clear()
    out = str(tmp_path)
    p = H._paths(out)
    now = time.time()
    iso = lambda t: datetime.fromtimestamp(t, tz=timezone.utc).isoformat()
    for i in range(40):
        _append(p["inbox"], {"id": f"old{i}", "priority": 0.1, "created_at": iso(now - 10 * 86400)})
    for i in range(10):
        _append(p["inbox"], {"id": f"new{i}", "priority": 0.5 + i / 100, "created_at": iso(now - 3600)})
    _append(p["inbox"], {"id": "talk", "priority": 0.9, "created_at": iso(now - 60)})
    H.act_recommendation(out, {"id": "talk", "priority": 0.9}, action="discuss_with_user")
    before_pending = [r["id"] for r in _old_pending(out, 100) if r["id"].startswith("new")]
    before_block = _old_block(out, 3600)
    result = H.settle_recommendations(out, now=now, force=True)
    assert result["aged_out"] == 40
    assert result["released"] == 41                       # 40 aged out + the discussed one
    assert [r["id"] for r in H.pending_recommendations(out, 100)] == \
        [r["id"] for r in _old_pending(out, 100)] == sorted(before_pending, key=lambda x: -int(x[3:]))
    assert H._recent_discuss_block(out, 3600) == _old_block(out, 3600) == before_block is True
    assert len(H._read_jsonl(p["inbox"])) == 10              # only what is still open
    # not again within the window
    assert H.settle_recommendations(out, now=now + 60) == {"aged_out": 0, "released": 0}
