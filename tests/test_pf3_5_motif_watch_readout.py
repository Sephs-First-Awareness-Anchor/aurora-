# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
PF3.5: motif promotion watch, weekly readout script. Observation only
-- no seeding happens in this script; seeding via MotifLineage.
seed_motifs is a human call at window close, per the directive.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from scripts.pf3_5_motif_watch_readout import _motif_readout, _repetition_share  # noqa: E402


def _write_motifs(entries):
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump({"motifs": entries, "saved_at": 0}, tmp)
    tmp.close()
    return tmp.name


def test_counts_only_promoted_and_clause_valid_motifs():
    entries = {
        "agent_action": {
            "pattern_id": "agent_action", "role_sequence": ["agent", "action"],
            "promoted": True,
        },
        "agent_action_object": {
            "pattern_id": "agent_action_object",
            "role_sequence": ["agent", "action", "object"], "promoted": True,
        },
        "not_promoted": {
            "pattern_id": "not_promoted", "role_sequence": ["agent", "action"],
            "promoted": False,
        },
        "promoted_but_invalid_shape": {
            "pattern_id": "promoted_but_invalid_shape",
            "role_sequence": ["descriptor", "action", "object"], "promoted": True,
        },
    }
    path = _write_motifs(entries)
    report = _motif_readout(Path(path))
    assert report["total_motifs"] == 4
    assert report["total_promoted"] == 3
    assert report["promoted_clause_valid_count"] == 2
    assert "agent_action" in report["clause_valid_shapes"]
    assert "agent_action_object" in report["clause_valid_shapes"]
    assert "descriptor_action_object" not in report["clause_valid_shapes"]


def test_handles_unknown_role_strings_gracefully():
    entries = {
        "weird": {
            "pattern_id": "weird", "role_sequence": ["agent", "not_a_real_role"],
            "promoted": True,
        },
    }
    path = _write_motifs(entries)
    report = _motif_readout(Path(path))
    assert report["promoted_clause_valid_count"] == 0


def _write_characterization(records):
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump({"records": records}, tmp)
    tmp.close()
    return tmp.name


def test_repetition_share_flags_cross_clause_token_overlap():
    records = [
        {"delivered": "I denied claims. I denied.", "coherent": False, "adequacy": 1.0},
        {"delivered": "I need water clearly today.", "coherent": True, "adequacy": 0.9},
    ]
    path = _write_characterization(records)
    report = _repetition_share(Path(path))
    assert report["residue_records"] == 1
    assert report["repeated_clause_records"] == 1
    assert report["repetition_share_of_residue"] == 1.0


def test_repetition_share_none_when_no_residue():
    records = [
        {"delivered": "I need water clearly today.", "coherent": True, "adequacy": 0.9},
    ]
    path = _write_characterization(records)
    report = _repetition_share(Path(path))
    assert report["residue_records"] == 0
    assert report["repetition_share_of_residue"] is None


def test_repetition_share_single_sentence_response_not_flagged():
    records = [
        {"delivered": "I move.", "coherent": False, "adequacy": 0.5},
    ]
    path = _write_characterization(records)
    report = _repetition_share(Path(path))
    assert report["residue_records"] == 1
    assert report["repeated_clause_records"] == 0
