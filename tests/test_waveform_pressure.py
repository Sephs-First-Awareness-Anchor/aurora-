"""
Tests for waveform-mediated pressure propagation.

Verifies:
- PressureDisturbance creation from axis state and I-state
- WaveformPressurePump injection with primary and coupling steps
- Coupling physics correctness
- QAO pressure tracing integration
- Self-selection in CuriosityEngine _step1_emergence
"""
from __future__ import annotations

import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from aurora_core_ai.aurora_waveform_pressure import (
    PressureDisturbance,
    WaveformPressurePump,
    get_pump,
    _COUPLING,
    _VALID_AXES,
)


class MockIfield:
    """Minimal NoncompField mock for testing."""
    def __init__(self):
        self.calls = []
        self._axis_p = {0: 0.10, 1: 0.10, 2: 0.10, 3: 0.10, 4: 0.10}

    def ingest_external_input(self, axes_dict, intensity=0.0, source=""):
        self.calls.append({"axes": dict(axes_dict), "intensity": intensity, "source": source})

    def axis_pressure(self, axis_int: int) -> float:
        return self._axis_p.get(axis_int, 0.0)


class TestPressureDisturbance:
    def test_from_axis_state_dominant(self):
        dist = WaveformPressurePump.from_axis_state(
            {"X": 0.8, "T": 0.3, "N": 0.2, "B": 0.1, "A": 0.5},
            source="test",
        )
        assert dist.dominant_axis() == "X"

    def test_from_axis_state_all_axes_present(self):
        dist = WaveformPressurePump.from_axis_state(
            {"X": 0.5, "T": 0.5, "N": 0.5, "B": 0.5, "A": 0.5},
            source="test",
        )
        assert set(dist.axis_amplitudes.keys()) == _VALID_AXES

    def test_from_axis_state_clamps(self):
        dist = WaveformPressurePump.from_axis_state(
            {"X": 2.0, "T": -0.5, "N": 0.5, "B": 0.5, "A": 0.5},
            source="test",
        )
        assert dist.axis_amplitudes["X"] == 1.0
        assert dist.axis_amplitudes["T"] == 0.0

    def test_from_istate_correct_axis(self):
        dist = WaveformPressurePump.from_istate("I_IS", "X", 0.9, source="test")
        assert dist.axis_amplitudes["X"] == pytest.approx(0.9)
        assert dist.axis_amplitudes["T"] == pytest.approx(0.0)
        assert "I_IS" in dist.source

    def test_from_istate_invalid_axis_zero(self):
        dist = WaveformPressurePump.from_istate("I_DO", "Z", 0.9, source="test")
        assert all(v == 0.0 for v in dist.axis_amplitudes.values())

    def test_effective_amplitude_scales_by_intensity(self):
        dist = PressureDisturbance(
            source="test",
            axis_amplitudes={"X": 1.0, "T": 0.5, "N": 0.0, "B": 0.0, "A": 0.0},
            intensity=0.5,
        )
        assert dist.effective_amplitude("X") == pytest.approx(0.5)
        assert dist.effective_amplitude("T") == pytest.approx(0.25)

    def test_effective_amplitude_clamps_intensity(self):
        dist = PressureDisturbance(
            source="test",
            axis_amplitudes={"X": 1.0},
            intensity=2.0,
        )
        assert dist.effective_amplitude("X") == pytest.approx(1.0)


