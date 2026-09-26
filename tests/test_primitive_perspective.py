#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_primitive_perspective.py -- Layer 2.5 required tests.

Destination: Aurora's repository `tests/` directory.

Covers Section 21 items B through J against REAL build types
(RecursionLevel, BeingResponse, ExistenceMode) rather than stand-ins:

  B  same occurrence identity and frozen pre-occurrence state
  C  execution-order invariance
  D  no cross-lineage bleed
  E  access-fence proof -- the lineages are not weighted copies
  F  pre-semantic operation
  G  existing DIFFERENCE untouched
  H  no forced convergence
  I  independent representational support survives persistence
  J  no pre-representational comparison

Item A (baseline preservation) and item K (representation-birth timing) are
exercised where the rest of the build is involved, not here.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from aurora_i_state_beings import BeingResponse
from aurora_ivm import ALIGN_GAIN, REACT_GAIN, ExistenceMode, RecursionLevel
try:
    # Its home in the repository.
    import aurora_internal.aurora_primitive_perspective as _perspective_module
except ImportError:     # the app build flattens modules into one directory
    import aurora_primitive_perspective as _perspective_module

FORBIDDEN_PROJECTION_FIELDS = _perspective_module.FORBIDDEN_PROJECTION_FIELDS
LINEAGE_P0 = _perspective_module.LINEAGE_P0
LINEAGE_P1 = _perspective_module.LINEAGE_P1
P0_ACCESS = _perspective_module.P0_ACCESS
P1_ACCESS = _perspective_module.P1_ACCESS
PerspectivePair = _perspective_module.PerspectivePair
PrimitiveOccurrenceSnapshot = _perspective_module.PrimitiveOccurrenceSnapshot
PrimitivePerspectiveEngine = _perspective_module.PrimitivePerspectiveEngine
_AlignmentAccessView = _perspective_module._AlignmentAccessView
_ReactionAccessView = _perspective_module._ReactionAccessView
AXES = ("X", "T", "N", "B", "A")
LEVELS = (RecursionLevel.SURFACE, RecursionLevel.SHALLOW, RecursionLevel.MODERATE,
          RecursionLevel.DEEP, RecursionLevel.CORE)


class _Envelope:
    def __init__(self, node_id="node_1", mode=ExistenceMode.AGENTIC, data="hello"):
        self.node_id = node_id
        self.mode = mode
        self.data = data


def _response(predicate, axis, level, displacement, resonance=0.4, silent=False):
    return BeingResponse(
        predicate=predicate, axis=axis, polarity="positive",
        input_mode=ExistenceMode.AGENTIC, required_mode=ExistenceMode.AGENTIC,
        recursion_level=level, constraint_axis=axis, silent=silent,
        resonance=resonance, constraint_displacement=displacement)


def _responses():
    return {
        "I_IS": _response("I_IS", "X", RecursionLevel.SURFACE, 0.68),
        "I_CAN": _response("I_CAN", "T", RecursionLevel.SHALLOW, 0.43),
        "I_DO": _response("I_DO", "N", RecursionLevel.MODERATE, 0.07),
        "I_SAW": _response("I_SAW", "B", RecursionLevel.DEEP, -0.34),
        "I_DID": _response("I_DID", "A", RecursionLevel.CORE, -0.64),
    }


def _snapshot(*, polarity=None, coherence=1.0, occurrence_id="occ_1",
              axes_weight=0.5, data="hello", node_id="node_1"):
    envelope = _Envelope(node_id=node_id, data=data)
    observations = {
        predicate: type("O", (), {"silent": False, "resonance": 0.4,
                                  "constraint_displacement": r.constraint_displacement})()
        for predicate, r in _responses().items()
    }
    return PrimitivePerspectiveEngine.freeze(
        envelope, observations,
        # The real key names the lattice snapshot uses.
        lattice_axes={axis: {"phase": 0.3, "positive_weight": axes_weight,
                             "negative_weight": 1.0 - axes_weight,
                             "polarity": 1.0, "at_transition": False}
                      for axis in AXES},
        global_polarity=polarity if polarity is not None
        else {axis: 0.0 for axis in AXES},
        being_continuity={p: {"coherence": coherence, "generation": 3.0}
                          for p in _responses()},
        collective_continuity={"synthesis_count": 12.0},
        occurrence_id=occurrence_id)


@pytest.fixture()
def engine(tmp_path):
    return PrimitivePerspectiveEngine(state_dir=str(tmp_path))


# ---------------------------------------------------------------------------
# B. Same occurrence
# ---------------------------------------------------------------------------

def test_both_lineages_receive_the_same_occurrence(engine):
    snapshot = _snapshot()
    pair = engine.form(snapshot, _responses())
    assert pair.p0.occurrence_id == pair.p1.occurrence_id == snapshot.occurrence_id
    assert pair.p0.source_mode == pair.p1.source_mode
    assert pair.snapshot_digest == snapshot.digest()


