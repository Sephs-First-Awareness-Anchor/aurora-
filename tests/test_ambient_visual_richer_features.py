#!/usr/bin/env python3
"""Regression coverage for Build 650 Multimodal Representational Autonomy
Directive, Section VIII (Sunni & Cael): richer, real, bounded visual
features (hue histogram, edge density, orientation, symmetry, shape
complexity, real-valued motion magnitude) computed from raw frame data --
tested directly against synthetic images, independent of any Android
runtime or cv2.
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


def _solid_rgb(color, size=64):
    arr = np.zeros((size, size, 3), dtype=np.uint8)
    arr[:, :, 0] = color[0]
    arr[:, :, 1] = color[1]
    arr[:, :, 2] = color[2]
    return arr


def _checkerboard(size=64, square=8):
    arr = np.zeros((size, size, 3), dtype=np.uint8)
    for y in range(0, size, square):
        for x in range(0, size, square):
            if ((y // square) + (x // square)) % 2 == 0:
                arr[y:y + square, x:x + square] = 255
    return arr


def _gray_from_rgb(rgb):
    return np.mean(rgb, axis=2).astype(np.float32) / 255.0


def test_solid_red_frame_peaks_hue_histogram_near_zero_degrees(bridge):
    rgb = _solid_rgb((255, 10, 10))
    gray = _gray_from_rgb(rgb)
    features = bridge._extract_richer_visual_features(rgb, gray, motion_magnitude=0.0)

    hist = features["hsv_histogram"]
    assert len(hist) == 24
    assert sum(hist) == pytest.approx(1.0, abs=0.01)
    # Pure red is hue ~0 degrees -> bin 0 (and its immediate neighbor from
    # rounding) should dominate the histogram.
    assert hist[0] + hist[1] + hist[23] > 0.8


def test_solid_frame_has_near_zero_edge_density(bridge):
    rgb = _solid_rgb((100, 150, 200))
    gray = _gray_from_rgb(rgb)
    features = bridge._extract_richer_visual_features(rgb, gray, motion_magnitude=0.0)
    assert features["edge_density"] < 0.05


def test_checkerboard_has_high_edge_density(bridge):
    rgb = _checkerboard()
    gray = _gray_from_rgb(rgb)
    features = bridge._extract_richer_visual_features(rgb, gray, motion_magnitude=0.0)
    assert features["edge_density"] > 0.3


def test_symmetric_frame_scores_high_symmetry(bridge):
    left_half = np.random.default_rng(7).integers(0, 255, (64, 32, 3), dtype=np.uint8)
    rgb = np.concatenate([left_half, left_half[:, ::-1, :]], axis=1)
    gray = _gray_from_rgb(rgb)
    features = bridge._extract_richer_visual_features(rgb, gray, motion_magnitude=0.0)
    assert features["symmetry_score"] > 0.85


def test_asymmetric_random_frame_scores_lower_symmetry_than_mirrored(bridge):
    rng = np.random.default_rng(11)
    left_half = rng.integers(0, 255, (64, 32, 3), dtype=np.uint8)
    mirrored_rgb = np.concatenate([left_half, left_half[:, ::-1, :]], axis=1)
    random_rgb = rng.integers(0, 255, (64, 64, 3), dtype=np.uint8)

    mirrored_sym = bridge._extract_richer_visual_features(
        mirrored_rgb, _gray_from_rgb(mirrored_rgb), motion_magnitude=0.0
    )["symmetry_score"]
    random_sym = bridge._extract_richer_visual_features(
        random_rgb, _gray_from_rgb(random_rgb), motion_magnitude=0.0
    )["symmetry_score"]

    assert mirrored_sym > random_sym


def test_checkerboard_has_higher_shape_complexity_than_solid(bridge):
    solid_rgb = _solid_rgb((80, 80, 80))
    checker_rgb = _checkerboard()
    solid = bridge._extract_richer_visual_features(solid_rgb, _gray_from_rgb(solid_rgb), motion_magnitude=0.0)
    checker = bridge._extract_richer_visual_features(checker_rgb, _gray_from_rgb(checker_rgb), motion_magnitude=0.0)
    assert checker["shape_complexity"] >= solid["shape_complexity"]


def test_motion_magnitude_is_real_valued_and_bounded(bridge):
    rgb = _solid_rgb((50, 60, 70))
    gray = _gray_from_rgb(rgb)
    low = bridge._extract_richer_visual_features(rgb, gray, motion_magnitude=0.1)
    high = bridge._extract_richer_visual_features(rgb, gray, motion_magnitude=0.9)
    assert 0.0 <= low["motion_magnitude"] <= 1.0
    assert 0.0 <= high["motion_magnitude"] <= 1.0
    assert high["motion_magnitude"] > low["motion_magnitude"]


def test_depth_variation_is_honestly_absent_not_fabricated(bridge):
    """Section VIII: depth/variation proxy is explicitly 'where available' --
    no depth sensor data exists on this capture path, so it must stay a
    known, documented zero rather than a fabricated proxy value."""
    rgb = _checkerboard()
    features = bridge._extract_richer_visual_features(rgb, _gray_from_rgb(rgb), motion_magnitude=0.0)
    assert features["depth_variation"] == 0.0


def test_provide_camera_frame_populates_features_dict_end_to_end(bridge):
    from PIL import Image
    import io

    img = Image.fromarray(_checkerboard(), mode="RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    jpeg_bytes = buf.getvalue()

    bridge._last_camera_observation = {}
    bridge._last_camera_frame_gray = None
    bridge.provide_camera_frame(jpeg_bytes)

    obs = bridge._last_camera_observation
    assert obs, "provide_camera_frame must populate an observation"
    assert "features" in obs and isinstance(obs["features"], dict)
    feat = obs["features"]
    assert "hsv_histogram" in feat and len(feat["hsv_histogram"]) == 24
    assert "edge_density" in feat
    assert "orientation" in feat
    assert "symmetry_score" in feat
    assert "shape_complexity" in feat
    assert "motion_magnitude" in feat
    # dominant_hue (backward-compatible categorical field) must still exist.
    assert "dominant_hue" in obs


def test_visual_dict_to_crystal_57d_now_receives_real_hue_and_shape_signal(bridge):
    """The actual regression this section fixes: visual_dict_to_crystal_57d()
    previously saw an empty 'features' dict from provide_camera_frame's
    output, so dims [0:24] (hue) and most of [24:51] (shape) stayed at
    their zero default regardless of what the camera saw. Uses a COLORED
    checkerboard (not black/white) -- a greyscale checkerboard has zero
    saturation everywhere and correctly produces an all-zero hue
    histogram, which is real DSP behavior, not a bug (see the dedicated
    black/white edge-density test above for that case)."""
    from PIL import Image
    import io

    colored = _checkerboard()
    # Recolor: white squares -> orange, black squares -> teal, so the frame
    # has both real hue content AND real edge/shape content simultaneously.
    is_white = colored[:, :, 0] > 128
    colored = colored.copy()
    colored[is_white] = [255, 140, 0]
    colored[~is_white] = [0, 128, 128]

    img = Image.fromarray(colored, mode="RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    bridge._last_camera_observation = {}
    bridge._last_camera_frame_gray = None
    bridge.provide_camera_frame(buf.getvalue())

    from aurora_internal.aurora_sensory_crystal import visual_dict_to_crystal_57d
    vec = visual_dict_to_crystal_57d(bridge._last_camera_observation)
    assert len(vec) == 57
    hue_dims = vec[0:24]
    shape_dims = vec[24:51]
    assert sum(hue_dims) > 0.0, "hue histogram dims must carry real signal, not stay at zero default"
    assert sum(shape_dims) > 0.0, "shape dims (edge density etc.) must carry real signal on a checkerboard frame"
