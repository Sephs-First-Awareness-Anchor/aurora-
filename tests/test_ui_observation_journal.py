#!/usr/bin/env python3
"""Regression coverage for the UI observation session journal (Sunni &
Cael, "Autonomous Development Integrity" pass): a bounded, per-turn,
durable visual+timing record of one conversational interaction --
timeline.jsonl + screenshots/ + session_manifest.json -- plus the real
pixel-measured brightness/motion correction to provide_screen_observation()'s
previously-always-synthetic (0.5 default) visual channel.

Tested directly against synthetic PNG images, independent of any Android
runtime or Kotlin screenshot capture.
"""
from __future__ import annotations

import io
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANDROID_PY_DIR = os.path.join(REPO_ROOT, "flutter_app", "android", "app", "src", "main", "python")

import numpy as np
import pytest
from PIL import Image


@pytest.fixture()
def bridge():
    if ANDROID_PY_DIR not in sys.path:
        sys.path.insert(0, ANDROID_PY_DIR)
    import aurora_bridge
    # Reset module-level session/visual state between tests -- these are
    # process-global by design (mirrors _systems/_last_camera_observation
    # elsewhere in this module), so tests must not leak into each other.
    aurora_bridge._ui_observation_session = {}
    aurora_bridge._last_ui_screenshot_gray = None
    aurora_bridge._last_screen_visual_data = {}
    return aurora_bridge


def _png_bytes(rgb_array: np.ndarray) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(rgb_array, mode="RGB").save(buf, format="PNG")
    return buf.getvalue()


def _solid(color, size=32):
    arr = np.zeros((size, size, 3), dtype=np.uint8)
    arr[:, :, 0], arr[:, :, 1], arr[:, :, 2] = color
    return arr


# ── Session lifecycle ────────────────────────────────────────────────────

def test_start_session_creates_directory_structure(bridge, tmp_path, monkeypatch):
    monkeypatch.setattr(bridge, "_systems", {"state_dir": str(tmp_path)}, raising=False)
    session_dir = bridge.start_ui_observation_session()
    assert session_dir
    assert os.path.isdir(session_dir)
    assert os.path.isdir(os.path.join(session_dir, "screenshots"))
    assert os.path.exists(os.path.join(session_dir, "timeline.jsonl"))
    assert session_dir.startswith(str(tmp_path))


def test_each_session_gets_its_own_directory(bridge, tmp_path, monkeypatch):
    monkeypatch.setattr(bridge, "_systems", {"state_dir": str(tmp_path)}, raising=False)
    dir_a = bridge.start_ui_observation_session()
    bridge.stop_ui_observation_session()
    dir_b = bridge.start_ui_observation_session()
    assert dir_a != dir_b


# ── Timeline events ──────────────────────────────────────────────────────

def test_record_timeline_event_appends_jsonl_with_seq_and_timestamp(bridge, tmp_path, monkeypatch):
    monkeypatch.setattr(bridge, "_systems", {"state_dir": str(tmp_path)}, raising=False)
    session_dir = bridge.start_ui_observation_session()

    bridge.record_ui_timeline_event(json.dumps({"kind": "input_submitted", "text": "hi"}))
    bridge.record_ui_timeline_event(json.dumps({"kind": "response_available"}))

    lines = open(os.path.join(session_dir, "timeline.jsonl")).read().strip().splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    second = json.loads(lines[1])
    assert first["kind"] == "input_submitted"
    assert first["text"] == "hi"
    assert first["seq"] == 1
    assert second["seq"] == 2
    assert isinstance(first["timestamp"], float)


def test_record_timeline_event_is_a_noop_without_an_active_session(bridge):
    # Must not raise, must not create any files.
    bridge.record_ui_timeline_event(json.dumps({"kind": "input_submitted"}))


# ── Screenshots ──────────────────────────────────────────────────────────

