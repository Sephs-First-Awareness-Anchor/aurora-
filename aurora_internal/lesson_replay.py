# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
lesson_replay.py -- teach her by saying it, not by placing it.

A lesson is plain text: what the teacher says to her, one utterance per line.
Replaying it is the same as the teacher typing it: every line goes through the
function a typed message goes through (the phone bridge's handle_message), with
no extra arguments, no marker, no special source, and real time between lines.
Whatever learning touches -- her relations, concepts, affect, memory, genealogy,
grammar, pressure -- is touched because a live turn touched it.  Nothing is
written into her state by this module, and nothing in her state records that a
lesson file existed.

Used by scripts/teach_lesson.py (laptop) and aurora_bridge.teach_lesson (phone).
"""
from __future__ import annotations

import time
from typing import Callable, List, Optional

DEFAULT_PACE_S = 45.0


def parse_lesson(text: str) -> List[str]:
    """One utterance per non-empty line; lines starting with '#' are the
    teacher's notes to themselves and are never said."""
    lines: List[str] = []
    for raw in str(text or "").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            lines.append(line)
    return lines


def replay(say: Callable[[str], object], lines: List[str], *, pace_s: float = DEFAULT_PACE_S,
           sleep: Callable[[float], None] = time.sleep,
           on_turn: Optional[Callable[[int, str, object], None]] = None) -> int:
    """Say each line through `say` (the typed-message function), waiting pace_s
    after each reply so time passes between turns as it does in a conversation.
    Returns how many lines were said."""
    said = 0
    for index, line in enumerate(lines):
        reply = say(line)
        said += 1
        if on_turn is not None:
            on_turn(index, line, reply)
        if index < len(lines) - 1 and pace_s > 0:
            sleep(pace_s)
    return said
