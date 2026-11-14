#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""A lesson is said, not placed: the typed-message function gets exactly the line."""
from aurora_internal.lesson_replay import parse_lesson, replay


def test_notes_and_blanks_are_never_said():
    assert parse_lesson("# note\n\n You feel calm. \n#x\nYou are safe.\n") == ["You feel calm.", "You are safe."]


def test_each_line_goes_through_the_typed_message_function_unchanged_with_time_between():
    said, waits = [], []
    n = replay(lambda text: said.append(text) or "reply", ["a b", "c d", "e f"], pace_s=7, sleep=waits.append)
    assert n == 3 and said == ["a b", "c d", "e f"] and waits == [7, 7]


def test_no_wait_after_the_last_line_and_callback_sees_replies():
    seen = []
    replay(lambda t: t.upper(), ["x y"], pace_s=5, sleep=lambda s: seen.append(("slept", s)),
           on_turn=lambda i, line, reply: seen.append((i, line, reply)))
    assert seen == [(0, "x y", "X Y")]
