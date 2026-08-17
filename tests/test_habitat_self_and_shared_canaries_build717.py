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


# ── Section 22: Self-Revisitation Canary ────────────────────────────────────

def test_self_revisitation_canary(tmp_path):
    rt = HabitatRuntime(tmp_path / "self_revisit")

    # Step 1: Aurora creates two real entities in her own real Habitat action.
    untouched = rt.act(actor="aurora", territory="space", operation="create", parameters={"entity_type": "shape"})
    untouched_id = untouched.affected_entities[0]
    revisited = rt.act(actor="aurora", territory="space", operation="create", parameters={"entity_type": "shape"})
    revisited_id = revisited.affected_entities[0]

    # Step 2: neither has been interacted with again yet -- real, not assumed.
    assert rt.get_entity(untouched_id)["interaction_count"] == 0
    assert rt.get_entity(revisited_id)["interaction_count"] == 0

    # Step 3: a comparable observation window (real elapsed-time cutoff, not
    # a fabricated one) -- both entities' modified_at falls before `since`.
    since = _time.time() + 1.0
    before_revisit = rt.observe(actor="aurora", since=since)["aurora_created_unrevisited"]
    assert untouched_id in before_revisit
    assert revisited_id in before_revisit, "not yet revisited -- correctly reported"

    # Step 4: Aurora genuinely revisits ONE of the two, via a real action.
    rt.act(actor="aurora", territory="space", operation="move", target_ids=[revisited_id], parameters={"x": 0.4, "y": 0.4})

    # Step 5: interaction_count now real (Section 18 fix) -- exactly the
    # revisited entity moved, the untouched one did not.
    assert rt.get_entity(revisited_id)["interaction_count"] == 1
    assert rt.get_entity(untouched_id)["interaction_count"] == 0

    # Step 6: the SAME comparable window now correctly distinguishes them --
    # revisited drops out, untouched remains (comparability-gated, section 19,
    # never fabricated from silence: both entities had the identical real
    # observation window; only the one with a real subsequent interaction
    # is excluded).
    since2 = _time.time() + 1.0
    after_revisit = rt.observe(actor="aurora", since=since2)["aurora_created_unrevisited"]
    assert revisited_id not in after_revisit, "genuinely revisited entity must not be reported as unrevisited"
    assert untouched_id in after_revisit, "genuinely untouched entity must still be reported"

    # Step 7 (negative control): many OTHER unrelated real actions must not
    # spuriously clear the untouched entity's own unrevisited status --
    # proves the check tracks THIS entity's real history, not global
    # activity volume.
    other = rt.act(actor="aurora", territory="space", operation="create", parameters={"entity_type": "text"})
    other_id = other.affected_entities[0]
    for _ in range(5):
        rt.act(actor="aurora", territory="space", operation="recolor", target_ids=[other_id], parameters={"color": "green"})
    since3 = _time.time() + 1.0
    final = rt.observe(actor="aurora", since=since3)["aurora_created_unrevisited"]
    assert untouched_id in final, "unrelated activity elsewhere must not clear this entity's own unrevisited status"

    # No interpretation anywhere in the observation surface.
    blob = json.dumps(rt.observe(actor="aurora", since=since3))
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
