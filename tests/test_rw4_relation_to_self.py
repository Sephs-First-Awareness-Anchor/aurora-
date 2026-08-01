# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
RW4 -- Relation-to-self into comprehension (closes F5), wiring audit
2026-07-20 (`wiring_audit.md`).

F5 found `RelationalComparisonEngine` mounted at boot
(`systems['relational_comparison']`) with zero repo-wide readers --
the organ that implements the design doctrine's "comparison-to-self as
the origin of meaning" was constructed every boot and consulted by
nothing. RW4's smallest honest wiring: call it inside
`_apply_noncomp_input_guidance` after anchor selection, grounding the
turn's anchor concept against Aurora's own current constraint state
("I-State polarities + identity field" per the directive) via
`ground_to_self`, and deposit the resulting self-relation scalar into
the input summary alongside the anchor.

Structural tests confirm the wiring exists at the right place (this
campaign's established pattern). Unit tests exercise the two new
helpers (`_self_state_axis_pressures`, `_compute_self_relation`)
directly against a real `RelationalComparisonEngine` +
`OntologicalWeb`, not mocks, matching the zip-integration phases'
"exercise the real ported/wired function" practice. One real live-boot
test confirms `self_relation` actually appears in the input summary
after a real turn.
"""
import os
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import aurora as A  # noqa: E402


def _read_aurora_source():
    with open(os.path.join(REPO_ROOT, "aurora.py"), "r", encoding="utf-8") as f:
        return f.read()


def _apply_noncomp_input_guidance_block():
    source = _read_aurora_source()
    start = source.index("def _apply_noncomp_input_guidance(")
    end = source.index("\ndef ", start + 10)
    return source[start:end]


class _MockIdentityField:
    def __init__(self, pressures):
        self._pressures = dict(pressures)

    def axis_pressure(self, axis_int):
        _AXIS_INT_TO_STR = {0: "X", 1: "T", 2: "N", 3: "B", 4: "A"}
        return self._pressures.get(_AXIS_INT_TO_STR.get(axis_int, ""), 0.0)


class _FakeSynthesisResult:
    def __init__(self, axis_tensions):
        self.axis_tensions = dict(axis_tensions)


class _FakeCollective:
    def __init__(self, history):
        self.history = list(history)


def _real_engine_with_node(word, valence=0.4, depth=0.5, connected=()):
    from aurora_internal.aurora_ontological_scaffolding import OntologicalWeb
    from aurora_internal.aurora_relational_comparison import RelationalComparisonEngine

    web = OntologicalWeb()
    node = web.add_node(word, role="noun", valence=valence)
    node.ontological_depth = depth
    for other in connected:
        web.add_node(other, role="noun")
    return RelationalComparisonEngine(web)


def test_wiring_calls_compute_self_relation_after_anchor_selection_and_deposits_into_summary():
    block = _apply_noncomp_input_guidance_block()
    anchor_idx = block.index(
        'anchor = _select_noncomp_anchor(user_text, understood=understood, pipeline_state=pipeline_state)'
    )
    compute_idx = block.index("self_relation = _compute_self_relation(systems, anchor)")
    deposit_idx = block.index('summary["self_relation"] = self_relation')
    anchor_deposit_idx = block.index('summary["anchor"] = anchor')
    assert anchor_idx < compute_idx, "self-relation must be computed after anchor selection"
    assert anchor_deposit_idx < deposit_idx, "self_relation must land in the input summary"


def test_self_state_axis_pressures_blends_identity_field_and_istate_collective():
    systems = {
        "identity_field": _MockIdentityField({"X": 0.2, "T": 0.4, "N": 0.0, "B": 0.0, "A": 0.0}),
        "collective": _FakeCollective([_FakeSynthesisResult({"X": 0.6, "T": 0.0, "N": 0.0, "B": 0.0, "A": 0.0})]),
    }
    pressures = A._self_state_axis_pressures(systems)
    assert pressures["X"] == (0.2 + 0.6) / 2.0
    assert pressures["T"] == (0.4 + 0.0) / 2.0


def test_self_state_axis_pressures_identity_field_only_when_no_collective_history():
    systems = {"identity_field": _MockIdentityField({"X": 0.3, "T": 0.0, "N": 0.0, "B": 0.0, "A": 0.0})}
    pressures = A._self_state_axis_pressures(systems)
    assert pressures["X"] == 0.3


def test_self_state_axis_pressures_empty_when_nothing_mounted():
    assert A._self_state_axis_pressures({}) == {}


def test_compute_self_relation_grounds_anchor_against_real_engine():
    rce = _real_engine_with_node("water", valence=0.3, depth=0.6)
    systems = {
        "relational_comparison": rce,
        "identity_field": _MockIdentityField({"X": 0.1, "T": 0.1, "N": 0.3, "B": 0.1, "A": 0.1}),
    }
    result = A._compute_self_relation(systems, "water")
    assert result["anchor"] == "water"
    assert 0.0 <= result["similarity"] <= 1.0
    assert isinstance(result["relational_type"], str)
    assert "water" in result["description"]


def test_compute_self_relation_empty_without_anchor():
    rce = _real_engine_with_node("water")
    result = A._compute_self_relation({"relational_comparison": rce}, "")
    assert result == {}


def test_compute_self_relation_empty_without_engine():
    result = A._compute_self_relation({}, "water")
    assert result == {}


def test_compute_self_relation_empty_for_unknown_concept():
    rce = _real_engine_with_node("water")
    result = A._compute_self_relation({"relational_comparison": rce}, "xyzzyflorp")
    # ground_to_self returns a zeroed RelationalDelta for an unresolved node --
    # still a real dict, not an empty short-circuit, since the engine itself
    # was consulted (this is the whole point of RW4: it must be *asked*).
    assert result["anchor"] == "xyzzyflorp"
    assert result["similarity"] == 0.0


def test_live_turn_populates_self_relation_in_last_noncomp_input():
    """Real end-to-end confirmation: boot Aurora for real, run a live turn
    with a concrete anchor-bearing utterance, and confirm the self-relation
    wiring actually fired (not just structurally present)."""
    import shutil

    scratch = tempfile.mkdtemp(prefix="aurora_rw4_live_")
    try:
        scratch_state = os.path.join(scratch, "aurora_state")
        shutil.copytree(os.path.join(REPO_ROOT, "aurora_state"), scratch_state)
        systems = A.boot_aurora(state_dir=scratch_state)

        result = A.process_external_user_turn(systems, "What is the boiling point of water?")
        assert result, "live turn produced no result"

        last_input = systems.get("_last_noncomp_input") or {}
        assert "self_relation" in last_input, (
            "RW4 wiring did not run -- 'self_relation' key missing from the "
            "noncomp input summary after a real live turn"
        )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
