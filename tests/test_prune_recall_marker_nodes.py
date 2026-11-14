#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""FIX-A128 clean-up tool: removes only marker nodes and what touches them."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import prune_recall_marker_nodes as prune


def _web():
    return {
        "nodes": {"fence": {}, "posts": {}, "[recalled:fence]": {}, "[recalled:recalled:posts]": {}},
        "relations": {
            "r1": {"source_word": "fence", "target_word": "posts"},
            "r2": {"source_word": "fence", "target_word": "[recalled:fence]"},
            "r3": {"source_word": "[recalled:recalled:posts]", "target_word": "posts"},
        },
        "categories": {"growth": ["fence", "[recalled:fence]", "posts"], "noun": ["[recalled:recalled:posts]"]},
    }


def test_only_markers_and_what_touches_them_go():
    data = _web()
    removed = prune.prune_web_dict(data)
    assert removed == {"nodes": 2, "relations": 2, "category_entries": 2}
    assert set(data["nodes"]) == {"fence", "posts"}
    assert set(data["relations"]) == {"r1"}
    assert data["categories"] == {"growth": ["fence", "posts"], "noun": []}


def test_apply_backs_up_replaces_and_is_idempotent(tmp_path):
    (tmp_path / "aurora_oets_web.json").write_text(json.dumps(_web()))
    dry = prune.run(str(tmp_path), apply=False)
    assert dry["status"] == "dry_run" and "[recalled:fence]" in (tmp_path / "aurora_oets_web.json").read_text()
    done = prune.run(str(tmp_path), apply=True)
    assert done["status"] == "pruned" and Path(done["backup"]).exists()
    saved = json.loads((tmp_path / "aurora_oets_web.json").read_text())
    assert "[recalled" not in json.dumps(saved["nodes"]) and saved["_checksum"] == prune._checksum(saved)
    assert prune.run(str(tmp_path), apply=True)["status"] == "nothing_to_prune"
