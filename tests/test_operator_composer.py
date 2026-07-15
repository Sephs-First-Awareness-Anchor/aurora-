# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
tests/test_operator_composer.py
===================================
Phase 2 of the ICC Landing / Strategic Horizon / Operator Composition
directive (2026-07-14): aurora_internal/aurora_operator_composer.py.

Makes operation composition organic -- but flows through the existing
latent -> promotion containment, never straight to active. The
explosion risk the directive warned about is contained by REUSING the
quarantine pipeline (VariantPromoter), not inventing a new one.
"""
import json
import os

from aurora_internal.aurora_operator_composer import (
    MAX_NEW_COMPOSITES_PER_TICK,
    OperatorComposer,
    _rediscovery_fixture,
    make_operator_composer,
    verify_operator_composer,
)
from aurora_internal.aurora_worth_evaluator import WorthHistory, make_worth_evaluator

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _write_fixture(tmp_path, ops=None, coupling_shapes=None):
    (tmp_path / "aurora_state").mkdir(exist_ok=True)
    (tmp_path / "aurora_genealogy").mkdir(exist_ok=True)
    fixture_ops, fixture_shapes, _loops = _rediscovery_fixture()
    ops = ops if ops is not None else fixture_ops
    coupling_shapes = coupling_shapes if coupling_shapes is not None else fixture_shapes
    (tmp_path / "aurora_state" / "operation_descriptors.json").write_text(
        json.dumps({"operations": ops, "latent_operations": []})
    )
    (tmp_path / "aurora_genealogy" / "couplings.json").write_text(
        json.dumps({"experiments": {"adoptions": [{"shape": s} for s in coupling_shapes]}})
    )
    return ops, coupling_shapes


# ---- built-in self-verification (rediscovery, 2.4) ----

def test_builtin_self_verification_all_pass():
    results = verify_operator_composer(_REPO_ROOT)
    assert results["all_passed"] is True, results["checks"]


def test_rediscovery_self_test_never_touches_real_production_state():
    """The self-test's fixture is entirely synthetic -- confirms
    verify_operator_composer() never reads/writes the real
    aurora_state/operation_descriptors.json, only in-memory fixture data."""
    real_path = os.path.join(_REPO_ROOT, "aurora_state", "operation_descriptors.json")
    before = os.path.getmtime(real_path)
    verify_operator_composer(_REPO_ROOT)
    after = os.path.getmtime(real_path)
    assert before == after


# ---- candidate selection (2.1) ----

def test_find_candidates_requires_both_scope_and_affinity_signals(tmp_path):
    ops, shapes = _write_fixture(tmp_path)
    composer = make_operator_composer(repo_root=str(tmp_path))
    _ops2, _shapes2, loops = _rediscovery_fixture()
    candidates = composer.find_candidates(operations=ops, coupling_shapes=shapes, tcl_loops=loops)
    unions = {tuple(sorted(c["union"])) for c in candidates}
    # op.unrelated (X+T) has no affinity signal covering it -- must never appear
    assert ("T", "X") not in unions


def test_find_candidates_rejects_union_already_covered_by_active_op(tmp_path):
    ops, shapes = _write_fixture(tmp_path)
    _ops2, _shapes2, loops = _rediscovery_fixture()
    # add an active op that ALREADY covers X+B+A
    ops_with_coverage = list(ops) + [{"op_id": "op.already_covers_XBA", "constraints": ["X", "B", "A"], "_generation": 1}]
    composer = make_operator_composer(repo_root=str(tmp_path))
    candidates = composer.find_candidates(operations=ops_with_coverage, coupling_shapes=shapes, tcl_loops=loops)
    unions = {tuple(sorted(c["union"])) for c in candidates}
    assert ("A", "B", "X") not in unions


def test_find_candidates_degrades_gracefully_on_malformed_input(tmp_path):
    composer = make_operator_composer(repo_root=str(tmp_path))
    assert composer.find_candidates(operations=None, coupling_shapes=None, tcl_loops=None) == [] \
        or isinstance(composer.find_candidates(operations=[{"op_id": "x"}]), list)
    # malformed op entries (missing constraints) never raise
    result = composer.find_candidates(operations=[{"op_id": "bad"}, {"constraints": ["X"]}])
    assert isinstance(result, list)


# ---- composite construction (2.2) ----

def test_composite_carries_parents_generation_and_signals(tmp_path):
    ops, shapes = _write_fixture(tmp_path)
    _ops2, _shapes2, loops = _rediscovery_fixture()
    composer = make_operator_composer(repo_root=str(tmp_path))
    promoted = {op["op_id"] for op in ops}
    composed = composer.compose_tick(
        current_tick=5.0, promoted_op_ids=promoted, operations=ops,
        coupling_shapes=shapes, tcl_loops=loops, persist=False,
    )
    assert composed
    c = composed[0]
    assert c.op_id.startswith("latent.")
    assert len(c.parents) == 2
    assert c.generation >= 2  # both parents at generation 1
    assert c.composed_at_tick == 5.0
    assert c.composition_signals  # shape or loop_id present
    desc = c.to_descriptor()
    assert desc["parents"] == list(c.parents)
    assert desc["_generation"] == c.generation
    assert desc["composed_at_tick"] == 5.0
    assert desc["composition_signals"] == c.composition_signals
    assert desc["kind"] == "composite"


def test_composite_constraints_equal_union_of_parent_scopes(tmp_path):
    ops, shapes = _write_fixture(tmp_path)
    _ops2, _shapes2, loops = _rediscovery_fixture()
    composer = make_operator_composer(repo_root=str(tmp_path))
    promoted = {op["op_id"] for op in ops}
    composed = composer.compose_tick(
        current_tick=1.0, promoted_op_ids=promoted, operations=ops,
        coupling_shapes=shapes, tcl_loops=loops, persist=False,
    )
    op_by_id = {op["op_id"]: op for op in ops}
    for c in composed:
        expected = set(op_by_id[c.parents[0]]["constraints"]) | set(op_by_id[c.parents[1]]["constraints"])
        assert set(c.constraints) == expected


# ---- containment (2.3) ----

def test_rate_cap_five_eligible_pairs_composes_exactly_two(tmp_path):
    ops, shapes = _write_fixture(tmp_path)
    _ops2, _shapes2, loops = _rediscovery_fixture()
    composer = make_operator_composer(repo_root=str(tmp_path))
    promoted = {op["op_id"] for op in ops}
    candidates = composer.find_candidates(operations=ops, coupling_shapes=shapes, tcl_loops=loops)
    assert len(candidates) >= 5, "fixture must offer at least 5 eligible pairs for this test to be meaningful"

    composed = composer.compose_tick(
        current_tick=1.0, promoted_op_ids=promoted, operations=ops,
        coupling_shapes=shapes, tcl_loops=loops, max_new=2, persist=False,
    )
    assert len(composed) == 2


def test_no_promotion_authority_composed_ops_only_ever_enter_latent(tmp_path):
    ops, shapes = _write_fixture(tmp_path)
    _ops2, _shapes2, loops = _rediscovery_fixture()
    composer = make_operator_composer(repo_root=str(tmp_path))
    promoted = {op["op_id"] for op in ops}
    composed = composer.compose_tick(
        current_tick=1.0, promoted_op_ids=promoted, operations=ops,
        coupling_shapes=shapes, tcl_loops=loops, persist=True,
    )
    assert composed

    state = json.loads((tmp_path / "aurora_state" / "operation_descriptors.json").read_text())
    active_ids = {op["op_id"] for op in state["operations"]}
    latent_ids = {op["op_id"] for op in state["latent_operations"]}
    composed_ids = {c.op_id for c in composed}
    assert composed_ids <= latent_ids
    assert not (composed_ids & active_ids)
    # OperatorComposer has no method that writes to `operations` at all --
    # structural proof, not just this one observation.
    assert not hasattr(composer, "promote") and not hasattr(composer, "_write_active")


def test_both_parents_must_be_promoted(tmp_path):
    ops, shapes = _write_fixture(tmp_path)
    _ops2, _shapes2, loops = _rediscovery_fixture()
    composer = make_operator_composer(repo_root=str(tmp_path))
    # only ONE op promoted -- no pair can pass the both-promoted gate
    composed = composer.compose_tick(
        current_tick=1.0, promoted_op_ids={"op.XB"}, operations=ops,
        coupling_shapes=shapes, tcl_loops=loops, persist=False,
    )
    assert composed == []


def test_parent_trajectory_gate_blocks_falling_parent(tmp_path):
    ops, shapes = _write_fixture(tmp_path)
    _ops2, _shapes2, loops = _rediscovery_fixture()
    composer = make_operator_composer(repo_root=str(tmp_path))
    promoted = {op["op_id"] for op in ops}

    ev = make_worth_evaluator(rng_seed=1)
    ev._histories["op.XB"] = WorthHistory("op.XB")
    for v in [0.9, 0.7, 0.5, 0.4]:
        ev._histories["op.XB"].record(v)
    assert ev._histories["op.XB"].trajectory.value == "falling"

    composed = composer.compose_tick(
        current_tick=1.0, promoted_op_ids=promoted, operations=ops,
        coupling_shapes=shapes, tcl_loops=loops, worth_evaluator=ev,
        max_new=10, persist=False,
    )
    assert all("op.XB" not in c.parents for c in composed)


def test_parent_trajectory_gate_permissive_when_no_history_yet(tmp_path):
    """No history recorded yet is NOT declining -- must not block."""
    ops, shapes = _write_fixture(tmp_path)
    _ops2, _shapes2, loops = _rediscovery_fixture()
    composer = make_operator_composer(repo_root=str(tmp_path))
    promoted = {op["op_id"] for op in ops}
    ev = make_worth_evaluator(rng_seed=1)  # no history recorded for any op
    composed = composer.compose_tick(
        current_tick=1.0, promoted_op_ids=promoted, operations=ops,
        coupling_shapes=shapes, tcl_loops=loops, worth_evaluator=ev,
        max_new=10, persist=False,
    )
    assert composed  # gate did not block everything


def test_ceiling_inert_when_latent_pool_over_boot_plus_margin(tmp_path):
    ops, shapes = _write_fixture(tmp_path)
    _ops2, _shapes2, loops = _rediscovery_fixture()
    composer = make_operator_composer(repo_root=str(tmp_path))
    assert composer._boot_latent_count == 0

    # grow the pool past boot+25 while this SAME composer instance is alive
    state = json.loads((tmp_path / "aurora_state" / "operation_descriptors.json").read_text())
    state["latent_operations"] = [{"op_id": f"latent.filler_{i}"} for i in range(30)]
    (tmp_path / "aurora_state" / "operation_descriptors.json").write_text(json.dumps(state))

    promoted = {op["op_id"] for op in ops}
    composed = composer.compose_tick(
        current_tick=1.0, promoted_op_ids=promoted, tcl_loops=loops, max_new=10, persist=False,
    )
    assert composed == []


def test_ceiling_never_exceeded_when_pool_starts_exactly_at_ceiling(tmp_path):
    """Codex review, PR #129: the ceiling check must block AT the ceiling
    (>=), not just when already past it (>) -- otherwise a tick starting
    exactly at boot+25 could still persist up to max_new more composites,
    writing past the documented hard ceiling."""
    ops, shapes = _write_fixture(tmp_path)
    _ops2, _shapes2, loops = _rediscovery_fixture()
    composer = make_operator_composer(repo_root=str(tmp_path))
    assert composer._boot_latent_count == 0

    state = json.loads((tmp_path / "aurora_state" / "operation_descriptors.json").read_text())
    state["latent_operations"] = [{"op_id": f"latent.filler_{i}"} for i in range(25)]  # exactly at ceiling
    (tmp_path / "aurora_state" / "operation_descriptors.json").write_text(json.dumps(state))

    promoted = {op["op_id"] for op in ops}
    composed = composer.compose_tick(
        current_tick=1.0, promoted_op_ids=promoted, tcl_loops=loops, max_new=10, persist=False,
    )
    assert composed == []


def test_ceiling_caps_accepted_count_to_remaining_headroom(tmp_path):
    """A tick starting a few slots below the ceiling must never accept
    more composites than remaining headroom, even if max_new and
    eligible-candidate count both exceed it."""
    ops, shapes = _write_fixture(tmp_path)
    _ops2, _shapes2, loops = _rediscovery_fixture()
    composer = make_operator_composer(repo_root=str(tmp_path))

    state = json.loads((tmp_path / "aurora_state" / "operation_descriptors.json").read_text())
    state["latent_operations"] = [{"op_id": f"latent.filler_{i}"} for i in range(24)]  # 1 slot of headroom
    (tmp_path / "aurora_state" / "operation_descriptors.json").write_text(json.dumps(state))

    promoted = {op["op_id"] for op in ops}
    composed = composer.compose_tick(
        current_tick=1.0, promoted_op_ids=promoted, operations=ops,
        coupling_shapes=shapes, tcl_loops=loops, max_new=10, persist=True,
    )
    assert len(composed) <= 1

    final_state = json.loads((tmp_path / "aurora_state" / "operation_descriptors.json").read_text())
    assert len(final_state["latent_operations"]) <= 25


def test_ceiling_still_composes_when_under_margin(tmp_path):
    ops, shapes = _write_fixture(tmp_path)
    _ops2, _shapes2, loops = _rediscovery_fixture()
    composer = make_operator_composer(repo_root=str(tmp_path))

    state = json.loads((tmp_path / "aurora_state" / "operation_descriptors.json").read_text())
    state["latent_operations"] = [{"op_id": f"latent.filler_{i}"} for i in range(10)]  # under +25
    (tmp_path / "aurora_state" / "operation_descriptors.json").write_text(json.dumps(state))

    promoted = {op["op_id"] for op in ops}
    composed = composer.compose_tick(
        current_tick=1.0, promoted_op_ids=promoted, tcl_loops=loops, max_new=2, persist=False,
    )
    assert composed


def test_ceiling_logs_reason_via_summary(tmp_path):
    """directive 2.5: 'Ceiling: latent pool over limit -> composer
    inert, logs reason' -- summary() exposes the ceiling state so a
    caller can tell WHY nothing composed."""
    ops, shapes = _write_fixture(tmp_path)
    composer = make_operator_composer(repo_root=str(tmp_path))
    summ = composer.summary()
    assert summ["latent_pool_ceiling"] == summ["boot_latent_count"] + 25
    assert summ["current_latent_count"] <= summ["latent_pool_ceiling"]


# ---- persistence ----

def test_persist_writes_only_to_latent_operations(tmp_path):
    ops, shapes = _write_fixture(tmp_path)
    _ops2, _shapes2, loops = _rediscovery_fixture()
    composer = make_operator_composer(repo_root=str(tmp_path))
    promoted = {op["op_id"] for op in ops}
    before_ops_count = len(ops)
    composed = composer.compose_tick(
        current_tick=1.0, promoted_op_ids=promoted, operations=ops,
        coupling_shapes=shapes, tcl_loops=loops, persist=True,
    )
    assert composed

    state = json.loads((tmp_path / "aurora_state" / "operation_descriptors.json").read_text())
    assert len(state["operations"]) == before_ops_count
    assert len(state["latent_operations"]) == len(composed)


def test_persist_never_duplicates_existing_op_ids(tmp_path):
    ops, shapes = _write_fixture(tmp_path)
    _ops2, _shapes2, loops = _rediscovery_fixture()
    composer = make_operator_composer(repo_root=str(tmp_path))
    promoted = {op["op_id"] for op in ops}
    composed = composer.compose_tick(
        current_tick=1.0, promoted_op_ids=promoted, operations=ops,
        coupling_shapes=shapes, tcl_loops=loops, persist=True,
    )
    count_after_first = len(json.loads((tmp_path / "aurora_state" / "operation_descriptors.json").read_text())["latent_operations"])
    # composing the exact same parents again mints the SAME op_id (hash of
    # sorted parents only, not tick) -- persisting again must not duplicate it.
    composer._persist(composed)
    count_after_second = len(json.loads((tmp_path / "aurora_state" / "operation_descriptors.json").read_text())["latent_operations"])
    assert count_after_first == count_after_second


def test_same_parent_pair_mints_identical_op_id_across_different_ticks(tmp_path):
    """Codex review, PR #129: if the same eligible gap persists across
    ticks, the op_id must be STABLE (parents-only, no tick component) so
    _persist()'s existing-op_id dedup actually catches the repeat instead
    of silently accumulating duplicate composites of the same parents
    every tick until the ceiling is hit."""
    ops, shapes = _write_fixture(tmp_path)
    _ops2, _shapes2, loops = _rediscovery_fixture()
    composer = make_operator_composer(repo_root=str(tmp_path))
    promoted = {op["op_id"] for op in ops}

    composed_tick1 = composer.compose_tick(
        current_tick=1.0, promoted_op_ids=promoted, operations=ops,
        coupling_shapes=shapes, tcl_loops=loops, max_new=10, persist=True,
    )
    assert composed_tick1

    state = json.loads((tmp_path / "aurora_state" / "operation_descriptors.json").read_text())
    latent_count_after_tick1 = len(state["latent_operations"])

    # same candidates, later tick -- the gap they cover is still uncovered
    composed_tick2 = composer.compose_tick(
        current_tick=2.0, promoted_op_ids=promoted, operations=ops,
        coupling_shapes=shapes, tcl_loops=loops, max_new=10, persist=True,
    )
    assert {c.op_id for c in composed_tick2} == {c.op_id for c in composed_tick1}

    state_after_tick2 = json.loads((tmp_path / "aurora_state" / "operation_descriptors.json").read_text())
    assert len(state_after_tick2["latent_operations"]) == latent_count_after_tick1


# ---- failure isolation ----

def test_compose_tick_never_raises_on_missing_descriptor_file(tmp_path):
    composer = make_operator_composer(repo_root=str(tmp_path))  # no aurora_state/ dir at all
    composed = composer.compose_tick(current_tick=1.0, promoted_op_ids=set(), persist=False)
    assert composed == []


def test_compose_tick_never_raises_on_corrupt_descriptor_file(tmp_path):
    (tmp_path / "aurora_state").mkdir()
    (tmp_path / "aurora_state" / "operation_descriptors.json").write_text("{not valid json")
    composer = make_operator_composer(repo_root=str(tmp_path))
    composed = composer.compose_tick(current_tick=1.0, promoted_op_ids=set(), persist=False)
    assert composed == []


def test_find_candidates_never_raises_on_corrupt_couplings_file(tmp_path):
    ops, _shapes = _write_fixture(tmp_path)
    (tmp_path / "aurora_genealogy" / "couplings.json").write_text("{not valid json")
    composer = make_operator_composer(repo_root=str(tmp_path))
    result = composer.find_candidates(operations=ops)
    assert isinstance(result, list)


# ---- public surface / privacy ----

def test_summary_exposes_no_raw_candidate_internals(tmp_path):
    ops, shapes = _write_fixture(tmp_path)
    composer = make_operator_composer(repo_root=str(tmp_path))
    summ = composer.summary()
    for forbidden in ("candidates", "operations", "coupling_shapes"):
        assert forbidden not in summ