def test_the_snapshot_is_frozen_before_either_lineage_runs(engine):
    snapshot = _snapshot()
    responses = _responses()
    first = engine.form(snapshot, responses)
    # Mutating the live responses after the fact must not retro-change what
    # was already formed from the frozen occurrence.
    responses["I_IS"].constraint_displacement = 99.0
    assert first.p0.axis_projection["X"] == engine.last_pair.p0.axis_projection["X"]


def test_snapshot_holds_no_semantic_material(engine):
    snapshot = _snapshot(data="the cat sat on the mat")
    blob = json.dumps({
        "obs": {k: dict(v) for k, v in snapshot.observations.items()},
        "axes": {k: dict(v) for k, v in snapshot.lattice_axes.items()},
        "mode": snapshot.existence_mode,
    }).lower()
    for word in ("cat", "mat", "concept", "intent", "emotion", "topic", "draft"):
        assert word not in blob


# ---------------------------------------------------------------------------
# C. Execution-order invariance
# ---------------------------------------------------------------------------

def test_p0_first_and_p1_first_are_identical(tmp_path):
    forward = PrimitivePerspectiveEngine(state_dir=str(tmp_path / "a"))
    reverse = PrimitivePerspectiveEngine(state_dir=str(tmp_path / "b"))
    snapshot = _snapshot()
    one = forward.form(snapshot, _responses(), order=(LINEAGE_P0, LINEAGE_P1))
    two = reverse.form(snapshot, _responses(), order=(LINEAGE_P1, LINEAGE_P0))
    assert one.p0.to_dict() == two.p0.to_dict()
    assert one.p1.to_dict() == two.p1.to_dict()


def test_order_invariance_holds_across_a_run_of_occurrences(tmp_path):
    forward = PrimitivePerspectiveEngine(state_dir=str(tmp_path / "a"))
    reverse = PrimitivePerspectiveEngine(state_dir=str(tmp_path / "b"))
    for index in range(8):
        snapshot = _snapshot(occurrence_id=f"occ_{index}",
                             polarity={ax: 0.1 * index for ax in AXES})
        a = forward.form(snapshot, _responses(), order=(LINEAGE_P0, LINEAGE_P1))
        b = reverse.form(snapshot, _responses(), order=(LINEAGE_P1, LINEAGE_P0))
        assert a.to_dict() == b.to_dict(), index


# ---------------------------------------------------------------------------
# D. No cross-lineage bleed
# ---------------------------------------------------------------------------

def test_mutating_p0_state_mid_run_does_not_change_p1(tmp_path):
    engine = PrimitivePerspectiveEngine(state_dir=str(tmp_path))
    baseline = engine.form(_snapshot(), _responses())

    poisoned = PrimitivePerspectiveEngine(state_dir=str(tmp_path / "p"))
    poisoned.states[LINEAGE_P0].occurrences = 5000
    poisoned.states[LINEAGE_P0].magnitude_mean = 1234.5
    after = poisoned.form(_snapshot(), _responses())
    assert after.p1.to_dict() == baseline.p1.to_dict()


def test_mutating_p1_state_mid_run_does_not_change_p0(tmp_path):
    engine = PrimitivePerspectiveEngine(state_dir=str(tmp_path))
    baseline = engine.form(_snapshot(), _responses())

    poisoned = PrimitivePerspectiveEngine(state_dir=str(tmp_path / "p"))
    poisoned.states[LINEAGE_P1].occurrences = 5000
    poisoned.states[LINEAGE_P1].magnitude_mean = 999.0
    after = poisoned.form(_snapshot(), _responses())
    assert after.p0.to_dict() == baseline.p0.to_dict()


def test_neither_view_can_reach_the_other_lineage():
    snapshot = _snapshot()
    responses = _responses()
    reaction = _ReactionAccessView(snapshot, responses)
    alignment = _AlignmentAccessView(snapshot, responses)
    for attribute in ("p0", "p1", "pair", "other", "projection"):
        assert not hasattr(reaction, attribute)
        assert not hasattr(alignment, attribute)


# ---------------------------------------------------------------------------
# E. Access-fence proof -- not merely weighted copies
# ---------------------------------------------------------------------------

def _physical_fields(view):
    fields = {name for name in view.VIEW_FIELDS if hasattr(view, name)}
    for row in view.rows:
        fields |= set(row)
    return fields


@pytest.mark.parametrize("view_cls,access", [
    (_ReactionAccessView, P0_ACCESS), (_AlignmentAccessView, P1_ACCESS)])
def test_views_physically_hold_exactly_their_access(view_cls, access):
    """What ACCESS says exists = what the lineage can physically inspect."""
    view = view_cls(_snapshot(polarity={a: 0.4 for a in AXES}), _responses())
    assert _physical_fields(view) == set(access)
    assert not hasattr(view, "__dict__"), "a view must not accept new attributes"
    with pytest.raises(AttributeError):
        view.pre_global_polarity_backdoor = {}


def test_p0_view_contains_no_displacement_at_all():
    """Not merely unused: absent.  A future edit cannot start using what the
    view does not hold."""
    view = _ReactionAccessView(_snapshot(), _responses())
    assert "constraint_displacement" not in _physical_fields(view)
    blob = json.dumps(view.contents(), default=str)
    assert "constraint_displacement" not in blob


