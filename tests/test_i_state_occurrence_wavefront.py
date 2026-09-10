# Authors: Sunni (Sir) Morningstar & Ceph
"""Regression coverage for the I-State observe -> commit occurrence barrier.

The collective's ten beings are co-equal reactions to one admitted occurrence.
They may eventually be scheduled with wider execution capacity, but they must
all observe the same frozen lattice state before any sibling stimulus is
committed. These tests pin that semantic boundary independently of scheduler
choice.
"""
from __future__ import annotations

from types import MethodType

import pytest

from foundational_contract import FoundationalContract, ExistencePredicate
from aurora_ivm import IVMLattice, IVMEnvelope
from aurora_i_state_beings import IStateCollective


_AGENTIC_EVIDENCE = {
    "has_temporality": True,
    "conserves_state": True,
    "has_identity": True,
    "initiates_change": True,
}


def _collective_and_envelope():
    contract = FoundationalContract()
    lattice = IVMLattice(contract, max_nodes=10000)
    collective = IStateCollective(contract, lattice)
    node = lattice.admit(
        payload="one admitted occurrence",
        payload_type="test",
        evidence=dict(_AGENTIC_EVIDENCE),
    )
    return collective, lattice, IVMEnvelope.from_node(node)


def _set_deterministic_axis_state(lattice):
    phases = {
        "existence": 0.23,
        "temporal": 0.91,
        "energy": 1.47,
        "boundary": 2.08,
        "agency": 2.71,
    }
    for name, phase in phases.items():
        axis = lattice.vertices.axes[name]
        axis.phase = phase
        axis.angular_velocity = 0.0
        axis.energy = 1.0
        axis.t_energy_spent = 0.0
    return phases


def _prime_being_state(collective):
    # Four samples means the occurrence under test is exactly the sample which
    # crosses _update_coherence()'s five-observation threshold.
    for being in collective.beings.values():
        being.resonance_history.extend((0.18, 0.42, 0.67, 0.31))
        being.coherence = 0.73


def test_observation_is_side_effect_free():
    collective, lattice, envelope = _collective_and_envelope()
    _set_deterministic_axis_state(lattice)
    being = collective.beings["I_IS"]

    before_being = (
        being.generation,
        being.total_processed,
        being.total_silent,
        tuple(being.resonance_history),
        being.coherence,
    )
    before_axes = {
        name: (axis.phase, axis.angular_velocity, axis.energy, axis.t_energy_spent)
        for name, axis in lattice.vertices.axes.items()
    }

    observation = being.observe(envelope)

    after_being = (
        being.generation,
        being.total_processed,
        being.total_silent,
        tuple(being.resonance_history),
        being.coherence,
    )
    after_axes = {
        name: (axis.phase, axis.angular_velocity, axis.energy, axis.t_energy_spent)
        for name, axis in lattice.vertices.axes.items()
    }

    assert observation.silent is False
    assert observation.resonance > 0.0
    assert before_being == after_being
    assert before_axes == after_axes


def test_collective_observes_every_being_before_first_stimulus_commit():
    collective, lattice, envelope = _collective_and_envelope()
    _set_deterministic_axis_state(lattice)
    events = []

    for predicate, being in collective.beings.items():
        original = being.observe

        def wrapped(self, env, *, axis_snapshot=None, _original=original, _predicate=predicate):
            events.append(("observe", _predicate))
            return _original(env, axis_snapshot=axis_snapshot)

        being.observe = MethodType(wrapped, being)

    original_inject = lattice.vertices.inject_stimulus

    def inject_spy(predicate, strength=0.5, level=None):
        events.append(("inject", predicate))
        if level is None:
            return original_inject(predicate, strength)
        return original_inject(predicate, strength, level=level)

    lattice.vertices.inject_stimulus = inject_spy
    result = collective.process(envelope)

    first_inject = next(i for i, event in enumerate(events) if event[0] == "inject")
    assert first_inject == len(collective.beings)
    assert all(kind == "observe" for kind, _ in events[:first_inject])
    assert sum(1 for kind, _ in events if kind == "inject") == result.active_count


def test_frozen_lattice_view_survives_commit_time_phase_mutation():
    collective, lattice, envelope = _collective_and_envelope()
    phases = _set_deterministic_axis_state(lattice)
    original_inject = lattice.vertices.inject_stimulus

    def hostile_inject(predicate, strength=0.5, level=None):
        # Exaggerate exactly the bleed a same-generation barrier must prevent:
        # if a later sibling were still observing live lattice state, it would
        # see this artificial phase movement from an earlier sibling.
        axis_name = ExistencePredicate.axis_for(predicate)
        lattice.vertices.axes[axis_name].phase += 0.77
        if level is None:
            return original_inject(predicate, strength)
        return original_inject(predicate, strength, level=level)

    lattice.vertices.inject_stimulus = hostile_inject
    result = collective.process(envelope)

    for predicate, response in result.responses.items():
        being = collective.beings[predicate]
        assert response.interpretation["axis_phase"] == round(phases[being.axis], 4)


def test_wavefront_matches_legacy_immediate_path_under_current_ivm_physics():
    wavefront, lattice_w, envelope_w = _collective_and_envelope()
    legacy, lattice_l, envelope_l = _collective_and_envelope()
    _set_deterministic_axis_state(lattice_w)
    _set_deterministic_axis_state(lattice_l)
    _prime_being_state(wavefront)
    _prime_being_state(legacy)

    # Legacy reference: IStateBeing.process() retains the original single-being
    # contract, including immediate stimulus application. The new collective
    # path must remain numerically equivalent while moving the shared-lattice
    # writes behind the occurrence barrier.
    legacy_responses = {
        predicate: being.process(envelope_l)
        for predicate, being in legacy.beings.items()
    }
    result = wavefront.process(envelope_w)

    for predicate, expected in legacy_responses.items():
        actual = result.responses[predicate]
        assert actual.silent == expected.silent
        assert actual.active == expected.active
        assert actual.resonance == pytest.approx(expected.resonance)
        assert actual.constraint_displacement == pytest.approx(expected.constraint_displacement)
        assert actual.interpretation == expected.interpretation

        b_actual = wavefront.beings[predicate]
        b_expected = legacy.beings[predicate]
        assert b_actual.generation == b_expected.generation
        assert b_actual.total_processed == b_expected.total_processed
        assert b_actual.total_silent == b_expected.total_silent
        assert tuple(b_actual.resonance_history) == tuple(b_expected.resonance_history)
        assert b_actual.coherence == pytest.approx(b_expected.coherence)

    for axis_name in lattice_w.vertices.axes:
        actual_axis = lattice_w.vertices.axes[axis_name]
        expected_axis = lattice_l.vertices.axes[axis_name]
        assert actual_axis.phase == pytest.approx(expected_axis.phase)
        assert actual_axis.angular_velocity == pytest.approx(expected_axis.angular_velocity)
        assert actual_axis.energy == pytest.approx(expected_axis.energy)
        assert actual_axis.t_energy_spent == pytest.approx(expected_axis.t_energy_spent)
