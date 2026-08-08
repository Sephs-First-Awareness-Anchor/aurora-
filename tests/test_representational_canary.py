# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Tests for aurora_representational_canary.py -- the cross-system canary
required by the SYSTEM-WIDE REPRESENTATIONAL CONSERVATION directive.
"""
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aurora_representational_canary import run_canary, EXPERIENCE_A, EXPERIENCE_B, MANIFOLD_DIR

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _hash_tree(root):
    digest = hashlib.sha256()
    if not os.path.isdir(root):
        return None
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in sorted(filenames):
            p = os.path.join(dirpath, fn)
            try:
                st = os.stat(p)
            except OSError:
                continue
            digest.update(f"{p}:{st.st_size}:{st.st_mtime_ns}".encode("utf-8"))
    return digest.hexdigest()


def test_canary_produces_all_eight_boundary_records(tmp_path):
    records = run_canary(state_dir=str(tmp_path))
    ids = [r.boundary for r in records]
    expected = [
        "1_semantic_matcher_classification",
        "2_manifold_field_map_accountability_weight",
        "3_live_slotcoord_construction",
        "4_warp",
        "5_genealogy_evolution_rcec",
        "6_memory_understanding_sediment_overlay",
        "6b_memory_older_sedimemory_system",
        "6c_memory_dream_episodic_system",
        "7_cognition_worth_score",
        "8_communication_behavior_actuation",
    ]
    assert ids == expected


def test_the_two_experiences_actually_differ_only_at_confirmed_independent_coordinate():
    """Sanity check on the canary's own premise: both experiences must
    classify to the same dimension (OPERATOR) but different constraints --
    otherwise the canary wouldn't isolate the intended coordinate."""
    from aurora_reflexive_interpreter import ReflexiveInterpreter
    from aurora_manifold_directory_reader import ManifoldDirectory
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        ri = ReflexiveInterpreter(directory=ManifoldDirectory(MANIFOLD_DIR), state_dir=td)
        state_a = ri.interpret(EXPERIENCE_A)
        state_b = ri.interpret(EXPERIENCE_B)
        assert state_a.dimension == state_b.dimension == "OPERATOR"
        assert state_a.constraint != state_b.constraint


def test_boundaries_marked_preserved_are_actually_distinguishable(tmp_path):
    records = run_canary(state_dir=str(tmp_path))
    for r in records:
        if r.classification == "preserved":
            assert r.distinguishable is True, (
                f"{r.boundary} is classified 'preserved' but distinguishable={r.distinguishable}"
            )


def test_boundaries_marked_unreachable_carry_no_false_distinguishable_claim(tmp_path):
    records = run_canary(state_dir=str(tmp_path))
    for r in records:
        if r.classification == "unreachable":
            assert r.distinguishable is None, (
                f"{r.boundary} is 'unreachable' but claims a distinguishable value -- "
                "an unreachable boundary cannot honestly report survival or collapse"
            )


def test_canary_run_does_not_mutate_manifold_directory_or_aurora_state():
    manifold_dir = os.path.join(REPO_ROOT, "aurora_manifold_directory")
    state_dir = os.path.join(REPO_ROOT, "aurora_state")
    before_manifold = _hash_tree(manifold_dir)
    before_state = _hash_tree(state_dir)

    run_canary()  # uses its own tempdir internally

    after_manifold = _hash_tree(manifold_dir)
    after_state = _hash_tree(state_dir)
    assert before_manifold == after_manifold
    assert before_state == after_state