def test_p1_view_contains_no_local_state_and_no_extra_continuity():
    snapshot = PrimitivePerspectiveEngine.freeze(
        _Envelope(), {}, lattice_axes={"X": {"phase": 0.3, "inertia": 1.0}},
        global_polarity={"X": 0.1},
        being_continuity={"I_IS": {"coherence": 0.9, "generation": 7.0,
                                   "total_processed": 41.0, "total_silent": 3.0}},
        collective_continuity={"synthesis_count": 88.0, "history_depth": 12.0,
                               "history_capacity": 200.0})
    view = _AlignmentAccessView(snapshot, _responses())
    fields = _physical_fields(view)
    for hidden in ("local_axis_phase", "local_axis_inertia", "resonance",
                   "generation", "total_processed", "total_silent", "synthesis_count"):
        assert hidden not in fields
        assert hidden not in json.dumps(view.contents(), default=str)


def test_rows_are_read_only():
    view = _ReactionAccessView(_snapshot(), _responses())
    with pytest.raises(TypeError):
        view.rows[0]["resonance"] = 99.0


def test_projection_code_reads_only_its_view():
    """The lineage functions never reach past their view: no law table and no
    snapshot is consulted inside them.  Gains arrive as view fields."""
    import ast
    import inspect
    engine = PrimitivePerspectiveEngine
    for fn in (engine._reactive_impulse, engine._project_p0,
               engine._orientation_anchor, engine._project_p1):
        tree = ast.parse(inspect.getsource(fn).strip().replace("\n    ", "\n"))
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        for forbidden in ("REACT_GAIN", "ALIGN_GAIN", "T_COST_MULTIPLIER", "snapshot"):
            assert forbidden not in names, (fn.__name__, forbidden)


def test_same_geometry_different_history_moves_p1_only(tmp_path):
    """The proof that the lineages are informationally non-equivalent."""
    left = PrimitivePerspectiveEngine(state_dir=str(tmp_path / "l"))
    right = PrimitivePerspectiveEngine(state_dir=str(tmp_path / "r"))
    plain = left.form(_snapshot(polarity={a: 0.0 for a in AXES}, coherence=1.0),
                      _responses())
    oriented = right.form(_snapshot(polarity={a: 0.7 for a in AXES}, coherence=0.4),
                          _responses())
    assert oriented.p0.to_dict()["axis_projection"] == \
        plain.p0.to_dict()["axis_projection"]
    assert oriented.p1.to_dict()["axis_projection"] != \
        plain.p1.to_dict()["axis_projection"]


def test_the_lineages_are_not_one_generator_rescaled(engine):
    """If P1 were P0 times a constant, every axis ratio would be equal."""
    pair = engine.form(_snapshot(polarity={"X": 0.5, "T": -0.2, "N": 0.1,
                                           "B": 0.4, "A": -0.3}), _responses())
    ratios = []
    for axis, value in pair.p0.axis_projection.items():
        counterpart = pair.p1.axis_projection.get(axis, 0.0)
        if abs(value) > 1e-9 and abs(counterpart) > 1e-9:
            ratios.append(counterpart / value)
    assert len(ratios) >= 3
    assert max(ratios) - min(ratios) > 1e-6


def test_each_lineage_uses_its_own_depth_law():
    assert REACT_GAIN[RecursionLevel.SURFACE] > REACT_GAIN[RecursionLevel.CORE]
    assert ALIGN_GAIN[RecursionLevel.CORE] > ALIGN_GAIN[RecursionLevel.SURFACE]


def test_signed_polarity_is_never_abs_stripped(engine):
    pair = engine.form(_snapshot(), _responses())
    # B and A carry negative displacement in the canary occurrence.
    assert pair.p0.axis_projection["B"] < 0
    assert pair.p0.axis_projection["A"] < 0


# ---------------------------------------------------------------------------
# F. Pre-semantic proof
# ---------------------------------------------------------------------------

def test_different_text_identical_primitive_state_gives_identical_output(tmp_path):
    left = PrimitivePerspectiveEngine(state_dir=str(tmp_path / "l"))
    right = PrimitivePerspectiveEngine(state_dir=str(tmp_path / "r"))
    one = left.form(_snapshot(data="tell me about entropy"), _responses())
    two = right.form(_snapshot(data="ein völlig anderer text"), _responses())
    assert one.to_dict() == two.to_dict()


# ---------------------------------------------------------------------------
# G. Existing DIFFERENCE untouched
# ---------------------------------------------------------------------------

def _code_only(module) -> str:
    """The module's CODE, with docstrings and comments removed.

    A static test must inspect what the layer does, not the prose explaining
    what it refuses to do -- the first version of these two tests failed on
    their own documentation.
    """
    import ast
    tree = ast.parse(Path(module.__file__).read_text())
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)) and ast.get_docstring(node):
            node.body = node.body[1:] or [ast.Pass()]
    return ast.unparse(tree)