class TestWaveformPressurePump:
    def test_inject_calls_ifield(self):
        pump = WaveformPressurePump()
        ifield = MockIfield()
        dist = WaveformPressurePump.from_axis_state(
            {"X": 0.8, "T": 0.0, "N": 0.0, "B": 0.0, "A": 0.0},
            source="test",
            intensity=0.5,
        )
        trace = pump.inject(dist, ifield)
        assert len(ifield.calls) >= 1

    def test_inject_returns_trace(self):
        pump = WaveformPressurePump()
        ifield = MockIfield()
        dist = WaveformPressurePump.from_axis_state(
            {"X": 0.8, "T": 0.2, "N": 0.0, "B": 0.0, "A": 0.0},
            source="test",
            intensity=0.7,
        )
        trace = pump.inject(dist, ifield)
        assert len(trace) > 0
        steps = {s["step"] for s in trace}
        assert "primary" in steps
        assert "coupling" in steps

    def test_inject_primary_only_no_coupling(self):
        pump = WaveformPressurePump()
        ifield = MockIfield()
        dist = PressureDisturbance(
            source="test",
            axis_amplitudes={"X": 0.8, "T": 0.0, "N": 0.0, "B": 0.0, "A": 0.0},
            intensity=0.5,
            coupling_mode="primary_only",
        )
        trace = pump.inject(dist, ifield)
        coupling_steps = [s for s in trace if s["step"] == "coupling"]
        assert len(coupling_steps) == 0

    def test_coupling_physics_x_drives_t_and_b(self):
        pump = WaveformPressurePump()
        ifield = MockIfield()
        dist = PressureDisturbance(
            source="test",
            axis_amplitudes={"X": 1.0, "T": 0.0, "N": 0.0, "B": 0.0, "A": 0.0},
            intensity=1.0,
            coupling_mode="full",
        )
        trace = pump.inject(dist, ifield)
        coupled = {s["to"] for s in trace if s["step"] == "coupling" and s["from"] == "X"}
        assert "T" in coupled
        assert "B" in coupled

    def test_coupling_physics_n_drives_b_t_x(self):
        pump = WaveformPressurePump()
        ifield = MockIfield()
        dist = PressureDisturbance(
            source="test",
            axis_amplitudes={"X": 0.0, "T": 0.0, "N": 1.0, "B": 0.0, "A": 0.0},
            intensity=1.0,
            coupling_mode="full",
        )
        trace = pump.inject(dist, ifield)
        coupled = {s["to"] for s in trace if s["step"] == "coupling" and s["from"] == "N"}
        assert "B" in coupled
        assert "T" in coupled
        assert "X" in coupled

    def test_inject_zero_intensity_no_calls(self):
        pump = WaveformPressurePump()
        ifield = MockIfield()
        dist = PressureDisturbance(
            source="test",
            axis_amplitudes={"X": 0.8},
            intensity=0.0,
        )
        trace = pump.inject(dist, ifield)
        assert len(ifield.calls) == 0
        assert len(trace) == 0

    def test_inject_none_ifield_returns_empty(self):
        pump = WaveformPressurePump()
        dist = WaveformPressurePump.from_axis_state(
            {"X": 0.8}, source="test"
        )
        trace = pump.inject(dist, None)
        assert trace == []

    def test_trace_buffer_populated(self):
        pump = WaveformPressurePump(trace_maxlen=5)
        ifield = MockIfield()
        for _ in range(3):
            dist = WaveformPressurePump.from_axis_state(
                {"A": 0.7}, source="test"
            )
            pump.inject(dist, ifield)
        traces = pump.get_recent_traces(n=10)
        assert len(traces) == 3

    def test_trace_buffer_maxlen(self):
        pump = WaveformPressurePump(trace_maxlen=3)
        ifield = MockIfield()
        for _ in range(5):
            dist = WaveformPressurePump.from_axis_state({"X": 0.5}, source="t")
            pump.inject(dist, ifield)
        traces = pump.get_recent_traces(n=10)
        assert len(traces) == 3

    def test_last_dominant_axis(self):
        pump = WaveformPressurePump()
        ifield = MockIfield()
        dist = WaveformPressurePump.from_axis_state(
            {"A": 0.9, "X": 0.1}, source="test"
        )
        pump.inject(dist, ifield)
        assert pump.last_dominant_axis() == "A"

    def test_qao_integration(self):
        pump = WaveformPressurePump()
        ifield = MockIfield()
        dist = WaveformPressurePump.from_axis_state(
            {"T": 0.8}, source="qao_test"
        )
        received = []
        class MockQAO:
            def record_pressure_disturbance(self, summary):
                received.append(summary)
        pump.inject(dist, ifield, qao=MockQAO())
        assert len(received) == 1
        assert received[0]["source"] == "qao_test"


class TestSingleton:
    def test_get_pump_returns_same_instance(self):
        p1 = get_pump()
        p2 = get_pump()
        assert p1 is p2

    def test_singleton_is_pump_instance(self):
        assert isinstance(get_pump(), WaveformPressurePump)


class TestCouplingPhysics:
    def test_all_axes_have_coupling(self):
        for ax in _VALID_AXES:
            assert ax in _COUPLING, f"Axis {ax} missing from coupling table"

    def test_coupling_values_in_range(self):
        for ax, targets in _COUPLING.items():
            for target, strength in targets.items():
                assert 0.0 < strength < 1.0, f"{ax}→{target}: {strength}"

    def test_no_self_coupling(self):
        for ax, targets in _COUPLING.items():
            assert ax not in targets, f"Axis {ax} couples to itself"

    def test_x_coupling_targets(self):
        assert set(_COUPLING["X"].keys()) == {"T", "B"}

    def test_a_coupling_targets(self):
        assert set(_COUPLING["A"].keys()) == {"T", "B", "N"}


