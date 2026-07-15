# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
tests/test_strategic_horizon.py
===================================
Phase 1 of the ICC Landing / Strategic Horizon / Operator Composition
directive (2026-07-14): aurora_internal/aurora_strategic_horizon.py.

Deferred-Relief Tolerance: the one capability the audit confirmed
absent -- choosing a worse immediate state for a better long-term one.
Like MoralWeightLedger, this layer never tells the system what to do;
it carves a landscape where deferred-relief paths cost slightly less to
walk, gated on three conditions that must ALL hold.
"""
import json

from foundational_contract import ExistenceMode
from aurora_internal.aurora_constraint_manifold_patched import Constraint
from aurora_internal.aurora_energy_layer_costs import make_accountant, MagnitudeShiftRequest
from aurora_internal.aurora_entropy_detector import SaturationLevel, SaturationSignal
from aurora_internal.aurora_icc_ledger import ICCLedger
from aurora_internal.aurora_strategic_horizon import (
    StrategicHorizonLayer,
    T_MAX,
    make_strategic_horizon_layer,
    verify_strategic_horizon,
)
from aurora_internal.aurora_variant_promotion import MoralWeightLedger, VariantRecord, _MORAL_WEIGHT_MAX
from aurora_internal.aurora_worth_evaluator import WorthReport, make_worth_evaluator


def _sig(level=SaturationLevel.NOMINAL, projected_critical_tick=None, shallow_headroom=True):
    return SaturationSignal(
        level=level, tick=10, pressure_rising=False, fastest_rising_constraint=None,
        projected_critical_tick=projected_critical_tick,
        shallow_headroom_available=shallow_headroom, ticks_above_warn=0,
    )


def _rising_intake(intake_id="intake_A", rng_seed=7):
    """Drive a real CrossScaleWorthEvaluator to a horizon crossing, then
    force a clean RISING trajectory (8 values = full maxlen, evicts the
    noisy real sample so the direction is unambiguous -- same pattern
    used in test_icc_ledger.py's own gate tests)."""
    ev = make_worth_evaluator(rng_seed=rng_seed)
    acc = make_accountant(initial_pool=50000.0)
    acc.tick()
    for c in (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A):
        acc.apply_shift(MagnitudeShiftRequest(c, 1.0, "bal"))
    crossing_report = None
    score = 0.0
    for t in range(1, 20):
        score, report = ev.evaluate(intake_id, ExistenceMode.BOUNDED, acc, t)
        if report.horizon is not None:
            crossing_report = report
            break
    assert crossing_report is not None
    hist = ev.history_for(intake_id)
    for v in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]:
        hist.record(v)
    assert hist.trajectory.value == "rising"
    return ev, crossing_report, score


def _driven_icc_ledger(tmp_path, n=10, minted=0.5):
    ledger = ICCLedger(state_dir=str(tmp_path))
    for i in range(n):
        ledger.mint_from_contradiction_resolution(tick=i, contradiction_id=f"c{i}", minted=minted)
    return ledger


def _registered_moral_ledger():
    ledger = MoralWeightLedger()
    variant = VariantRecord(
        variant_id="V:test", source_solid_id="solid:test", intake_id="intake:test",
        depth_reached=ExistenceMode.BOUNDED, promoted_tick=1, recurrence_count=6,
        context_variety=2, polarity_coherence_rate=0.8, constraint_signature="XTNBA",
        deepest_constraint=Constraint.B, moral_weight=0.02, cost_reduction_factor=0.1,
    )
    ledger.register(variant)
    return ledger


# ---- built-in self-verification ----

def test_builtin_self_verification_all_pass(tmp_path):
    results = verify_strategic_horizon(str(tmp_path))
    assert results["all_passed"] is True, results["checks"]


def test_t_max_sourced_not_redeclared():
    assert T_MAX == _MORAL_WEIGHT_MAX


# ---- grants when all three gates pass ----

def test_grants_tolerance_when_all_three_gates_pass(tmp_path):
    ev, report, score = _rising_intake()
    icc_ledger = _driven_icc_ledger(tmp_path)
    moral_ledger = _registered_moral_ledger()
    layer = make_strategic_horizon_layer(state_dir=str(tmp_path))
    assessment = layer.assess(
        intake_id="intake_A", immediate_worth=score, worth_evaluator=ev,
        worth_report=report, current_tick=report.horizon.promoted_tick,
        saturation_signal=_sig(), icc_ledger=icc_ledger, moral_ledger=moral_ledger,
    )
    assert assessment.tolerance > 0.0
    assert assessment.tolerance <= T_MAX
    assert "all three gates passed" in assessment.rationale


# ---- denies on each gate failing individually ----

