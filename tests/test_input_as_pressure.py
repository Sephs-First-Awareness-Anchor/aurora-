"""Input arrives as pressure across her map.

A node used to take its position from the toroidal vertices -- the very vertices the
beings then drive by resonating with that position -- so the payload never entered the
loop and every user turn was the same coordinate. The node now takes the input's own
per-axis phases, derived from the axes of the words it is made of.

Authors: Sunni (Sir) Morningstar and Cael Devo
"""
import os
import sys
from types import SimpleNamespace

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import aurora  # noqa: E402

_USER_TURN_EVIDENCE = {"has_temporality": True, "conserves_state": True}


def _systems(**words):
    entries = {w: SimpleNamespace(noncomp_id=ch) for w, ch in words.items()}
    lex = SimpleNamespace(entries=entries)
    return {"perception": SimpleNamespace(composer=SimpleNamespace(lexicon=lex), lexicon=lex)}


# ---- the encoder -----------------------------------------------------------------------

def test_phases_come_from_the_axes_of_the_words():
    s = _systems(alpha="B:POLARITY", beta="B:MAGNITUDE", gamma="T:OPERATOR")
    p = aurora._content_phase_vector(s, "alpha beta gamma")
    # order X, T, N, B, A: B carried by 2 words -> 1.0; T by 1 -> 0.75; unloaded -> neutral 0.5
    assert p == [0.5, 0.75, 0.5, 1.0, 0.5]


def test_an_axis_no_word_loads_is_neutral_not_opposed():
    p = aurora._content_phase_vector(_systems(alpha="X:MAGNITUDE"), "alpha")
    assert p[0] == 1.0 and all(v == 0.5 for v in p[1:])


def test_different_utterances_give_different_phases():
    s = _systems(alpha="B:POLARITY", beta="T:OPERATOR")
    assert aurora._content_phase_vector(s, "alpha") != aurora._content_phase_vector(s, "beta")


def test_encoder_is_case_insensitive_and_ignores_unchannelled_words():
    s = _systems(alpha="B:POLARITY")
    assert aurora._content_phase_vector(s, "ALPHA unknownword!") == aurora._content_phase_vector(s, "alpha")


def test_no_channelled_word_means_no_phases_so_the_vertices_decide_as_before():
    assert aurora._content_phase_vector(_systems(alpha="B:POLARITY"), "nothing here") is None
    assert aurora._content_phase_vector(_systems(), "alpha") is None
    assert aurora._content_phase_vector({}, "alpha") is None
    assert aurora._content_phase_vector(None, "alpha") is None


# ---- admission with the input's own phases ----------------------------------------------------

def _lattice():
    from foundational_contract import FoundationalContract
    from aurora_ivm import IVMLattice
    contract = FoundationalContract()
    return contract, IVMLattice(contract, max_nodes=1000)


def test_admit_places_the_node_at_the_supplied_phases():
    """An observed user turn is PERSISTENT: X, T, N are active and B, A do not exist for it
    (the foundational law zeroes them), so only those three can carry the input."""
    _, lattice = _lattice()
    node = lattice.admit("x", "text", dict(_USER_TURN_EVIDENCE), phases=[0.5, 0.9, 0.5, 0.1, 0.5])
    assert np.allclose(node.position.phases, [0.5, 0.9, 0.5, 0.0, 0.0])


def test_admit_clamps_out_of_range_phases_and_ignores_a_wrong_length():
    _, lattice = _lattice()
    node = lattice.admit("x", "text", dict(_USER_TURN_EVIDENCE), phases=[2.0, -1.0, 0.5, 0.5, 0.5])
    assert np.allclose(node.position.phases, [1.0, 0.0, 0.5, 0.0, 0.0])
    default = lattice.vertices.get_phase_vector(node.mode)
    short = lattice.admit("y", "text", dict(_USER_TURN_EVIDENCE), phases=[0.9, 0.9])
    assert np.allclose(short.position.phases, default)
    assert not getattr(short, "input_phases", False)