def test_no_second_difference_primitive_was_added():
    module = _perspective_module
    code = _code_only(module)
    assert "NonCompDimension" not in code
    # The only occurrences of the word may be inside the deny-list constant.
    for line in code.splitlines():
        if "difference" in line.lower() and "FORBIDDEN" not in line \
                and "forbidden" not in line:
            assert "difference_score" in line and "'" in line, line


def test_projection_cannot_carry_forbidden_fields(engine):
    pair = engine.form(_snapshot(), _responses())
    blob = json.dumps(pair.to_dict()).lower()
    for name in FORBIDDEN_PROJECTION_FIELDS:
        assert f'"{name}"' not in blob


def test_perspective_is_not_a_sixth_axis(engine):
    pair = engine.form(_snapshot(), _responses())
    assert set(pair.p0.axis_projection) <= set(AXES)
    assert set(pair.p1.axis_projection) <= set(AXES)


# ---------------------------------------------------------------------------
# H. No forced convergence
# ---------------------------------------------------------------------------

def test_shared_experience_does_not_merge_the_lineages(tmp_path):
    engine = PrimitivePerspectiveEngine(state_dir=str(tmp_path))
    for index in range(60):
        engine.form(_snapshot(occurrence_id=f"occ_{index}",
                              polarity={a: 0.3 for a in AXES}), _responses())
    final = engine.last_pair
    assert final.p0.to_dict()["axis_projection"] != \
        final.p1.to_dict()["axis_projection"]
    assert engine.states[LINEAGE_P0].magnitude_mean != \
        engine.states[LINEAGE_P1].magnitude_mean


def test_no_randomness_manufactures_divergence(tmp_path):
    first = PrimitivePerspectiveEngine(state_dir=str(tmp_path / "1"))
    second = PrimitivePerspectiveEngine(state_dir=str(tmp_path / "2"))
    assert first.form(_snapshot(), _responses()).to_dict() == \
        second.form(_snapshot(), _responses()).to_dict()


# ---------------------------------------------------------------------------
# I. Independent support survives persistence
# ---------------------------------------------------------------------------

def test_lineage_state_persists_and_rehydrates(tmp_path):
    engine = PrimitivePerspectiveEngine(state_dir=str(tmp_path))
    for index in range(7):
        engine.form(_snapshot(occurrence_id=f"occ_{index}"), _responses())
    reopened = PrimitivePerspectiveEngine(state_dir=str(tmp_path))
    for lineage in (LINEAGE_P0, LINEAGE_P1):
        assert reopened.states[lineage].to_dict() == engine.states[lineage].to_dict()
    assert reopened.formed == engine.formed


def test_support_can_be_p0_only_p1_only_or_both(engine):
    """A silent lineage contributes no support; both cases must be expressible
    and must survive a round trip through the projection's own dict form."""
    silent_for_p1 = {k: _response(k, r.constraint_axis, r.recursion_level,
                                  0.0, resonance=0.0)
                     for k, r in _responses().items()}
    pair = engine.form(_snapshot(polarity={a: 0.0 for a in AXES}), silent_for_p1)
    assert all(abs(v) < 1e-9 for v in pair.p1.axis_projection.values())
    both = engine.form(_snapshot(), _responses())
    assert both.p0.axis_projection and both.p1.axis_projection


def test_a_lineage_keeps_its_own_history_only(tmp_path):
    engine = PrimitivePerspectiveEngine(state_dir=str(tmp_path))
    for index in range(5):
        engine.form(_snapshot(occurrence_id=f"occ_{index}"), _responses())
    persisted = json.loads((tmp_path / "perspective_lineages.json").read_text())
    assert set(persisted["lineages"]) == {LINEAGE_P0, LINEAGE_P1}
    assert persisted["lineages"][LINEAGE_P0]["accessibility_signature"] != \
        persisted["lineages"][LINEAGE_P1]["accessibility_signature"]


def test_accessibility_signature_changes_if_the_fence_changes():
    _signature = _perspective_module._signature
    assert _signature(P0_ACCESS) != _signature(P1_ACCESS)
    assert _signature(P0_ACCESS) != _signature(tuple(P0_ACCESS) + ("crystals",))


# ---------------------------------------------------------------------------
# J. No pre-representational comparison
# ---------------------------------------------------------------------------

def test_the_module_imports_nothing_semantic_or_relational():
    import ast

    module = _perspective_module
    tree = ast.parse(Path(module.__file__).read_text())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
            imported.update(alias.name for alias in node.names)
    forbidden = ("RelationalComparisonEngine", "ConceptExtractor", "ConceptSignal",
                 "aurora_relational_comparison", "aurora_dimensional_systems",
                 "NonCompDimension", "crystal", "Crystal", "semantic")
    for name in forbidden:
        assert not any(name in entry for entry in imported), name