def test_gate_1_denies_when_trajectory_not_rising(tmp_path):
    ev = make_worth_evaluator(rng_seed=1)
    acc = make_accountant(initial_pool=50000.0)
    acc.tick()
    for c in (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A):
        acc.apply_shift(MagnitudeShiftRequest(c, 1.0, "bal"))
    score, report = ev.evaluate("intake_stable", ExistenceMode.BOUNDED, acc, 1)
    hist = ev.history_for("intake_stable")
    for v in [0.5, 0.5, 0.5, 0.5]:
        hist.record(v)
    assert hist.trajectory.value != "rising"

    icc_ledger = _driven_icc_ledger(tmp_path)
    layer = make_strategic_horizon_layer(state_dir=str(tmp_path))
    assessment = layer.assess(
        intake_id="intake_stable", immediate_worth=score, worth_evaluator=ev,
        worth_report=report, current_tick=1, saturation_signal=_sig(), icc_ledger=icc_ledger,
        moral_ledger=_registered_moral_ledger(),
    )
    assert assessment.tolerance == 0.0
    assert "not RISING" in assessment.rationale


def test_gate_2_denies_under_watch_or_worse(tmp_path):
    ev, report, score = _rising_intake(intake_id="intake_B")
    icc_ledger = _driven_icc_ledger(tmp_path)
    layer = make_strategic_horizon_layer(state_dir=str(tmp_path))
    for level in (SaturationLevel.WATCH, SaturationLevel.CAUTION, SaturationLevel.CRITICAL, SaturationLevel.EMERGENCY):
        assessment = layer.assess(
            intake_id="intake_B", immediate_worth=score, worth_evaluator=ev,
            worth_report=report, current_tick=report.horizon.promoted_tick,
            saturation_signal=_sig(level=level), icc_ledger=icc_ledger,
            moral_ledger=_registered_moral_ledger(),
        )
        assert assessment.tolerance == 0.0, f"level={level} should deny"


def test_gate_3_denies_when_icc_trend_negative(tmp_path):
    ev, report, score = _rising_intake(intake_id="intake_D")
    layer = make_strategic_horizon_layer(state_dir=str(tmp_path))

    class _FakeLedger:
        def balance_trajectory(self, window, **kw):
            return [0.5, 0.4, 0.3, 0.2]  # clearly declining

    assessment = layer.assess(
        intake_id="intake_D", immediate_worth=score, worth_evaluator=ev,
        worth_report=report, current_tick=report.horizon.promoted_tick,
        saturation_signal=_sig(), icc_ledger=_FakeLedger(),
        moral_ledger=_registered_moral_ledger(),
    )
    assert assessment.tolerance == 0.0
    assert "negative" in assessment.rationale


# ---- WATCH+ zeroes tolerance regardless of other factors ----

def test_watch_plus_saturation_zeroes_tolerance_even_with_maxed_inputs(tmp_path):
    ev, report, score = _rising_intake(intake_id="intake_E")
    icc_ledger = _driven_icc_ledger(tmp_path, n=50, minted=5.0)  # generous ICC history
    moral_ledger = _registered_moral_ledger()
    layer = make_strategic_horizon_layer(state_dir=str(tmp_path))
    assessment = layer.assess(
        intake_id="intake_E", immediate_worth=score, worth_evaluator=ev,
        worth_report=report, current_tick=report.horizon.promoted_tick,
        saturation_signal=_sig(level=SaturationLevel.CRITICAL, shallow_headroom=True),
        icc_ledger=icc_ledger, moral_ledger=moral_ledger,
    )
    assert assessment.tolerance == 0.0


# ---- cap respected when stacked with a maxed MoralWeightLedger bias ----

def test_cap_respected_when_stacked_with_maxed_moral_bias(tmp_path):
    ev, report, score = _rising_intake(intake_id="intake_F")
    icc_ledger = _driven_icc_ledger(tmp_path, n=50, minted=10.0)
    moral_ledger = _registered_moral_ledger()

    layer = make_strategic_horizon_layer(state_dir=str(tmp_path))
    assessment = layer.assess(
        intake_id="intake_F", immediate_worth=score, worth_evaluator=ev,
        worth_report=report, current_tick=report.horizon.promoted_tick,
        saturation_signal=_sig(), icc_ledger=icc_ledger, moral_ledger=moral_ledger,
    )
    assert assessment.tolerance <= T_MAX

    layer.grant_bias(Constraint.B, assessment.tolerance)
    # MoralWeightLedger's own max bias for a constraint, stacked with this
    # layer's own capped contribution -- each source enforces its OWN
    # ceiling (directive 1.3), so this layer's contribution alone must
    # never exceed T_MAX regardless of how large the OTHER source's bias is.
    moral_ledger.moral_bias(Constraint.B)  # exists independently, not summed here
    layer.grant_bias(Constraint.B, T_MAX * 10)  # try to blow past the cap
    assert layer.flip_threshold_bias(Constraint.B) <= T_MAX


# ---- journal entry written for every grant ----

