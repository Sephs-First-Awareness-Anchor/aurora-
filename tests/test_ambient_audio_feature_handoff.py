#!/usr/bin/env python3
"""Regression coverage for the Build 656 follow-up (Sunni & Cael): the
confirmed audio feature handoff kink between provide_audio_observation_raw()
(real DSP measurements) and _sample_ambient_perception()'s normalization
into the dict Sensory Crystal actually consumes.

Reproduced directly with known values matching independent testing: feeding
zcr=.1234, spectral centroid=1234Hz, bandwidth=456Hz, rolloff=2345Hz,
flux=.321, harmonicity=.67, pitch=440Hz through the real DSP path showed
Sensory Crystal receiving rms=1.0, zcr=.08 (category heuristic, not the
measured value), harmonicity=.80 (category heuristic), spectral_flux=.321
(the one field that happened to carry over) -- centroid, bandwidth,
rolloff, and pitch vanished entirely. Root cause: the carry-over key list
checked for "pitch"/"centroid"/"bandwidth" (names the DSP path never
produces -- it emits pitch_hz/spectral_centroid/spectral_bandwidth), never
checked "spectral_rolloff" or "harmonicity" at all, and the zcr/harmonicity
heuristic fallback was unconditional -- it overwrote real measurements
rather than only filling in when none existed.
"""
from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANDROID_PY_DIR = os.path.join(REPO_ROOT, "flutter_app", "android", "app", "src", "main", "python")

import numpy as np
import pytest


@pytest.fixture()
def bridge():
    if ANDROID_PY_DIR not in sys.path:
        sys.path.insert(0, ANDROID_PY_DIR)
    import aurora_bridge
    return aurora_bridge


def _tone(freq_hz, sample_rate=16000, duration_s=0.5, amplitude=0.6):
    t = np.linspace(0, duration_s, int(sample_rate * duration_s), endpoint=False)
    samples = amplitude * np.sin(2 * np.pi * freq_hz * t)
    pcm = (samples * 32767).astype(np.int16)
    return pcm.tobytes()


def test_real_measured_features_survive_into_sensory_crystal_feed(bridge, monkeypatch):
    captured = {}

    def _spy_feed(systems, audio_data, visual_data):
        captured["audio_data"] = audio_data

    monkeypatch.setattr(bridge, "_feed_sensory_crystal_frames", _spy_feed)
    monkeypatch.setattr(bridge, "_last_perceptual_ts", 0.0, raising=False)
    bridge._last_audio_observation = {}

    # A real tone gives real, non-heuristic centroid/pitch/rolloff/bandwidth.
    bridge.provide_audio_observation_raw(_tone(440.0), sample_rate=16000)
    assert bridge._last_audio_observation, "DSP path must have produced an observation"
    raw_obs = dict(bridge._last_audio_observation)
    for key in ("zero_crossing_rate", "spectral_centroid", "spectral_bandwidth",
                "spectral_rolloff", "spectral_flux", "harmonicity"):
        assert key in raw_obs, f"DSP path did not produce {key}"

    bridge._sample_ambient_perception({})

    assert "audio_data" in captured, "sensory crystal feed must have been called"
    feat = captured["audio_data"].get("features", {})

    # The exact regression: these must now be the REAL measured values, not
    # category-keyword heuristics or silently absent.
    assert feat.get("centroid") == pytest.approx(raw_obs["spectral_centroid"], rel=1e-6)
    assert feat.get("bandwidth") == pytest.approx(raw_obs["spectral_bandwidth"], rel=1e-6)
    assert feat.get("rolloff") == pytest.approx(raw_obs["spectral_rolloff"], rel=1e-6)
    assert feat.get("zcr") == pytest.approx(raw_obs["zero_crossing_rate"], rel=1e-6)
    assert feat.get("harmonicity") == pytest.approx(raw_obs["harmonicity"], rel=1e-6)
    if "pitch_hz" in raw_obs:
        assert feat.get("pitch") == pytest.approx(raw_obs["pitch_hz"], rel=1e-6)

    # audio_dict_to_crystal_20d() must actually be able to read them back
    # out via its own alias resolution -- prove the fix end-to-end through
    # the real consumer, not just the intermediate dict shape.
    from aurora_internal.aurora_sensory_crystal import audio_dict_to_crystal_20d
    vec = audio_dict_to_crystal_20d(captured["audio_data"])
    assert len(vec) == 20
    assert vec[2] == pytest.approx(raw_obs["spectral_centroid"], rel=1e-6)
    assert vec[3] == pytest.approx(raw_obs["spectral_bandwidth"], rel=1e-6)
    assert vec[4] == pytest.approx(raw_obs["spectral_rolloff"], rel=1e-6)
    assert vec[5] == pytest.approx(raw_obs["spectral_flux"], rel=1e-6)
    assert vec[6] == pytest.approx(raw_obs["harmonicity"], rel=1e-6)


def test_heuristic_fallback_still_applies_when_no_real_measurement_exists(bridge, monkeypatch):
    """The JSON-file polling fallback path (no DSP measurements available)
    must still get a sensible category-based guess -- this is a real
    fallback, not something the fix should remove."""
    captured = {}
    monkeypatch.setattr(bridge, "_feed_sensory_crystal_frames",
                         lambda systems, audio_data, visual_data: captured.update(audio_data=audio_data))
    monkeypatch.setattr(bridge, "_last_perceptual_ts", 0.0, raising=False)
    bridge._last_audio_observation = {"activity": "music", "rms_db": -20.0, "confidence": 0.6}

    bridge._sample_ambient_perception({})

    feat = captured["audio_data"]["features"]
    assert feat["zcr"] == pytest.approx(0.08)
    assert feat["harmonicity"] == pytest.approx(0.80)


def test_real_measurement_wins_even_when_it_equals_zero(bridge, monkeypatch):
    """A genuine measured zcr/harmonicity of 0.0 must not be treated as
    'absent' and silently replaced by the heuristic -- key presence, not
    truthiness, must gate the fallback."""
    captured = {}
    monkeypatch.setattr(bridge, "_feed_sensory_crystal_frames",
                         lambda systems, audio_data, visual_data: captured.update(audio_data=audio_data))
    monkeypatch.setattr(bridge, "_last_perceptual_ts", 0.0, raising=False)
    bridge._last_audio_observation = {
        "activity": "music", "rms_db": -20.0, "confidence": 0.6,
        "zero_crossing_rate": 0.0, "harmonicity": 0.0,
    }

    bridge._sample_ambient_perception({})

    feat = captured["audio_data"]["features"]
    assert feat["zcr"] == 0.0
    assert feat["harmonicity"] == 0.0