def test_there_is_no_comparator_anywhere_in_the_layer():
    """No function that compares the lineages, and no expression that
    compares one lineage's material against the other's."""
    import ast

    module = _perspective_module
    tree = ast.parse(Path(module.__file__).read_text())

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = node.name.lower().lstrip("_")
            assert not name.startswith(("compare", "difference", "diff",
                                        "agree", "disagree", "match")), node.name

    def _mentions(node, needles):
        text = ast.unparse(node).lower()
        return any(needle in text for needle in needles)

    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            left_p0 = _mentions(node.left, ("p0", "lineage_p0"))
            left_p1 = _mentions(node.left, ("p1", "lineage_p1"))
            for comparator in node.comparators:
                right_p0 = _mentions(comparator, ("p0", "lineage_p0"))
                right_p1 = _mentions(comparator, ("p1", "lineage_p1"))
                assert not ((left_p0 and right_p1) or (left_p1 and right_p0)), \
                    ast.unparse(node)

    assert not hasattr(PerspectivePair, "compare")
    assert not hasattr(PerspectivePair, "difference")


def test_the_pair_only_holds_both_views(engine):
    pair = engine.form(_snapshot(), _responses())
    assert set(pair.to_dict()) == {"occurrence_id", "snapshot_digest",
                                   "access_digest", "formation_digest", "P0", "P1"}
    assert pair.get(LINEAGE_P0) is pair.p0
    assert pair.get(LINEAGE_P1) is pair.p1


def test_diagnostics_are_read_only_and_do_not_feed_development(engine):
    engine.form(_snapshot(), _responses())
    before = {k: v.to_dict() for k, v in engine.states.items()}
    for _ in range(5):
        engine.diagnostics()
    assert {k: v.to_dict() for k, v in engine.states.items()} == before


# ---------------------------------------------------------------------------
# Real windows: every lineage-specific input is looked THROUGH, not painted on
# ---------------------------------------------------------------------------

def _window_pair(tmp_path, tag, *, phase=0.3, inertia=1.0, resonance=0.4,
                 pole="positive", displacement_scale=1.0, polarity=0.2,
                 coherence=0.8, history_depth=40.0, history_capacity=200.0):
    responses = {}
    for predicate, r in _responses().items():
        responses[predicate] = _response(
            predicate, r.constraint_axis, r.recursion_level,
            r.constraint_displacement * displacement_scale, resonance=resonance)
        responses[predicate].polarity = pole
    envelope = _Envelope()
    observations = {p: type("O", (), {"silent": False, "resonance": resonance,
                                      "constraint_displacement": r.constraint_displacement})()
                    for p, r in responses.items()}
    snapshot = PrimitivePerspectiveEngine.freeze(
        envelope, observations,
        lattice_axes={a: {"phase": phase, "inertia": inertia} for a in AXES},
        global_polarity={a: polarity for a in AXES},
        being_continuity={p: {"coherence": coherence} for p in responses},
        collective_continuity={"history_depth": history_depth,
                               "history_capacity": history_capacity},
        occurrence_id="window")
    return PrimitivePerspectiveEngine(state_dir=str(tmp_path / tag)).form(snapshot, responses)


def _view(projection):
    data = projection.to_dict()
    return data["axis_projection"], data["depth_distribution"]


# (advertised input, lineage that must move, how to vary it alone)
WINDOWS = [
    ("local_axis_phase", "P0", dict(phase=4.0)),          # crosses pi: other half of the torus
    ("local_axis_inertia", "P0", dict(inertia=3.0)),
    ("resonance", "P0", dict(resonance=0.9)),
    ("polarity", "P0", dict(pole="negative")),            # the predicate's own pole
    ("react_gain", "P0", "REACT_GAIN"),
    ("constraint_displacement", "P1", dict(displacement_scale=1.7)),
    ("pre_global_polarity", "P1", dict(polarity=-0.6)),
    ("being_coherence", "P1", dict(coherence=0.2)),
    ("collective_history_depth", "P1", dict(history_depth=180.0)),
    ("collective_history_capacity", "P1", dict(history_capacity=90.0)),
    ("align_gain", "P1", "ALIGN_GAIN"),
    ("t_cost", "P1", "T_COST_MULTIPLIER"),
]


@pytest.mark.parametrize("name,lineage,change", WINDOWS, ids=[w[0] for w in WINDOWS])
def test_each_advertised_input_moves_its_own_lineage_only(tmp_path, monkeypatch, name,
                                                         lineage, change):
    base = _window_pair(tmp_path, "base")
    if isinstance(change, str):
        table = dict(getattr(_perspective_module, change))
        if change == "T_COST_MULTIPLIER":
            # P1 sees the SHAPE of T-cost across depths (it prices where
            # alignment spends temporal energy, as a share).  A uniform
            # rescale cancels by construction -- exactly as it only rescales
            # total T-energy in Aurora's own law -- so vary the shape.
            scaled = {level: value * (3.0 if level.name == "CORE" else 1.0)
                      for level, value in table.items()}
        else:
            scaled = {level: value * 1.9 for level, value in table.items()}
        monkeypatch.setattr(_perspective_module, change, scaled)
        varied = _window_pair(tmp_path, "varied")
    else:
        varied = _window_pair(tmp_path, "varied", **change)
    mine, other = (("p0", "p1") if lineage == "P0" else ("p1", "p0"))
    assert _view(getattr(varied, mine)) != _view(getattr(base, mine)), \
        f"{name} is advertised to {lineage} but {lineage} never looks through it"
    assert _view(getattr(varied, other)) == _view(getattr(base, other)), \
        f"{name} leaked into the other lineage"


