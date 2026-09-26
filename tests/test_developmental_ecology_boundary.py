from __future__ import annotations

import json

import pytest

from aurora_internal.aurora_developmental_ecology import (
    DevelopmentalWorldJournal,
    EcologyBoundaryError,
    ExperienceEnvelope,
    build_consequence,
)


def test_ecology_event_maps_to_canonical_live_turn_without_training_shortcut():
    event = ExperienceEnvelope(
        world_id="seed_world",
        actor_id="river",
        kind="situation",
        text="The path you used yesterday is blocked by water today.",
    )

    kwargs = event.canonical_turn_kwargs()

    assert kwargs == {
        "source_label": "developmental_ecology:river",
        "session_id": "ecology:seed_world",
        "auto_search_enabled": False,
        "record_exchange": True,
        "update_interactive_state": True,
        "track_evolutionary_trace": True,
        "run_periodic_maintenance": True,
    }


def test_environment_cannot_smuggle_target_development_across_membrane():
    event = ExperienceEnvelope(
        world_id="seed_world",
        actor_id="teacher_shaped_weather",
        kind="utterance",
        text="Here is something that happened.",
        metadata={"target_meaning": "Aurora should infer causality"},
    )

    with pytest.raises(EcologyBoundaryError):
        event.validate()


def test_world_memory_is_external_and_preserves_real_consequence_relation(tmp_path):
    path = tmp_path / "world.json"
    journal = DevelopmentalWorldJournal(path, world_id="seed_world")

    cause = ExperienceEnvelope(
        world_id="seed_world",
        actor_id="mara",
        kind="entity_action",
        text="Mara leaves the blue key beneath the planter.",
    ).validate()
    journal.append_occurrence(cause)
    journal.record_reply(cause.event_id, "I will remember where Mara put it.")

    consequence = build_consequence(
        cause,
        actor_id="mara",
        text="Two days later, Mara asks Aurora where the blue key is.",
    )
    journal.append_occurrence(consequence)

    reloaded = DevelopmentalWorldJournal(path, world_id="seed_world")
    assert len(reloaded.records) == 2
    assert reloaded.records[0].aurora_reply == "I will remember where Mara put it."
    assert reloaded.records[1].envelope.consequence_of == cause.event_id
    assert reloaded.causal_children(cause.event_id)[0].envelope.event_id == consequence.event_id


def test_world_journal_rejects_duplicate_occurrence(tmp_path):
    journal = DevelopmentalWorldJournal(tmp_path / "world.json", world_id="seed_world")
    event = ExperienceEnvelope(
        world_id="seed_world",
        actor_id="clock",
        kind="world_change",
        text="The room light turns off.",
        event_id="same-event",
    ).validate()

    journal.append_occurrence(event)
    with pytest.raises(EcologyBoundaryError):
        journal.append_occurrence(event)


def test_unfinished_events_are_world_delivery_state_not_aurora_memory(tmp_path):
    journal = DevelopmentalWorldJournal(tmp_path / "world.json", world_id="seed_world")
    event = ExperienceEnvelope(
        world_id="seed_world",
        actor_id="door",
        kind="observation",
        text="A knock sounds from the other side of the door.",
    ).validate()
    journal.append_occurrence(event)

    assert [r.envelope.event_id for r in journal.unfinished()] == [event.event_id]
    journal.record_reply(event.event_id, "Who is there?")
    assert journal.unfinished() == ()


def test_envelope_round_trip_preserves_provenance_and_not_hidden_targets():
    original = ExperienceEnvelope(
        world_id="long_world",
        actor_id="entity/one",
        kind="evidence",
        text="The second measurement differs from the first.",
        parent_event_id="prior",
        metadata={"evidence_source": "instrument_7"},
    ).validate()

    restored = ExperienceEnvelope.from_dict(json.loads(json.dumps(original.to_dict())))
    assert restored == original
    assert restored.source_label == "developmental_ecology:entity_one"
    assert restored.session_id == "ecology:long_world"
