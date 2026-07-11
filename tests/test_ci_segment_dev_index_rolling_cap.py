# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Regression test: scripts/aurora_ci_segment.py's dev_index_start/dev_index_end
reporting silently broke once developmental_timeline.jsonl reached its
rolling cap (aurora_developmental_log.py: _MAX_LINES = 2000, oldest lines
trimmed on every write).

The old logic counted lines before the run (dev_start = len(...)) and
sliced dev[dev_start:] afterward to find "this run's" entries. Once the
file is at the 2000-line cap, appending N new entries also trims N old
ones, so len(file) is identical before and after -- the slice lands past
the end of the list, dev_index_start/dev_index_end silently report None
forever. Confirmed happening for real: 6 consecutive scheduled runs
reported "dev_index None->None" once the timeline first filled up, even
though the underlying entries were completely healthy real growth.

_last_dev_index() reads the last line's value directly instead, which is
immune to the file's length being capped.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import aurora_ci_segment as seg


def _write_lines(path, dev_indices):
    with open(path, "w", encoding="utf-8") as f:
        for v in dev_indices:
            f.write(json.dumps({"dev_index": v}) + "\n")


def test_last_dev_index_empty_file_returns_none(tmp_path):
    path = str(tmp_path / "developmental_timeline.jsonl")
    assert seg._last_dev_index(path) is None


def test_last_dev_index_missing_file_returns_none(tmp_path):
    path = str(tmp_path / "does_not_exist.jsonl")
    assert seg._last_dev_index(path) is None


def test_last_dev_index_returns_most_recent_entry(tmp_path):
    path = str(tmp_path / "developmental_timeline.jsonl")
    _write_lines(path, [100.0, 150.0, 205.5])
    assert seg._last_dev_index(path) == 205.5


def test_dev_index_growth_detected_correctly_below_rolling_cap(tmp_path):
    path = str(tmp_path / "developmental_timeline.jsonl")
    _write_lines(path, [500.0, 510.0])
    before = seg._last_dev_index(path)

    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"dev_index": 540.0}) + "\n")
    after = seg._last_dev_index(path)

    assert before == 510.0
    assert after == 540.0


def test_dev_index_growth_still_detected_when_file_is_at_the_rolling_cap(tmp_path):
    """The exact real-world failure mode: file already at the 2000-line
    cap, a run appends new entries while the same number of old ones get
    trimmed off the front (aurora_developmental_log.py's own behavior),
    so total line count never changes across the run."""
    path = str(tmp_path / "developmental_timeline.jsonl")
    _write_lines(path, [1000.0 + i for i in range(2000)])
    before = seg._last_dev_index(path)

    # Simulate the rolling-cap trim: drop the oldest 30, append 30 new.
    with open(path) as f:
        kept = f.readlines()[30:]
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(kept)
        for i in range(30):
            f.write(json.dumps({"dev_index": 3000.0 + i}) + "\n")
    after = seg._last_dev_index(path)

    total_lines = sum(1 for _ in open(path))
    assert total_lines == 2000, "file must still be at the rolling cap for this test to be meaningful"
    assert before == 2999.0
    assert after == 3029.0
    assert after > before, "real growth must be detected even though the file's line count never changed"