# Fields both lineages inspect: the shared identity of the occurrence and of
# each response.  Each is varied by test_each_shared_field_moves_both_lineages.
SHARED_FIELDS = ("occurrence_id", "existence_mode", "predicate",
                 "constraint_axis", "recursion_level", "silent")


def test_every_accessible_field_is_varied_by_a_test():
    """ACCESS = what tests vary, exactly.  An advertised field with no test
    fails the build; so does a test for a field no longer advertised."""
    tested = {name for name, _, _ in WINDOWS} | set(SHARED_FIELDS)
    assert tested == set(P0_ACCESS) | set(P1_ACCESS)


def test_the_lineages_draw_on_disjoint_specific_inputs():
    """Beyond the shared occurrence and response identity, each lineage's
    inputs are its own."""
    assert set(P0_ACCESS) & set(P1_ACCESS) == set(SHARED_FIELDS)


def test_t_cost_prices_alignment_it_does_not_steer_it(tmp_path, monkeypatch):
    """As in Aurora's own alignment law: T-cost is charged, not pulled."""
    base = _window_pair(tmp_path, "base")
    table = dict(_perspective_module.T_COST_MULTIPLIER)
    monkeypatch.setattr(_perspective_module, "T_COST_MULTIPLIER",
                        {level: value * 1.9 if level.name in ("SURFACE", "SHALLOW")
                         else value for level, value in table.items()})
    varied = _window_pair(tmp_path, "varied")
    assert varied.p1.axis_projection == base.p1.axis_projection
    assert varied.p1.depth_distribution != base.p1.depth_distribution


def test_p0_is_aurora_reactive_law_verbatim():
    """P0's impulse equals what ToroidalAxis.apply_torque would add to the
    frozen axis's angular velocity for the same stimulus."""
    from aurora_ivm import ToroidalAxis
    for phase in (0.3, 2.0, 3.5, 5.9):
        for pole in ("positive", "negative"):
            axis = ToroidalAxis(name="X", positive_pole="I_IS", negative_pole="I_ISNT",
                                phase=phase) if "name" in ToroidalAxis.__dataclass_fields__ \
                else ToroidalAxis(phase=phase)
            axis.inertia = 2.5
            before = axis.angular_velocity
            axis.apply_torque(0.4 * 0.3, pole == "positive",
                              react_gain=REACT_GAIN[RecursionLevel.SHALLOW])
            expected = axis.angular_velocity - before
            row = {"local_axis_phase": phase, "local_axis_inertia": 2.5, "resonance": 0.4,
                   "react_gain": REACT_GAIN[RecursionLevel.SHALLOW], "polarity": pole}
            got = PrimitivePerspectiveEngine._reactive_impulse(row)
            assert abs(got - expected) < 1e-12, (phase, pole)


# ---------------------------------------------------------------------------
# Shared fields move BOTH lineages
# ---------------------------------------------------------------------------

def _shared_pair(tmp_path, tag, mutate=None, occurrence_id="shared", mode=None):
    responses = _responses()
    if mutate:
        mutate(responses)
    envelope = _Envelope(mode=mode or ExistenceMode.AGENTIC)
    snapshot = PrimitivePerspectiveEngine.freeze(
        envelope, {}, lattice_axes={a: {"phase": 4.0, "inertia": 1.0} for a in AXES},
        global_polarity={a: 0.2 for a in AXES},
        being_continuity={p: {"coherence": 0.8} for p in responses},
        collective_continuity={"history_depth": 40.0, "history_capacity": 200.0},
        occurrence_id=occurrence_id)
    return PrimitivePerspectiveEngine(state_dir=str(tmp_path / tag)).form(snapshot, responses)


def _silence(r):
    r["I_IS"].silent = True


def _move_axis(r):
    r["I_CAN"].constraint_axis = "N"


def _deepen(r):
    r["I_IS"].recursion_level = RecursionLevel.CORE


def _rename(r):
    r["I_IS_RENAMED"] = r.pop("I_IS")


SHARED_CASES = [
    ("silent", dict(mutate=_silence)),
    ("constraint_axis", dict(mutate=_move_axis)),
    ("recursion_level", dict(mutate=_deepen)),
    ("predicate", dict(mutate=_rename)),
    ("occurrence_id", dict(occurrence_id="another")),
    ("existence_mode", dict(mode=ExistenceMode.PERSISTENT)),
]


