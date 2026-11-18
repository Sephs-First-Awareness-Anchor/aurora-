"""Regression coverage for distributed Surface predictive-frame state paths."""
import json

from aurora_internal.dual_strata.predictive_stager import PredictiveStager


def test_predictive_frames_follow_active_state_directory(tmp_path, monkeypatch):
    first = tmp_path / "surface_one"
    second = tmp_path / "surface_two"
    monkeypatch.setenv("AURORA_STATE_DIR", str(first))
    PredictiveStager.push_staged_frame({"context_hash": "first", "topic": "alpha"})
    assert (first / "predictive_frame_queue.json").exists()

    monkeypatch.setenv("AURORA_STATE_DIR", str(second))
    assert PredictiveStager.pop_staged_frames() == []
    PredictiveStager.push_staged_frame({"context_hash": "second", "topic": "beta"})
    assert PredictiveStager.pop_staged_frame()["context_hash"] == "second"

    monkeypatch.setenv("AURORA_STATE_DIR", str(first))
    assert PredictiveStager.pop_staged_frame()["context_hash"] == "first"
    assert PredictiveStager.pop_staged_frame() is None


def test_predictive_queue_recovers_from_wrong_json_shape(tmp_path, monkeypatch):
    monkeypatch.setenv("AURORA_STATE_DIR", str(tmp_path))
    (tmp_path / "predictive_frame_queue.json").write_text(json.dumps({"not": "a queue"}))
    assert PredictiveStager.pop_staged_frames() == []