def test_record_screenshot_writes_a_sequence_numbered_png(bridge, tmp_path, monkeypatch):
    monkeypatch.setattr(bridge, "_systems", {"state_dir": str(tmp_path)}, raising=False)
    session_dir = bridge.start_ui_observation_session()

    path = bridge.record_ui_screenshot(_png_bytes(_solid((200, 200, 200))), "input")
    assert path
    assert os.path.exists(path)
    assert os.path.basename(path) == "000001_input.png"
    assert os.path.dirname(path) == os.path.join(session_dir, "screenshots")


def test_record_screenshot_appends_a_timeline_event(bridge, tmp_path, monkeypatch):
    monkeypatch.setattr(bridge, "_systems", {"state_dir": str(tmp_path)}, raising=False)
    session_dir = bridge.start_ui_observation_session()
    bridge.record_ui_screenshot(_png_bytes(_solid((200, 200, 200))), "response")

    lines = open(os.path.join(session_dir, "timeline.jsonl")).read().strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["kind"] == "screenshot"
    assert record["transition"] == "response"
    assert record["file"] == os.path.join("screenshots", "000001_response.png")
    assert "brightness" in record["features"]


def test_record_screenshot_without_active_session_returns_empty_string(bridge):
    assert bridge.record_ui_screenshot(_png_bytes(_solid((128, 128, 128))), "input") == ""


def test_screenshot_transition_label_is_sanitized(bridge, tmp_path, monkeypatch):
    monkeypatch.setattr(bridge, "_systems", {"state_dir": str(tmp_path)}, raising=False)
    session_dir = bridge.start_ui_observation_session()
    path = bridge.record_ui_screenshot(_png_bytes(_solid((10, 10, 10))), "../../etc/passwd")
    assert path
    assert os.path.dirname(path) == os.path.join(session_dir, "screenshots")
    assert ".." not in os.path.basename(path)


# ── Real pixel measurement (the synthetic-vs-measured fix) ─────────────────

def test_bright_and_dark_screenshots_produce_different_measured_brightness(bridge, tmp_path, monkeypatch):
    monkeypatch.setattr(bridge, "_systems", {"state_dir": str(tmp_path)}, raising=False)
    bridge.start_ui_observation_session()

    bridge.record_ui_screenshot(_png_bytes(_solid((10, 10, 10))), "dark_frame")
    dark_brightness = bridge._last_screen_visual_data["brightness"]

    bridge.record_ui_screenshot(_png_bytes(_solid((240, 240, 240))), "bright_frame")
    bright_brightness = bridge._last_screen_visual_data["brightness"]

    assert dark_brightness < 0.2
    assert bright_brightness > 0.8
    assert bright_brightness > dark_brightness


def test_identical_consecutive_screenshots_show_no_motion(bridge, tmp_path, monkeypatch):
    monkeypatch.setattr(bridge, "_systems", {"state_dir": str(tmp_path)}, raising=False)
    bridge.start_ui_observation_session()
    frame = _png_bytes(_solid((128, 128, 128)))

    bridge.record_ui_screenshot(frame, "first")
    bridge.record_ui_screenshot(frame, "second")

    assert bridge._last_screen_visual_data["motion_detected"] is False


def test_sharply_different_consecutive_screenshots_show_motion(bridge, tmp_path, monkeypatch):
    monkeypatch.setattr(bridge, "_systems", {"state_dir": str(tmp_path)}, raising=False)
    bridge.start_ui_observation_session()

    bridge.record_ui_screenshot(_png_bytes(_solid((0, 0, 0))), "first")
    bridge.record_ui_screenshot(_png_bytes(_solid((255, 255, 255))), "second")

    assert bridge._last_screen_visual_data["motion_detected"] is True


def test_measured_flag_is_set_after_a_real_screenshot(bridge, tmp_path, monkeypatch):
    monkeypatch.setattr(bridge, "_systems", {"state_dir": str(tmp_path)}, raising=False)
    bridge.start_ui_observation_session()
    bridge.record_ui_screenshot(_png_bytes(_solid((128, 128, 128))), "frame")
    assert bridge._last_screen_visual_data.get("measured_from_pixels") is True