@pytest.mark.parametrize("name,change", SHARED_CASES, ids=[c[0] for c in SHARED_CASES])
def test_each_shared_field_moves_both_lineages(tmp_path, name, change):
    base = _shared_pair(tmp_path, "base")
    varied = _shared_pair(tmp_path, "varied", **change)
    assert varied.p0.to_dict() != base.p0.to_dict(), f"{name} did not reach P0"
    assert varied.p1.to_dict() != base.p1.to_dict(), f"{name} did not reach P1"


def test_shared_cases_cover_exactly_the_shared_fields():
    assert {name for name, _ in SHARED_CASES} == set(SHARED_FIELDS)


# ---------------------------------------------------------------------------
# Provenance: digests that do not lie by omission
# ---------------------------------------------------------------------------

def _frozen(**overrides):
    kwargs = dict(
        lattice_axes={a: {"phase": 0.3, "inertia": 1.0} for a in AXES},
        global_polarity={a: 0.0 for a in AXES},
        being_continuity={p: {"coherence": 1.0} for p in _responses()},
        collective_continuity={"history_depth": 12.0, "history_capacity": 200.0},
        occurrence_id="occ_same")
    kwargs.update(overrides)
    return PrimitivePerspectiveEngine.freeze(_Envelope(), {}, **kwargs)


def test_the_reported_collision_is_gone():
    """Two snapshots with different global polarity AND continuity used to
    share one digest (d5cf6af10ed9edb7).  They must not."""
    a = _frozen()
    b = _frozen(global_polarity={x: 0.7 for x in AXES},
                being_continuity={p: {"coherence": 0.3} for p in _responses()},
                collective_continuity={"history_depth": 150.0, "history_capacity": 200.0})
    assert a.digest() != b.digest()


@pytest.mark.parametrize("override", [
    dict(global_polarity={x: 0.7 for x in AXES}),
    dict(being_continuity={p: {"coherence": 0.3} for p in _responses()}),
    dict(collective_continuity={"history_depth": 150.0, "history_capacity": 200.0}),
    dict(collective_continuity={"history_depth": 12.0, "history_capacity": 64.0}),
    dict(lattice_axes={a: {"phase": 2.2, "inertia": 1.0} for a in AXES}),
    dict(lattice_axes={a: {"phase": 0.3, "inertia": 4.0} for a in AXES}),
], ids=["global_polarity", "coherence", "history_depth", "history_capacity",
        "phase", "inertia"])
def test_every_lineage_shaping_frozen_field_changes_the_digest(override):
    assert _frozen().digest() != _frozen(**override).digest()


def test_capture_time_does_not_change_the_digest():
    import dataclasses
    snapshot = _frozen()
    later = dataclasses.replace(snapshot, captured_at=snapshot.captured_at + 3600.0)
    assert snapshot.digest() == later.digest()


def test_fields_no_lineage_can_read_are_dropped_at_the_door():
    """Informationally identical states hash identically: production's extra
    bookkeeping never enters the snapshot, a view, or the digest."""
    lean = _frozen()
    noisy = _frozen(
        lattice_axes={a: {"phase": 0.3, "inertia": 1.0, "positive_weight": 0.9,
                          "polarity": 0.9, "at_transition": False} for a in AXES},
        being_continuity={p: {"coherence": 1.0, "generation": 9.0,
                              "total_processed": 120.0, "total_silent": 4.0}
                          for p in _responses()},
        collective_continuity={"history_depth": 12.0, "history_capacity": 200.0,
                               "synthesis_count": 999.0})
    assert noisy.digest() == lean.digest()
    assert set(noisy.being_continuity["I_IS"]) == {"coherence"}
    assert set(noisy.collective_continuity) == {"history_depth", "history_capacity"}


def test_formation_digest_covers_the_committed_responses(tmp_path):
    """Responses are committed after the freeze and live in no snapshot; the
    formation digest is what identifies the perspective-generating inputs."""
    snapshot = _frozen()
    base = PrimitivePerspectiveEngine(state_dir=str(tmp_path / "a")).form(snapshot, _responses())
    changed = _responses()
    changed["I_SAW"].constraint_displacement = -0.9
    other = PrimitivePerspectiveEngine(state_dir=str(tmp_path / "b")).form(snapshot, changed)
    assert base.snapshot_digest == other.snapshot_digest
    assert base.formation_digest != other.formation_digest


def test_formation_digest_ignores_what_no_lineage_can_see(tmp_path):
    snapshot = _frozen()
    base = PrimitivePerspectiveEngine(state_dir=str(tmp_path / "a")).form(snapshot, _responses())
    unseen = _responses()
    unseen["I_IS"].required_mode = ExistenceMode.PERSISTENT     # in no view
    other = PrimitivePerspectiveEngine(state_dir=str(tmp_path / "b")).form(snapshot, unseen)
    assert base.formation_digest == other.formation_digest


# ---------------------------------------------------------------------------
# Provenance II: key order, development, and the prose
# ---------------------------------------------------------------------------

