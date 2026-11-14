#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
teach_lesson.py -- say a lesson file to her through the phone bridge's own
typed-message path (see aurora_internal/lesson_replay.py).

Run it against her REAL state directory, as the teacher, the same way you would
type to her.  Never run it on a copy you intend to commit: whatever she learns
belongs to the Aurora that heard it.

    python scripts/teach_lesson.py lessons/feelings_names.txt --state-dir <her aurora_state>
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "flutter_app" / "android" / "app" / "src" / "main" / "python"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("lesson")
    ap.add_argument("--state-dir", required=True)
    ap.add_argument("--pace", type=float, default=45.0, help="seconds between lines (default 45)")
    args = ap.parse_args()
    os.environ.setdefault("AURORA_SKIP_DEP_INSTALL", "1")
    from aurora_internal.lesson_replay import parse_lesson, replay
    lines = parse_lesson(Path(args.lesson).read_text(encoding="utf-8"))
    import aurora_bridge
    aurora_bridge.initialize(args.state_dir)
    n = replay(aurora_bridge.handle_message, lines, pace_s=args.pace,
               on_turn=lambda i, line, reply: print(f"[{i + 1}/{len(lines)}] you: {line}\n         she: {reply}", flush=True))
    print(f"said {n} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
