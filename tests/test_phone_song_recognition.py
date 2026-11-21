#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_phone_song_recognition.py -- song recognition inside the app.

In the app the clip comes from PhoneHands.recordClip (her own hearing, or a
short recording of the app's own), never from termux-microphone-record, and
the clip is deleted afterwards whatever the answer.
"""
from __future__ import annotations

import io
import json

from aurora_internal import tool_registry as tr


def test_in_the_app_the_clip_comes_from_her_hearing_and_is_cleaned_up(tmp_path, monkeypatch):
    clip = tmp_path / "song.wav"
    clip.write_bytes(b"RIFF" + b"\0" * 4000)
    calls = []

    def fake_hands(method, *args):
        calls.append((method, args))
        return {"ok": True, "data": {"path": str(clip), "seconds": 8.0, "source": "her_hearing"}}

    class Resp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    sent = {}

    def fake_urlopen(req, timeout=0):
        sent["url"] = req.full_url
        return Resp(json.dumps({"status": "success", "result": {
            "artist": "An Artist", "title": "A Song", "album": "An Album"}}).encode())

    monkeypatch.setattr(tr, "_is_chaquopy_android", lambda: True)
    monkeypatch.setattr(tr, "_is_termux", lambda: False)
    monkeypatch.setattr(tr, "_phone_hands", fake_hands)
    monkeypatch.setattr(tr.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(tr._subprocess, "Popen", lambda *a, **k: (_ for _ in ()).throw(AssertionError("termux used")))

    out = tr._mobile_music_identify(duration_s=8)
    assert out.success, out.note
    assert "A Song" in out.data
    assert calls == [("recordClip", (8,))]
    assert sent["url"].startswith("https://api.audd.io")
    assert not clip.exists()


def test_a_missing_microphone_permission_is_named(monkeypatch):
    monkeypatch.setattr(tr, "_is_chaquopy_android", lambda: True)
    monkeypatch.setattr(tr, "_phone_hands",
                        lambda m, *a: {"ok": False, "error": "needs_permission:android.permission.RECORD_AUDIO"})
    out = tr._mobile_music_identify(duration_s=8)
    assert not out.success
    assert "RECORD_AUDIO" in out.note
