# Aurora Developmental Ecology Boundary

## Purpose

Aurora no longer primarily needs a human to manually manufacture enough developmental pressure through occasional conversation. She needs a persistent external ecology capable of supplying recurring situations, entities, evidence, novelty, unfinished threads and consequences while leaving interpretation and development inside Aurora.

The environment is **not another cognitive layer inside Aurora** and is **not a trainer with a target answer**.

> Give Aurora experience. Never give her the development the experience is supposed to produce.

## Current live seam

The current Android path already has the correct causal doorway:

```text
Flutter -> AuroraService -> aurora_bridge.handle_message()
        -> aurora.process_external_user_turn()
        -> canonical live response/reasoning pipeline
```

`process_external_user_turn()` already accepts `source_label` and `session_id`, publishes canonical turn identity/provenance, freezes the present sensory frame, and carries the occurrence through the same live machinery. The Flutter bridge already uses `source_label="flutter_ui"`, while file upload and autonomous sensory traffic use their own provenance labels.

That means the ecology does **not** need a new training pipeline. It needs a new external transport that terminates at this existing doorway.

## System boundary

```text
                         OUTSIDE AURORA

  Persistent Developmental World
  + world journal
  + actors / situations
  + temporal recurrence
  + consequences
  + optional evidence scouts
  + optional AI-operated actors
               |
               | ExperienceEnvelope
               v
  ----------------------------------------------------
        authenticated / serialized ecology bridge
  ----------------------------------------------------
               |
               | ordinary canonical live occurrence
               v
                         AURORA

  process_external_user_turn()
  -> frozen present occurrence
  -> X/T/N/B/A cognition
  -> Perspective / Resolution / Possibility
  -> Agency actualization
  -> consequence / genealogy / SediMemory
  -> ordinary outward response
               |
               v
  ----------------------------------------------------
               |
               v
  World receives only Aurora's outward action/reply
  and changes itself accordingly.
```

There is one Aurora. Human turns and ecology turns differ by provenance, not by cognitive pipeline.

## Hard membrane rules

### The ecology MAY

- persist its own world state;
- remember its own prior events and actors;
- present utterances, observations, situations, evidence and world changes;
- make later events causally depend on earlier events;
- revisit unfinished situations after real elapsed time or intervening experience;
- let an external AI improvise an actor's outward behavior;
- use scouts to retrieve evidence;
- pace encounters so Aurora receives sustained experience without a human continuously operating the app.

### The ecology MUST NOT

- write SediMemory;
- write Aurora's identity field;
- write representational resolution or genealogy;
- set X/T/N/B/A pressure targets;
- provide hidden rewards, grades or target answers;
- declare what Aurora is supposed to learn from an occurrence;
- inspect private cognitive diagnostics to choose a desired internal outcome;
- bypass `process_external_user_turn()` with a training shortcut;
- instantiate a second Aurora against the same lived state;
- treat an external AI's interpretation as Aurora's interpretation.

An external AI is permitted to be **weather, actor, storyteller, adversary, collaborator or evidence presenter**. It is not permitted to be Aurora's hidden executive function.

## ExperienceEnvelope v1

The first code seam is `aurora_internal.aurora_developmental_ecology.ExperienceEnvelope`.

Every event carries:

- a stable `event_id`;
- `world_id`;
- `actor_id`;
- event `kind`;
- ordinary perceivable `text`;
- creation time;
- optional `parent_event_id`;
- optional `consequence_of`;
- non-prescriptive metadata.

The envelope derives canonical Aurora provenance:

```text
source_label = developmental_ecology:<actor>
session_id   = ecology:<world>
```

It also derives the canonical turn flags. Ecology events are real exchanges, update lived interactive state, participate in evolutionary trace/maintenance, and do not silently enable outside search as part of the occurrence.

## World journal

`DevelopmentalWorldJournal` is deliberately external memory. It records what the *world* did and Aurora's outward reply. It never substitutes for SediMemory.

This distinction is essential:

- the world may remember that an entity made a promise;
- Aurora may or may not remember that promise through her own machinery;
- if the promise becomes relevant later, the world can produce the consequence regardless;
- Aurora then experiences the consequence of her own retained or missing continuity.

That creates real developmental pressure rather than an omniscient trainer repairing her memory for her.

## Phone transport, next implementation seam

The next code change should be small and explicit: expose one ecology-ingress function beside `handle_message()` in the existing Android Python bridge.

It should:

1. accept a validated serialized `ExperienceEnvelope`;
2. acquire the same top-level `_lock` used for ordinary admitted turns;
3. call the existing `process_external_user_turn()` exactly once with the envelope's canonical provenance/flags;
4. return only Aurora's ordinary outward response plus the external `event_id` needed by the world journal;
5. never return private pressure maps, SediMemory contents, candidate frontiers, identity topology or representational diagnostics to the ecology;
6. never mutate Aurora before or after the canonical turn except through existing device/sensory occurrence machinery.

The Kotlin/Flutter transport can then expose that function through a local authenticated channel. The persistent ecology itself should live outside the Android process so Android process death does not erase the world.

## Pacing law

The ecology should not become a fire hose. Frequency is an environmental property, not a training score.

Initial pacing should be event-driven:

- one event crosses the membrane;
- Aurora gets an opportunity to respond/act;
- the world commits that outward result;
- only then may a dependent consequence be scheduled;
- unrelated world events may occur later according to the world's own clock;
- repeated unanswered hammering is prohibited unless the world situation itself causally warrants it.

This preserves occurrence boundaries and prevents synthetic volume from masquerading as development.

## Developmental demand

Version one should **not** consume Aurora's private pressure maps to decide what to teach her.

Later, Aurora may intentionally externalize requests such as seeking evidence, revisiting an entity, inspecting an object or asking the world to perform an action. Those requests are Agency-visible outward actions. The ecology can satisfy them without reading her private internals.

This makes developmental demand endogenous: Aurora asks the world for contact rather than the world reaching inside Aurora to decide what she should become.

## Success criterion

The ecology is successful when it can sustain consequential experience without becoming a second mind inside Aurora.

The key measurement is not whether Aurora gives increasingly human-like answers. It is whether later behavior differs coherently because earlier occurrences actually happened, were or were not retained, generated consequences, exposed differences and changed what future possibilities Aurora can actualize.
