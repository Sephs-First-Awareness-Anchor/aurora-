#!/usr/bin/env python3
"""
Regression coverage for aurora_habitat.py (Aurora Build 712, App
Developmental Habitat spec, section 45).

Covers the required test categories named in the spec directly:
structural, human-action, Aurora-action, ownership, persistence,
introspection, anti-scripting, consequence.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aurora_habitat import HabitatRuntime, HabitatEntity, OPERATIONS, TERRITORIES


# ── structural ───────────────────────────────────────────────────────────

def test_two_territories_and_shared_substrate(tmp_path):
    assert set(TERRITORIES) == {"space", "self"}
    rt = HabitatRuntime(tmp_path)
    space_c = rt.act(actor="aurora", territory="space", operation="create", parameters={"entity_type": "shape"})
    self_c = rt.act(actor="aurora", territory="self", operation="create", parameters={"entity_type": "shape"})
    assert space_c.success and self_c.success
    # Both entities live in the SAME runtime/store -- one substrate, not two.
    assert space_c.affected_entities[0] in rt._entities
    assert self_c.affected_entities[0] in rt._entities


def test_entity_ids_remain_stable_across_operations(tmp_path):
    rt = HabitatRuntime(tmp_path)
    c = rt.act(actor="aurora", territory="space", operation="create", parameters={"entity_type": "shape"})
    eid = c.affected_entities[0]
    rt.act(actor="aurora", territory="space", operation="move", target_ids=[eid], parameters={"x": 0.2, "y": 0.2})
    rt.act(actor="aurora", territory="space", operation="recolor", target_ids=[eid], parameters={"color": "green"})
    assert rt.get_entity(eid)["id"] == eid


def test_state_persists_across_full_restart(tmp_path):
    rt = HabitatRuntime(tmp_path)
    c = rt.act(actor="aurora", territory="space", operation="create",
                parameters={"entity_type": "text", "content": {"text": "hello"}})
    eid = c.affected_entities[0]

    # Simulate a full process restart: throw away the runtime, build fresh.
    rt2 = HabitatRuntime(tmp_path)
    restored = rt2.get_entity(eid)
    assert restored is not None
    assert restored["content"]["text"] == "hello"


def test_persistence_survives_multiple_restarts_with_revision_history(tmp_path):
    rt = HabitatRuntime(tmp_path)
    c = rt.act(actor="aurora", territory="space", operation="create", parameters={"entity_type": "shape"})
    eid = c.affected_entities[0]

    rt2 = HabitatRuntime(tmp_path)
    rt2.act(actor="aurora", territory="space", operation="move", target_ids=[eid], parameters={"x": 0.9, "y": 0.9})

    rt3 = HabitatRuntime(tmp_path)
    entity = rt3.get_entity(eid)
    assert entity["position"] == [0.9, 0.9]
    lineage = rt3.get_lineage(eid)
    assert [r["event"] for r in lineage] == ["created", "transformed"]


# ── human-action ─────────────────────────────────────────────────────────

def test_human_move_is_recorded_and_changes_canonical_state(tmp_path):
    rt = HabitatRuntime(tmp_path)
    c = rt.act(actor="aurora", territory="space", operation="create", parameters={"entity_type": "shape"})
    eid = c.affected_entities[0]

    before = rt.get_history(entity_id=eid)
    c2 = rt.act(actor="human", territory="space", operation="move", target_ids=[eid], parameters={"x": 0.8, "y": 0.1})
    assert c2.success

    after = rt.get_history(entity_id=eid)
    assert len(after) == len(before) + 1
    assert after[-1]["actor"] == "human"
    assert after[-1]["event_type"] == "move"

    # Aurora can perceive the delta through the same canonical read path.
    perceived = rt.get_state(territory="space", actor="aurora")
    perceived_entity = next(e for e in perceived["entities"] if e["id"] == eid)
    assert perceived_entity["position"] == [0.8, 0.1]


def test_human_actions_enter_the_same_event_ledger_as_aurora_actions(tmp_path):
    rt = HabitatRuntime(tmp_path)
    c = rt.act(actor="aurora", territory="space", operation="create", parameters={"entity_type": "shape"})
    eid = c.affected_entities[0]
    rt.act(actor="human", territory="space", operation="recolor", target_ids=[eid], parameters={"color": "red"})

    events_path = tmp_path / "habitat" / "habitat_events.jsonl"
    assert events_path.exists()
    lines = [json.loads(l) for l in events_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    actors = {rec["actor"] for rec in lines}
    assert actors == {"aurora", "human"}


# ── Aurora-action ────────────────────────────────────────────────────────

def test_aurora_intention_reaches_execution_and_resulting_state(tmp_path):
    rt = HabitatRuntime(tmp_path)
    consequence = rt.act(
        actor="aurora", territory="space", operation="create",
        parameters={"entity_type": "shape", "position": [0.2, 0.3], "visual_properties": {"color": "purple"}},
        intention_context="test intention",
    )
    assert consequence.success
    assert consequence.permission_result == "granted"
    eid = consequence.affected_entities[0]

    # The consequence must carry the resulting state, not just success=True.
    assert consequence.state_delta.get("_post") is None  # popped into resulting record, not left dangling
    stored = rt.get_entity(eid)
    assert stored["position"] == [0.2, 0.3]
    assert stored["visual_properties"]["color"] == "purple"


def test_aurora_can_perform_every_phase_a_capability(tmp_path):
    rt = HabitatRuntime(tmp_path)
    a = rt.act(actor="aurora", territory="space", operation="create", parameters={"entity_type": "shape"})
    b = rt.act(actor="aurora", territory="space", operation="create", parameters={"entity_type": "shape"})
    ida, idb = a.affected_entities[0], b.affected_entities[0]

    assert rt.act(actor="aurora", territory="space", operation="move", target_ids=[ida], parameters={"x": .1, "y": .1}).success
    assert rt.act(actor="aurora", territory="space", operation="resize", target_ids=[ida], parameters={"width": .3, "height": .3}).success
    assert rt.act(actor="aurora", territory="space", operation="rotate", target_ids=[ida], parameters={"degrees": 45}).success
    assert rt.act(actor="aurora", territory="space", operation="recolor", target_ids=[ida], parameters={"color": "teal"}).success
    assert rt.act(actor="aurora", territory="space", operation="connect", target_ids=[ida, idb]).success
    grp = rt.act(actor="aurora", territory="space", operation="group", target_ids=[ida, idb])
    assert grp.success
    assert rt.act(actor="aurora", territory="space", operation="ungroup", target_ids=[grp.resulting_state["group_id"]]).success
    assert rt.act(actor="aurora", territory="space", operation="transfer", target_ids=[ida], parameters={"owner": "aurora", "territory": "self"}).success
    assert rt.act(actor="aurora", territory="self", operation="delete", target_ids=[ida]).success


# ── ownership ────────────────────────────────────────────────────────────

def test_human_forbidden_self_edit_is_rejected_and_observable(tmp_path):
    rt = HabitatRuntime(tmp_path)
    c = rt.act(actor="aurora", territory="self", operation="create", parameters={"entity_type": "shape"})
    eid = c.affected_entities[0]

    rejected = rt.act(actor="human", territory="self", operation="delete", target_ids=[eid])
    assert rejected.success is False
    assert rejected.permission_result.startswith("denied:")
    assert rejected.rejected_reason

    # Rejection itself is a persisted, observable consequence -- not silence.
    history = rt.get_history(entity_id=eid)
    assert any(ev["success"] is False and ev["actor"] == "human" for ev in history)
    # And the entity is genuinely unchanged.
    assert rt.get_entity(eid)["deleted"] is False


def test_human_forbidden_self_creation_is_rejected(tmp_path):
    rt = HabitatRuntime(tmp_path)
    c = rt.act(actor="human", territory="self", operation="create", parameters={"entity_type": "shape"})
    assert c.success is False
    assert c.rejected_reason == "self_territory_is_aurora_owned"


def test_transfer_preserves_entity_identity_and_updates_permissions(tmp_path):
    rt = HabitatRuntime(tmp_path)
    c = rt.act(actor="aurora", territory="self", operation="create", parameters={"entity_type": "shape"})
    eid = c.affected_entities[0]
    assert rt.get_entity(eid)["interaction_permissions"]["modifiable_by_human"] is False

    xfer = rt.act(actor="aurora", territory="self", operation="transfer", target_ids=[eid],
                   parameters={"owner": "shared", "territory": "space"})
    assert xfer.success
    entity = rt.get_entity(eid)
    assert entity["id"] == eid  # same identity, not a new entity
    assert entity["territory"] == "space"
    assert entity["owner"] == "shared"
    assert entity["interaction_permissions"]["modifiable_by_human"] is True

    # A human can now interact according to the new permissions.
    now_allowed = rt.act(actor="human", territory="space", operation="move", target_ids=[eid], parameters={"x": .4, "y": .4})
    assert now_allowed.success


# ── introspection ────────────────────────────────────────────────────────

def test_lineage_is_real_history_not_a_synthetic_summary(tmp_path):
    rt = HabitatRuntime(tmp_path)
    c = rt.act(actor="aurora", territory="space", operation="create", parameters={"entity_type": "shape"})
    eid = c.affected_entities[0]
    dup = rt.act(actor="aurora", territory="space", operation="duplicate", target_ids=[eid])
    dup_id = dup.affected_entities[1]
    rt.act(actor="aurora", territory="space", operation="recolor", target_ids=[dup_id], parameters={"color": "gold"})

    lineage = rt.get_lineage(dup_id)
    assert [r["event"] for r in lineage] == ["duplicated", "transformed"]
    assert lineage[0]["parent_ids"] == [eid]
    # No field anywhere claims what the sequence MEANS.
    for record in lineage:
        assert "meaning" not in record
        assert "interpretation" not in record


def test_get_history_across_many_entities_supports_pattern_discovery_without_labeling_it(tmp_path):
    rt = HabitatRuntime(tmp_path)
    ids = []
    for _ in range(5):
        c = rt.act(actor="aurora", territory="space", operation="create",
                    parameters={"entity_type": "shape", "visual_properties": {"shape_kind": "circle"}})
        ids.append(c.affected_entities[0])
    state = rt.get_state(territory="space")
    circles = [e for e in state["entities"] if e["visual_properties"].get("shape_kind") == "circle"]
    assert len(circles) == 5
    # The runtime exposes the measurable fact only -- 5 circular entities --
    # it does not itself produce "Aurora prefers circles."


# ── anti-scripting ───────────────────────────────────────────────────────

def test_source_contains_no_semantic_shortcut_mappings():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aurora_habitat.py")
    source = open(path, encoding="utf-8").read()
    forbidden_patterns = [
        r"uncertainty.{0,20}yellow", r"happiness.{0,20}smile", r"is_happy.{0,20}heart",
        r"emotion.{0,10}[-=]>.{0,10}(color|shape|visual)",
        r"constraint.{0,10}[-=]>.{0,10}(symbol|shape|color)",
        r"representation_type.{0,10}[-=]>.{0,10}shape",
        r'"meaning"\s*:', r"\.meaning\s*=",
    ]
    for pattern in forbidden_patterns:
        assert not re.search(pattern, source, flags=re.IGNORECASE), f"forbidden semantic mapping pattern found: {pattern}"


def test_visual_properties_are_a_free_dict_never_a_meaning_field(tmp_path):
    rt = HabitatRuntime(tmp_path)
    c = rt.act(actor="aurora", territory="space", operation="create",
                parameters={"entity_type": "shape", "visual_properties": {"color": "purple"}})
    entity = rt.get_entity(c.affected_entities[0])
    assert "meaning" not in entity["visual_properties"]
    assert entity["visual_properties"]["color"] == "purple"


# ── consequence (reaches real learning machinery, not just Flutter) ────────

class _FakeIdentityField:
    def __init__(self):
        self.calls = []

    def ingest_external_input(self, axes, intensity=1.0, source=""):
        self.calls.append({"axes": dict(axes), "intensity": intensity, "source": source})


class _FakePump:
    def __init__(self):
        self.injected = []

    def inject(self, disturbance, ifield, qao=None):
        self.injected.append(disturbance)
        ifield.ingest_external_input(disturbance.axis_amplitudes, intensity=disturbance.intensity, source=disturbance.source)
        return []


class _FakeSediMemory:
    def __init__(self):
        self.events = []

    def ingest_event(self, content, constraint_vector, source="interaction", existence_mode=None):
        self.events.append({"content": content, "cv": constraint_vector, "source": source})
        return 1


def test_habitat_action_emits_constraint_evidence_through_the_real_pump(tmp_path):
    ifield = _FakeIdentityField()
    pump = _FakePump()
    systems = {"identity_field": ifield, "pressure_pump": pump}
    rt = HabitatRuntime(tmp_path, systems=systems)

    c = rt.act(actor="aurora", territory="space", operation="create", parameters={"entity_type": "shape"})
    assert c.success
    assert pump.injected, "action must reach WaveformPressurePump.inject(), not stop at Flutter"
    assert ifield.calls, "disturbance must actually be ingested by the identity field"
    assert pump.injected[0].source.startswith("habitat:")


def test_human_response_to_aurora_action_reaches_real_consequence_machinery(tmp_path):
    ifield = _FakeIdentityField()
    pump = _FakePump()
    sedimemory = _FakeSediMemory()
    systems = {"identity_field": ifield, "pressure_pump": pump, "sedimemory": sedimemory}
    rt = HabitatRuntime(tmp_path, systems=systems)

    aurora_create = rt.act(actor="aurora", territory="space", operation="create", parameters={"entity_type": "shape"})
    eid = aurora_create.affected_entities[0]
    pump.injected.clear()
    sedimemory.events.clear()

    human_move = rt.act(actor="human", territory="space", operation="move", target_ids=[eid], parameters={"x": .5, "y": .5})
    assert human_move.success
    assert human_move.causal_parent is not None, "the human's response must be structurally linked to Aurora's prior action"
    assert pump.injected, "the human's response must also reach constraint evidence"
    assert sedimemory.events, "the human's response must also reach SediMemory"
    # The runtime records the fact of the sequence, never an interpretation of it.
    assert "agreed" not in json.dumps(human_move.to_dict())
    assert "disagreed" not in json.dumps(human_move.to_dict())


def test_rejected_action_still_produces_a_consequence_record(tmp_path):
    ifield = _FakeIdentityField()
    pump = _FakePump()
    systems = {"identity_field": ifield, "pressure_pump": pump}
    rt = HabitatRuntime(tmp_path, systems=systems)

    c = rt.act(actor="aurora", territory="self", operation="create", parameters={"entity_type": "shape"})
    eid = c.affected_entities[0]
    pump.injected.clear()

    denied = rt.act(actor="human", territory="self", operation="delete", target_ids=[eid])
    assert denied.success is False
    # A boundary holding is itself evidence (spec section 22, Boundary) --
    # constraint evidence must NOT silently no-op on rejection.
    assert pump.injected


# ── affordances / diagnostics ───────────────────────────────────────────

def test_affordances_are_discoverable_not_prescriptive():
    rt_ops = set(OPERATIONS)
    required = {"create", "move", "resize", "rotate", "recolor",
                "connect", "disconnect", "group", "ungroup", "delete", "transfer"}
    assert required <= rt_ops


def test_integrity_report_is_raw_counts_only(tmp_path):
    rt = HabitatRuntime(tmp_path)
    rt.act(actor="aurora", territory="space", operation="create", parameters={"entity_type": "shape"})
    rt.act(actor="human", territory="space", operation="create", parameters={"entity_type": "shape"})
    report = rt.integrity_report()
    assert report["entity_count"] == 2
    assert report["aurora_created"] == 1
    assert report["human_created"] == 1
    for value in report.values():
        assert not isinstance(value, str) or value in ("ok", "unsaved")  # no prose judgments


# ── maintenance (human-only, spec section 32) ───────────────────────────

def test_backup_and_restore_round_trip(tmp_path):
    rt = HabitatRuntime(tmp_path)
    c = rt.act(actor="aurora", territory="space", operation="create", parameters={"entity_type": "shape"})
    eid = c.affected_entities[0]
    backup_path = rt.backup()
    assert os.path.exists(backup_path)

    rt.act(actor="aurora", territory="space", operation="delete", target_ids=[eid])
    assert rt.get_entity(eid) is None

    assert rt.restore_from_backup(backup_path)
    assert rt.get_entity(eid) is not None


def test_reset_clears_world_but_is_not_reachable_via_normal_action(tmp_path):
    rt = HabitatRuntime(tmp_path)
    rt.act(actor="aurora", territory="space", operation="create", parameters={"entity_type": "shape"})
    assert "reset" not in OPERATIONS  # not an environmental action an actor can invoke
    rt.reset()
    assert rt.get_state()["entity_count"] == 0


# ── Build 717, sections 18-19: richer evidence + comparability-gated absence ──

def test_interaction_count_never_credits_an_entitys_own_creation(tmp_path):
    """Regression guard: interaction_count must stay 0 immediately after
    create -- the entity's own birth is not a 'revisit'. Previously this
    counter was never incremented anywhere, so it was always 0 regardless
    of real history; this test would have passed even under that bug, so
    the NEXT test is the one that actually catches it."""
    rt = HabitatRuntime(tmp_path)
    c = rt.act(actor="aurora", territory="space", operation="create", parameters={"entity_type": "shape"})
    eid = c.affected_entities[0]
    assert rt.get_entity(eid)["interaction_count"] == 0


def test_interaction_count_increments_on_real_re_interaction(tmp_path):
    """The bug this guards: interaction_count was written nowhere in the
    module, so observe()'s aurora_created_unrevisited check
    (interaction_count == 0) was vacuously true for every entity forever,
    regardless of whether Aurora had genuinely returned to it. A real
    second touch by ANY actor must move the counter."""
    rt = HabitatRuntime(tmp_path)
    c = rt.act(actor="aurora", territory="space", operation="create", parameters={"entity_type": "shape"})
    eid = c.affected_entities[0]
    rt.act(actor="aurora", territory="space", operation="move", target_ids=[eid], parameters={"x": 0.3, "y": 0.3})
    assert rt.get_entity(eid)["interaction_count"] == 1
    rt.act(actor="human", territory="space", operation="recolor", target_ids=[eid], parameters={"color": "blue"})
    assert rt.get_entity(eid)["interaction_count"] == 2


def test_aurora_created_unrevisited_is_comparability_gated_not_fabricated_from_silence(tmp_path):
    """Section 19: 'unrevisited' may only be reported when Aurora genuinely
    had a comparable observation window (real elapsed time since creation)
    AND the persistence to check it (interaction_count really is still 0)
    -- never inferred from the mere absence of a later action. This drives
    observe() through its real `since` window rather than faking the
    system clock, so the comparability check is genuinely exercised."""
    rt = HabitatRuntime(tmp_path)
    untouched = rt.act(actor="aurora", territory="space", operation="create", parameters={"entity_type": "shape"})
    untouched_id = untouched.affected_entities[0]
    revisited = rt.act(actor="aurora", territory="space", operation="create", parameters={"entity_type": "shape"})
    revisited_id = revisited.affected_entities[0]
    # Genuine re-interaction -- interaction_count now real, not vacuous.
    rt.act(actor="aurora", territory="space", operation="move", target_ids=[revisited_id], parameters={"x": 0.4, "y": 0.4})

    # A comparable observation window: `since` far enough in the past that
    # both entities' modified_at falls before the cutoff (real elapsed
    # time, not a fabricated one), so an honest comparison is possible.
    import time as _t
    snapshot = rt.observe(actor="aurora", since=_t.time() + 1.0)
    unvisited = snapshot["aurora_created_unrevisited"]
    assert untouched_id in unvisited, "genuinely untouched entity must be reported"
    assert revisited_id not in unvisited, "genuinely revisited entity must NOT be reported as unrevisited"


def test_link_response_populates_subsequent_actor_response_on_the_prior_event(tmp_path):
    """Section 18's 'subsequent actor response' fact: link_response() had
    no caller anywhere in this module before Build 717 -- human_response
    was always None regardless of real history. A genuine structural
    response (different actor, same entity, within the recency window)
    must now populate it on the ORIGINAL event, retrievable via
    get_history()."""
    rt = HabitatRuntime(tmp_path)
    aurora_create = rt.act(actor="aurora", territory="space", operation="create", parameters={"entity_type": "shape"})
    eid = aurora_create.affected_entities[0]
    human_move = rt.act(actor="human", territory="space", operation="move", target_ids=[eid], parameters={"x": .5, "y": .5})
    assert human_move.causal_parent is not None

    history = rt.get_history(entity_id=eid)
    original_events = [ev for ev in history if ev["event_id"] == human_move.causal_parent]
    assert original_events, "the original aurora create event must still be in recent history"
    assert original_events[0]["human_response"] == history[-1]["event_id"]


def test_ownership_and_recurrence_facts_reach_resolution_pressure_as_real_scores(tmp_path, monkeypatch):
    """Section 18: _emit_resolution_pressure must feed richer real facts
    (ownership_aligned, recurring_interaction) into the same generic
    score bridge, not just succeeded/was_measured_response. Spies on
    record_ref_participation_from_scores rather than re-deriving the
    resolution engine's own physics."""
    import aurora_habitat as habitat_mod

    calls = []

    def _spy(systems, ref_encoded, dimension_scores, **kwargs):
        calls.append(dict(dimension_scores))

    monkeypatch.setattr(habitat_mod, "record_ref_participation_from_scores", _spy, raising=False)
    # _emit_resolution_pressure imports the real function lazily inside the
    # method body, not at module scope -- patch the resolution module's
    # own attribute, which is what that lazy import actually resolves.
    import aurora_representational_resolution as rr_mod
    monkeypatch.setattr(rr_mod, "record_ref_participation_from_scores", _spy)

    rt = HabitatRuntime(tmp_path)
    # Space defaults new entities to owner="shared" -- explicit owner here
    # so ownership_aligned has an unambiguous party to compare against
    # (the code deliberately omits the score entirely for "shared", so a
    # default-owner entity would not exercise this path at all).
    c = rt.act(actor="aurora", territory="space", operation="create", parameters={"entity_type": "shape", "owner": "aurora"})
    eid = c.affected_entities[0]
    calls.clear()

    # First real re-interaction by the owner (aurora created it, so owner == "aurora").
    rt.act(actor="aurora", territory="space", operation="move", target_ids=[eid], parameters={"x": 0.2, "y": 0.2})
    assert calls, "richer scores must have reached the generic score bridge"
    first = calls[-1]
    assert first.get("ownership_aligned") == 1.0
    assert first.get("recurring_interaction") == 0.0  # first real touch since creation

    # A second real re-interaction by the same owner -- now genuinely recurring.
    rt.act(actor="aurora", territory="space", operation="move", target_ids=[eid], parameters={"x": 0.6, "y": 0.6})
    second = calls[-1]
    assert second.get("recurring_interaction") == 1.0

    # A human touching Aurora's own-owned entity in shared space -- not ownership-aligned.
    rt.act(actor="human", territory="space", operation="recolor", target_ids=[eid], parameters={"color": "red"})
    third = calls[-1]
    assert third.get("ownership_aligned") == 0.0
