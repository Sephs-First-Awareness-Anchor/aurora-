# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
tests/test_icc_ledger.py
===========================
Phase 0 of the ICC Landing / Strategic Horizon / Operator Composition
directive (2026-07-14): aurora_internal/aurora_icc_ledger.py.

ICC = Internal Coherence Credit. Currency grounded in resolved ignorance
that survived reality pressure. Hash-chained, tamper-evident,
append-only; read-only observer of CrossScaleWorthEvaluator,
EntropySaturationDetector, MoralWeightLedger, and FailureGuardSuite --
never an actuator, never commands them.
"""
import json
import os

from foundational_contract import ExistenceMode
from aurora_constraint_engine import GuardResult
from aurora_internal.aurora_constraint_manifold_patched import Constraint
from aurora_internal.aurora_energy_layer_costs import make_accountant, MagnitudeShiftRequest
from aurora_internal.aurora_entropy_detector import SaturationLevel, SaturationSignal
from aurora_internal.aurora_icc_ledger import (
    GENESIS_PREV_HASH,
    ICCLedger,
    make_icc_ledger,
    verify_icc_ledger,
)
from aurora_internal.aurora_variant_promotion import MoralWeightLedger, VariantRecord
from aurora_internal.aurora_worth_evaluator import WorthReport, make_worth_evaluator


def _drive_to_horizon(intake_id="intake_A", rng_seed=42, extra_evals=3):
    """Drive a real CrossScaleWorthEvaluator against a real
    LayerEnergyAccountant until a horizon is granted (first threshold
    crossing), then a few more evaluations so trajectory/has_ever_risen
    have real data. Returns (evaluator, worth_report_with_horizon, score,
    eligible_tick)."""
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
    assert crossing_report is not None, "fixture must reach a horizon crossing"

    for extra in range(extra_evals):
        score, _ = ev.evaluate(intake_id, ExistenceMode.BOUNDED, acc, 100 + extra)

    return ev, crossing_report, score, crossing_report.horizon.eligible_tick


def _sig(level):
    return SaturationSignal(
        level=level, tick=1, pressure_rising=False, fastest_rising_constraint=None,
        projected_critical_tick=None, shallow_headroom_available=True, ticks_above_warn=0,
    )


def _registered_moral_ledger(constraint=Constraint.B, weight=0.02):
    ledger = MoralWeightLedger()
    variant = VariantRecord(
        variant_id="V:test", source_solid_id="solid:test", intake_id="intake:test",
        depth_reached=ExistenceMode.BOUNDED, promoted_tick=1, recurrence_count=6,
        context_variety=2, polarity_coherence_rate=0.8, constraint_signature="XTNBA",
        deepest_constraint=constraint, moral_weight=weight, cost_reduction_factor=0.1,
    )
    ledger.register(variant)
    return ledger


# ---- built-in self-verification ----

def test_builtin_self_verification_all_pass(tmp_path):
    results = verify_icc_ledger(str(tmp_path))
    assert results["all_passed"] is True, results["checks"]


# ---- genesis / construction ----

def test_genesis_entry_on_fresh_ledger(tmp_path):
    ledger = make_icc_ledger(state_dir=str(tmp_path))
    assert len(ledger._entries) == 1
    genesis = ledger._entries[0]
    assert genesis.prev_hash == GENESIS_PREV_HASH
    assert genesis.source == "manual_doctrine"
    assert genesis.minted == 0.0


def test_reload_preserves_chain(tmp_path):
    ledger = make_icc_ledger(state_dir=str(tmp_path))
    ledger.mint_from_contradiction_resolution(tick=1, contradiction_id="c1", minted=0.1)
    ledger2 = make_icc_ledger(state_dir=str(tmp_path))
    assert len(ledger2._entries) == 2
    assert ledger2.verify_chain() is True


# ---- chain integrity ----

def test_chain_integrity_tamper_freezes_and_logs_violation(tmp_path):
    ledger = make_icc_ledger(state_dir=str(tmp_path))
    for i in range(10):
        ledger.mint_from_contradiction_resolution(tick=i, contradiction_id=f"c{i}", minted=0.05)
    assert len(ledger._entries) == 11  # genesis + 10

    ledger_path = tmp_path / "icc_ledger.jsonl"
    lines = ledger_path.read_text().splitlines()
    tampered = json.loads(lines[5])
    tampered["minted"] = 999.0
    lines[5] = json.dumps(tampered)
    ledger_path.write_text("\n".join(lines) + "\n")

    reloaded = make_icc_ledger(state_dir=str(tmp_path))
    assert reloaded.is_frozen() is True
    assert reloaded.verify_chain() is False

    violations_path = tmp_path / "icc_violations.jsonl"
    assert violations_path.exists()
    entries = [json.loads(l) for l in violations_path.read_text().splitlines() if l.strip()]
    assert any(e["reason"] == "entry_hash_mismatch" for e in entries)


def test_frozen_ledger_refuses_new_mints(tmp_path):
    ledger = make_icc_ledger(state_dir=str(tmp_path))
    ledger.mint_from_contradiction_resolution(tick=1, contradiction_id="c1", minted=0.1)
    ledger_path = tmp_path / "icc_ledger.jsonl"
    lines = ledger_path.read_text().splitlines()
    tampered = json.loads(lines[0])
    tampered["entry_hash"] = "0" * 64
    lines[0] = json.dumps(tampered)
    ledger_path.write_text("\n".join(lines) + "\n")

    reloaded = make_icc_ledger(state_dir=str(tmp_path))
    assert reloaded.is_frozen() is True
    result = reloaded.mint_from_contradiction_resolution(tick=2, contradiction_id="c2", minted=0.1)
    assert result is None


# ---- minting gates: worth_survival ----

def test_mint_if_eligible_succeeds_when_all_three_conditions_hold(tmp_path):
    ledger = make_icc_ledger(state_dir=str(tmp_path))
    ev, report, score, eligible_tick = _drive_to_horizon()
    entry = ledger.mint_if_eligible(
        "intake_A", eligible_tick, worth_evaluator=ev, worth_report=report,
        depth_weight=0.5, worth_score=score,
    )
    assert entry is not None
    assert entry.source == "worth_survival"
    assert entry.minted > 0.0
    assert entry.evidence["intake_id"] == "intake_A"


def test_mint_if_eligible_never_mints_twice_for_same_intake(tmp_path):
    ledger = make_icc_ledger(state_dir=str(tmp_path))
    ev, report, score, eligible_tick = _drive_to_horizon()
    first = ledger.mint_if_eligible(
        "intake_A", eligible_tick, worth_evaluator=ev, worth_report=report,
        depth_weight=0.5, worth_score=score,
    )
    second = ledger.mint_if_eligible(
        "intake_A", eligible_tick, worth_evaluator=ev, worth_report=report,
        depth_weight=0.5, worth_score=score,
    )
    assert first is not None
    assert second is None


def test_gate_1_fails_without_horizon(tmp_path):
    """No horizon (no promotion crossing yet) -> gate 1 fails -> no mint.
    Constructed directly rather than via a real evaluator run: whether a
    given tick crosses the promotion threshold is CrossScaleWorthEvaluator's
    own concern (verified in its own test suite), not gate 1's -- gate 1
    only needs to prove it rejects a horizon-less report."""
    ledger = make_icc_ledger(state_dir=str(tmp_path))
    ev = make_worth_evaluator(rng_seed=1)
    acc = make_accountant(initial_pool=50000.0)
    acc.tick()
    score, real_report = ev.evaluate("intake_no_horizon", ExistenceMode.TRANSIENT, acc, 1)
    report = WorthReport(
        intake_id=real_report.intake_id, tick=real_report.tick,
        crossed_threshold=False, trajectory=real_report.trajectory,
        polarity_coherent=real_report.polarity_coherent, horizon=None,
        tense_transitions=real_report.tense_transitions,
    )
    entry = ledger.mint_if_eligible(
        "intake_no_horizon", 1, worth_evaluator=ev, worth_report=report,
        depth_weight=0.5, worth_score=score,
    )
    assert entry is None


def test_gate_2_fails_when_trajectory_is_falling(tmp_path):
    """has_ever_risen False (monotonically flat/declining from the start)
    -> gate 2 fails -> no mint, even with a real horizon."""
    ledger = make_icc_ledger(state_dir=str(tmp_path))
    ev, report, score, eligible_tick = _drive_to_horizon(intake_id="intake_flat", extra_evals=0)
    # Force a declining trajectory directly on the history buffer -- the
    # evaluator's own noise makes a clean FALLING run hard to guarantee
    # black-box, so drive the same public surface the module reads.
    history = ev.history_for("intake_flat")
    for v in [0.9, 0.7, 0.5, 0.4, 0.3]:
        history.record(v)
    assert history.trajectory.value == "falling"
    entry = ledger.mint_if_eligible(
        "intake_flat", eligible_tick, worth_evaluator=ev, worth_report=report,
        depth_weight=0.5, worth_score=score,
    )
    assert entry is None


def test_gate_3_fails_before_horizon_eligibility(tmp_path):
    ledger = make_icc_ledger(state_dir=str(tmp_path))
    ev, report, score, eligible_tick = _drive_to_horizon(intake_id="intake_early")
    entry = ledger.mint_if_eligible(
        "intake_early", eligible_tick - 1, worth_evaluator=ev, worth_report=report,
        depth_weight=0.5, worth_score=score,
    )
    assert entry is None


def test_mint_if_eligible_degrades_gracefully_on_missing_inputs(tmp_path):
    ledger = make_icc_ledger(state_dir=str(tmp_path))
    assert ledger.mint_if_eligible("x", 1) is None
    assert ledger.mint_if_eligible("x", 1, worth_evaluator=make_worth_evaluator()) is None


# ---- minting gates: contradiction_resolution ----

def test_mint_from_contradiction_resolution_mints_directly(tmp_path):
    ledger = make_icc_ledger(state_dir=str(tmp_path))
    entry = ledger.mint_from_contradiction_resolution(
        tick=1, contradiction_id="cid_1", axes={"N": 0.2}, minted=0.15,
    )
    assert entry is not None
    assert entry.source == "contradiction_resolution"
    assert entry.minted == 0.15
    assert entry.axes == {"N": 0.2}


def test_mint_from_contradiction_resolution_never_negative(tmp_path):
    ledger = make_icc_ledger(state_dir=str(tmp_path))
    entry = ledger.mint_from_contradiction_resolution(
        tick=1, contradiction_id="cid_neg", minted=-5.0,
    )
    assert entry is not None
    assert entry.minted == 0.0


# ---- balance factors / monotonicity ----

def test_balance_zero_with_no_moral_ledger_provided(tmp_path):
    """moral_standing defaults to 0.0 without a MoralWeightLedger --
    balance is the product of all four factors, so it floors to 0."""
    ledger = make_icc_ledger(state_dir=str(tmp_path))
    ledger.mint_from_contradiction_resolution(tick=1, contradiction_id="c1", minted=1.0)
    bal = ledger.current_balance(current_tick=1)
    assert bal == 0.0


def test_balance_positive_when_all_factors_present(tmp_path):
    ledger = make_icc_ledger(state_dir=str(tmp_path))
    ledger.mint_from_contradiction_resolution(tick=1, contradiction_id="c1", minted=1.0)
    moral_ledger = _registered_moral_ledger()
    bal = ledger.current_balance(
        current_tick=1, saturation_signal=_sig(SaturationLevel.NOMINAL),
        moral_ledger=moral_ledger,
    )
    assert bal > 0.0


def test_active_coherence_penalised_beyond_watch(tmp_path):
    ledger = make_icc_ledger(state_dir=str(tmp_path))
    ledger.mint_from_contradiction_resolution(tick=1, contradiction_id="c1", minted=1.0)
    moral_ledger = _registered_moral_ledger()
    bal_nominal = ledger.current_balance(
        current_tick=1, saturation_signal=_sig(SaturationLevel.NOMINAL), moral_ledger=moral_ledger,
    )
    bal_critical = ledger.current_balance(
        current_tick=1, saturation_signal=_sig(SaturationLevel.CRITICAL), moral_ledger=moral_ledger,
    )
    assert bal_critical < bal_nominal


def test_moral_standing_respects_floor_at_zero_bias(tmp_path):
    ledger = make_icc_ledger(state_dir=str(tmp_path))
    ledger.mint_from_contradiction_resolution(tick=1, contradiction_id="c1", minted=1.0)
    empty_moral_ledger = MoralWeightLedger()  # no variants registered -> all biases 0
    bal = ledger.current_balance(
        current_tick=1, saturation_signal=_sig(SaturationLevel.NOMINAL),
        moral_ledger=empty_moral_ledger,
    )
    assert bal == 0.0


def test_historical_weight_decays_with_age():
    ledger_recent = ICCLedger.__new__(ICCLedger)
    ledger_recent._entries = []
    from aurora_internal.aurora_icc_ledger import _mint_entry, GENESIS_PREV_HASH
    e = _mint_entry(tick=100, prev_hash=GENESIS_PREV_HASH, source="manual_doctrine",
                     axes={}, minted=1.0, evidence={})
    ledger_recent._entries = [e]
    hw_close = ledger_recent._historical_weight(current_tick=101)
    hw_far = ledger_recent._historical_weight(current_tick=1000)
    assert hw_close > hw_far > 0.0


def test_balance_trajectory_returns_a_list_of_floats(tmp_path):
    ledger = make_icc_ledger(state_dir=str(tmp_path))
    for i in range(5):
        ledger.mint_from_contradiction_resolution(tick=i, contradiction_id=f"c{i}", minted=0.1)
    traj = ledger.balance_trajectory(3, saturation_signal=_sig(SaturationLevel.NOMINAL),
                                      moral_ledger=_registered_moral_ledger())
    assert len(traj) == 3
    assert all(isinstance(v, float) for v in traj)


# ---- intent_integrity (FailureGuardSuite sweeps) ----

def test_intent_integrity_full_when_no_sweeps_recorded(tmp_path):
    ledger = make_icc_ledger(state_dir=str(tmp_path))
    assert ledger._intent_integrity() == 1.0


def test_intent_integrity_reflects_pass_fraction(tmp_path):
    ledger = make_icc_ledger(state_dir=str(tmp_path))
    passing = [GuardResult(True, "g1", ""), GuardResult(True, "g2", "")]
    failing = [GuardResult(True, "g1", ""), GuardResult(False, "g2", "bad")]
    ledger.record_guard_sweep(passing)
    ledger.record_guard_sweep(passing)
    ledger.record_guard_sweep(failing)
    ledger.record_guard_sweep(failing)
    assert ledger._intent_integrity() == 0.5


def test_intent_integrity_acknowledged_uncertainty_counts_as_full_pass(tmp_path):
    """directive 0.3: UncertaintySignalingGuard passes obtained via
    acknowledgment count fully -- since GuardResult.passed is already True
    once acknowledge_uncertainty() has cleared the flag, a sweep containing
    an acknowledged-high-uncertainty guard result must count as a pass,
    identical to a sweep with no uncertainty at all."""
    ledger = make_icc_ledger(state_dir=str(tmp_path))
    from aurora_constraint_engine import UncertaintySignalingGuard
    guard = UncertaintySignalingGuard()
    guard.update_uncertainty(0.9)  # raises the flag
    guard.acknowledge_uncertainty()  # clears it -- honest, not suppressed
    result = guard.check()
    assert result.passed is True
    ledger.record_guard_sweep([result])
    assert ledger._intent_integrity() == 1.0


def test_record_guard_sweep_never_raises_on_bad_input(tmp_path):
    ledger = make_icc_ledger(state_dir=str(tmp_path))
    ledger.record_guard_sweep(None)
    ledger.record_guard_sweep("not a list")
    ledger.record_guard_sweep([object()])  # no .passed attribute


# ---- failure isolation ----

def test_current_balance_never_raises_on_malformed_saturation_signal(tmp_path):
    ledger = make_icc_ledger(state_dir=str(tmp_path))

    class _BadSignal:
        level = "not_a_real_level"

    bal = ledger.current_balance(current_tick=1, saturation_signal=_BadSignal())
    assert isinstance(bal, float)


def test_current_balance_never_raises_on_malformed_moral_ledger(tmp_path):
    ledger = make_icc_ledger(state_dir=str(tmp_path))

    class _BadMoralLedger:
        def all_biases(self):
            raise RuntimeError("entropy detector import broken")

    bal = ledger.current_balance(current_tick=1, moral_ledger=_BadMoralLedger())
    assert isinstance(bal, float)
    assert bal == 0.0


def test_verify_chain_on_corrupt_json_line_does_not_raise(tmp_path):
    ledger = make_icc_ledger(str(tmp_path))
    ledger_path = tmp_path / "icc_ledger.jsonl"
    ledger_path.write_text(ledger_path.read_text() + "{not valid json\n")
    reloaded = make_icc_ledger(str(tmp_path))
    # corrupt trailing line means the loader's own except-Exception clears
    # entries entirely (matches semantic_variant_registry.py's own
    # "index lost -> degrade to no candidates" posture) -- must not raise,
    # and a fresh genesis reappears on next use.
    assert isinstance(reloaded._entries, list)


# ---- public surface / privacy ----

def test_summary_exposes_no_raw_factor_internals(tmp_path):
    ledger = make_icc_ledger(state_dir=str(tmp_path))
    ledger.mint_from_contradiction_resolution(tick=1, contradiction_id="c1", minted=0.2)
    summ = ledger.summary()
    for forbidden in ("historical_weight", "active_coherence", "moral_standing", "intent_integrity"):
        assert forbidden not in summ
    assert summ["entry_count"] == 2
    assert summ["chain_intact"] is True
    assert "contradiction_resolution" in summ["mint_sources"]


def test_entry_to_dict_and_from_dict_roundtrip(tmp_path):
    ledger = make_icc_ledger(state_dir=str(tmp_path))
    entry = ledger.mint_from_contradiction_resolution(tick=1, contradiction_id="c1", minted=0.2)
    from aurora_internal.aurora_icc_ledger import ICCEntry
    roundtrip = ICCEntry.from_dict(entry.to_dict())
    assert roundtrip == entry


# ---- boundary rules ----

def test_ledger_never_writes_to_constraint_state():
    """Read-only observer -- ICCLedger has no method that touches a
    constraint manifold, WarpField, or CERS verdict. Enforced structurally:
    confirm the class exposes only the documented public surface."""
    public_methods = {
        name for name in dir(ICCLedger)
        if not name.startswith("_") and callable(getattr(ICCLedger, name))
    }
    expected = {
        "current_balance", "balance_trajectory", "mint_if_eligible",
        "mint_from_contradiction_resolution", "verify_chain", "is_frozen",
        "summary", "record_guard_sweep",
    }
    assert public_methods == expected
