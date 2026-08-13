#!/usr/bin/env python3
"""Regression coverage for Build 650 Multimodal Representational Autonomy
Directive, Section VI/VII (Sunni & Cael): the parallel nonsemantic audio
path -- provide_audio_observation_raw() and its DSP feature extraction --
tested directly against synthetic PCM signals, independent of any Android
runtime.
"""
from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANDROID_PY_DIR = os.path.join(REPO_ROOT, "flutter_app", "android", "app", "src", "main", "python")

import numpy as np
import pytest


@pytest.fixture()
def bridge(monkeypatch):
    if ANDROID_PY_DIR not in sys.path:
        sys.path.insert(0, ANDROID_PY_DIR)
    import aurora_bridge
    # Reset module-level rolling state between tests so flux computations
    # don't leak across synthetic signals.
    monkeypatch.setattr(aurora_bridge, "_last_audio_spectrum", None, raising=False)
    monkeypatch.setattr(aurora_bridge, "_last_audio_observation", {}, raising=False)
    return aurora_bridge


def _pcm16(samples_float):
    clipped = np.clip(samples_float, -1.0, 1.0)
    return (clipped * 32767.0).astype("<i2").tobytes()


def _tone(freq_hz, sample_rate=16000, duration_s=0.1, amplitude=0.8):
    t = np.arange(int(sample_rate * duration_s)) / float(sample_rate)
    return np.sin(2.0 * np.pi * freq_hz * t) * amplitude


def _white_noise(sample_rate=16000, duration_s=0.1, amplitude=0.5, seed=42):
    rng = np.random.default_rng(seed)
    return rng.uniform(-amplitude, amplitude, int(sample_rate * duration_s))


def _silence(sample_rate=16000, duration_s=0.1):
    return np.zeros(int(sample_rate * duration_s))


def test_pure_tone_produces_accurate_pitch_estimate(bridge):
    sample_rate = 16000
    true_freq = 220.0  # A3
    signal = _tone(true_freq, sample_rate=sample_rate, duration_s=0.2)
    pitch_hz, harmonicity = bridge._estimate_pitch_autocorr(signal.astype(np.float32), sample_rate)

    assert pitch_hz is not None
    # Autocorrelation pitch estimation has some lag-quantization error at
    # low frequencies; require it within 15% of the true frequency, not
    # bit-exact.
    assert abs(pitch_hz - true_freq) / true_freq < 0.15
    assert harmonicity > 0.5, "a clean sine tone must register as highly harmonic"


def test_white_noise_has_low_harmonicity(bridge):
    signal = _white_noise(duration_s=0.2).astype(np.float32)
    _pitch_hz, harmonicity = bridge._estimate_pitch_autocorr(signal, 16000)
    assert harmonicity < 0.4, "white noise must not register as strongly tonal"


def test_silence_is_classified_as_silence(bridge):
    activity = bridge._classify_ambient_activity(rms_db=-70.0, zcr=0.0, centroid_hz=0.0, harmonicity=0.0)
    assert activity == "silence"


def test_noisy_high_zcr_signal_is_classified_as_noise(bridge):
    activity = bridge._classify_ambient_activity(rms_db=-10.0, zcr=0.5, centroid_hz=3000.0, harmonicity=0.1)
    assert activity == "noise"


def test_tonal_speech_range_signal_is_classified_as_speech(bridge):
    activity = bridge._classify_ambient_activity(rms_db=-15.0, zcr=0.1, centroid_hz=400.0, harmonicity=0.7)
    assert activity == "speech"


def test_provide_audio_observation_raw_end_to_end_updates_last_observation(bridge):
    signal = _tone(440.0, duration_s=0.2, amplitude=0.6).astype(np.float32)
    pcm = _pcm16(signal)

    bridge.provide_audio_observation_raw(pcm, sample_rate=16000)

    obs = bridge._last_audio_observation
    assert obs, "provide_audio_observation_raw must forward through provide_audio_observation"
    assert obs["activity"] in {"speech", "music"}  # a clean 440Hz tone is strongly tonal
    assert "rms_db" in obs and obs["rms_db"] > -50.0
    assert obs["source"] == "raw_pcm"
    assert "spectral_centroid" in obs
    assert "spectral_bandwidth" in obs
    assert "spectral_rolloff" in obs
    assert "zero_crossing_rate" in obs
    assert "harmonicity" in obs
    assert obs["pitch_hz"] == pytest.approx(440.0, rel=0.15)


def test_provide_audio_observation_raw_never_performs_transcription(bridge):
    """Section VII: 'Do not perform speech transcription through this
    path.' Confirmed structurally: the function's only external call is to
    provide_audio_observation() with numeric/string labels, never anything
    resembling a transcript field."""
    signal = _tone(300.0, duration_s=0.2).astype(np.float32)
    bridge.provide_audio_observation_raw(_pcm16(signal), sample_rate=16000)
    obs = bridge._last_audio_observation
    assert "transcript" not in obs
    assert "text" not in obs
    forbidden_value_types = [v for v in obs.values() if isinstance(v, str) and len(v.split()) > 3]
    assert forbidden_value_types == [], "no multi-word string value should appear -- this path is nonsemantic"


def test_spectral_flux_reflects_change_between_consecutive_chunks(bridge):
    quiet = _pcm16(_silence(duration_s=0.1))
    loud_tone = _pcm16(_tone(500.0, duration_s=0.1, amplitude=0.9))

    bridge.provide_audio_observation_raw(quiet, sample_rate=16000)
    first_flux = bridge._last_audio_observation.get("spectral_flux", 0.0)

    bridge.provide_audio_observation_raw(loud_tone, sample_rate=16000)
    second_flux = bridge._last_audio_observation.get("spectral_flux", 0.0)

    assert second_flux > first_flux, (
        "a sharp transition from silence to a loud tone should register a "
        "larger spectral flux than silence-to-silence"
    )


def test_short_or_empty_pcm_is_safely_ignored(bridge):
    before = dict(bridge._last_audio_observation)
    bridge.provide_audio_observation_raw(b"", sample_rate=16000)
    bridge.provide_audio_observation_raw(b"\x00\x00", sample_rate=16000)
    assert bridge._last_audio_observation == before, "degenerate input must not corrupt or fabricate an observation"
