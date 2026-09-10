# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA DIRECTIVE -- Causal-Generation Correction, Phase 4 regression suite
(continued). Two more confirmed real-concurrency hazards, found by
extending the same investigation that produced test_causal_generation_
daemon_concurrency.py: aurora_surface_daemon.py's own in-process threads
(camera capture vs. voice-triggered "what do you see?") and aurora_
working_memory.py's WorkingMemory.stated_facts (shared across the main
turn thread, aurora_daemon.py's ambient-overhearing thread, and its
voice-session thread), plus a third hazard spanning ~15 call sites in
aurora_daemon.py for aurora_room_notes.json/aurora_room_activity.json
(the room-operator thread vs. a dozen main-thread writers).

As with the first daemon-concurrency file, these tests use REAL
threading.Thread -- this hazard shape only manifests under actual
concurrent execution, not shuffled call order.
"""
import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

# aurora_hardware_io must be imported BEFORE aurora_daemon: aurora_
# internal/aurora_ability_lineage_compiler.py (reachable from aurora_
# daemon's own import chain) does os.environ.setdefault(
# "AURORA_SKIP_HARDWARE_IMPORTS", "1") at module scope, which -- once
# set -- makes aurora_hardware_io skip `import cv2` for the rest of the
# process. Importing it first here means its cv2 binding is already
# established before that setdefault() can ever run.
import aurora_hardware_io  # noqa: E402,F401

import aurora_daemon as D  # noqa: E402
from aurora_working_memory import WorkingMemory  # noqa: E402


# ============================================================================
# WorkingMemory.stated_facts: RLock around note_user_facts()'s critical section
# ============================================================================

def test_note_user_facts_concurrent_calls_are_mutually_exclusive():
    """Spies on _note_user_facts_locked (the RLock-protected tail of
    note_user_facts()) to record each call's [start, end) interval under
    an artificially widened window. If the lock is doing its job, no two
    intervals overlap -- proving true mutual exclusion, not just "the
    test happened to pass this run."""
    wm = WorkingMemory()
    intervals = []
    real_locked = wm._note_user_facts_locked

    def spy(*args, **kwargs):
        start = time.time()
        time.sleep(0.05)
        result = real_locked(*args, **kwargs)
        intervals.append((start, time.time()))
        return result

    wm._note_user_facts_locked = spy
    try:
        topics = ["alpha", "beta", "gamma", "delta", "epsilon"]
        threads = [
            threading.Thread(target=wm.note_user_facts, args=(f"{t} is great",))
            for t in topics
        ]
        for th in threads:
            th.start()
        for th in threads:
            th.join()
    finally:
        wm._note_user_facts_locked = real_locked

    assert len(intervals) == 5
    intervals.sort()
    overlapping = any(
        intervals[i][1] > intervals[i + 1][0] for i in range(len(intervals) - 1)
    )
    assert not overlapping, (
        "concurrent note_user_facts() calls overlapped -- "
        "_stated_facts_lock is not providing mutual exclusion"
    )


def test_note_user_facts_concurrent_calls_lose_no_updates():
    """The actual consequence of the race this fix closes: every distinct
    topic asserted by a concurrent thread must survive into stated_facts,
    not just some of them (a lost-update race would silently drop a
    concurrent thread's topic, or its own dict, when a check-then-create
    on self.stated_facts[topic] interleaves between two threads)."""
    wm = WorkingMemory()
    topics = [f"topic{c}" for c in "abcdefghij"]  # letters only -- the
    # "X is Y" regex requires [a-zA-Z]+ for the subject, digits don't match

    threads = [
        threading.Thread(target=wm.note_user_facts, args=(f"{t} is great",))
        for t in topics
    ]
    for th in threads:
        th.start()
    for th in threads:
        th.join()

    missing = [t for t in topics if t not in wm.stated_facts]
    assert not missing, f"lost updates for topics: {missing}"


def test_note_user_facts_recursive_call_does_not_deadlock():
    """_stated_facts_lock is an RLock specifically because
    note_user_facts() recurses into itself for "X said Y"-shaped text
    (the reported_match branch). A plain Lock here would deadlock the
    first time that branch fired."""
    wm = WorkingMemory()

    def call():
        wm.note_user_facts("my friend said cats are wonderful")

    t = threading.Thread(target=call)
    t.start()
    t.join(timeout=5)
    assert not t.is_alive(), "note_user_facts() deadlocked on its own recursive call"


# ============================================================================
# aurora_room_notes.json / aurora_room_activity.json: shared, locked writers
# ============================================================================

def test_room_note_and_activity_writers_are_mutually_exclusive():
    """Spies on Path.write_text to record every write's [start, end)
    interval across a mix of concurrent _append_room_note()/
    _append_room_activity() calls (both funnel through the same
    _ROOM_FILES_LOCK). No two writes may overlap."""
    tmpdir = tempfile.mkdtemp()
    original_state_dir = D._STATE_DIR
    D._STATE_DIR = Path(tmpdir)

    intervals = []
    real_write_text = Path.write_text

    def spy_write_text(self, data, *args, **kwargs):
        start = time.time()
        time.sleep(0.05)
        result = real_write_text(self, data, *args, **kwargs)
        intervals.append((start, time.time()))
        return result

    Path.write_text = spy_write_text
    try:
        threads = []
        for i in range(3):
            threads.append(threading.Thread(
                target=D._append_room_note, args=(f"note {i}",)))
            threads.append(threading.Thread(
                target=D._append_room_activity, args=(f"action {i}", f"detail {i}")))
        for th in threads:
            th.start()
        for th in threads:
            th.join()
    finally:
        Path.write_text = real_write_text
        D._STATE_DIR = original_state_dir

    assert len(intervals) == 6
    intervals.sort()
    overlapping = any(
        intervals[i][1] > intervals[i + 1][0] for i in range(len(intervals) - 1)
    )
    assert not overlapping, (
        "concurrent room-note/activity writes overlapped -- "
        "_ROOM_FILES_LOCK is not providing mutual exclusion"
    )


def test_room_note_and_activity_writers_lose_no_updates():
    tmpdir = tempfile.mkdtemp()
    original_state_dir = D._STATE_DIR
    D._STATE_DIR = Path(tmpdir)

    try:
        threads = []
        for i in range(4):
            threads.append(threading.Thread(
                target=D._append_room_note, args=(f"note {i}",)))
            threads.append(threading.Thread(
                target=D._append_room_activity, args=(f"action {i}", f"detail {i}")))
        for th in threads:
            th.start()
        for th in threads:
            th.join()

        notes = json.loads((D._STATE_DIR / "aurora_room_notes.json").read_text())
        activity = json.loads((D._STATE_DIR / "aurora_room_activity.json").read_text())
    finally:
        D._STATE_DIR = original_state_dir

    note_contents = {n["content"] for n in notes}
    activity_actions = {a["action"] for a in activity}
    assert note_contents == {f"note {i}" for i in range(4)}
    assert activity_actions == {f"action {i}" for i in range(4)}


def test_room_operator_thread_local_functions_delegate_to_shared_writers():
    """_room_operator_thread()'s local _append_note()/_log_activity()
    (called by _do_boot_tour/_do_post_study_visit/_do_idle_scan) must
    route through the same _ROOM_FILES_LOCK as every other writer --
    verified by checking they now call the module-level shared helpers
    rather than doing their own unlocked file I/O."""
    import inspect
    # These are locally-defined closures inside _room_operator_thread, not
    # independently importable -- assert indirectly via source inspection
    # that the function body calls the shared helpers.
    source = inspect.getsource(D)
    # The two nested defs should each be a one-line delegation now.
    assert "_append_room_note(content=content, note_type=note_type, source=source)" in source
    assert "_append_room_activity(action=action, detail=detail, category=\"operator\")" in source


# ============================================================================
# aurora_hardware_io.py camera snapshot: locked + atomic tmp-then-replace
# ============================================================================

def test_camera_snapshot_writes_are_mutually_exclusive():
    """Real reproduction against SensoryIntegrationEngine._save_camera_
    snapshot(): confirmed live during development that the pre-fix
    unlocked glob-delete-then-cv2.imwrite pattern let concurrent see()
    calls interleave; this test proves the fixed version doesn't."""
    import numpy as np
    import aurora_hardware_io as HW

    tmpdir = tempfile.mkdtemp()
    engine = HW.SensoryIntegrationEngine(state_dir=tmpdir)

    class _FakeCamera:
        last_frame = np.zeros((10, 10, 3), dtype="uint8")

    class _FakeHardware:
        camera = _FakeCamera()

    engine.hardware = _FakeHardware()

    intervals = []
    real_imwrite = HW.cv2.imwrite

    def spy_imwrite(path, frame, *args, **kwargs):
        start = time.time()
        time.sleep(0.05)
        result = real_imwrite(path, frame, *args, **kwargs)
        intervals.append((start, time.time(), path))
        return result

    HW.cv2.imwrite = spy_imwrite
    try:
        threads = [threading.Thread(target=engine._save_camera_snapshot)
                   for _ in range(4)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()
    finally:
        HW.cv2.imwrite = real_imwrite

    assert len(intervals) == 8  # 4 threads x 2 files (sight_latest.jpg, frame_latest.png)
    by_target = {}
    for start, end, path in intervals:
        key = "jpg" if path.endswith(".jpg") else "png"
        by_target.setdefault(key, []).append((start, end))
    for key, ivs in by_target.items():
        ivs.sort()
        overlapping = any(ivs[i][1] > ivs[i + 1][0] for i in range(len(ivs) - 1))
        assert not overlapping, f"concurrent {key} snapshot writes overlapped"


def test_camera_snapshot_leaves_no_tmp_files_and_produces_a_valid_image():
    import numpy as np
    import aurora_hardware_io as HW

    tmpdir = tempfile.mkdtemp()
    engine = HW.SensoryIntegrationEngine(state_dir=tmpdir)

    class _FakeCamera:
        last_frame = np.zeros((10, 10, 3), dtype="uint8")

    class _FakeHardware:
        camera = _FakeCamera()

    engine.hardware = _FakeHardware()

    threads = [threading.Thread(target=engine._save_camera_snapshot)
               for _ in range(4)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()

    leftover_tmp = list(Path(tmpdir).rglob("*.tmp*"))
    assert not leftover_tmp, f"leftover tmp files after concurrent writes: {leftover_tmp}"

    final = engine._vision_snapshot_dir / "sight_latest.jpg"
    img = HW.cv2.imread(str(final))
    assert img is not None, "final sight_latest.jpg is missing or unreadable (torn write?)"
    assert img.shape == (10, 10, 3)