def test_journal_entry_written_for_every_grant(tmp_path):
    ev, report, score = _rising_intake(intake_id="intake_G")
    icc_ledger = _driven_icc_ledger(tmp_path)
    moral_ledger = _registered_moral_ledger()
    layer = make_strategic_horizon_layer(state_dir=str(tmp_path))
    assessment = layer.assess(
        intake_id="intake_G", immediate_worth=score, worth_evaluator=ev,
        worth_report=report, current_tick=report.horizon.promoted_tick,
        saturation_signal=_sig(), icc_ledger=icc_ledger, moral_ledger=moral_ledger,
    )
    assert assessment.tolerance > 0.0

    log_path = tmp_path / "strategic_horizon_log.jsonl"
    assert log_path.exists()
    entries = [json.loads(l) for l in log_path.read_text().splitlines() if l.strip()]
    assert len(entries) == 1
    assert entries[0]["intake_id"] == "intake_G"
    assert entries[0]["tolerance"] == assessment.tolerance


def test_no_journal_entry_written_when_denied(tmp_path):
    ev, report, score = _rising_intake(intake_id="intake_H")
    layer = make_strategic_horizon_layer(state_dir=str(tmp_path))
    layer.assess(
        intake_id="intake_H", immediate_worth=score, worth_evaluator=ev,
        worth_report=report, current_tick=report.horizon.promoted_tick,
        saturation_signal=_sig(level=SaturationLevel.CRITICAL),
    )
    log_path = tmp_path / "strategic_horizon_log.jsonl"
    assert not log_path.exists()


# ---- degraded ICC read disables cleanly ----

def test_degraded_icc_read_disables_cleanly(tmp_path):
    ev, report, score = _rising_intake(intake_id="intake_I")
    layer = make_strategic_horizon_layer(state_dir=str(tmp_path))

    class _BrokenLedger:
        def balance_trajectory(self, *a, **kw):
            raise RuntimeError("icc ledger unavailable")

    assessment = layer.assess(
        intake_id="intake_I", immediate_worth=score, worth_evaluator=ev,
        worth_report=report, current_tick=report.horizon.promoted_tick,
        saturation_signal=_sig(), icc_ledger=_BrokenLedger(),
        moral_ledger=_registered_moral_ledger(),
    )
    # icc_trend degrades to 0.0 on a broken ledger -- 0.0 >= 0.0 still
    # passes gate 3, but icc_trend_factor=0.0 zeroes the tolerance, so a
    # broken ICC read cannot silently authorize an ungrounded grant.
    assert assessment.tolerance == 0.0


def test_assess_never_raises_on_none_worth_report(tmp_path):
    layer = make_strategic_horizon_layer(state_dir=str(tmp_path))
    assessment = layer.assess(
        intake_id="x", immediate_worth=0.5, worth_evaluator=make_worth_evaluator(),
        worth_report=None, current_tick=1, saturation_signal=_sig(),
    )
    assert assessment.tolerance == 0.0


# ---- SaturationSignal.urgency_ticks() evolved-native corruption isolation ----

def test_projected_gain_survives_urgency_ticks_returning_non_numeric(tmp_path):
    """Regression: known_fixes_registry.md's second occurrence -- the
    evolved-native override can turn urgency_ticks()'s legitimate None
    into a dict. _projected_gain must not raise or misbehave either way."""
    ev, report, score = _rising_intake(intake_id="intake_J")
    layer = make_strategic_horizon_layer(state_dir=str(tmp_path))

    class _WeirdSignal:
        level = SaturationLevel.NOMINAL
        shallow_headroom_available = True

        def urgency_ticks(self):
            return {"available": False, "reason": "evolved_surface_engine_unavailable"}

    gain = layer._projected_gain(report, report.horizon.promoted_tick, _WeirdSignal())
    assert isinstance(gain, float)


# ---- public surface / privacy ----

def test_summary_exposes_no_raw_factor_internals(tmp_path):
    ev, report, score = _rising_intake(intake_id="intake_K")
    icc_ledger = _driven_icc_ledger(tmp_path)
    moral_ledger = _registered_moral_ledger()
    layer = make_strategic_horizon_layer(state_dir=str(tmp_path))
    layer.assess(
        intake_id="intake_K", immediate_worth=score, worth_evaluator=ev,
        worth_report=report, current_tick=report.horizon.promoted_tick,
        saturation_signal=_sig(), icc_ledger=icc_ledger, moral_ledger=moral_ledger,
    )
    summ = layer.summary()
    for forbidden in ("projected_gain", "icc_trend", "saturation_headroom", "immediate_worth"):
        assert forbidden not in summ


def test_boundary_no_direct_constraint_writes():
    """Read-only observer -- StrategicHorizonLayer has no method that
    writes constraint state, no expression-path involvement, no CERS
    override. Enforced structurally: confirm the public surface matches
    exactly what the directive documents (1.4)."""
    public_methods = {
        name for name in dir(StrategicHorizonLayer)
        if not name.startswith("_") and callable(getattr(StrategicHorizonLayer, name))
    }
    expected = {"assess", "grant_bias", "flip_threshold_bias", "summary"}
    assert public_methods == expected
