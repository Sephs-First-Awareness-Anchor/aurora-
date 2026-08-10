# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Regression tests for the SYSTEM-WIDE REPRESENTATIONAL CONSERVATION AND
PROPAGATION REPAIR DIRECTIVE's second confirmed loss-boundary repair.

CONFIRMED LOSS (before this repair): aurora.py's ConstraintFieldBalancer.
_inject_to_genealogy() (~line 4345) called genealogy.observe() with
pressure_before/pressure_after as plain dicts and trace as a list of plain
dicts, instead of the PressureVec/TraceItem objects observe() actually
requires (aurora_internal/constraint_genealogy.py:1869-1877). observe()
immediately calls pressure_after.relief_from(pressure_before)
(constraint_genealogy.py:1897) -- dict has no such method, so this raised
AttributeError on every single call, for every starved axis, every time
this ran. The surrounding try/except (aurora.py) swallowed the exception
silently, so the entire field-balance-to-genealogy relief mechanism never
functioned in production despite running every ~10 exchanges.

This is a pure wrong-type / dict-vs-object contract mismatch -- the exact
values being passed (five X/T/N/B/A floats, one ability id string) were
already correct; they just needed the correct wrapper types, which already
existed (PressureVec, TraceItem, both re-exported from
aurora_evolution_stack exactly as already used at aurora.py's other,
working genealogy.observe() call site around line 17702). No new
representational physics: this restores an existing, already-used contract.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from aurora_internal.constraint_genealogy import ConstraintGenealogyLogger, PressureVec, TraceItem


def _old_broken_shape_reproduction(genealogy):
    """Reproduces the exact pre-repair call shape (plain dicts) to prove
    the bug was real, without needing to check out the old aurora.py."""
    pv_before = {a: (0.02 if a == "B" else 0.0) for a in ("X", "T", "N", "B", "A")}
    pv_after = {a: 0.0 for a in ("X", "T", "N", "B", "A")}
    genealogy.observe(
        pressure_before=pv_before,
        trace=[{"ability": "B:INTERFACE_WEAKEN", "cost": 0.0003, "source": "field_balance"}],
        pressure_after=pv_after,
        state_sig_before="aaa", state_sig_after="bbb",
        notes={"tag": "field_balance", "axis": "B", "gradient": 0.02, "ema": 0.1},
        difference_snapshot=None,
    )


class TestBugReproduction:
    def test_plain_dict_pressure_vectors_raise_attribute_error(self, tmp_path):
        """Proves the confirmed loss: the pre-repair argument shape really
        did crash inside observe(), not merely produce a degraded result."""
        genealogy = ConstraintGenealogyLogger(run_id="bug_repro", output_dir=str(tmp_path))
        with pytest.raises(AttributeError, match="relief_from"):
            _old_broken_shape_reproduction(genealogy)


class TestRepairedContract:
    def test_pressurevec_and_traceitem_shape_succeeds(self, tmp_path):
        genealogy = ConstraintGenealogyLogger(run_id="repaired", output_dir=str(tmp_path))
        pv_before = PressureVec(**{a: (0.02 if a == "B" else 0.0) for a in ("X", "T", "N", "B", "A")})
        pv_after = PressureVec(**{a: 0.0 for a in ("X", "T", "N", "B", "A")})
        result = genealogy.observe(
            pressure_before=pv_before,
            trace=[TraceItem(kind="ABILITY", id="B:INTERFACE_WEAKEN")],
            pressure_after=pv_after,
            state_sig_before="aaa", state_sig_after="bbb",
            notes={"tag": "field_balance", "axis": "B", "gradient": 0.02, "ema": 0.1},
            difference_snapshot=None,
        )
        assert genealogy.tick_count == 1
        assert result is not None
        assert result.dominant_relief_axis == "B"
        assert result.pressure_before.B == pytest.approx(0.02)
        assert result.relief.B == pytest.approx(0.02 * 0.94, abs=0.01)  # relief_tolerance factor applied

    def test_field_balancer_inject_to_genealogy_no_longer_silently_fails(self, tmp_path):
        """End-to-end: the real ConstraintFieldBalancer._inject_to_genealogy()
        method, called against a real genealogy logger, must actually log a
        relief event for a starved axis instead of silently swallowing an
        AttributeError."""
        import aurora
        balancer = aurora.ConstraintFieldBalancer()
        # Force sustained imbalance on B so field_gradient() reports it starved.
        for _ in range(30):
            balancer.update(
                {"X": 0.60, "T": 0.15, "N": 0.10, "B": 0.05, "A": 0.10},
                systems={},
            )
        genealogy = ConstraintGenealogyLogger(run_id="fieldbal_e2e", output_dir=str(tmp_path))
        gradient_before = balancer.field_gradient()
        assert any(g >= 0.005 for g in gradient_before.values()), (
            "test setup did not produce a starved axis -- adjust the forced imbalance"
        )

        balancer._inject_to_genealogy(genealogy)

        assert genealogy.tick_count >= 1, (
            "no relief event was logged -- the type-mismatch repair regressed "
            "or the exception is still being silently swallowed"
        )
