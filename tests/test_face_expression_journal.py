#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_face_expression_journal.py -- she feels her own face (surface
restructure 4, Sir's adjustment).

These pin:
  * a settled change of expression is kept with the state it came from, in
    the surface-present face_expression_journal.jsonl;
  * it is offered to her concept crystal as a self-observation at the axis
    coordinate it came from;
  * a bad payload is answered with an error the face can show, never raised;
  * the axis poll carries what she is attending to, so her eyes can follow.
"""
from __future__ import annotations

import json
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANDROID_PY_DIR = os.path.join(REPO_ROOT, "flutter_app", "android", "app", "src", "main", "python")


@pytest.fixture()
def bridge(tmp_path, monkeypatch):
    if ANDROID_PY_DIR not in sys.path:
        sys.path.insert(0, ANDROID_PY_DIR)
    import aurora_bridge
    monkeypatch.setattr(aurora_bridge, "_systems", {"state_dir": str(tmp_path)})
    return aurora_bridge


class _Registry:
    def __init__(self):
        self.seen = []

    def observe_sensory(self, ax, dim, node_ref, overlay=None):
        self.seen.append((dict(ax), dim, node_ref, dict(overlay or {})))


def test_a_settled_expression_is_kept_with_the_state_it_came_from(bridge, tmp_path, monkeypatch):
    registry = _Registry()
    monkeypatch.setattr(bridge, "_concept_registry", registry)
    payload = {"axes": {"X": 0.7, "T": 0.4, "N": 0.6, "B": 0.5, "A": 0.8},
               "pressure": {"X": 0.2, "A": 0.1},
               "face": {"eyeOpen": 0.9, "mouthCurve": 0.4},
               "speaking": False, "attention": "camera"}
    out = json.loads(bridge.record_face_expression(json.dumps(payload)))
    assert out == {"ok": True}
    rows = [json.loads(l) for l in (tmp_path / "face_expression_journal.jsonl").read_text().splitlines()]
    assert len(rows) == 1
    assert rows[0]["axes"]["A"] == 0.8 and rows[0]["face"]["eyeOpen"] == 0.9
    assert rows[0]["attention"] == "camera"
    (ax, dim, ref, overlay) = registry.seen[0]
    assert dim == "self_obs" and ax["X"] == 0.7 and ref.startswith("face:")
    assert overlay["mouthCurve"] == 0.4


def test_a_bad_payload_is_answered_not_raised(bridge):
    out = json.loads(bridge.record_face_expression("[1, 2]"))
    assert out["ok"] is False and out["error"]
    out = json.loads(bridge.record_face_expression("{not json"))
    assert out["ok"] is False and out["error"]


def test_the_journal_is_a_surface_present_store():
    sys.path.insert(0, REPO_ROOT)
    from aurora_internal.aurora_store_ownership import SURFACE_PRESENT, classify
    assert classify("face_expression_journal.jsonl") == SURFACE_PRESENT


def test_the_axis_poll_carries_her_attention(bridge, monkeypatch):
    monkeypatch.setattr(bridge, "_current_attention_modality", lambda: "audio")
    monkeypatch.setattr(bridge, "_refresh_axis_state_from_systems", lambda: None)
    state = json.loads(bridge.get_axis_state())
    assert state["attention"] == "audio"
    assert "X" in state and "speaking" in state


def test_before_boot_nothing_is_kept_and_nothing_fails(bridge, tmp_path, monkeypatch):
    monkeypatch.setattr(bridge, "_systems", None)
    out = json.loads(bridge.record_face_expression(json.dumps({"face": {"eyeOpen": 1.0}})))
    assert out == {"ok": True, "skipped": "not_booted"}
    assert not (tmp_path / "face_expression_journal.jsonl").exists()