def test_provide_screen_observation_prefers_measured_brightness_over_synthetic_default(bridge, tmp_path, monkeypatch):
    """The exact confirmed gap: the accessibility payload never sends
    "brightness" at all, so this previously ALWAYS used the 0.5 constant.
    Once a real screenshot has been measured, provide_screen_observation()
    must use that measurement instead."""
    monkeypatch.setattr(bridge, "_systems", {"state_dir": str(tmp_path)}, raising=False)
    bridge.start_ui_observation_session()
    bridge.record_ui_screenshot(_png_bytes(_solid((250, 250, 250))), "frame")

    payload = json.dumps({
        "source": "android_accessibility", "observed_at": 0.0,
        "package": "org.aurora.app", "class": "x", "event_type": "window_state_changed",
        "visible_text": [], "action_surface": "phone_screen",
    })
    bridge.provide_screen_observation(payload)

    assert bridge._last_screen_visual_data["brightness"] > 0.9
    assert bridge._last_screen_visual_data["measured_from_pixels"] is True
    assert bridge._last_screen_visual_data["confidence"] == 0.90


def test_provide_screen_observation_falls_back_to_synthetic_default_with_no_screenshot(bridge, tmp_path, monkeypatch):
    """Positive control: without any screenshot ever measured, the old
    synthetic-default behavior is preserved exactly (no regression for
    installs/sessions where screenshot capture isn't available, e.g.
    below API 30)."""
    monkeypatch.setattr(bridge, "_systems", {"state_dir": str(tmp_path)}, raising=False)
    payload = json.dumps({
        "source": "android_accessibility", "observed_at": 0.0,
        "package": "org.aurora.app", "class": "x", "event_type": "window_state_changed",
        "visible_text": [], "action_surface": "phone_screen",
    })
    bridge.provide_screen_observation(payload)
    assert bridge._last_screen_visual_data["brightness"] == 0.5
    assert bridge._last_screen_visual_data["measured_from_pixels"] is False
    assert bridge._last_screen_visual_data["confidence"] == 0.70


# ── Session finalization ────────────────────────────────────────────────

def test_stop_session_writes_manifest_with_correct_counts(bridge, tmp_path, monkeypatch):
    monkeypatch.setattr(bridge, "_systems", {"state_dir": str(tmp_path)}, raising=False)
    session_dir = bridge.start_ui_observation_session()
    bridge.record_ui_timeline_event(json.dumps({"kind": "input_submitted"}))
    bridge.record_ui_screenshot(_png_bytes(_solid((10, 10, 10))), "input")
    bridge.record_ui_screenshot(_png_bytes(_solid((250, 250, 250))), "response")

    manifest_json = bridge.stop_ui_observation_session()
    manifest = json.loads(manifest_json)
    assert manifest["event_count"] == 3   # 1 explicit event + 2 screenshot events
    assert manifest["screenshot_count"] == 2
    assert manifest["duration_s"] >= 0.0
    assert manifest["session_id"] == os.path.basename(session_dir)

    on_disk = json.loads(open(os.path.join(session_dir, "session_manifest.json")).read())
    assert on_disk == manifest


def test_stop_session_clears_active_session_state(bridge, tmp_path, monkeypatch):
    monkeypatch.setattr(bridge, "_systems", {"state_dir": str(tmp_path)}, raising=False)
    bridge.start_ui_observation_session()
    bridge.stop_ui_observation_session()
    # A no-op event/screenshot call after stop must behave exactly like
    # "no session was ever started."
    bridge.record_ui_timeline_event(json.dumps({"kind": "x"}))
    assert bridge.record_ui_screenshot(_png_bytes(_solid((1, 1, 1))), "x") == ""


def test_stop_session_without_an_active_session_returns_empty_object(bridge):
    assert bridge.stop_ui_observation_session() == "{}"