def test_key_order_never_changes_any_digest(tmp_path):
    """The reported bug: identical global polarity inserted in opposite order
    gave identical snapshot digests and identical P1 output, but different
    formation digests -- a MappingProxyType was stringified before sort_keys
    could normalise it."""
    forward = {"X": 0.1, "T": -0.2, "N": 0.3, "B": -0.4, "A": 0.5}
    backward = dict(reversed(list(forward.items())))
    assert list(forward) != list(backward) and forward == backward
    one = PrimitivePerspectiveEngine(state_dir=str(tmp_path / "f")).form(
        _frozen(global_polarity=forward), _responses())
    two = PrimitivePerspectiveEngine(state_dir=str(tmp_path / "b")).form(
        _frozen(global_polarity=backward), _responses())
    assert one.snapshot_digest == two.snapshot_digest
    assert one.p1.to_dict() == two.p1.to_dict()
    assert one.access_digest == two.access_digest
    assert one.formation_digest == two.formation_digest


def test_digests_normalise_any_mapping_type():
    from types import MappingProxyType
    plain = {"b": 2, "a": {"y": 1, "x": 0}}
    proxied = MappingProxyType({"a": MappingProxyType({"x": 0, "y": 1}), "b": 2})
    assert _perspective_module._stable_digest(plain) == \
        _perspective_module._stable_digest(proxied)


def _experienced(tmp_path, tag, experiences):
    engine = PrimitivePerspectiveEngine(state_dir=str(tmp_path / tag))
    for index in range(experiences):
        engine.form(_frozen(occurrence_id=f"prior_{index}",
                            global_polarity={x: 0.05 * index for x in AXES}), _responses())
    return engine


def test_access_digest_is_history_free_formation_digest_is_not(tmp_path):
    """The reported gap: same occurrence, same views, fresh engine versus ten
    prior experiences -- different maturity and coherence, same digest."""
    snapshot = _frozen(occurrence_id="the_same_one")
    fresh = _experienced(tmp_path, "fresh", 0).form(snapshot, _responses())
    lived = _experienced(tmp_path, "lived", 10).form(snapshot, _responses())
    assert fresh.access_digest == lived.access_digest
    assert fresh.formation_digest != lived.formation_digest
    for mine in ("p0", "p1"):
        a, b = getattr(fresh, mine), getattr(lived, mine)
        assert a.axis_projection == b.axis_projection      # history does not leak into the view
        assert a.maturity != b.maturity


def test_equal_formation_digest_means_equal_output(tmp_path):
    """Completeness: two engines whose lineage states differ ONLY in fields no
    projection can read must produce the same formation digest and the same
    pair -- and changing a field a projection does read must change both."""
    snapshot = _frozen(occurrence_id="probe")
    left = _experienced(tmp_path, "l", 6)
    right = _experienced(tmp_path, "r", 6)
    for lineage in (LINEAGE_P0, LINEAGE_P1):
        right.states[lineage].axis_recurrence = {"X": 999}
        right.states[lineage].last_occurrence_id = "somewhere_else"
        right.states[lineage].updated_at = 12345.0
        right.states[lineage].accessibility_signature = "stale"
    a = left.form(snapshot, _responses())
    b = right.form(snapshot, _responses())
    assert a.formation_digest == b.formation_digest
    assert {k: v for k, v in a.to_dict().items()} == {k: v for k, v in b.to_dict().items()}

    shifted = _experienced(tmp_path, "s", 6)
    shifted.states[LINEAGE_P1].magnitude_mean *= 3.0
    c = shifted.form(snapshot, _responses())
    assert c.formation_digest != a.formation_digest
    assert c.p1.coherence != a.p1.coherence


def test_projections_read_development_only_through_their_fenced_view():
    import ast
    import inspect
    for fn in (PrimitivePerspectiveEngine._project_p0, PrimitivePerspectiveEngine._project_p1):
        source = inspect.getsource(fn)
        tree = ast.parse(source.strip().replace("\n    ", "\n"))
        attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        assert "states" not in attrs, f"{fn.__name__} reaches the full lineage state"
    dev = _perspective_module._DevelopmentView(3, 0.5)
    assert set(dev.__slots__) == set(_perspective_module.LINEAGE_DEVELOPMENT_FIELDS)
    assert not hasattr(dev, "__dict__")


def _sees_clause(docstring, start, stop):
    paragraph = docstring[docstring.index(start):docstring.index(stop)]
    return paragraph.split("CANNOT")[0].lower()


def test_the_architecture_prose_matches_the_fence():
    """Prose is not the fence, but stale prose resurrects dead bugs.  The
    module's description of what each lineage SEES must agree with ACCESS."""
    doc = _perspective_module.__doc__
    p0 = _sees_clause(doc, "P0  reaction-access", "P1  alignment-access")
    p1 = _sees_clause(doc, "P1  alignment-access", "Both inspect")
    assert "phase" in p0 and "inertia" in p0
    for stale in ("displacement", "weight", "polarity field", "continuity"):
        assert stale not in p0, f"P0 prose claims it sees {stale!r}"
    for claimed in ("displacement", "align_gain", "t-cost", "global", "coherence"):
        assert claimed in p1
    for stale in ("resonance", "inertia", "phase"):
        assert stale not in p1, f"P1 prose claims it sees {stale!r}"
