#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""test_learning_probe.py -- the weekly question set."""
from __future__ import annotations

import sys
import threading
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import aurora_learning_probe as P  # noqa: E402


class Clock:
    def __init__(self):
        self.t = 1_800_000_000.0

    def __call__(self):
        return self.t


def make(tmp_path, answers, clock=None, **kw):
    systems = {}
    replies = iter(answers)

    def turn(systems, text, **kwargs):
        assert kwargs["session_id"] == P.PROBE_SESSION and kwargs["record_exchange"] is False
        text_out, voice = next(replies)
        systems["_last_voice_gate"] = {"outcome": voice}
        return {"src": "x", "resp_A": SimpleNamespace(content=text_out)}

    return P.LearningProbe(systems, state_dir=str(tmp_path), process_turn=turn,
                           extract_reply=lambda r: r["resp_A"].content, clock=clock or Clock(), **kw)


def test_runs_all_questions_and_compares_weeks(tmp_path):
    clock = Clock()
    week1 = [("", "silence")] * 15 + [("I am rain.", "own_voice")] * 5
    week2 = [("", "silence")] * 10 + [("I am rain.", "own_voice")] * 10
    probe = make(tmp_path, week1 + week2, clock=clock)
    assert probe.due()
    first = probe.run_once()
    assert len(first["answers"]) == len(P.QUESTIONS) == 20
    assert not probe.due()
    clock.t += P.PROBE_INTERVAL_S
    assert probe.due()
    probe.run_once()
    summary = probe.summary()
    assert summary["runs"] == 2 and summary["latest_own_voice"] == 10
    assert summary["own_voice_delta"] == 5 and summary["silent_delta"] == -5
    assert summary["changed_vs_previous"] == 5


def test_never_runs_while_sunni_is_here_or_the_mind_is_busy(tmp_path):
    assert make(tmp_path, [], live_idle=lambda: False).run_once() is None
    lock = threading.Lock()
    lock.acquire()
    assert make(tmp_path, [], field_lock=lock).run_once() is None
