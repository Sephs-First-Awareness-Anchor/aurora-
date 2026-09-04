"""Regression tests for wiring DreamTrainer._record_fail_dimension() to the
live genealogy object (aurora_dream_trainer.py) -- "the dream trainer
rewiring through apply_targeted_pressure()" Sunni flagged as outstanding.

apply_targeted_pressure()/get_pressure_recommendations() (aurora_internal/
constraint_genealogy.py) is a real, complete, closed-loop pressure
mechanism that _record_fail_dimension already called -- but the genealogy
object it needed was resolved via a broken fallback chain
(self._systems["simulation"]._chamber/.chamber._genealogy) that always
returned None on a real boot, since SimulationEngine never carries a
_chamber/chamber attribute. The real, live genealogy instance was sitting
one dict lookup away the whole time, in the same self._systems reference
(boot_aurora assigns self._systems = systems by direct reference, and
systems["genealogy"] is the canonical live instance every other consumer
in the codebase already reads).

_record_fail_dimension now reads self._systems.get("genealogy") directly,
with self._genealogy_ref still taking priority when set. No change to
apply_targeted_pressure's own logic, get_pressure_recommendations'
scoring, or _check_pending_outcomes' outcome tracking.
"""
from __future__ import annotations

import os
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from aurora_dream_trainer import DreamTrainer


def _fresh_trainer():
    return DreamTrainer(state_dir=tempfile.mkdtemp(prefix="aurora_dream_trainer_wiring_"))


class _FakeGenealogy:
    """Lightweight stand-in exposing exactly the two methods
    _record_fail_dimension calls, recording whether each was reached."""

    def __init__(self, recs=None):
        self._recs = recs if recs is not None else []
        self.get_pressure_recommendations_calls = []
        self.apply_targeted_pressure_calls = []
        self.inject_training_plateau_pressure_calls = []

    def get_pressure_recommendations(self, fail_dims, top_n=1):
        self.get_pressure_recommendations_calls.append((fail_dims, top_n))
        return self._recs

    def apply_targeted_pressure(self, axis, env_key, magnitude, source=""):
        self.apply_targeted_pressure_calls.append((axis, env_key, magnitude, source))

    def inject_training_plateau_pressure(self, magnitude, axis_hint=""):
        self.inject_training_plateau_pressure_calls.append((magnitude, axis_hint))


def test_record_fail_dimension_reaches_genealogy_via_systems_dict():
    """Direct proof of the fix: with no _genealogy_ref set, a genealogy
    object reachable only via self._systems["genealogy"] is found and
    apply_targeted_pressure is called on it when a recommendation exists."""
    trainer = _fresh_trainer()
    fake = _FakeGenealogy(recs=[{
        "env_key": "test_env", "axis": "T",
        "recommended_magnitude": 0.4, "effectiveness": 0.6,
    }])
    trainer._systems = {"genealogy": fake}

    trainer._record_fail_dimension("coherence_maintenance", 0.7)

    assert fake.get_pressure_recommendations_calls, "genealogy was never reached"
    assert fake.apply_targeted_pressure_calls, "apply_targeted_pressure was never called"
    axis, env_key, magnitude, source = fake.apply_targeted_pressure_calls[0]
    assert env_key == "test_env"
    assert source == "coherence_maintenance_fail"


def test_record_fail_dimension_falls_back_to_plateau_injection_with_no_recs():
    """When get_pressure_recommendations returns nothing (e.g. no
    environment history yet -- the realistic state right after a fresh
    boot), the plateau-injection fallback must still be reached through
    the same systems-dict resolution."""
    trainer = _fresh_trainer()
    fake = _FakeGenealogy(recs=[])
    trainer._systems = {"genealogy": fake}

    trainer._record_fail_dimension("semantic_precision", 0.5)

    assert fake.get_pressure_recommendations_calls
    assert not fake.apply_targeted_pressure_calls
    assert fake.inject_training_plateau_pressure_calls, "plateau fallback was never reached"


def test_genealogy_ref_takes_priority_over_systems_dict():
    """A directly-set _genealogy_ref (e.g. a future caller that wires it
    explicitly) must still win over the systems-dict fallback."""
    trainer = _fresh_trainer()
    direct = _FakeGenealogy(recs=[{
        "env_key": "direct_env", "axis": "X",
        "recommended_magnitude": 0.3, "effectiveness": 0.5,
    }])
    via_systems = _FakeGenealogy(recs=[{
        "env_key": "systems_env", "axis": "X",
        "recommended_magnitude": 0.3, "effectiveness": 0.5,
    }])
    trainer._genealogy_ref = direct
    trainer._systems = {"genealogy": via_systems}

    trainer._record_fail_dimension("uncertainty_signaling", 0.6)

    assert direct.apply_targeted_pressure_calls
    assert not via_systems.get_pressure_recommendations_calls


def test_missing_systems_or_genealogy_key_degrades_silently():
    """No self._systems, or a systems dict with no 'genealogy' key, must
    not raise -- the whole block stays inside the existing try/except and
    simply does nothing, same as today's silent no-op behavior."""
    trainer = _fresh_trainer()
    trainer._systems = None
    trainer._record_fail_dimension("boundary_calibration", 0.5)  # must not raise

    trainer._systems = {}
    trainer._record_fail_dimension("boundary_calibration", 0.5)  # must not raise


def test_real_boot_dream_trainer_reaches_the_live_genealogy_object():
    """Real-boot integration test: boot Aurora for real, then call
    _record_fail_dimension directly on the live systems["dream_trainer"]
    and confirm the live systems["genealogy"] object is actually reached
    -- not just that no exception was raised. Spies on both
    apply_targeted_pressure and inject_training_plateau_pressure (either
    is proof of reachability; which one fires depends on whether this
    fresh genealogy already has environment/axis relief history)."""
    import shutil
    import aurora

    scratch = tempfile.mkdtemp(prefix="aurora_dream_trainer_wiring_realboot_")
    shutil.copytree(os.path.join(REPO_ROOT, "aurora_state"), os.path.join(scratch, "aurora_state"))
    systems = aurora.boot_aurora(state_dir=os.path.join(scratch, "aurora_state"), verbose=False)

    dream_trainer = systems.get("dream_trainer")
    genealogy = systems.get("genealogy")
    assert dream_trainer is not None, "real boot must produce a live dream_trainer instance"
    assert genealogy is not None, "real boot must produce a live genealogy instance"
    assert dream_trainer._systems is systems

    reached = {"apply_targeted_pressure": False, "inject_training_plateau_pressure": False}
    real_apply = genealogy.apply_targeted_pressure
    real_inject = genealogy.inject_training_plateau_pressure

    def _spy_apply(*args, **kwargs):
        reached["apply_targeted_pressure"] = True
        return real_apply(*args, **kwargs)

    def _spy_inject(*args, **kwargs):
        reached["inject_training_plateau_pressure"] = True
        return real_inject(*args, **kwargs)

    genealogy.apply_targeted_pressure = _spy_apply
    genealogy.inject_training_plateau_pressure = _spy_inject
    try:
        dream_trainer._record_fail_dimension("coherence_maintenance", 0.8)
    finally:
        genealogy.apply_targeted_pressure = real_apply
        genealogy.inject_training_plateau_pressure = real_inject

    assert any(reached.values()), (
        "neither apply_targeted_pressure nor inject_training_plateau_pressure "
        "was reached -- genealogy resolution is still broken"
    )
