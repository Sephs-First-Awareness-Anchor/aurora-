# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
RW6(c) -- Track-1 (ICC Landing / Strategic Horizon / Operator
Composition directive, 2026-07-14), wiring audit F7, 2026-07-20.

F7's zero-caller census: `aurora_internal/aurora_icc_ledger.py`,
`aurora_internal/aurora_strategic_horizon.py`, `aurora_internal/
aurora_operator_composer.py` all existed with zero repo-wide imports.
Unlike RW4/RW5 (single-function reconnections), these three modules are
large, directive-specific, and self-document real intended hook points
(explicit `TODO: wire from X call site` comments already present in
the code). This landing wires what is safely, mechanically wireable:

* All four modules mounted at boot (`icc_ledger`, `strategic_horizon`,
  `operator_composer`, `entropy_detector` -- the last one previously
  existed only in `boot_stack`, per RW5's boot-parity table).
* `EntropySaturationDetector.measure()` runs once per tick inside
  `_advance_intake_pipeline`, right after `accountant.tick()` (the
  module's own documented INTEGRATION contract), giving the live spine
  a real `SaturationSignal` for the first time.
* `OperatorComposer.compose_tick()` runs on the same recurring
  maintenance cadence RW3 already established for QuasiArch
  (`scripts/aurora_ci_segment.py`), fully self-contained and gated
  purely on trajectory direction + promotion status -- no currency
  value fabricated.

Deliberately NOT wired: `ICCLedger.mint_if_eligible`, `ICCLedger.
mint_from_contradiction_resolution`, `StrategicHorizonLayer.assess`/
`grant_bias`. Each needs a worth_score/immediate_worth/minted currency
magnitude that is not derivable from any publicly-exposed WorthReport/
WorthHistory field (their own docstrings say raw worth score is never
exposed), and even these modules' own test suites use a placeholder
0.0/0.1 rather than a real derivation. Minting a fabricated amount into
a hash-chained, tamper-evident, append-only ledger is exactly the kind
of guess `mint_from_contradiction_resolution`'s own existing comment
already refuses to make ("if ambiguous, stub the hook with a TODO and
flag rather than guessing") -- this landing follows that same rule.
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import aurora as A  # noqa: E402


def _read_aurora_source():
    with open(os.path.join(REPO_ROOT, "aurora.py"), "r", encoding="utf-8") as f:
        return f.read()


def test_track1_modules_mounted_in_boot_aurora():
    source = _read_aurora_source()
    start = source.index("\ndef boot_aurora(")
    end = source.index("\ndef ", start + 10)
    body = source[start:end]
    for key in ("entropy_detector", "icc_ledger", "strategic_horizon", "operator_composer"):
        assert f"systems['{key}']" in body, f"{key} not mounted in boot_aurora"
    assert "ICCLedger(state_dir=state_dir)" in body
    assert "StrategicHorizonLayer(state_dir=state_dir)" in body
    assert "OperatorComposer(repo_root=" in body


def test_entropy_detector_measured_once_per_tick_after_accountant_tick():
    source = _read_aurora_source()
    start = source.index("\ndef _advance_intake_pipeline(")
    end = source.index("\ndef ", start + 10)
    body = source[start:end]
    tick_idx = body.index("accountant.tick()")
    measure_idx = body.index("entropy_detector.measure(accountant, tick)")
    assert tick_idx < measure_idx, "must measure saturation after accountant.tick(), not before"
    assert "systems['_last_saturation_signal']" in body


def test_entropy_detector_measure_survives_extra_nonconstraint_magnitude_keys():
    """Real bug found by this landing: LayerEnergyAccountant.magnitudes()
    can carry extra non-Constraint telemetry keys (self-healing
    rewrite-profile bookkeeping, e.g. '_aurora_rewrite_profile') alongside
    the 5 canonical constraints -- EntropySaturationDetector had never
    been exercised live before RW6c (boot_stack-only, per RW5's
    boot-parity table) and crashed with a raw KeyError the first time it
    was. measure() must skip keys it wasn't constructed with windows for."""
    from aurora_internal.aurora_entropy_detector import EntropySaturationDetector
    from aurora_internal.aurora_constraint_manifold_patched import Constraint

    class _FakeAccountant:
        def entropy_pressure(self):
            return 0.1

        def magnitudes(self):
            return {
                Constraint.X: 0.1, Constraint.T: 0.1, Constraint.N: 0.1,
                Constraint.B: 0.1, Constraint.A: 0.1,
                "_aurora_rewrite_profile": "generic",
                "_aurora_genealogy_strategy": "generic",
            }

        pool = 100.0

    detector = EntropySaturationDetector()
    signal = detector.measure(_FakeAccountant(), 1)
    assert signal is not None
    assert signal.tick == 1


def test_entropy_detector_shallow_headroom_survives_callable_pool_override():
    """Real bug found by this landing: an "evolved surfaces" self-healing
    mechanism (aurora_internal/aurora_energy_layer_costs.py) can replace
    LayerEnergyAccountant.pool -- normally an @property -- with a plain
    override function at import time, so `accountant.pool` returns a
    bound method instead of a float. _has_shallow_headroom must not
    assume either shape."""
    from aurora_internal.aurora_entropy_detector import EntropySaturationDetector

    class _CallablePoolAccountant:
        _pool = 50.0

        def pool(self):  # simulates the evolved-surfaces override shape
            return 50.0

    detector = EntropySaturationDetector()
    # Must not raise TypeError comparing a bound method to a float.
    result = detector._has_shallow_headroom(_CallablePoolAccountant())
    assert isinstance(result, bool)


def test_mint_and_assess_hooks_remain_deliberately_unwired():
    """The currency-fabrication risk means these must NOT be called live
    yet -- confirms the scope decision stuck, not silently expanded."""
    source = _read_aurora_source()
    assert "icc_ledger.mint_if_eligible(" not in source
    assert "icc_ledger.mint_from_contradiction_resolution(" not in source
    assert "strategic_horizon.assess(" not in source
    assert "strategic_horizon.grant_bias(" not in source


def test_operator_composer_maintenance_tick_wired_into_ci_segment():
    ci_segment_path = os.path.join(REPO_ROOT, "scripts", "aurora_ci_segment.py")
    with open(ci_segment_path, "r", encoding="utf-8") as f:
        source = f.read()
    assert "def _run_operator_composer_maintenance_tick(systems):" in source
    assert "composer.compose_tick(" in source
    assert "_run_operator_composer_maintenance_tick(systems)" in source


def test_operator_composer_maintenance_tick_calls_compose_tick_and_reports_count():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "aurora_ci_segment_rw6c", os.path.join(REPO_ROOT, "scripts", "aurora_ci_segment.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    class _FakeComposer:
        def __init__(self):
            self.calls = []

        def compose_tick(self, **kwargs):
            self.calls.append(kwargs)
            return ["fake_composite_1"]

    class _FakeWorkingMemory:
        turn_count = 7

    composer = _FakeComposer()
    systems = {"operator_composer": composer, "working_memory": _FakeWorkingMemory(), "worth_eval": None}
    summary = mod._run_operator_composer_maintenance_tick(systems)

    assert summary["composites_proposed"] == 1
    assert len(composer.calls) == 1
    assert composer.calls[0]["current_tick"] == 7.0


def test_operator_composer_maintenance_tick_noop_without_composer():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "aurora_ci_segment_rw6c_2", os.path.join(REPO_ROOT, "scripts", "aurora_ci_segment.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    summary = mod._run_operator_composer_maintenance_tick({})
    assert summary["composites_proposed"] == 0


def test_real_boot_mounts_working_track1_instances():
    """Real end-to-end confirmation: boot Aurora for real and confirm all
    four Track-1 organs are actual, correctly-typed instances -- not
    just structurally present in source."""
    import shutil
    import tempfile

    from aurora_internal.aurora_entropy_detector import EntropySaturationDetector
    from aurora_internal.aurora_icc_ledger import ICCLedger
    from aurora_internal.aurora_strategic_horizon import StrategicHorizonLayer
    from aurora_internal.aurora_operator_composer import OperatorComposer

    scratch = tempfile.mkdtemp(prefix="aurora_rw6c_boot_")
    try:
        scratch_state = os.path.join(scratch, "aurora_state")
        shutil.copytree(os.path.join(REPO_ROOT, "aurora_state"), scratch_state)
        systems = A.boot_aurora(state_dir=scratch_state)

        assert isinstance(systems.get("entropy_detector"), EntropySaturationDetector)
        assert isinstance(systems.get("icc_ledger"), ICCLedger)
        assert isinstance(systems.get("strategic_horizon"), StrategicHorizonLayer)
        assert isinstance(systems.get("operator_composer"), OperatorComposer)

        result = A.process_external_user_turn(systems, "What is the boiling point of water?")
        assert result, "live turn produced no result"
        assert "_last_saturation_signal" in systems, (
            "EntropySaturationDetector.measure() did not run during a real live turn"
        )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
