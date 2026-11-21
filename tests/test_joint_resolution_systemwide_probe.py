"""Cross-system, production-read-only joint resolution probe.

The proposed joint view is built ONLY inside this test file. Nothing here
changes Aurora's learning, representation authority or output pipelines.

Intended interpretation:
* Native individual views and downstream calculation are directly exercised.
* A test-local joint view establishes whether a missing combination could help.
* Passing tests do NOT mean live cognition, recall or speech adopted that view.
"""
from dataclasses import replace

import aurora_representational_resolution as rr
import aurora_habitat_motivation as hm
from aurora_representational_address import RepresentationalRef
from aurora_internal.crystal_facets import FacetBook
from aurora_internal.aurora_live_possibility_frontier import _extract_representational_refs
from aurora_internal.aurora_confluence import plan as confluence_plan


def _base():
    return RepresentationalRef.for_c1("X", "MAGNITUDE", "A")


def _sources():
    base = _base()
    first = replace(base, sub_law_c="T", sub_law_d="POLARITY")
    second = replace(base, col_law_c="B", col_law_d="DIFFERENCE")
    return [
        ("real:first", first, {"subject": "entity-1", "episode": "episode-1", "basis": "observed"}),
        ("real:second", second, {"subject": "entity-1", "episode": "episode-1", "basis": "observed"}),
    ]


def _shadow_joint(base, sources):
    """Experimental composition, NOT a production Aurora function.

    The identity and circumstance checks here exist to stop a test from
    treating unrelated evidence as a single observation. A production
    implementation would need grounding against her actual event lineage.
    """
    if len(sources) < 2:
        return None
    contexts = [(ev.get("subject"), ev.get("episode")) for _, _, ev in sources]
    if any(not a or not b for a, b in contexts) or len(set(contexts)) != 1:
        return None
    if any(ev.get("basis") not in ("observed", "recurrence") for _, _, ev in sources):
        return None
    out = base
    used = set()
    for source_id, source, _ in sources:
        if any(
            getattr(source, name) != getattr(base, name)
            for name in ("nc_law_c", "nc_dim", "nc_target")
        ):
            return None
        for field in base.unresolved_fields():
            val = getattr(source, field)
            if val is None:
                continue
            prior = getattr(out, field)
            if prior is not None and prior != val:
                return None
            out = replace(out, **{field: val})
            used.add(source_id)
    return out if len(used) >= 2 else None


def test_existing_native_frontier_does_not_make_joint_view():
    base = _base()
    source1, source2 = _sources()
    native = rr.build_perspective_projections(base, [source1, source2], max_projections=None)
    assert native
    assert not any(
        (view["exposed_fields"].get("sub_law_c") == "T"
         and view["exposed_fields"].get("col_law_c") == "B")
        for view in native
    )
    shadow = _shadow_joint(base, [source1, source2])
    assert shadow is not None
    assert shadow.sub_law_c == "T" and shadow.col_law_c == "B"
    assert all(getattr(base, field) is None for field in base.unresolved_fields())


def test_context_collision_and_unqualified_source_do_not_combine():
    base = _base()
    left, right = _sources()
    assert _shadow_joint(base, [left, (right[0], right[1], {**right[2], "episode": "other"})]) is None
    assert _shadow_joint(base, [left, (right[0], right[1], {**right[2], "subject": "other"})]) is None
    assert _shadow_joint(base, [left, (right[0], right[1], {**right[2], "basis": "dreamed"})]) is None
    conflict = replace(right[1], sub_law_c="N")
    assert _shadow_joint(base, [left, (right[0], conflict, right[2])]) is None


def test_perception_and_recall_refs_reach_shared_possibility_input_without_being_fused():
    a, b = _sources()
    seen = _extract_representational_refs(
        {"perception": {"representational_ref": a[1].encode()}},
        {"memory": [{"representational_ref": b[1].encode()}]},
    )
    assert set(seen) == {a[1].encode(), b[1].encode()}


def test_historical_contexts_remain_separate_and_recollection_does_not_count():
    book = FacetBook()
    for ref, episode, context in (
        ("e1", "first", "quiet_room"),
        ("e2", "second", "crowded_room"),
    ):
        assert book.add("person", "condition", "responds", {"predicate": "responds"},
                        ref=ref, basis="observed", context={"episode": episode, "room": context},
                        consequence={"change": context}, occurrence_class="perceived")
    assert book.add("person", "condition", "responds", {"predicate": "responds"},
                    ref="dream1", basis="supposed", context={"episode": "dream"},
                    occurrence_class="dreamed")
    occasions = book.counted_occasions("person")
    assert len(occasions) == 2
    assert {ev["context"]["room"] for ev in occasions} == {"quiet_room", "crowded_room"}
    assert book.to_dict() == FacetBook.from_dict(book.to_dict()).to_dict()


def _habitat_score(ref):
    base = _base()
    dimensions = ["persistence", "territory_boundary"]
    # Physical consequence weights, normalized from aurora_habitat.py.
    axis_profile = {"X": .2, "T": 1.0, "N": 0., "B": .8, "A": .28}
    internal = {
        "axis_strength": {"T": 1.0},
        "native_dimensions": {},
        "resolution_context": {"T": {
            "provisional_candidate": {"field": "sub_law_c", "value": "T", "ref_encoded": base.encode()},
            "_without_ref": base,
            "_with_ref": ref,
            "representation_without_candidate": base.encode(),
            "representation_with_candidate": ref.encode(),
        }},
    }
    return hm._score_affordance(
        internal, {}, dimensions, axis_profile, 0., {}, 1.0
    )


def test_actual_habitat_consumer_can_discriminate_joint_view_better_than_either():
    base = _base()
    (_, a, _), (_, b, _) = _sources()
    joint = _shadow_joint(base, _sources())
    assert joint is not None
    sa, sb, sj = (_habitat_score(v)[0] for v in (a, b, joint))
    assert sj > max(sa, sb) + .01
    # This establishes a real consumer arithmetic benefit, NOT an observed
    # Habitat consequence or a change in Aurora's present understanding.


def test_communication_planner_can_consume_a_qualified_conclusion_if_supplied():
    # Demonstrates a consumer contract only. The joint inference is NOT
    # generated by confluence here and cannot be claimed as Aurora knowledge.
    item = {
        "source": "context", "target": "response", "axis": "X",
        "asked": True, "derived": True,
        "lex": {"agent": "context", "action": "changes", "object": "response",
                "predicate": "change"},
    }
    clauses = confluence_plan(
        {"stance": {}, "options": [], "knowledge": [item]},
        {"clauses": 1, "axis_order": ["X"], "generation_role": "PRIMARY"},
    )
    assert clauses and clauses[0]["system"] == "knowledge"
    assert clauses[0]["relation"]["derived"] is True


def test_shadow_view_does_not_acquire_any_resolution_authority():
    base = _base()
    before = base.encode()
    joint = _shadow_joint(base, _sources())
    assert joint is not None
    assert base.encode() == before
    # A view is not evidence, nor permission to call resolve_field.
    assert rr.build_perspective_projections(base, _sources(), max_projections=None)
