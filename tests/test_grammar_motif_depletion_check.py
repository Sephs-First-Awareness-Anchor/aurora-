# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Regression test for FIX-A007 (fitness-collapse diagnosis, 2026-07-11):
aurora_daemon._run_grammar_motif_training() checked
`len(_md.get("promoted", [])) >= 5` to decide whether enough grammar
motifs already exist -- but MotifLineage._save() (aurora_grammar_engine.py)
persists {"motifs": {...}, "discourse": {...}, "saved_at": ...}, where
promotion is a per-motif "promoted": true bool, not a top-level "promoted"
list. The phantom key always read [] (length 0), so the early-return never
fired and the 8-epoch AGENTIC training burst ran on every daemon cycle
regardless of how many motifs were already promoted -- confirmed against
the real aurora_state/grammar_motifs.json, which has 14 promoted motifs
right now and would still have triggered a full burst under the old check.
"""
import json
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aurora_daemon


def _write_motifs(path, promoted_count, total=20):
    motifs = {}
    for i in range(total):
        motifs[f"motif_{i}"] = {"promoted": i < promoted_count}
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"motifs": motifs, "discourse": {}, "saved_at": 0.0}, f)


def _fake_systems(tmp_path):
    calls = []

    class _FakeSim:
        def run_epoch(self, **kwargs):
            calls.append(kwargs)

    systems = {
        "state_dir": str(tmp_path),
        "simulation": _FakeSim(),
        "ExistenceMode": types.SimpleNamespace(AGENTIC="AGENTIC"),
    }
    return systems, calls


def test_training_burst_skipped_when_real_schema_has_enough_promoted(tmp_path):
    """The exact real-world case: 14 promoted motifs (matching the actual
    aurora_state/grammar_motifs.json checked live), stored under the real
    per-motif schema -- must NOT trigger the training burst."""
    _write_motifs(os.path.join(str(tmp_path), "grammar_motifs.json"), promoted_count=14)
    systems, calls = _fake_systems(tmp_path)

    aurora_daemon._run_grammar_motif_training(systems)

    assert calls == [], "14 real promoted motifs must short-circuit the training burst"


def test_training_burst_fires_when_genuinely_depleted(tmp_path):
    _write_motifs(os.path.join(str(tmp_path), "grammar_motifs.json"), promoted_count=2)
    systems, calls = _fake_systems(tmp_path)

    aurora_daemon._run_grammar_motif_training(systems)

    assert len(calls) == 8, "genuinely depleted motifs (< 5 promoted) must still run the 8-epoch burst"


def test_training_burst_fires_when_no_motif_file_exists_yet(tmp_path):
    systems, calls = _fake_systems(tmp_path)

    aurora_daemon._run_grammar_motif_training(systems)

    assert len(calls) == 8, "no file yet is a legitimate 'depleted' state"
