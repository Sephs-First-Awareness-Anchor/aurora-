# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA BUILD 717, Sections 22-23 -- Self-Revisitation Canary and
Shared-Space Reciprocity Canary.

Both drive only real HabitatRuntime.act() calls (Aurora's and a human's
own production entry point) -- never a manual engine/genealogy call --
and assert on real, already-existing observation surfaces
(observe()/get_history()/get_entity()), never a fabricated interpretation
layer. Both canaries depend on the Section 18/19 repairs made in this
build: interaction_count was previously never incremented anywhere (so
"unrevisited" was vacuously true for every entity forever), and
link_response() previously had no caller (so "subsequent actor response"
was never recorded) -- these canaries are the dedicated, purpose-built
demonstrations those repairs were made for.
"""
from __future__ import annotations

import json
import time as _time

from aurora_habitat import HabitatRuntime
from aurora_habitat_motivation import maybe_engage_habitat
from aurora_internal.constraint_genealogy import ConstraintGenealogyLogger, GenealogyConfig


# ── Section 22: Self-Revisitation Canary ────────────────────────────────────

def test_self_revisitation_canary(tmp_path):
    genealogy = ConstraintGenealogyLogger(
        "self_revisit", config=GenealogyConfig(),
        output_dir=str(tmp_path / "self_revisit" / "genealogy"),
    )
    systems = {
        "genealogy": genealogy,
        "state_dir": str(tmp_path / "self_revisit" / "state"),
    }
    rt = HabitatRuntime(tmp_path / "self_revisit" / "world", systems=systems)
    systems["habitat"] = rt

    # The canary now genuinely concerns Self: Aurora-owned state is created
    # there and survives a full runtime restart.
    created = rt.act(
        actor="aurora", territory="self", operation="create",
        parameters={"entity_type": "shape"},
    )
    entity_id = created.affected_entities[0]
    assert rt.get_entity(entity_id)["territory"] == "self"
    assert rt.get_entity(entity_id)["owner"] == "aurora"
    rt = HabitatRuntime(tmp_path / "self_revisit" / "world", systems=systems)
    systems["habitat"] = rt
    assert rt.get_entity(entity_id)["territory"] == "self"

    # A real reactivated memory identity supplies the later internal reason.
    # No elapsed-time observation, revisit interval, or Self bonus participates.
    systems["_sedi_surface_frags"] = [{
        "event_id": "self-memory",
        "resonance": 1.0,
        "content": {"source": "habitat", "entity_ids": [entity_id]},
    }]
    record = maybe_engage_habitat(systems)
    assert record.engaged is True
    assert record.selected_action is not None
    assert entity_id in record.selected_action["target_ids"]
    assert record.selected_action["territory"] == "self"
    assert record.selected_action["reason"]["ownership_bonus"] == 0.0
    assert record.selected_action["candidate_score_components"].get(
        "entity:reactivated_memory_binding", 0.0,
    ) > 0.0

    history = rt.get_history(entity_id=entity_id)
    assert len(history) >= 2
    assert history[-1]["actor"] == "aurora"
    blob = json.dumps(record.to_dict())
    for word in ("lonely", "forgotten", "abandoned", "neglected"):
        assert word not in blob.lower()


# ── Section 23: Shared-Space Reciprocity Canary ─────────────────────────────

def test_shared_space_reciprocity_canary(tmp_path):
    rt = HabitatRuntime(tmp_path / "reciprocity")

    # Step 1: Aurora acts first in the shared "space" territory.
    aurora_create = rt.act(actor="aurora", territory="space", operation="create", parameters={"entity_type": "shape"})
    eid = aurora_create.affected_entities[0]

    # Step 2: the human genuinely responds -- same entity, different actor,
    # within the real recency window (_RESPONSE_LINK_WINDOW_S).
    human_move = rt.act(actor="human", territory="space", operation="move", target_ids=[eid], parameters={"x": 0.5, "y": 0.5})
    assert human_move.causal_parent is not None, "structural adjacency must be detected"

    # Step 3 (Section 18 fix): link_response() now actually fires, so the
    # ORIGINAL aurora_create event carries a real subsequent-actor-response
    # fact -- previously always None regardless of real history.
    history = rt.get_history(entity_id=eid)
    original = [ev for ev in history if ev["event_id"] == human_move.causal_parent]
    assert original, "the original event must still be in recent history"
    assert original[0]["human_response"] is not None
    assert original[0]["human_response"] == history[-1]["event_id"]

    # Step 4: reciprocity is retrievable, structural, no interpretation of
    # agreement/disagreement/sentiment anywhere in the record.
    blob = json.dumps(human_move.to_dict())
    for word in ("agreed", "disagreed", "liked", "approved", "rejected_by_human"):
        assert word not in blob.lower()

    # Step 5: symmetric in the other direction -- human acts first, Aurora
    # responds -- reciprocity is not privileged to one actor.
    human_create = rt.act(actor="human", territory="space", operation="create", parameters={"entity_type": "shape"})
    eid2 = human_create.affected_entities[0]
    aurora_response = rt.act(actor="aurora", territory="space", operation="recolor", target_ids=[eid2], parameters={"color": "blue"})
    assert aurora_response.causal_parent is not None
    history2 = rt.get_history(entity_id=eid2)
    original2 = [ev for ev in history2 if ev["event_id"] == aurora_response.causal_parent]
    assert original2 and original2[0]["human_response"] == history2[-1]["event_id"]

    # Step 6 (negative control): the SAME actor acting again on their own
    # prior action is never mistaken for reciprocity -- _find_causal_parent
    # only matches a DIFFERENT actor.
    third = rt.act(actor="human", territory="space", operation="move", target_ids=[eid2], parameters={"x": 0.2, "y": 0.2})
    # aurora_response was the most recent DIFFERENT-actor touch before this,
    # so causal_parent should point back to aurora_response's own event,
    # never to human_create (same actor as this new action).
    assert third.causal_parent is not None
    history3 = rt.get_history(entity_id=eid2)
    parent_event = next((ev for ev in history3 if ev["event_id"] == third.causal_parent), None)
    assert parent_event is not None
    assert parent_event["actor"] == "aurora", "reciprocity must link to the most recent DIFFERENT actor, never the same one"