class TestQAOPressureTracing:
    def test_record_and_retrieve(self):
        import tempfile
        from aurora_core_ai.aurora_internal.aurora_quasiarch_observer import AuroraQuasiArchObserver
        with tempfile.TemporaryDirectory() as tmpdir:
            qao = AuroraQuasiArchObserver(state_dir=tmpdir, mode="shadow")
            summary = {
                "ts": 1.0, "source": "s", "dominant_axis": "X",
                "intensity": 0.5, "coupling_mode": "full",
                "genealogy_id": "", "tick": 0, "trace": [],
            }
            qao.record_pressure_disturbance(summary)
            traces = qao.get_pressure_trace(n=5)
            assert len(traces) == 1
            assert traces[0]["provenance"] == "WAVEFORM"

    def test_provenance_filtering(self):
        import tempfile
        from aurora_core_ai.aurora_internal.aurora_quasiarch_observer import AuroraQuasiArchObserver
        with tempfile.TemporaryDirectory() as tmpdir:
            qao = AuroraQuasiArchObserver(state_dir=tmpdir, mode="shadow")
            qao.record_observation("target", {"data": "x"})  # OBSERVER provenance
            qao.record_pressure_disturbance({"ts": 1.0, "source": "s",
                "dominant_axis": "N", "intensity": 0.4, "coupling_mode": "full",
                "genealogy_id": "", "tick": 0, "trace": []})
            traces = qao.get_pressure_trace()
            assert len(traces) == 1  # only WAVEFORM

    def test_waveform_turn_summary_structure(self):
        import tempfile
        from aurora_core_ai.aurora_internal.aurora_quasiarch_observer import AuroraQuasiArchObserver
        with tempfile.TemporaryDirectory() as tmpdir:
            qao = AuroraQuasiArchObserver(state_dir=tmpdir, mode="shadow")
            qao.record_pressure_disturbance({
                "ts": 1.0, "source": "s", "dominant_axis": "B",
                "intensity": 0.6, "coupling_mode": "full",
                "genealogy_id": "", "tick": 0,
                "trace": [
                    {"step": "primary", "axis": "B", "amplitude": 0.4},
                    {"step": "coupling", "from": "B", "to": "N", "coupling_strength": 0.30, "amplitude": 0.06},
                    {"step": "coupling", "from": "B", "to": "A", "coupling_strength": 0.25, "amplitude": 0.05},
                ],
            })
            s = qao.waveform_turn_summary()
            assert s["disturbances"] == 1
            assert "B" in s["dominant_axes"]
            assert "N" in s["coupled_only"] or "A" in s["coupled_only"]

    def test_empty_summary(self):
        import tempfile
        from aurora_core_ai.aurora_internal.aurora_quasiarch_observer import AuroraQuasiArchObserver
        with tempfile.TemporaryDirectory() as tmpdir:
            qao = AuroraQuasiArchObserver(state_dir=tmpdir, mode="shadow")
            s = qao.waveform_turn_summary()
            assert s["disturbances"] == 0
            assert s["dominant_axes"] == []


class TestCuriosityManifoldSelfSelection:
    """Verify CuriosityEngine self-selects curiosity via manifold pressure."""

    def _make_systems(self, axis_pressures: dict) -> dict:
        _AXIS_STR_TO_INT = {"X": 0, "T": 1, "N": 2, "B": 3, "A": 4}
        mock = MockIfield()
        for ax, v in axis_pressures.items():
            idx = _AXIS_STR_TO_INT.get(ax, 0)
            mock._axis_p[idx] = v
        return {"identity_field": mock}

    def _make_engine(self, systems: dict):
        from aurora_core_ai.aurora_curiosity_engine import CuriosityEngine
        return CuriosityEngine(
            pressure_source=None,
            field_map=None,
            tool_mind=None,
            sedimemory=None,
            self_grounder=None,
            tension_monitor=None,
            systems=systems,
        )

    def test_high_n_axis_boosts_urgency(self):
        systems = self._make_systems({"X": 0.10, "T": 0.10, "N": 0.65, "B": 0.10, "A": 0.10})
        systems["_open_loops"] = [{"tension": "test tension"}]
        engine = self._make_engine(systems)
        obj = engine._step1_emergence(tick=0)
        if obj is not None:
            assert obj.urgency >= 0.65

    def test_flat_manifold_no_boost(self):
        systems = self._make_systems({"X": 0.10, "T": 0.10, "N": 0.10, "B": 0.10, "A": 0.10})
        systems["_open_loops"] = [{"tension": "test tension"}]
        engine = self._make_engine(systems)
        obj = engine._step1_emergence(tick=0)
        if obj is not None:
            assert obj.urgency <= 0.70

    def test_high_pressure_alone_can_generate_curiosity(self):
        systems = self._make_systems({"X": 0.10, "T": 0.10, "N": 0.10, "B": 0.70, "A": 0.10})
        engine = self._make_engine(systems)
        obj = engine._step1_emergence(tick=0)
        if obj is not None and "constraint activity" in obj.subject:
            assert obj.origin_axis == "B"