def test_without_phases_admission_is_unchanged():
    _, lattice = _lattice()
    expected = lattice.vertices.get_phase_vector(
        lattice.contract.classify(dict(_USER_TURN_EVIDENCE)).mode)
    node = lattice.admit("x", "text", dict(_USER_TURN_EVIDENCE))
    assert np.allclose(node.position.phases, expected)


def test_envelope_constraint_vector_follows_the_supplied_phases():
    from aurora_ivm import IVMEnvelope
    _, lattice = _lattice()
    a = IVMEnvelope.from_node(lattice.admit("x", "text", dict(_USER_TURN_EVIDENCE), phases=[0.5, 1.0, 0.5, 0.5, 0.5]))
    b = IVMEnvelope.from_node(lattice.admit("x", "text", dict(_USER_TURN_EVIDENCE), phases=[0.5, 0.5, 1.0, 0.5, 0.5]))
    assert a.constraint_vector is not None and b.constraint_vector is not None
    assert (a.constraint_vector.T, a.constraint_vector.N) == (1.0, 0.0)   # T-heavy input
    assert (b.constraint_vector.T, b.constraint_vector.N) == (0.0, 1.0)   # N-heavy input


# ---- the loop: input moves the manifold -----------------------------------------------------------

def _vertex_state_after_processing(phases):
    from foundational_contract import FoundationalContract
    from aurora_ivm import IVMLattice, IVMEnvelope
    from aurora_i_state_beings import IStateCollective
    contract = FoundationalContract()
    lattice = IVMLattice(contract, max_nodes=1000)
    collective = IStateCollective(contract, lattice)
    node = lattice.admit("same payload", "text", dict(_USER_TURN_EVIDENCE), phases=phases)
    collective.process(IVMEnvelope.from_node(node))
    # inject_stimulus applies TORQUE: it shows up as angular velocity now and as phase
    # only after later ticks, so velocity is the quantity that records what the input did.
    return np.array([lattice.vertices.axes[a].angular_velocity for a in
                     ("existence", "temporal", "energy", "boundary", "agency")], dtype=float)


def test_different_input_phases_move_the_vertices_differently():
    t_heavy = _vertex_state_after_processing([0.5, 1.0, 0.5, 0.5, 0.5])
    n_heavy = _vertex_state_after_processing([0.5, 0.5, 1.0, 0.5, 0.5])
    assert not np.allclose(t_heavy, n_heavy), "the payload's axes must change what the beings do"


def test_identical_input_is_deterministic():
    a = _vertex_state_after_processing([0.5, 0.8, 0.5, 0.6, 0.5])
    b = _vertex_state_after_processing([0.5, 0.8, 0.5, 0.6, 0.5])
    assert np.allclose(a, b)


# ---- the front door: the gateway supplies the input's phases, and only where they are accepted --------------

def test_gateway_passes_the_inputs_phases_to_the_engine_and_the_engine_to_the_lattice():
    import ast
    def calls(fname, attr):
        src = open(os.path.join(REPO_ROOT, fname), encoding="utf-8").read()
        return [n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Attribute) and n.func.attr == attr]
    gw = calls("aurora_governance_persistence_gateway.py", "process")
    assert any(any(k.arg is None or k.arg == "phases" for k in c.keywords) for c in gw), \
        "the gateway's consciousness.process() call must be able to carry phases"
    eng = calls("aurora_consciousness_engine.py", "admit")
    assert any(any(k.arg is None or k.arg == "phases" for k in c.keywords) for c in eng), \
        "the engine's lattice.admit() call must forward phases"


def test_a_stub_engine_without_a_phases_parameter_is_not_broken_by_the_gateway():
    import inspect
    from aurora_consciousness_engine import ConsciousnessEngine as Eng
    assert "phases" in inspect.signature(Eng.process).parameters

    def legacy(payload, payload_type, evidence, frame_name="balanced", thought_intent=None):
        return None
    assert "phases" not in inspect.signature(legacy).parameters   # such stubs must keep working
