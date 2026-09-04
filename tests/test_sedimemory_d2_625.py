"""Regression tests for the D2/625-cell NCStrainFilter redesign
(aurora_sedimemory.py) -- the second of two items Sunni flagged as
outstanding after the causal_action stability fix (PR #221): "the 625
experiential channel". Investigation established there is no non-arbitrary
way today to feed NCStrainFilter genuine independent row+column D2
evidence, so this builds the real 625-cell machinery now (matching
aurora_representational_address.py's D2 addressing rung,
RepresentationalRef.for_d2()) while every real ingestion call site keeps
supplying only today's single ConstraintVector -- which the redesign
treats as an explicit, named diagonal pin (col := row), never a
fabricated row x col relationship. Sunni also required that Aurora
recognize discoveries as they develop: a newly-populated D2 cell now
surfaces as a StudyEvent via an optional per-call `oets` parameter,
mirroring PressureExperienceLedger._bridge_to_oets's existing pattern.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import aurora_sedimemory as sm
from aurora_representational_address import RepresentationalRef, LEVEL_D2

CHECKPOINT_PATH = os.path.join(REPO_ROOT, "aurora_state", "sedimemory_checkpoint.json")


class _FakeOets:
    def __init__(self):
        self.events = []

    def log_study_event(self, ev):
        self.events.append(ev)


def _fresh_strainer():
    return sm.NCStrainFilter()


def _fresh_mem():
    return sm.SediMemory()


def _cv(**kwargs):
    base = {"X": 0.1, "T": 0.1, "N": 0.1, "B": 0.1, "A": 0.1}
    base.update(kwargs)
    return sm.ConstraintVector(**base)


# ---------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------

def test_625_signatures_and_25_d1_basis_built():
    f = _fresh_strainer()
    assert len(f._signatures) == 625
    assert len(f._d1_signatures) == 25


def test_625_basins_built():
    mem = _fresh_mem()
    assert len(mem._column._basins) == 625


# ---------------------------------------------------------------------
# Diagonal equivalence -- the load-bearing correctness guarantee
# ---------------------------------------------------------------------

def test_diagonal_resonance_equals_legacy_25cell_resonance():
    """Frozen, verbatim copy of the pre-D2 25-cell signature/resonance
    formula, kept inline as an oracle (not imported from the module, so a
    future accidental change to the real formula is caught rather than
    silently inherited). Verified exact float equality against the new
    diagonal cells for several real vectors."""
    f = _fresh_strainer()

    def legacy_signature(constraint, dimension):
        dim_mods = {
            sm.NonCompDimension.POLARITY:   [0.1, 0.0, 0.0, 0.0, 0.0],
            sm.NonCompDimension.MAGNITUDE:  [0.0, 0.1, 0.0, 0.0, 0.0],
            sm.NonCompDimension.OPERATOR:   [0.0, 0.0, 0.1, 0.0, 0.0],
            sm.NonCompDimension.COST:       [0.0, 0.0, 0.0, 0.1, 0.0],
            sm.NonCompDimension.DIFFERENCE: [0.0, 0.0, 0.0, 0.0, 0.1],
        }
        base = [0.1] * 5
        base[constraint.value] = 0.9
        mod = dim_mods[dimension]
        vec = [max(0.01, base[i] + mod[i]) for i in range(5)]
        vec[0] = max(0.05, vec[0])
        return sm.ConstraintVector(X=vec[0], T=vec[1], N=vec[2], B=vec[3], A=vec[4])

    def legacy_resonance(event_cv, sig):
        a = event_cv.to_array()
        b = sig.to_array()
        dot = float(a @ b)
        norm = float((a @ a) ** 0.5) * float((b @ b) ** 0.5)
        return 0.0 if norm < 1e-9 else max(0.0, min(1.0, dot / norm))

    probe_vectors = [
        _cv(X=1.0), _cv(T=1.0), _cv(N=1.0), _cv(B=1.0), _cv(A=1.0),
        sm.ConstraintVector(X=1.0, T=0.5, N=0.8, B=0.3, A=0.2),
    ]
    for cv in probe_vectors:
        cells = f._resonant_cells(cv, None)
        cell_by_pos = {(rc, rd): res for (rc, rd, cc, cd, res) in cells}
        for constraint in sm.Constraint.all():
            for dimension in sm.NonCompDimension:
                expected = legacy_resonance(cv, legacy_signature(constraint, dimension))
                if expected >= f.resonance_threshold:
                    assert cell_by_pos[(constraint, dimension)] == expected
                else:
                    assert (constraint, dimension) not in cell_by_pos


def test_diagonal_only_when_no_col_evidence():
    f = _fresh_strainer()
    event = sm.MemoryEvent.create(
        content={"user_text": "hello"},
        constraint_vector=sm.ConstraintVector(X=1.0, T=0.5, N=0.8, B=0.3, A=0.2),
        source="test",
    )
    frags = f.strain(event)
    assert frags
    for frag in frags.values():
        assert frag.constraint == frag.col_constraint
        assert frag.dimension == frag.col_dimension


def test_off_diagonal_reachable_with_independent_col_evidence():
    """Proof the 625-cell machinery is real and reachable, not dead code:
    an event with independent column evidence must produce at least one
    genuine off-diagonal fragment."""
    f = _fresh_strainer()
    row_cv = _cv(X=1.0)
    col_cv = _cv(T=1.0)
    event = sm.MemoryEvent.create(
        content={"user_text": "hello"},
        constraint_vector=row_cv,
        col_constraint_vector=col_cv,
        source="test",
    )
    frags = f.strain(event)
    off_diagonal = [
        frag for frag in frags.values()
        if (frag.constraint, frag.dimension) != (frag.col_constraint, frag.col_dimension)
    ]
    assert off_diagonal, "expected at least one off-diagonal fragment with independent column evidence"


def test_slot_id_is_representational_ref_d2_encoding():
    bid = sm._slot_id_for(
        sm.Constraint.X, sm.NonCompDimension.POLARITY,
        sm.Constraint.T, sm.NonCompDimension.MAGNITUDE,
    )
    ref = RepresentationalRef.decode(bid)
    assert ref.level() == LEVEL_D2
    assert ref.nc_law_c == "X" and ref.nc_dim == "POLARITY"
    assert ref.col_law_c == "T" and ref.col_law_d == "MAGNITUDE"


def test_spoke_weights_diagonal_equivalence():
    """4-term formula must reduce to the original 2-term formula exactly
    whenever every basin involved is diagonal (col == row) -- always true
    for real traffic today."""
    mem = _fresh_mem()
    basins = mem._column._basins
    dom_id = sm._slot_id_for(sm.Constraint.A, sm.NonCompDimension.COST, sm.Constraint.A, sm.NonCompDimension.COST)
    spoke_id = sm._slot_id_for(sm.Constraint.X, sm.NonCompDimension.POLARITY, sm.Constraint.X, sm.NonCompDimension.POLARITY)
    weights = sm._spoke_weights(dom_id, frozenset([dom_id, spoke_id]), basins)

    dom_basin = basins[dom_id]
    spoke_basin = basins[spoke_id]
    axis_dist = abs(sm.AXIS_DEPTH_ORDER.index(dom_basin.axis) - sm.AXIS_DEPTH_ORDER.index(spoke_basin.axis)) / 4.0
    dim_dist = abs(dom_basin.dimension.value - spoke_basin.dimension.value) / 4.0
    legacy_proximity = 1.0 - (axis_dist + dim_dist) / 2.0

    assert weights[dom_id] == 1.0
    assert weights[spoke_id] == max(0.1, round(legacy_proximity, 4))


# ---------------------------------------------------------------------
# Migration
# ---------------------------------------------------------------------

def test_migration_legacy_checkpoint():
    assert os.path.exists(CHECKPOINT_PATH), "real checkpoint fixture must exist"
    with open(CHECKPOINT_PATH) as fh:
        data = json.load(fh)

    mem = _fresh_mem()
    restored_deep = mem.load_deep(data["sedimemory_deep"])
    restored_chan = mem.load_channels(data["sedimemory_channels"])

    assert restored_deep == 10
    assert restored_chan == 24

    for basin_id, basin in mem._column._basins.items():
        if basin.compressed_mass:
            ref = RepresentationalRef.decode(basin_id)
            assert ref.level() == LEVEL_D2
            assert ref.nc_law_c == ref.col_law_c and ref.nc_dim == ref.col_law_d

    for legacy_key, orig_mass in data["sedimemory_deep"].items():
        if legacy_key.startswith("_"):
            continue
        new_key = sm._migrate_basin_id(legacy_key)
        basin = mem._column._basins.get(new_key)
        assert basin is not None
        assert basin.compressed_mass == orig_mass

    reg = mem._column._path_reg
    for ch in reg._channels.values():
        for bid in ch.target_basin_ids:
            assert bid.startswith("REF:")
        assert ch.dominant_slot_id.startswith("REF:")


def test_migrate_basin_id_idempotent_on_already_migrated():
    new_id = sm._slot_id_for(sm.Constraint.B, sm.NonCompDimension.COST, sm.Constraint.B, sm.NonCompDimension.COST)
    assert sm._migrate_basin_id(new_id) == new_id


# ---------------------------------------------------------------------
# Discovery surfacing
# ---------------------------------------------------------------------

def test_first_cell_population_logs_study_event():
    mem = _fresh_mem()
    oets = _FakeOets()
    cv = sm.ConstraintVector(X=1.0, T=0.5, N=0.8, B=0.3, A=0.2)

    mem.ingest_event(content={"user_text": "hi"}, constraint_vector=cv, source="test", oets=oets)

    assert len(oets.events) == 25  # 25 diagonal cells, all first-time
    assert all(ev.announce_worthy for ev in oets.events)
    assert all(ev.autonomy_mode == "sediment_discovery" for ev in oets.events)


def test_second_ingest_does_not_reannounce():
    mem = _fresh_mem()
    oets = _FakeOets()
    cv = sm.ConstraintVector(X=1.0, T=0.5, N=0.8, B=0.3, A=0.2)

    mem.ingest_event(content={"user_text": "hi"}, constraint_vector=cv, source="test", oets=oets)
    mem.ingest_event(content={"user_text": "hi again"}, constraint_vector=cv, source="test", oets=oets)

    assert len(oets.events) == 25  # unchanged after 2nd deposit into the same cells


def test_no_oets_param_no_crash():
    mem = _fresh_mem()
    cv = sm.ConstraintVector(X=1.0, T=0.5, N=0.8, B=0.3, A=0.2)
    n = mem.ingest_event(content={"user_text": "hi"}, constraint_vector=cv, source="test")
    assert n == 25


def test_cross_restart_accuracy_suppresses_known_deep_cells():
    """total_deposited pre-marking (via _populated_basin_ids in the
    checkpoint) must prevent a fresh boot from re-announcing B/A cells it
    already knew about, while still legitimately re-discovering X/T/N
    (ephemeral, never checkpointed by existing design)."""
    cv_b = sm.ConstraintVector(X=0.1, T=0.1, N=0.1, B=1.0, A=0.1)

    mem1 = _fresh_mem()
    mem1.ingest_event(content={"boundary": "test"}, constraint_vector=cv_b, source="test")
    checkpoint = mem1.save_deep()
    assert "_populated_basin_ids" in checkpoint

    oets = _FakeOets()
    mem2 = _fresh_mem()
    mem2.load_deep(checkpoint)
    mem2.ingest_event(content={"boundary": "test2"}, constraint_vector=cv_b, source="test", oets=oets)

    b_or_a = [ev for ev in oets.events if ev.studied_items[0]["row_axis"] in ("B", "A")]
    assert not b_or_a, "B/A cells must not re-announce as discoveries after restart"


# ---------------------------------------------------------------------
# Performance guard
# ---------------------------------------------------------------------

def test_performance_soft_benchmark():
    import time as _time

    mem = _fresh_mem()
    cv = sm.ConstraintVector(X=1.0, T=0.5, N=0.8, B=0.3, A=0.2)
    n_iters = 200
    t0 = _time.perf_counter()
    for i in range(n_iters):
        mem.ingest_event(content={"user_text": f"msg {i}"}, constraint_vector=cv, source="test")
    elapsed_ms_per_event = (_time.perf_counter() - t0) * 1000.0 / n_iters
    # Generous bound -- a real regression guard, not a strict SLA. Measured
    # locally well under 1ms/event for the diagonal-only-when-pinned path.
    assert elapsed_ms_per_event < 5.0, f"strain()/ingest() cost {elapsed_ms_per_event:.3f}ms/event, expected <5ms"


# ---------------------------------------------------------------------
# Real-boot integration
# ---------------------------------------------------------------------

def test_real_boot_sedimemory_is_625_cells():
    import shutil
    import aurora

    scratch = tempfile.mkdtemp(prefix="aurora_sedimemory_d2_625_realboot_")
    shutil.copytree(os.path.join(REPO_ROOT, "aurora_state"), os.path.join(scratch, "aurora_state"))
    systems = aurora.boot_aurora(state_dir=os.path.join(scratch, "aurora_state"), verbose=False)

    sedi = systems.get("sedimemory")
    assert sedi is not None
    assert len(sedi._column._basins) == 625

    for turn_text in (
        "I need to protect my boundaries here",
        "existence itself feels uncertain right now",
        "time keeps slipping away from me",
    ):
        aurora.process_external_user_turn(systems, turn_text)

    assert len(sedi._column._basins) == 625
