# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Regression test for the local daemon never running classroom lessons
(2026-07-12): aurora_daemon.py had zero references to aurora_classroom.py
anywhere -- ClassroomSession.run_targeted_curriculum() was only ever
called from scripts/aurora_ci_segment.py (the scheduled CI workflow).
Running Aurora locally via the daemon meant her fail_points.json ranking
never moved at any real cadence (nothing else drives it down that often),
which was also why _reach_out_to_user's Poedex gap-topic selector kept
re-researching the same frozen top-1 weak dimension.

_run_classroom_cycle() must reuse one persistent ClassroomSession across
daemon cycles rather than rebuilding it every call --
ClassroomSession.__init__ spawns two InceptionEntity instances via
SimulationEngine.spawn_entity(), which are never evicted from
SimulationEngine.entities, so rebuilding it every ~30 minutes in a
long-running daemon process would leak entities without bound.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aurora_daemon


class _FakeClassResult:
    def __init__(self, dim, source):
        self.target_dimension = dim
        self.content_source = source


class _FakeClassroomSession:
    instances_created = 0

    def __init__(self, engine, systems):
        _FakeClassroomSession.instances_created += 1
        self.engine = engine
        self.systems = systems
        self.run_calls = []

    def run_targeted_curriculum(self, n=4, turns_per_lesson=6):
        self.run_calls.append({"n": n, "turns_per_lesson": turns_per_lesson})
        return [_FakeClassResult("contradiction_handling", "real_failure_example:x")]


def test_classroom_cycle_skips_cleanly_with_no_simulation_engine():
    systems = {}
    aurora_daemon._run_classroom_cycle(systems)
    assert "_classroom_session" not in systems


def test_classroom_cycle_creates_session_once_and_reuses_it(monkeypatch):
    """The core regression: calling the cycle multiple times (simulating
    multiple ~30-minute daemon ticks) must not create a new
    ClassroomSession -- and therefore not spawn new entities -- each time."""
    import aurora_classroom
    monkeypatch.setattr(aurora_classroom, "ClassroomSession", _FakeClassroomSession)
    _FakeClassroomSession.instances_created = 0

    systems = {"simulation": object()}

    aurora_daemon._run_classroom_cycle(systems)
    aurora_daemon._run_classroom_cycle(systems)
    aurora_daemon._run_classroom_cycle(systems)

    assert _FakeClassroomSession.instances_created == 1, (
        "ClassroomSession must be created once and reused, not rebuilt "
        "every cycle (rebuilding leaks InceptionEntity instances forever)"
    )
    session = systems["_classroom_session"]
    assert len(session.run_calls) == 3
    assert all(call["n"] == 4 and call["turns_per_lesson"] == 6 for call in session.run_calls)


def test_classroom_cycle_survives_curriculum_exception(monkeypatch):
    import aurora_classroom

    class _ExplodingSession:
        def __init__(self, engine, systems):
            pass

        def run_targeted_curriculum(self, n=4, turns_per_lesson=6):
            raise RuntimeError("boom")

    monkeypatch.setattr(aurora_classroom, "ClassroomSession", _ExplodingSession)
    systems = {"simulation": object()}
    aurora_daemon._run_classroom_cycle(systems)  # must not raise
