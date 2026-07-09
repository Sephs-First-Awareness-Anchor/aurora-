# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Regression test for a real state-loss bug found by tracing why dev_index
kept dropping back to a low floor across scheduled autonomous runs even
after the _deep_merge fix (see test_lineage_runtime_activation.py) landed.

aurora_ci_segment.py runs autonomy/curiosity/dream_substrate as concurrent
background threads that all touch the same shared ConstraintGenealogyLogger
instance (systems['genealogy']), and each can trigger flush_files(). The
writers (_write_abilities_file, _write_links_file, etc.) used a bare
`open(path, "w")` + `json.dump(...)`, which truncates the file the instant
it's opened. Two racing flush_files() calls -- or a single write torn by
process shutdown mid-dump on the ~20MB abilities.json -- could leave a
truncated/corrupt file on disk. _restore_genealogy_state() in
aurora_runtime.py silently swallows the resulting JSONDecodeError on the
next boot, so the corrupted file was indistinguishable from "no abilities
ever existed": the whole persisted lineage was lost and the next run
started back near its floor. Confirmed happening for real: commit
a91d0fd7 wrote an abilities.json that was valid JSON up to a point and
then cut off mid-object; the very next scheduled run's dev_index dropped
from 9879 down to 1844.

The fix routes every writer in constraint_genealogy.py through
aurora_persistence_utils.atomic_write_json(), which writes to a temp file
in the same directory and os.replace()s it into place under a process-wide
lock -- so a reader (or a racing writer) only ever sees the fully-old or
fully-new file, never a torn one.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aurora_internal.constraint_genealogy import ConstraintGenealogyLogger, AbilityProfile


def _make_logger(tmp_path):
    return ConstraintGenealogyLogger(run_id="test", output_dir=str(tmp_path))


def test_write_abilities_file_uses_atomic_replace_not_truncating_open(tmp_path, monkeypatch):
    """If a writer is killed mid-write, os.replace() guarantees the reader
    only ever sees the prior complete file or the new complete file -- never
    a half-written one. A bare open(path, "w") offers no such guarantee: it
    truncates to zero bytes immediately, so a kill mid-dump leaves a corrupt
    file. Simulate the "killed mid-write" case and assert the on-disk file
    from before the failed write is still fully intact and parseable."""
    logger = _make_logger(tmp_path)
    logger.abilities["A:1"] = AbilityProfile(id="A:1", axis="X", requires=("X",), cost={}, risk={}, effect_tags=(), notes="")
    logger._write_abilities_file()
    path = os.path.join(str(tmp_path), logger.cfg.ABILITIES_FILE)
    with open(path, "r", encoding="utf-8") as fh:
        good_snapshot = fh.read()
    good_data = json.loads(good_snapshot)
    assert good_data.get("A:1") == logger.abilities["A:1"].to_dict()

    # Simulate a write that fails partway through json.dump -- atomic_write_json
    # writes to a *.tmp sibling first, so this must never touch the real path.
    import aurora_internal.constraint_genealogy as cg_mod

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated interruption mid-write")

    monkeypatch.setattr(cg_mod.json, "dump", _boom)
    logger.abilities["A:2"] = AbilityProfile(id="A:2", axis="X", requires=("X",), cost={}, risk={}, effect_tags=(), notes="")
    logger._write_abilities_file()  # must not raise (writer methods are best-effort)

    with open(path, "r", encoding="utf-8") as fh:
        after_failed_write = fh.read()
    assert after_failed_write == good_snapshot, (
        "a failed write must leave the previously-committed file completely "
        "intact, not truncated -- otherwise the next boot silently restores "
        "nothing (json.load raises, _restore_genealogy_state swallows it)"
    )
    assert json.loads(after_failed_write) == good_data

    # No leftover temp files from the failed attempt.
    leftovers = [f for f in os.listdir(str(tmp_path)) if f.endswith(".tmp")]
    assert leftovers == []


def test_write_links_file_round_trips(tmp_path):
    logger = _make_logger(tmp_path)
    logger._write_links_file()
    path = os.path.join(str(tmp_path), logger.cfg.LINKS_FILE)
    assert os.path.exists(path)
    with open(path, "r", encoding="utf-8") as fh:
        assert json.load(fh) == {}


def test_write_tick_state_file_round_trips(tmp_path):
    logger = _make_logger(tmp_path)
    logger.tick_count = 42
    logger._last_promotion_tick = 7
    logger._write_tick_state_file()
    path = os.path.join(str(tmp_path), "tick_state.json")
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    assert data == {"tick_count": 42, "last_promotion_tick": 7}
