# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
R1.8/R1.8.1 Track C: governance liveness inventory, automated.

"verify_*() green != wired. Every module claiming a runtime role must show
boot-path reachability; claimed-but-unwired modules live in an explicit
quarantine manifest so their status is a decision, never an accident."
(liveness rule, R1.7 addendum)

This encodes the C1 inventory's verdicts as regression checks against
aurora.py's source, mirroring the pattern already established by
tests/test_flow_audit_and_tcl_wiring.py. A module regressing from LIVE to
unwired fails CI; a module quietly becoming reachable without updating the
quarantine manifest is exactly as much a decision that should be visible.
"""
import os

AURORA_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aurora.py")


def _aurora_source() -> str:
    with open(AURORA_PY, "r", encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# QUARANTINE MANIFEST -- modules confirmed claimed-but-not-live (C1 verdicts).
# Each entry is a decision, not an accident: if one of these becomes wired,
# move it to the LIVE section below (and celebrate) rather than deleting the
# check. If a LIVE module regresses to here, that is exactly the failure
# mode this file exists to catch.
# ---------------------------------------------------------------------------
QUARANTINE_STALE = {
    "aurora_constraint_engine.FailureGuardSuite": (
        "Zero references in aurora.py. Only referenced by this remediation's "
        "own probe-battery/ledger tooling (run_probe_battery.py, "
        "aurora_internal/aurora_icc_ledger.py, "
        "aurora_internal/aurora_semantic_probe_battery.py) -- confirmed R1.6, "
        "reconfirmed R1.8.1."
    ),
    "aurora_toroidal_circulation.ToroidalCirculationLayer": (
        "Zero references in aurora.py. Independently caught by the "
        "pre-existing failing test "
        "test_flow_audit_and_tcl_wiring.py::test_aurora_py_wires_toroidal_layer_into_cers_snapshot_pass "
        "(confirmed pre-existing and unrelated to this remediation's changes "
        "-- out of scope to fix here, tracked as its own known regression)."
    ),
}

# Modules with genuine call sites in aurora.py, but only reachable when
# boot_aurora() runs a NON-"surface" runtime_profile. Every probe-battery
# run and trace this entire R0-R1.8 campaign has produced used
# runtime_profile="surface" (see run_probe_battery.py), so these have never
# actually participated in any measurement this campaign has taken, despite
# being real, non-dead code.
QUARANTINE_PROFILE_GATED = {
    "aurora_internal.aurora_worth_evaluator": (
        "Instantiated + called (worth_eval.evaluate(...) at aurora.py "
        "L22920) only when NOT booted with runtime_profile='surface'. "
        "run_probe_battery.py boots with runtime_profile='surface' "
        "unconditionally, so this has been unreachable in every measurement "
        "R0-R1.8 took."
    ),
    "aurora_internal.aurora_variant_promotion.VariantPromoter": (
        "Same gating as worth_evaluator (aurora.py L22988, "
        "variant_promoter.process_solidified(...))."
    ),
}

# Referenced by separate runtime entry points (aurora_runtime.py,
# aurora_daemon.py) but not by aurora.py's boot_aurora() -- the path this
# entire investigation's probe battery and traces exercise. Not verified
# live or dead under those other entry points; simply out of this
# investigation's reach.
QUARANTINE_ALTERNATE_ENTRYPOINT_ONLY = {
    "aurora_internal.aurora_entropy_detector": (
        "Not referenced in aurora.py. Referenced by aurora_runtime.py and "
        "aurora_daemon.py, which this investigation did not boot or trace."
    ),
}

LIVE_CONFIRMED = {
    "aurora_constraint_emission.ConstraintEmitter": (
        "Instantiated unconditionally at boot (aurora.py L20103-20108, "
        "all runtime profiles). Called from _field_frame_compress and "
        "_emit_honest_abstain_and_seek. Confirmed executing live via "
        "instrumented single-turn trace, R1.8.1 Step 3."
    ),
    "ContradictionLedger": (
        "Instantiated at boot (aurora.py L20452-20453), wired to "
        "working_memory at both initial wiring and the final re-assert pass."
    ),
    "attention_engine": (
        "'.tick()' and '.get_meaning_nucleus()' called every turn inside "
        "_run_live_response_turn."
    ),
    "CERSBridge": (
        "Instantiated and called in aurora.py (CERS shadow pass). "
        "Explicitly documented as read-only/advisory/non-authoritative by "
        "design -- this is a design decision, not staleness."
    ),
}


def test_quarantine_stale_modules_remain_unreferenced_in_aurora_py():
    """If one of these gains a real reference in aurora.py, it graduated out
    of quarantine -- update this file's manifest deliberately rather than
    letting the assertion silently start failing."""
    source = _aurora_source()
    assert "FailureGuardSuite" not in source, (
        "FailureGuardSuite now appears in aurora.py -- if this is real "
        "wiring, move it out of QUARANTINE_STALE and add a LIVE assertion; "
        "if it's an incidental string match, this assertion needs updating."
    )
    assert "ToroidalCirculationLayer" not in source, (
        "ToroidalCirculationLayer now appears in aurora.py -- check whether "
        "test_flow_audit_and_tcl_wiring.py's known pre-existing failure has "
        "been fixed; if so this module graduated out of quarantine."
    )


def test_constraint_emitter_is_wired_at_boot():
    source = _aurora_source()
    assert "from aurora_constraint_emission import ConstraintEmitter" in source
    assert "constraint_emitter" in source


def test_contradiction_ledger_is_wired_at_boot():
    source = _aurora_source()
    assert "from aurora_ivm import ContradictionLedger" in source
    assert "contradiction_ledger" in source


def test_worth_evaluator_and_variant_promotion_are_profile_gated_not_dead():
    """Confirms these are real call sites (not literally dead code), while
    documenting that run_probe_battery.py's surface-profile boot never
    reaches them -- see QUARANTINE_PROFILE_GATED above."""
    source = _aurora_source()
    assert "worth_eval.evaluate(" in source
    assert "variant_promoter.process_solidified(" in source
    with open(
        os.path.join(os.path.dirname(AURORA_PY), "run_probe_battery.py"),
        "r", encoding="utf-8",
    ) as f:
        rpb_source = f.read()
    assert 'runtime_profile="surface"' in rpb_source, (
        "run_probe_battery.py no longer boots with runtime_profile='surface' "
        "-- if so, worth_evaluator/variant_promotion may now be reachable "
        "from probe-battery runs; update QUARANTINE_PROFILE_GATED."
    )


def test_quarantine_manifest_is_non_empty_and_documented():
    """The manifest existing and having reasons attached is itself the
    check -- an empty or undocumented quarantine is a silent accident."""
    all_quarantined = {
        **QUARANTINE_STALE,
        **QUARANTINE_PROFILE_GATED,
        **QUARANTINE_ALTERNATE_ENTRYPOINT_ONLY,
    }
    assert len(all_quarantined) >= 4
    for name, reason in all_quarantined.items():
        assert isinstance(reason, str) and len(reason) > 20, (
            f"{name} is quarantined without a real documented reason"
        )
